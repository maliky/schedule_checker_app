FROM python:3.11-slim

ENV FLASK_ENV=production


# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    nginx \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app
ENV PYTHONPATH=/app

# Copier les fichiers nécessaires
COPY . /app

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer les ports nécessaires
EXPOSE 80 443

# Lancer les services Nginx et Gunicorn
CMD ["uwsgi", "--ini", "conf/uwsgi.ini"]
