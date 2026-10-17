#!/usr/bin/env bash
# API smoke test. Usage: bash smoke-test.sh [base_url]   (default http://localhost)
# Uses a dummy ciphertext, so it only checks the server side of the flow.
set -uo pipefail

BASE="${1:-http://localhost}"
BLOB="$(python3 -c 'print("A"*64)')"
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    printf 'PASS  %-38s %s\n' "$name" "$actual"; PASS=$((PASS + 1))
  else
    printf 'FAIL  %-38s expected %s got %s\n' "$name" "$expected" "$actual"; FAIL=$((FAIL + 1))
  fi
}

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$@"; }

check "healthz" 200 "$(code "$BASE/healthz")"
check "api health (database)" 200 "$(code "$BASE/api/health")"

RESP="$(curl -s --max-time 8 -X POST "$BASE/api/secrets" -H 'Content-Type: application/json' \
  -d "{\"ciphertext\":\"$BLOB\",\"ttl\":3600,\"max_views\":1}")"
ID="$(printf '%s' "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)"
check "create returns 32 char id" 32 "${#ID}"

check "status does not burn" 200 "$(code "$BASE/api/secrets/$ID/status")"
check "status again" 200 "$(code "$BASE/api/secrets/$ID/status")"
check "first reveal" 200 "$(code -X POST "$BASE/api/secrets/$ID/reveal")"
check "second reveal is gone" 404 "$(code -X POST "$BASE/api/secrets/$ID/reveal")"
check "bad ttl rejected" 400 "$(code -X POST "$BASE/api/secrets" -H 'Content-Type: application/json' -d "{\"ciphertext\":\"$BLOB\",\"ttl\":5}")"
check "non-json rejected" 415 "$(code -X POST "$BASE/api/secrets" -H 'Content-Type: text/plain' -d 'x')"
check "malformed id looks like missing" 404 "$(code -X POST "$BASE/api/secrets/not-an-id/reveal")"

echo
echo "passed: $PASS  failed: $FAIL"
[[ $FAIL -eq 0 ]]
