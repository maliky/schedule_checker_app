FROM python:3.11-slim


ENV PYTHONPATH=/app \
    FLASK_ENV=production


# Instal system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Define working dir
WORKDIR /app

# Copy the necessary files to the app in the containeur
COPY . /app

# install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# mke 9090 port visible from outside the container
EXPOSE 9090

# Launch the app in production mode with the lightweight gunicorn server (check the run.sh file)
CMD ["bash", "./run.sh", "--prod"]

