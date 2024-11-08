FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

RUN pip install kafka-python psycopg2-binary

COPY db_service.py .

CMD ["python", "db_service.py"]
