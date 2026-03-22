#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLY_TOML="${ROOT_DIR}/fly.toml"
OUTPUT_FILE="${ROOT_DIR}/backend/.env.fly"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "flyctl is required but not installed." >&2
  exit 1
fi

if ! flyctl auth whoami >/dev/null 2>&1; then
  echo "flyctl is not authenticated. Run: flyctl auth login" >&2
  exit 1
fi

if [[ ! -f "${FLY_TOML}" ]]; then
  echo "Missing fly.toml at ${FLY_TOML}" >&2
  exit 1
fi

APP_NAME="${FLY_APP_NAME:-$(awk -F"'" '/^app = / {print $2}' "${FLY_TOML}")}"
if [[ -z "${APP_NAME}" ]]; then
  echo "Could not determine Fly app name from fly.toml" >&2
  exit 1
fi

DEFAULT_KEYS=(
  "ANTHROPIC_API_KEY"
  "OPENROUTER_API_KEY"
  "FISH_API_KEY"
)

if [[ "$#" -gt 0 ]]; then
  KEYS=("$@")
else
  KEYS=("${DEFAULT_KEYS[@]}")
fi

MACHINE_ROW="$(
  flyctl machine list -a "${APP_NAME}" \
    | awk '
      $1 ~ /^[0-9a-f]{14,}$/ && $3 == "started" { print $1 "\t" $3; found=1; exit }
      $1 ~ /^[0-9a-f]{14,}$/ && first == "" { first=$1 "\t" $3 }
      END { if (!found && first != "") print first }
    '
)"

if [[ -z "${MACHINE_ROW}" ]]; then
  echo "No Fly machines found for app ${APP_NAME}" >&2
  exit 1
fi

IFS=$'\t' read -r MACHINE_ID MACHINE_STATE <<<"${MACHINE_ROW}"

STARTED_BY_SCRIPT=0
if [[ "${MACHINE_STATE}" != "started" ]]; then
  echo "Starting Fly machine ${MACHINE_ID} for ${APP_NAME}..." >&2
  flyctl machine start "${MACHINE_ID}" -a "${APP_NAME}" >/dev/null
  STARTED_BY_SCRIPT=1
fi

cleanup() {
  if [[ "${STARTED_BY_SCRIPT}" -eq 1 ]]; then
    flyctl machine stop "${MACHINE_ID}" -a "${APP_NAME}" >/dev/null || true
  fi
}
trap cleanup EXIT

REMOTE_COMMAND='sh -lc '"'"'
for key in "$@"; do
  value="$(printenv "$key" || true)"
  if [ -n "$value" ]; then
    printf "%s=%s\n" "$key" "$value"
  fi
done
'"'"' --'
for key in "${KEYS[@]}"; do
  REMOTE_COMMAND+=" ${key}"
done

TMP_OUTPUT="$(mktemp)"
flyctl ssh console -a "${APP_NAME}" --machine "${MACHINE_ID}" -C "${REMOTE_COMMAND}" \
  | awk '/^[A-Z0-9_]+=/{print}' > "${TMP_OUTPUT}"

if [[ ! -s "${TMP_OUTPUT}" ]]; then
  rm -f "${TMP_OUTPUT}"
  echo "No secrets were returned from Fly machine ${MACHINE_ID}" >&2
  exit 1
fi

mv "${TMP_OUTPUT}" "${OUTPUT_FILE}"
chmod 600 "${OUTPUT_FILE}"

echo "Wrote $(wc -l < "${OUTPUT_FILE}" | tr -d ' ') secret(s) to ${OUTPUT_FILE}"
echo "Loaded keys:"
cut -d= -f1 "${OUTPUT_FILE}"
