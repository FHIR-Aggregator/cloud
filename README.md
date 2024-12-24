# hapi
HAPI FHIR server and reverse proxy
![](docs/images/hapi-fhir-aggregator.png)
## overview
This project contains configurations for the SWAG reverse proxy and the HAPI FHIR server
## usage

* start the server in the background
```bash
docker compose up --detach
```

* check the server is running
```bash
docker compose ps

NAME                        IMAGE                     COMMAND                  SERVICE                     CREATED         STATUS         PORTS
hapi       hapiproject/hapi:v7.4.0           "java --class-path /…"   hapi       3 hours ago   Up 3 hours   0.0.0.0:8080->8080/tcp, :::8080->8080/tcp
postgres   postgres:15-alpine                "docker-entrypoint.s…"   postgres   3 hours ago   Up 3 hours   5432/tcp
swag       lscr.io/linuxserver/swag:latest   "/init"                  swag       3 hours ago   Up 3 hours   0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443->443/tcp, :::443->443/tcp```
```
* configure the endpoint

```bash
# copy the subdirectories under the `./hapi-proxy-config` directory to SWAG's `./config` directory
# restart the reverse proxy
docker compose restart swag

```