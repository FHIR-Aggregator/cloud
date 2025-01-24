#!/bin/bash

# https://bertvv.github.io/cheat-sheets/Bash.html#writing-robust-scripts-and-debugging
set -euo pipefail


# Check if required environment variables are set
# See .env-k8s-sample
: "${CLOUD_SQL_INSTANCE:?Need to set CLOUD_SQL_INSTANCE}"
: "${DATABASE_NAME:?Need to set DATABASE_NAME}"
: "${DATABASE_PASSWORD:?Need to set DATABASE_PASSWORD}"
: "${DATABASE_TIER:?Need to set DATABASE_TIER}"
: "${DATABASE_VERSION:?Need to set DATABASE_VERSION}"

Possibility of only logging in if user is not already authenticated (avoids browser opening every debugging run)?

# 1. Authentication (if necessary)
# Skip logging in if user is already authenticated
# ref: https://stackoverflow.com/a/78138012/7656815
if gcloud projects list &> /dev/null; then
    echo "User is authenticated with gdcloud"
else
    echo "Logging in with gcould auth application-default login..."
    gcloud auth application-default login
fi

# 2. Create Cloud SQL instance
gcloud sql instances create ${CLOUD_SQL_INSTANCE} \
  --database-version=${DATABASE_VERSION} \
  --region=us-central1 \
  --tier=${DATABASE_TIER} \
  --activation-policy=ALWAYS \
  --database-flags="cloudsql.iam_authentication=on" #Consider Private IP for better security

# 3. Create a database within the instance
gcloud sql databases create ${DATABASE_NAME} --instance=${CLOUD_SQL_INSTANCE}

# 4. Create a user
gcloud sql users create hapi_user --instance=${CLOUD_SQL_INSTANCE} --password=${DATABASE_PASSWORD}

# 5. Connect to the instance and grant privileges
gcloud sql connect ${CLOUD_SQL_INSTANCE} --user=postgres <<EOF
GRANT ALL PRIVILEGES ON DATABASE ${DATABASE_NAME} TO hapi_user;
EOF

# 6. Check instance status
gcloud sql instances describe ${CLOUD_SQL_INSTANCE}
