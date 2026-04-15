#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
  set -- python app.py
fi

IDLE_ENABLED="${PANEL_IDLE_SHUTDOWN_ENABLED:-false}"
IDLE_TIMEOUT_SECONDS="${PANEL_IDLE_TIMEOUT_SECONDS:-10800}"
IDLE_CHECK_INTERVAL_SECONDS="${PANEL_IDLE_CHECK_INTERVAL_SECONDS:-60}"
ACTIVITY_FILE="${PANEL_IDLE_ACTIVITY_FILE:-/tmp/canvas-bulk-panel.last-activity}"
IDLE_SENTINEL_FILE="${ACTIVITY_FILE}.idle-stop"

mkdir -p "$(dirname "$ACTIVITY_FILE")"
date +%s > "$ACTIVITY_FILE"
rm -f "$IDLE_SENTINEL_FILE"

normalize_bool() {
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  [ "$value" = "1" ] || [ "$value" = "true" ] || [ "$value" = "yes" ] || [ "$value" = "on" ]
}

cleanup() {
  if [ "${WATCHDOG_PID:-}" ] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then
    kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
    wait "$WATCHDOG_PID" 2>/dev/null || true
  fi
  if [ "${APP_PID:-}" ] && kill -0 "$APP_PID" 2>/dev/null; then
    kill -TERM "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM

"$@" &
APP_PID=$!
WATCHDOG_PID=""

if normalize_bool "$IDLE_ENABLED"; then
  (
    while kill -0 "$APP_PID" 2>/dev/null; do
      now="$(date +%s)"
      last_activity="$(cat "$ACTIVITY_FILE" 2>/dev/null || printf '%s' "$now")"
      case "$last_activity" in
        ''|*[!0-9]*)
          last_activity="$now"
          ;;
      esac

      if [ "$last_activity" -gt 9999999999 ]; then
        last_activity=$((last_activity / 1000000000))
      fi

      if [ "$last_activity" -gt "$now" ]; then
        last_activity="$now"
      fi

      if [ $((now - last_activity)) -ge "$IDLE_TIMEOUT_SECONDS" ]; then
        echo "[idle-shutdown] Encerrando container por $IDLE_TIMEOUT_SECONDS segundos sem uso."
        date +%s > "$IDLE_SENTINEL_FILE"
        kill -TERM "$APP_PID" 2>/dev/null || true
        break
      fi

      sleep "$IDLE_CHECK_INTERVAL_SECONDS"
    done
  ) &
  WATCHDOG_PID=$!
fi

APP_STATUS=0
if ! wait "$APP_PID"; then
  APP_STATUS=$?
fi

if [ "$WATCHDOG_PID" ] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then
  kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
  wait "$WATCHDOG_PID" 2>/dev/null || true
fi

if [ -f "$IDLE_SENTINEL_FILE" ]; then
  rm -f "$IDLE_SENTINEL_FILE"
  exit 0
fi

exit "$APP_STATUS"
