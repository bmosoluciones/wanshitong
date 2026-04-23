FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    UPLOADS_ROOT=/data/uploads

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY app.py ./app.py
COPY babel.cfg ./babel.cfg

RUN mkdir -p /data/uploads

VOLUME ["/data/uploads"]

EXPOSE 8080

CMD ["python", "app.py"]