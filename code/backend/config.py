"""Runtime configuration.

In AWS the database settings live in SSM Parameter Store (SecureString for the
password) and are read through the SSM interface endpoint, so nothing sensitive
is written to disk or to the instance user data. Locally, plain environment
variables are used instead.
"""
from __future__ import annotations

import os


def _from_parameter_store(prefix: str, region: str) -> dict:
    import boto3  # imported lazily so tests and local runs do not need it

    client = boto3.client("ssm", region_name=region)
    values = {}
    paginator = client.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(Path=prefix, WithDecryption=True, Recursive=True):
        for item in page["Parameters"]:
            values[item["Name"].rsplit("/", 1)[-1]] = item["Value"]
    return values


def load_config(env=None) -> dict:
    env = os.environ if env is None else env
    cfg = {
        "STORE": env.get("STORE", "memory"),
        "REGION": env.get("AWS_REGION", env.get("AWS_DEFAULT_REGION", "eu-north-1")),
        "DB_PORT": int(env.get("DB_PORT", "3306")),
        "DB_NAME": env.get("DB_NAME", "appdb"),
        "DB_HOST": env.get("DB_HOST", ""),
        "DB_USER": env.get("DB_USER", ""),
        "DB_PASSWORD": env.get("DB_PASSWORD", ""),
        "DB_SSL_CA": env.get("DB_SSL_CA", ""),
        "LOG_FILE": env.get("LOG_FILE", ""),
        "FRONTEND_DIR": env.get("VAULT_FRONTEND_DIR", ""),
    }
    prefix = env.get("VAULT_SSM_PREFIX")
    if prefix:
        params = _from_parameter_store(prefix, cfg["REGION"])
        cfg["DB_HOST"] = params.get("host", cfg["DB_HOST"])
        cfg["DB_NAME"] = params.get("name", cfg["DB_NAME"])
        cfg["DB_USER"] = params.get("user", cfg["DB_USER"])
        cfg["DB_PASSWORD"] = params.get("password", cfg["DB_PASSWORD"])
        if "port" in params:
            cfg["DB_PORT"] = int(params["port"])
    return cfg


def mysql_connect_factory(cfg: dict):
    import pymysql  # imported lazily, only needed in production

    def connect():
        kwargs = dict(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
        if cfg.get("DB_SSL_CA"):
            kwargs.update(
                ssl_ca=cfg["DB_SSL_CA"], ssl_verify_cert=True, ssl_verify_identity=True
            )
        return pymysql.connect(**kwargs)

    return connect
