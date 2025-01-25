FROM python:3.11-slim


ENV PYTHONPATH=/app \
    FLASK_ENV=production


# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY . /app

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port nécessaire
EXPOSE 9090

# Lancer les services Nginx et Gunicorn
CMD ["bash", "./run.sh" "--prod"]

