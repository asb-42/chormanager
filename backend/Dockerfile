FROM python:3.12-slim

WORKDIR /srv/app/backend
ENV PYTHONPATH=/srv/app/backend:/srv/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /srv/app/backend/requirements.txt
RUN pip install --no-cache-dir -r /srv/app/backend/requirements.txt

COPY backend /srv/app/backend
COPY chormanager /srv/app/chormanager
COPY config /srv/app/config

EXPOSE 8000
ENTRYPOINT ["/srv/app/backend/docker-entrypoint.sh"]
