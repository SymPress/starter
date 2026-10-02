#!/usr/bin/env bash
set +x
set -euo pipefail

ping_url="${CANARY_HEARTBEAT_URL:-}"
unset CANARY_HEARTBEAT_URL
if [[ ! "$ping_url" =~ ^https://hc-ping\.com/[[:xdigit:]]{8}-[[:xdigit:]]{4}-[[:xdigit:]]{4}-[[:xdigit:]]{4}-[[:xdigit:]]{12}$ ]]; then
  echo "::error::Configure CANARY_HEARTBEAT_URL with the dedicated HTTPS check URL." >&2
  exit 1
fi

case "${CANARY_RESULT:-}" in
  success) failed=false ;;
  failure|cancelled|skipped)
    ping_url="$ping_url/fail"
    failed=true
    ;;
  *)
    echo "::error::The update canary result is missing or invalid." >&2
    exit 1
    ;;
esac

# The validated URL goes through stdin, never through curl's command-line arguments.
# Do not load curlrc, follow redirects, send logs or expose the check URL.
if ! http_status="$(printf 'url = "%s"\n' "$ping_url" |
  curl --disable --fail --silent --show-error --proto '=https' --tlsv1.2 \
    --request POST --max-time 10 --retry 2 --retry-delay 2 --retry-max-time 30 \
    --output /dev/null --write-out '%{http_code}' --config -)"; then
  echo "::error::External canary heartbeat delivery failed." >&2
  exit 1
fi
if [[ ! "$http_status" =~ ^2[0-9]{2}$ ]]; then
  echo "::error::External canary heartbeat was not accepted." >&2
  exit 1
fi
if [[ "$failed" == true ]]; then
  echo "::error::The update canary did not complete successfully." >&2
  exit 1
fi
