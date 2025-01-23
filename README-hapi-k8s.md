# Deploying HAPI FHIR JPA Server on GKE with Cloud SQL

This script deploys the HAPI FHIR JPA server starter on a Google Kubernetes Engine (GKE) cluster using Cloud SQL for PostgreSQL as the database.

## Prerequisites

*   A Google Cloud project with billing enabled.
*   A GKE cluster created.
*   A Cloud SQL for PostgreSQL instance created.
*   A service account with the necessary permissions to access Cloud SQL.
*   `kubectl` and `helm` installed and configured.
*   The `hapi-fhir-jpaserver` Helm chart added to your Helm repositories.  (If using the repo from examples, make sure its added)

Before running:

* Install gcloud: Ensure the Google Cloud SDK is installed and configured with the correct credentials for your project ( ncpi-rti-p01-007-ohsu ).
* Enable Kubernetes Engine API: Make sure the Kubernetes Engine API is enabled in your project.
* Choose a Region: Select an appropriate region ( REGION ) for your cluster. Consider latency and availability requirements.
* Node Count: Adjust NUM_NODES based on your application's resource needs. Start small and scale up as needed.

* Important Considerations:

* Networking: This script uses the default VPC network. For more complex networking scenarios (e.g., private clusters), you'll need to specify additional network parameters.
* Node Pools: This script uses cluster autoscaling. For more fine-grained control over node configuration (machine type, etc.), you'll need to explicitly create node pools using gcloud container node-pools create .
* Security: Consider adding appropriate security settings (e.g., IP allowlisting, Kubernetes Roles and RBAC) to secure your cluster.

After running this script successfully, you can use gcloud container clusters get-credentials to authenticate with your newly created cluster. Remember to always review the Google Cloud documentation for best practices and more advanced configuration options.

## Configuration

Before running the script, update the `deploy_hapi_fhir.sh` script with your project-specific values:

*   `PROJECT_ID`: Your Google Cloud project ID.
*   `CLUSTER_NAME`: The name of your GKE cluster.
*   `ZONE`: The zone of your GKE cluster.
*   `NAMESPACE`: The Kubernetes namespace for the deployment (default: `fhir`).
*   `CLOUD_SQL_INSTANCE`: The connection name of your Cloud SQL instance.
*   `DATABASE_NAME`: The name of your PostgreSQL database.
*   `DATABASE_USER`: The username for your PostgreSQL database.
*   `DATABASE_PASSWORD`: The password for your PostgreSQL database.


## Deployment

Run the script: `./deploy_hapi_k8s.sh`.


## Verification

After the script completes, verify the deployment:

```bash
kubectl get pods -n fhir
```
