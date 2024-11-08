from flask import Flask, request, jsonify
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input, decode_predictions
import numpy as np
from PIL import Image
import io
import base64
from kafka import KafkaConsumer, KafkaProducer
import json
import logging
import os
import requests
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)
model = ResNet50(weights='imagenet')

# Kafka configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka-service.kafka.svc.cluster.local:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'team21')
INFERENCE_RESULT_TOPIC = os.getenv('INFERENCE_RESULT_TOPIC', 'inference_result')

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def process_image(image_base64):
    try:
        logging.debug(f"Received image data. Length: {len(image_base64)}")
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        image = image.resize((224, 224))  # ResNet50 input size
        image_array = np.array(image)
        image_array = np.expand_dims(image_array, axis=0)
        return preprocess_input(image_array)
    except Exception as e:
        logging.error(f"Error in process_image: {str(e)}")
        raise

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        unique_id = data.get('unique_id') or data.get('image_id')
        image_data = data['image']
        
        if not unique_id:
            raise ValueError("Missing 'unique_id' or 'image_id' in request data")
        
        logging.debug(f"Processing request for image {unique_id}")
        
        processed_image = process_image(image_data)
        predictions = model.predict(processed_image)
        decoded_predictions = decode_predictions(predictions, top=1)[0]
        
        inferred_value = decoded_predictions[0][1]
        
        kafka_message = {
            'unique_id': unique_id,
            'inferred_value': inferred_value
        }
        
        # Send to both topics
        producer.send(KAFKA_TOPIC, kafka_message)
        producer.send(INFERENCE_RESULT_TOPIC, kafka_message)
        
        logging.info(f"Processed image {unique_id}. Inferred value: {inferred_value}")
        
        return jsonify(kafka_message)
    except Exception as e:
        logging.error(f"Error in predict: {str(e)}")
        return jsonify({'error': str(e)}), 500

class InferenceConsumer:
    def __init__(self, topic_name, bootstrap_servers, max_retries=3, retry_delay=5):
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def process_messages(self):
        for message in self.consumer:
            data = message.value
            if 'image' in data and 'unique_id' in data:
                image_id = data['unique_id']
                image_data = data['image']
                self.process_image(image_id, image_data)

    def process_image(self, image_id, image_data):
        logging.debug(f"Received image data for ID {image_id}. First 100 chars: {image_data[:100]}")
        
        for attempt in range(self.max_retries):
            try:
                payload = {'unique_id': image_id, 'image': image_data}
                response = requests.post(
                    f'http://127.0.0.1:5000/predict', 
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                inferred_value = result.get('inferred_value')
                logging.info(f"Processed image {image_id} successfully")
                logging.info(f"Inferred value: {inferred_value}")

                # Send result back to Kafka
                producer.send(INFERENCE_RESULT_TOPIC, {
                    'unique_id': image_id,
                    'inferred_value': inferred_value
                })
                return
            
            except requests.exceptions.RequestException as e:
                logging.error(f"Attempt {attempt + 1} failed for image {image_id}: {str(e)}")
                if attempt < self.max_retries - 1:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logging.error(f"Failed to process image {image_id} after {self.max_retries} attempts")

    def close(self):
        self.consumer.close()

if __name__ == "__main__":
    # Start the inference consumer in a separate thread
    topic_name = 'team21'
    bootstrap_servers = [KAFKA_BROKER]
    
    consumer = InferenceConsumer(topic_name, bootstrap_servers)
    
    # Start the Flask app in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
    flask_thread.start()
    
    try:
        logging.info("Starting the inference consumer...")
        consumer.process_messages()
    except KeyboardInterrupt:
        logging.info("Stopping the consumer...")
    finally:
        consumer.close()
