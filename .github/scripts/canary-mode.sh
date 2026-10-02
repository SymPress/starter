#!/usr/bin/env bash
set -euo pipefail

case "${GITHUB_EVENT_NAME:-}" in
  schedule)
    printf '%s\n' update
    ;;
  workflow_dispatch)
    if [[ ! -f "${GITHUB_EVENT_PATH:-}" ]]; then
      echo "::error::Manual canary event data is missing." >&2
      exit 1
    fi
    if ! mode="$(jq -ser '
      if length != 1 or (.[0] | type) != "object" then
        error("expected one event object")
      else .[0] end
      | if (.inputs | type) != "object" then
          error("expected the event inputs object")
        else .inputs end
      | (if has("update_dependencies") then .update_dependencies else false end) as $requested
      | if $requested == true or $requested == "true" then "update"
        elif $requested == false or $requested == "false" then "locked"
        else error("update_dependencies must be a boolean") end
    ' "$GITHUB_EVENT_PATH" 2>/dev/null)"; then
      echo "::error::Manual canary update selection is invalid." >&2
      exit 1
    fi
    case "$mode" in
      update|locked) printf '%s\n' "$mode" ;;
      *)
        echo "::error::Manual canary mode is invalid." >&2
        exit 1
        ;;
    esac
    ;;
  push|pull_request)
    printf '%s\n' locked
    ;;
  *)
    echo "::error::Unsupported canary event." >&2
    exit 1
    ;;
esac
