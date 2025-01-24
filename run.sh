#!/bin/bash

# Check the environment variable FLASK_ENV
if [ "$FLASK_ENV" == "development" ]; then
    echo "Running in development mode..."
    export PYTHONPATH=$(pwd)    
    flask run --host=127.0.0.1 --port=5000
else
    echo "Running in production mode..."
    gunicorn --bind 0.0.0.0:9090 --workers 4 --threads 2 online_schedule_checker:app
fi

