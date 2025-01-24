#!/bin/bash

# https://bertvv.github.io/cheat-sheets/Bash.html#writing-robust-scripts-and-debugging
set -euo pipefail

# Check if required environment variables are set
# See .env-k8s-sample

# --- Configuration ---
# see .env-k8s-sample file
: "${NAMESPACE:?Need to set NAMESPACE}"
: "${EMAIL:?Need to set EMAIL}"
: "${DOMAIN1:?Need to set DOMAIN1}"
: "${DOMAIN2:?Need to set DOMAIN2}"

# Create the namespace
kubectl create namespace $NAMESPACE

# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update
kubectl create namespace cert-manager
helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.11.0 --set installCRDs=true

# Create the ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: $EMAIL
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Create the Ingress resource
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  namespace: $NAMESPACE
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - $DOMAIN1
    - $DOMAIN2
    secretName: tls-secret
  rules:
  - host: $DOMAIN1
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: hapi
            port:
              number: 8080
  - host: $DOMAIN2
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: google-fhir
            port:
              number: 8080
EOF

# Create the Service resource for google-fhir-proxy
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: google-fhir-proxy
  namespace: $NAMESPACE
spec:
  selector:
    app: google-fhir-proxy
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
EOF