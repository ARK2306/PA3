from kafka import KafkaConsumer
import json
import psycopg2
import base64
import logging
import os
import time
from datetime import datetime
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka-service.kafka.svc.cluster.local:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'team21')
INFERENCE_TOPIC = os.getenv('INFERENCE_TOPIC', 'inference_result')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres-service')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'team21_data')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'team21user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'team21')

def get_db_connection():
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST
    )

def print_stats(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN inferred_value IS NOT NULL THEN 1 END) as processed,
                    COUNT(CASE WHEN inferred_value IS NULL THEN 1 END) as pending
                FROM iot_image_data
            """)
            total, processed, pending = cur.fetchone()
            logging.info(f"Stats - Total: {total}, Processed: {processed}, Pending: {pending}")
    except Exception as e:
        logging.error(f"Error getting stats: {str(e)}")

def stats_loop():
    conn = get_db_connection()
    try:
        while True:
            print_stats(conn)
            time.sleep(10)
    finally:
        conn.close()

def process_message(cur, message, message_type='original'):
    try:
        data = json.loads(message.value.decode('utf-8'))
        
        if message_type == 'original':
            unique_id = str(data['unique_id'])
            ground_truth = int(data['ground_truth'])
            image_data = base64.b64decode(data['image'])
            
            cur.execute("""
                INSERT INTO iot_image_data (unique_id, ground_truth, data)
                VALUES (%s, %s, %s)
                ON CONFLICT (unique_id) 
                DO UPDATE SET
                    ground_truth = EXCLUDED.ground_truth,
                    data = EXCLUDED.data
                RETURNING unique_id
            """, (unique_id, ground_truth, psycopg2.Binary(image_data)))
            
        else:  # inference
            unique_id = str(data['unique_id'])
            inferred_value = str(data['inferred_value'])
            
            cur.execute("""
                UPDATE iot_image_data
                SET inferred_value = %s
                WHERE unique_id = %s
                RETURNING unique_id
            """, (inferred_value, unique_id))
        
        result = cur.fetchone()
        if result:
            logging.info(f"Successfully processed {message_type} message for {result[0]}")
            return True
        return False
    
    except Exception as e:
        logging.error(f"Error processing {message_type} message: {str(e)}")
        return False

def consume_messages():
    while True:
        try:
            # Create consumers
            original_consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[KAFKA_BROKER],
                group_id='db_service_original_v5',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            inference_consumer = KafkaConsumer(
                INFERENCE_TOPIC,
                bootstrap_servers=[KAFKA_BROKER],
                group_id='db_service_inference_v5',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            conn = get_db_connection()
            logging.info("Connected to database and Kafka")
            
            while True:
                # Poll messages from both topics
                original_messages = original_consumer.poll(timeout_ms=100)
                inference_messages = inference_consumer.poll(timeout_ms=100)
                
                for partition_messages in original_messages.values():
                    for message in partition_messages:
                        with conn.cursor() as cur:
                            if process_message(cur, message, 'original'):
                                conn.commit()
                            else:
                                conn.rollback()
                
                for partition_messages in inference_messages.values():
                    for message in partition_messages:
                        with conn.cursor() as cur:
                            if process_message(cur, message, 'inference'):
                                conn.commit()
                            else:
                                conn.rollback()
                
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
                
        except Exception as e:
            logging.error(f"Consumer error: {str(e)}")
            time.sleep(5)
            continue
        
        finally:
            try:
                if 'conn' in locals() and conn:
                    conn.close()
                if 'original_consumer' in locals() and original_consumer:
                    original_consumer.close()
                if 'inference_consumer' in locals() and inference_consumer:
                    inference_consumer.close()
            except Exception as e:
                logging.error(f"Error during cleanup: {str(e)}")

def main():
    # Start stats thread
    stats_thread = threading.Thread(target=stats_loop, daemon=True)
    stats_thread.start()
    
    try:
        consume_messages()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
