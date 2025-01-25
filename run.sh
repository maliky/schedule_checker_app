#!/bin/bash

printusage() {
    prog=$(basename "$0")
    echo "lance l'application en mode dev ou prod"
    echo "Usage: $prog arg"  >&2
    echo "arg1: -d --dev  -p --prod: Option qui définie l'environement d'execution de l'application"
    echo "" >&2
    echo "Options:" >&2
    echo " -h or --help	  Print this messages" >&2
}

#### Run section

# print.cmd.helper
if [[ -z "$1" ]] || [[ "$1" == '-h' ]]  || [[ "$1" == '--help' ]];
then  # -z if for empty
    printusage
    exit 1
fi

# Check the environment variable FLASK_ENV
if [[ "$1" == "-d" ]] || [[ "$1" == "--dev" ]]; then
    echo "Running in development mode..."
    export PYTHONPATH=$(pwd)    
    flask run --host=127.0.0.1 --port=5000
elif [[ "$1" == "-p" ]] || [[ "$1" == "--prod" ]]; then
    echo "Running in production mode..."
    gunicorn --bind 0.0.0.0:9090 --workers 4 --threads 2 online_schedule_checker:app
fi

