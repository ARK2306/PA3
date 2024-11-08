#!/bin/bash

# Base directory for results
RESULTS_DIR="/opt/producer-results"

# Clean up existing results
rm -rf ${RESULTS_DIR}/*
mkdir -p ${RESULTS_DIR}

# Run experiments for different numbers of producers
for num_producers in {1..5}
do
    echo "----------------------------------------"
    echo "Starting experiment with $num_producers producer(s)..."
    
    # Create experiment-specific directory
    mkdir -p "${RESULTS_DIR}/producers_${num_producers}"
    
    # Create and apply job directly
    kubectl apply -f - << EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: iot-producer-job-${num_producers}
  namespace: kafka
spec:
  completions: ${num_producers}
  parallelism: ${num_producers}
  backoffLimit: 4
  template:
    spec:
      containers:
      - name: producer
        image: 192.168.5.107:5000/iot-producer:latest
        env:
        - name: KAFKA_BROKER
          value: "kafka-service.kafka.svc.cluster.local:9092"
        - name: PUBLISH_TOPIC
          value: "team21"
        - name: INFERENCE_TOPIC
          value: "inference_result"
        - name: TOTAL_SAMPLES
          value: "1000"
        - name: SAMPLE_FREQUENCY
          value: "1"
        - name: PRODUCER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.uid
        volumeMounts:
        - name: results
          mountPath: /results
      volumes:
      - name: results
        hostPath:
          path: ${RESULTS_DIR}/producers_${num_producers}
          type: DirectoryOrCreate
      restartPolicy: Never
EOF
    
    # Wait for job completion
    echo "Waiting for $num_producers producer(s) to complete..."
    kubectl wait --for=condition=complete job/iot-producer-job-${num_producers} -n kafka --timeout=600s
    
    # Check job status
    if kubectl get job iot-producer-job-${num_producers} -n kafka -o jsonpath='{.status.succeeded}' | grep -q "${num_producers}"; then
        echo "✓ Job completed successfully with ${num_producers} producer(s)"
    else
        echo "⚠ Warning: Job may not have completed successfully"
        kubectl describe job iot-producer-job-${num_producers} -n kafka
    fi
    
    # Delete the job
    kubectl delete job iot-producer-job-${num_producers} -n kafka
    
    # Wait between runs to let system stabilize
    echo "Waiting 30 seconds before next experiment..."
    echo "----------------------------------------"
    sleep 30
done

echo "All experiments complete. Generating analysis plots..."
python3 analyze_results.py

echo "Experiments finished. Results are in ${RESULTS_DIR}"
