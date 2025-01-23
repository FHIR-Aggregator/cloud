# healthcare-api
Devops for Google's healthcare-api
See [technical article](https://kellrott.medium.com/using-google-fhir-to-support-research-8f726834d77)

## Setup

How the healthcare API and FHIR store was created.

* setup environment
```bash
# see .env-sample and setup the environment variables
# collaborators will need to setup their own .env file
export $(cat .env | xargs)

export GOOGLE_PROJECT=$(gcloud projects list --filter=name=$GOOGLE_PROJECT_NAME --format="value(projectId)")
echo $GOOGLE_PROJECT
gcloud config set project $GOOGLE_PROJECT
```
* create the dataset and FHIR store
```bash
gcloud auth application-default set-quota-project $GOOGLE_PROJECT

gcloud services enable healthcare.googleapis.com

export GOOGLE_SERVICE_ACCOUNT=$(gcloud projects get-iam-policy $GOOGLE_PROJECT --format="value(bindings.members)" --flatten="bindings[]" | grep serviceAccount | uniq | grep healthcare)

gcloud healthcare datasets create $GOOGLE_DATASET --location=$GOOGLE_LOCATION

gcloud beta healthcare fhir-stores create $GOOGLE_DATASTORE --dataset=$GOOGLE_DATASET --location=$GOOGLE_LOCATION --version R4 --enable-update-create
```
* View the [FHIR store](https://console.cloud.google.com/healthcare/fhirviewer)

