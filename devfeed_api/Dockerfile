# Backend image for the DevFeed Django REST API.
# Build context is devfeed_api/ (the folder with manage.py and requirements.txt).
# Settings come from environment variables passed in at run time
# (docker-compose.yml reads them from .env); .env is never copied into the image.

# Same Python minor version as the local venv (3.14), slim Debian base
FROM python:3.14-slim

# No .pyc files in the image; print logs immediately instead of buffering them
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, in their own layer, so code-only changes
# reuse the cached install instead of reinstalling every package
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code (.dockerignore keeps local files out)
COPY . .

# Run as an unprivileged user instead of root
RUN useradd --create-home --shell /usr/sbin/nologin devfeed_user
USER devfeed_user

# Gunicorn listens on this port inside the container
EXPOSE 8000

# Serve the WSGI app with Gunicorn: 3 worker processes, request log to stdout
CMD ["gunicorn", "devfeed_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
