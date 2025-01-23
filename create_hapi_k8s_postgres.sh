#!/bin/bash

# Load environment variables from .env-k8s-sample
source .env-k8s-sample

# Check if required environment variables are set
: "${CLOUD_SQL_INSTANCE:?Need to set CLOUD_SQL_INSTANCE}"
: "${DATABASE_NAME:?Need to set DATABASE_NAME}"
: "${DATABASE_PASSWORD:?Need to set DATABASE_PASSWORD}"

# 1. Authentication (if necessary)
gcloud auth application-default login

# 2. Create Cloud SQL instance
gcloud sql instances create ${CLOUD_SQL_INSTANCE} \
  --database-version=POSTGRES_14 \
  --region=us-central1 \
  --tier=db-n1-standard-1 \
  --activation-policy=ALWAYS \
  --database-flags="cloudsql.iam_authentication=on" #Consider Private IP for better security

# 3. Create a database within the instance
gcloud sql databases create ${DATABASE_NAME} --instance=${CLOUD_SQL_INSTANCE}

# 4. Connect to the instance and create a user (replace with your actual password)
gcloud sql connect ${CLOUD_SQL_INSTANCE} --user=postgres --execute="CREATE USER hapi_user WITH PASSWORD '${DATABASE_PASSWORD}'; GRANT ALL PRIVILEGES ON DATABASE ${DATABASE_NAME} TO hapi_user;"

# 5. Check instance status
gcloud sql instances describe ${CLOUD_SQL_INSTANCE}
