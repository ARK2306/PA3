import threading
import time
from kafka import KafkaProducer, KafkaConsumer
import json
import base64
import numpy as np
from PIL import Image
import tensorflow as tf
import io
import csv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load CIFAR-100 dataset
(_, _), (x_test, y_test) = tf.keras.datasets.cifar100.load_data()

# Kafka configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka-service.kafka.svc.cluster.local:9092')
PUBLISH_TOPIC = os.getenv('PUBLISH_TOPIC', 'team21')
INFERENCE_TOPIC = os.getenv('INFERENCE_TOPIC', 'inference_result')

# Configuration
TOTAL_SAMPLES = int(os.getenv('TOTAL_SAMPLES', '1000'))
SAMPLE_FREQUENCY = float(os.getenv('SAMPLE_FREQUENCY', '1'))

class DistributedProducer:
    def __init__(self):
        self.producer_id = os.getenv('PRODUCER_ID', 'unknown')
        
        # Change results directory to root level
        self.results_dir = '/results'
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info(f"Producer {self.producer_id} initialized. Saving results to {self.results_dir}")
        
        self.producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            retries=5,
            retry_backoff_ms=1000
        )
        
        self.consumer = KafkaConsumer(
            INFERENCE_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id=f'producer_{self.producer_id}',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        self.sent_samples = {}
        self.lock = threading.Lock()
        self.sample_count = 0
        self.results = []
        self.is_running = True

    def produce_samples(self):
        logger.info(f"Producer {self.producer_id} starting to produce samples")
        while self.sample_count < TOTAL_SAMPLES:
            try:
                idx = np.random.randint(0, len(x_test))
                image = x_test[idx]
                label = y_test[idx][0]

                img = Image.fromarray(image)
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

                message_id = f"{self.producer_id}_{int(time.time() * 1000)}_{idx}"
                
                message = {
                    'unique_id': message_id,
                    'image': img_base64,
                    'ground_truth': int(label),
                    'producer_id': self.producer_id,
                    'timestamp': time.time()
                }

                self.producer.send(PUBLISH_TOPIC, json.dumps(message).encode('utf-8'))

                with self.lock:
                    self.sent_samples[message_id] = time.time()
                    self.sample_count += 1
                    
                if self.sample_count % 100 == 0:
                    logger.info(f"Producer {self.producer_id} has sent {self.sample_count} samples")

                time.sleep(SAMPLE_FREQUENCY)

            except Exception as e:
                logger.error(f"Error in producer {self.producer_id}: {str(e)}")
                time.sleep(1)

        self.is_running = False
        logger.info(f"Producer {self.producer_id} finished producing samples")

    def consume_results(self):
        logger.info(f"Consumer for producer {self.producer_id} starting")
        while self.is_running or self.sent_samples:
            try:
                messages = self.consumer.poll(timeout_ms=1000)
                
                for tp, msgs in messages.items():
                    for message in msgs:
                        result = message.value
                        message_id = result.get('unique_id')

                        with self.lock:
                            sent_time = self.sent_samples.pop(message_id, None)

                        if sent_time:
                            latency = time.time() - sent_time
                            self.results.append({
                                'message_id': message_id,
                                'latency': latency,
                                'producer_id': self.producer_id,
                                'timestamp': time.time()
                            })
                            # Save results periodically
                            if len(self.results) % 100 == 0:
                                self.save_results()

            except Exception as e:
                logger.error(f"Error in consumer {self.producer_id}: {str(e)}")
                time.sleep(1)

    def save_results(self):
        try:
            filename = os.path.join(self.results_dir, f'results_producer_{self.producer_id}.csv')
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['message_id', 'latency', 'producer_id', 'timestamp'])
                writer.writeheader()
                writer.writerows(self.results)
            
            logger.info(f"Producer {self.producer_id} saved {len(self.results)} results to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving results for producer {self.producer_id}: {str(e)}")

    def run(self):
        try:
            producer_thread = threading.Thread(target=self.produce_samples)
            consumer_thread = threading.Thread(target=self.consume_results)

            producer_thread.start()
            consumer_thread.start()

            producer_thread.join()
            consumer_thread.join()

            # Final save
            self.save_results()

        except Exception as e:
            logger.error(f"Error in producer {self.producer_id} main thread: {str(e)}")
            raise

if __name__ == "__main__":
    producer = DistributedProducer()
    producer.run()
