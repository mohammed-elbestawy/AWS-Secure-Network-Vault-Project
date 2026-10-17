"""Zero-knowledge secret vault: HTTP API.

The browser encrypts the secret with AES-256-GCM and keeps the key in the URL
fragment, which is never sent to a server. This API only stores and returns
opaque ciphertext, and destroys it once it has been read.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
import uuid
from datetime import timedelta
from logging.handlers import RotatingFileHandler

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from store import MemoryStore, utcnow
from validation import ValidationError, is_valid_id, validate_create

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

_ID_IN_PATH = re.compile(r"/api/secrets/([A-Za-z0-9_-]{6})[A-Za-z0-9_-]*")


def _mask(path: str) -> str:
    """Keep log lines useful without writing full secret IDs to disk."""
    return _ID_IN_PATH.sub(r"/api/secrets/\1...", path)


def _configure_logging(app, log_file=""):
    handler = (
        RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
        if log_file
        else logging.StreamHandler()
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def create_app(store=None, config=None, frontend_dir=None, clock=utcnow):
    config = config or {}
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    app.json.sort_keys = False
    _configure_logging(app, config.get("LOG_FILE", ""))

    app.extensions["vault_store"] = store if store is not None else MemoryStore()
    default_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
    frontend_dir = os.path.abspath(
        frontend_dir or config.get("FRONTEND_DIR") or default_frontend
    )

    def vault():
        return app.extensions["vault_store"]

    @app.before_request
    def _start():
        g.t0 = time.perf_counter()
        g.rid = uuid.uuid4().hex[:12]

    @app.after_request
    def _finish(resp):
        for key, value in SECURITY_HEADERS.items():
            resp.headers.setdefault(key, value)
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        else:
            resp.headers.setdefault("Cache-Control", "public, max-age=300")
        resp.headers["X-Request-Id"] = getattr(g, "rid", "-")
        elapsed = time.perf_counter() - getattr(g, "t0", time.perf_counter())
        app.logger.info(
            json.dumps(
                {
                    "ts": clock().isoformat() + "Z",
                    "rid": getattr(g, "rid", "-"),
                    "method": request.method,
                    "path": _mask(request.path),
                    "status": resp.status_code,
                    "ms": round(elapsed * 1000, 1),
                }
            )
        )
        return resp

    def error(code, status):
        return jsonify({"error": code}), status

    @app.errorhandler(HTTPException)
    def _http_error(exc):
        mapping = {
            400: "bad_request",
            404: "not_found",
            405: "method_not_allowed",
            413: "payload_too_large",
            415: "unsupported_media_type",
        }
        return error(mapping.get(exc.code, "error"), exc.code)

    @app.errorhandler(Exception)
    def _unhandled(exc):
        app.logger.error(
            json.dumps(
                {
                    "rid": getattr(g, "rid", "-"),
                    "event": "unhandled",
                    "type": type(exc).__name__,
                }
            )
        )
        return error("internal_error", 500)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.get("/api/health")
    def api_health():
        try:
            vault().ping()
        except Exception:
            return error("database_unavailable", 503)
        return jsonify({"status": "ok", "database": "ok"})

    @app.post("/api/secrets")
    def create_secret():
        if not request.is_json:
            return error("unsupported_media_type", 415)
        try:
            ciphertext, ttl, max_views = validate_create(request.get_json(silent=True))
        except ValidationError as exc:
            return error(exc.code, 400)
        id_ = secrets.token_urlsafe(24)
        expires_at = clock() + timedelta(seconds=ttl)
        vault().create(id_, ciphertext, expires_at, max_views)
        return jsonify({"id": id_, "expires_at": expires_at.isoformat() + "Z"}), 201

    @app.get("/api/secrets/<id_>/status")
    def secret_status(id_):
        if not is_valid_id(id_):
            return error("not_found", 404)
        info = vault().peek(id_, clock())
        if info is None:
            return error("not_found", 404)
        return jsonify(
            {
                "exists": True,
                "expires_at": info["expires_at"].isoformat() + "Z",
                "remaining_views": info["remaining_views"],
            }
        )

    @app.post("/api/secrets/<id_>/reveal")
    def secret_reveal(id_):
        if not is_valid_id(id_):
            return error("not_found", 404)
        result = vault().reveal(id_, clock())
        if result is None:
            return error("not_found", 404)
        ciphertext, remaining = result
        return jsonify({"ciphertext": ciphertext, "remaining_views": remaining})

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        if filename.startswith("api/"):
            return error("not_found", 404)
        return send_from_directory(frontend_dir, filename)

    return app
