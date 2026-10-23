# Steps to build ARAX docker container


### Successful Build Environment Specs
- Instance Type: AWS EC2 (m5a.4xlarge)
- OS: Ubuntu 22.04.5 LTS (host version)
- Kernel: Linux 6.8.0-1029-aws
- Docker: Version 28.3.1, build 38b7060
- Memory: 61GB total
- Disk: 993GB total


### Update System
`sudo apt-get update`

`sudo apt-get upgrade -y`

### Install essential tools
```
sudo apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

## Install Docker
### Add Docker's official GPG key

`curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg`

### Add Docker repository
`echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null`

### Install Docker
`sudo apt-get update`

`sudo apt-get install -y docker-ce docker-ce-cli containerd.io`

### Start and enable Docker
`sudo systemctl start docker`

`sudo systemctl enable docker`

### Verify Docker installation
`sudo docker --version`

### Install GCC (required for some builds)
`sudo apt-get install -y gcc python3-dev`

### Install nginx
`sudo apt-get install -y nginx`

### Install certbot for SSL
`sudo snap install --classic certbot`

`sudo ln -s /snap/bin/certbot /usr/bin/certbot`

## Clone and Setup ARAX Repository
### Navigate to home directory
`cd ~`

### Clone RTX repository
`git clone https://github.com/RTXteam/RTX.git`

`cd RTX`

### Check available branches
`git branch -a`

### Switch to itrb-test branch
`git fetch`

`git checkout itrb-test`

`git pull origin itrb-test`

### Verify you're on the right branch
`git branch`

### Navigate to Build Directory
`cd ~/RTX/DockerBuild/`

### Check Docker service status
`sudo systemctl status docker`

### Clean up any existing Docker artifacts (optional)
`sudo docker system prune -f`

### Run Docker Build
`sudo docker build -t arax-itrb-test .`
