#!/bin/bash

# --- Configuration ---
# see .env-k8s-sample file
#PROJECT_ID="ncpi-rti-p01-007-ohsu"
#REGION="us-central1" # Choose your preferred region
#CLUSTER_NAME="my-hapi-fhir-cluster"
#NUM_NODES=3 # Adjust as needed


# --- Create GKE Cluster ---

gcloud container clusters create "${CLUSTER_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --cluster-autoscaling \
  --min-nodes=1 \
  --max-nodes="${NUM_NODES}"


# --- Check Cluster Status ---

echo "Checking cluster status..."
gcloud container clusters describe "${CLUSTER_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}"


echo "Cluster creation complete.  You can now connect to your cluster using:"
echo "gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID}"

