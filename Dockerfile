FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/default-java \
    PATH="${JAVA_HOME}/bin:${PATH}"

# PySpark requires a local JVM for the offline ETL workflow. Use the distro default
# JRE so the package name stays valid across Debian/Ubuntu builders.
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 --worker-class gthread --threads 4 app:app"]
