FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl netcat-openbsd && \
    pip install --no-cache-dir cassandra-driver==3.29.1 kafka-python==2.0.2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY init.sh .
RUN chmod +x init.sh

CMD ["./init.sh"]
