import os
import psycopg2
from kafka import KafkaConsumer
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Kafka configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka-service.kafka.svc.cluster.local:9092')  # Use the Kafka service name
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'inference_result')

# Database configuration
DB_NAME = os.getenv("DB_NAME", "team21_data")
DB_USER = os.getenv("DB_USER", "team21user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "team21")
DB_HOST = os.getenv("DB_HOST", "postgres-service")  # Use the PostgreSQL service name

def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        return conn
    except psycopg2.Error as e:
        logging.error(f"Unable to connect to the database: {e}")
        return None



def update_inference_result(conn, unique_id, inferred_value):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE iot_image_data
                SET inferred_value = %s
                WHERE unique_id = %s
            """, (inferred_value, unique_id))
            conn.commit()
            logging.info(f"Updated inference result for image {unique_id}")
    except psycopg2.Error as e:
        logging.error(f"Error updating inference result: {e}")
        conn.rollback()

def main():
    conn = connect_to_db()
    if not conn:
        return

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    try:
        for message in consumer:
            data = message.value
            unique_id = data.get('unique_id')
            inferred_value = data.get('inferred_value')
            
            if unique_id and inferred_value:
                update_inference_result(conn, unique_id, inferred_value)
            else:
                logging.warning(f"Received incomplete data: {data}")
    except KeyboardInterrupt:
        logging.info("Stopping the consumer...")
    finally:
        consumer.close()
        conn.close()

if __name__ == "__main__":
    main()
