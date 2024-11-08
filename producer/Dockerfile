FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages directly
RUN pip install kafka-python \
    pillow \
    tensorflow \
    numpy \
    pandas \
    matplotlib

# Copy application code
COPY producer.py ./producer.py

# Add script to download dataset and run producer
RUN echo '#!/bin/bash\n\
# Download CIFAR dataset by importing tensorflow\n\
python3 -c "import tensorflow as tf; tf.keras.datasets.cifar100.load_data()"\n\
# Run the producer\n\
python3 producer.py' > /app/start.sh

# Make script executable
RUN chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"]
