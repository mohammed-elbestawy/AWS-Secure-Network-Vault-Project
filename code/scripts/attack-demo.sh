#!/usr/bin/env bash
# Probes your OWN deployment with common attack patterns and prints the status
# codes. Run it only against infrastructure you own.
# Usage: bash attack-demo.sh https://<cloudfront-domain>
set -uo pipefail

BASE="${1:?usage: attack-demo.sh https://your-domain}"
BLOB="$(python3 -c 'print("A"*64)')"

row() { printf '%-46s %s\n' "$1" "$2"; }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$@"; }

echo "Target: $BASE"
echo
row "Probe" "HTTP status"
row "----------------------------------------------" "-----------"

row "SQL injection in secret id" "$(code -X POST "$BASE/api/secrets/%27%20OR%201%3D1--/reveal")"
row "SQL injection in JSON ciphertext" "$(code -X POST "$BASE/api/secrets" -H 'Content-Type: application/json' -d "{\"ciphertext\":\"' OR '1'='1\",\"ttl\":3600}")"
row "XSS payload in query string" "$(code "$BASE/api/health?q=%3Cscript%3Ealert(1)%3C/script%3E")"
row "Path traversal" "$(code --path-as-is "$BASE/../../etc/passwd")"
row "Oversized body (64 KB)" "$(python3 -c 'print("x"*65536)' | code -X POST "$BASE/api/secrets" -H 'Content-Type: application/json' --data-binary @-)"
row "Wrong content type" "$(code -X POST "$BASE/api/secrets" -H 'Content-Type: text/plain' -d 'x')"
row "Valid request (control)" "$(code -X POST "$BASE/api/secrets" -H 'Content-Type: application/json' -d "{\"ciphertext\":\"$BLOB\",\"ttl\":3600,\"max_views\":1}")"

echo
echo "Guessing secret ids: 300 random lookups"
declare -A SEEN
for _ in $(seq 1 300); do
  RID="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  S="$(code "$BASE/api/secrets/$RID/status")"
  SEEN[$S]=$(( ${SEEN[$S]:-0} + 1 ))
done
for S in "${!SEEN[@]}"; do row "status $S" "${SEEN[$S]} responses"; done
echo
echo "404 for every guess means the app never confirms an id. 403 or 429 means the WAF rate limit stepped in."
