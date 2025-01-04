# cloud

## overview
This project contains configurations for the SWAG reverse proxy to a local instance of the [HAPI FHIR server](https://hapifhir.io/) and a proxy to the [Google Healthcare API](https://cloud.google.com/healthcare-api/docs/concepts/fhir).

* SSL termination
* Reverse proxy
* HAPI FHIR server
* Google Healthcare API
* Static html pages

 
![](docs/images/overview.png)


## prerequisites
You have access to a GCP instance (e2-highmem-2 for example).

## usage

* First, build the proxy to the google healthcare API [see](google-fhir-proxy/README.md)

```bash
cd google-fhir-proxy
docker build . -t google-fhir --no-cache
cd ..
```

* start the server in the background
```bash
docker compose up --detach
```

* check the server is running
```bash
docker compose ps
NAME          IMAGE                             COMMAND                  SERVICE       CREATED          STATUS          PORTS
google-fhir   google-fhir                       "python proxy.py"        google-fhir   9 minutes ago    Up 9 minutes    0.0.0.0:8090->8080/tcp, [::]:8090->8080/tcp
hapi          hapiproject/hapi:v7.4.0           "java --class-path /…"   hapi          45 minutes ago   Up 45 minutes   0.0.0.0:8080->8080/tcp, :::8080->8080/tcp
postgres      postgres:15-alpine                "docker-entrypoint.s…"   postgres      45 minutes ago   Up 45 minutes   5432/tcp
swag          lscr.io/linuxserver/swag:latest   "/init"                  swag          45 minutes ago   Up 45 minutes   0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443->443/tcp, :::443->443/tcp
```

* configure the endpoint

```bash
# copy the subdirectories under the `./swag-config` directory to SWAG's `./config` directory
cp -r swag-config/* swag/config/
# (for HAPI) add passwords to config/nginx/.htpasswd
# e.g. htpasswd config/nginx/.htpasswd user password
 
# restart the reverse proxy
docker compose restart swag

```

* load data into the hapi fhir server &/or the google healthcare api (documented elsewhere)
* query the servers

```bash
# 
curl -s https://hapi.test-fhir-aggregator.org/fhir/'Patient?_total=accurate&_count=0'  | jq .total
curl -s https://google-fhir.test-fhir-aggregator.org/'Patient?_total=accurate&_count=0' | jq .total

```

* static content is served from the `./swag-config/www` directory
