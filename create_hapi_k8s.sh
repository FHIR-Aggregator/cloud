#!/bin/bash

# https://bertvv.github.io/cheat-sheets/Bash.html#writing-robust-scripts-and-debugging
set -euo pipefail

# Check if required environment variables are set
# See .env-k8s-sample

# --- Configuration ---
# see .env-k8s-sample file
: "${PROJECT_ID:?Need to set PROJECT_ID}"
: "${REGION:?Need to set REGION}"
: "${CLUSTER_NAME:?Need to set CLUSTER_NAME}"
: "${NUM_NODES:?Need to set NUM_NODES}"


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

