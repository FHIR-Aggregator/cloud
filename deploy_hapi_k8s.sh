#!/bin/bash

# Load environment variables from .env-k8s-sample
source .env-k8s-sample

# Check if required environment variables are set
: "${PROJECT_ID:?Need to set PROJECT_ID}"
: "${CLUSTER_NAME:?Need to set CLUSTER_NAME}"
: "${ZONE:?Need to set ZONE}"
: "${NAMESPACE:?Need to set NAMESPACE}"
: "${CLOUD_SQL_INSTANCE:?Need to set CLOUD_SQL_INSTANCE}"
: "${DATABASE_NAME:?Need to set DATABASE_NAME}"
: "${DATABASE_USER:?Need to set DATABASE_USER}"
: "${DATABASE_PASSWORD:?Need to set DATABASE_PASSWORD}"
: "${CHART_REPO:?Need to set CHART_REPO}"
: "${CHART_NAME:?Need to set CHART_NAME}"

# --- Functions ---

create_secret() {
  local secret_name="$1"
  local key="$2"
  local value="$3"
  kubectl create secret generic "$secret_name" --from-literal="$key=$value" -n "$NAMESPACE" || true
}

deploy_chart() {
  helm install "$CHART_NAME" "$CHART_REPO/$CHART_NAME" \
    -n "$NAMESPACE" \
    --set spring.datasource.url="jdbc:postgresql://${CLOUD_SQL_INSTANCE}:5432/${DATABASE_NAME}" \
    --set spring.datasource.username="${DATABASE_USER}" \
    --set spring.datasource.password=$(kubectl get secret cloud-sql-credentials -o jsonpath="{.data.password}" -n "$NAMESPACE" | base64 --decode)
}

# --- Main Script ---

# Create Kubernetes secrets for Cloud SQL credentials
create_secret cloud-sql-credentials password "${DATABASE_PASSWORD}"

# Deploy the Helm chart
deploy_chart

echo "Deployment complete. Check the pods' status using:"
echo "kubectl get pods -n $NAMESPACE"