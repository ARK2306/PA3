   FROM python:3.8-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender-dev \
       && rm -rf /var/lib/apt/lists/*

   # Install Python packages
   RUN pip install flask tensorflow pillow numpy kafka-python requests

   # Copy application code
   COPY ml_service.py .

   # Expose the port
   EXPOSE 5000

   # Run the application
   CMD ["python3", "ml_service.py"]
