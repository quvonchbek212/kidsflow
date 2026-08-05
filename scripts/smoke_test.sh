#!/usr/bin/env bash
#
# KIDSFLOW smoke test — deploydan keyin asosiy endpointlar ishlayotganini tekshiradi.
#
# Ishlatish:
#   BASE_URL=http://localhost:8000 ./scripts/smoke_test.sh
#
# Production muhitida interaktiv hujjatlar (/docs, /redoc, /openapi.json)
# ataylab o'chirilgan, shuning uchun ular 404 qaytaradi. Buni tekshirish uchun:
#   EXPECT_DOCS=disabled BASE_URL=https://domen.uz ./scripts/smoke_test.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="${BASE_URL}/api/v1"
fail=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "${actual}" == "${expected}" ]]; then
    echo "  OK   ${name} (${actual})"
  else
    echo "  FAIL ${name}: kutilgan ${expected}, olindi ${actual}" >&2
    fail=1
  fi
}

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

EXPECT_DOCS="${EXPECT_DOCS:-enabled}"
if [[ "${EXPECT_DOCS}" == "disabled" ]]; then
  docs_expected=404
else
  docs_expected=200
fi

echo "Smoke test: ${BASE_URL}"
check "health"        200 "$(code "${API}/health")"
check "readiness"     200 "$(code "${API}/health/ready")"
check "openapi"       "${docs_expected}" "$(code "${API}/openapi.json")"
check "docs"          "${docs_expected}" "$(code "${BASE_URL}/docs")"
# Autentifikatsiyasiz himoyalangan endpoint 401 qaytarishi kerak.
check "auth-guard"    401 "$(code "${API}/auth/me")"

if [[ "${fail}" -ne 0 ]]; then
  echo "SMOKE TEST MUVAFFAQIYATSIZ" >&2
  exit 1
fi
echo "Smoke test muvaffaqiyatli."
