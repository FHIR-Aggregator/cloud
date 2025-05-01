# setting up a new VM

# remove any old docker installations
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

# install docker
# see https://docs.docker.com/engine/install/debian/
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
sudo groupadd docker
sudo usermod -aG docker $USER

# install utilities
sudo apt  install jq

# install docker-compose applications
sudo git clone https://github.com/FHIR-Aggregator/cloud
sudo chgrp docker cloud
sudo chgrp -R docker cloud
sudo chmod 770 cloud


# setup docker-compose swag service
cd cloud

mkdir config/
sudo cp -r swag-config/* config/

# build proxy
cd google-fhir-proxy/
docker build --cache-from=google-fhir:latest   . -t google-fhir

# launch service
cd ..
docker compose up -d
