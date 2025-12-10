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

# printusage() {
#     prog=$(basename "$0")
#     echo "lance l'application en mode dev ou prod"
#     echo "Usage: $prog arg"  >&2
#     echo "arg1: -d --dev  -p --prod: Option qui définie l'environement d'execution de l'application"
#     echo "" >&2
#     echo "Options:" >&2
#     echo " -h or --help	  Print this messages" >&2
# }

# #### Run section

# # print.cmd.helper
# if [[ -z "$1" ]] || [[ "$1" == '-h' ]]  || [[ "$1" == '--help' ]];
# then  # -z if for empty
#     printusage
#     exit 1
# fi

# # Check the environment variable FLASK_ENV
# if [[ "$1" == "-d" ]] || [[ "$1" == "--dev" ]]; then
#     echo "Running in development mode..."
#     export PYTHONPATH=$(pwd)    
#     flask run --host=127.0.0.1 --port=5000
# elif [[ "$1" == "-p" ]] || [[ "$1" == "--prod" ]]; then
#     echo "Running in production mode..."
#     gunicorn --bind 0.0.0.0:9090 --workers 4 --threads 2 online_schedule_checker:app
# fi

