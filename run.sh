#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_MODULE="online_schedule_checker.py"
IMAGE_NAME="schedule_checker_app:latest"

usage() {
    echo "Usage: $0 <dev|prod>" >&2
    exit 1
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: $1 is required to run in $MODE mode" >&2
        exit 1
    fi
}

MODE="${1-}"

if [[ -z "$MODE" ]]; then
    usage
fi

case "$MODE" in
    dev)
        export FLASK_ENV=development
        export FLASK_APP="$APP_MODULE"
        export PYTHONPATH="$PROJECT_ROOT"
        cd "$PROJECT_ROOT"
        flask run
        ;;
    prod)
        require_command docker
        export PYTHONPATH="$PROJECT_ROOT"
        cd "$PROJECT_ROOT"
        docker build -t "$IMAGE_NAME" .
        docker run --rm -p 8080:8080 "$IMAGE_NAME"
        ;;
    *)
        usage
        ;;
esac
