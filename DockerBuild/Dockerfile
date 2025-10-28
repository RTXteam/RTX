# THIS DOCKER FILE IS FOR TESTING THE TEST DOCKER IMAGE on UBUNTU 24.04 and PYTHON 3.12
#### IMPORTANT: THIS DOCKER FILE IS FOR TESTING ONLY AND IS NOT USED FOR PRODUCTION ####
FROM ubuntu:24.04

# suppress debconf error messages:
ARG DEBIAN_FRONTEND=noninteractive

# build based on branch
ARG BUILD_BRANCH=issue2521

# add user "rt" and give sudo privilege:
RUN useradd rt -m -s /bin/bash

# install git and sudo
RUN apt-get update
RUN apt-get update  # running this twice seems to work around a weird 404 error
RUN apt-get install -y apt-utils
RUN apt-get install -y git sudo curl rsync

# give sudo privilege to user rt:
RUN usermod -aG sudo rt
RUN echo "rt ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/rt
RUN touch /home/rt/.sudo_as_admin_successful
RUN chown rt.rt /home/rt/.sudo_as_admin_successful

# configure ssh for user rt
RUN mkdir /home/rt/.ssh
RUN echo "StrictHostKeyChecking no" > /home/rt/.ssh/config
RUN echo "UserKnownHostsFile /dev/null" >> /home/rt/.ssh/config
RUN chown -R rt.rt /home/rt/.ssh
RUN chmod -R 700 /home/rt/.ssh

# install network troubleshooting utilities and emacs, in case we need them
RUN apt-get update && apt-get install -y \
    netcat \
    dnsutils \
    iputils-ping \
    traceroute \
    telnet \
    net-tools \
    iproute2 \
    curl \
    wget \
    tcpdump \
 && rm -rf /var/lib/apt/lists/*

# clone RTX repo (FOR TESTING TEST DOCKER IMAGE)
RUN mkdir -p /mnt/data/orangeboard/test
RUN chown -R rt.rt /mnt/data/orangeboard/test
RUN su rt && cd /mnt/data/orangeboard/test && git clone https://github.com/RTXteam/RTX.git
# 08/12/2022 NCATS change
RUN su rt && cd /mnt/data/orangeboard/test/RTX && git checkout ${BUILD_BRANCH}
RUN chown -R rt.rt /mnt/data/orangeboard/test/RTX

# install apache2 and copy config file
RUN export DEBIAN_FRONTEND=noninteractive && apt-get update && apt-get install -yq apache2
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
RUN cd /var/www && mv html html-orig && ln -s /mnt/data/orangeboard/test/RTX/code/UI/interactive html
RUN cd /var/www && a2enmod proxy && a2enmod proxy_html && a2enmod proxy_http && a2enmod rewrite && a2enmod headers
RUN a2enmod remoteip
COPY remoteip.conf /etc/apache2/conf-available/remoteip.conf
RUN a2enconf remoteip
RUN cd /var/www && /usr/sbin/apachectl configtest

# install python 3.12 and packages
RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.12 python3.12-dev python3.12-venv
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
RUN python3.12 -m pip install --upgrade pip setuptools wheel
RUN su rt && cd /mnt/data/orangeboard/test/RTX && python3.12 -m pip install click==8.1.3 && python3.12 -m pip install -r requirements.txt

# setup services
RUN export DEVAREA=test
RUN cat /mnt/data/orangeboard/test/RTX/code/UI/OpenAPI/python-flask-server/RTX_OpenAPI | sed 's/template/test/g' > /etc/init.d/RTX_OpenAPI_test
RUN chmod 700 /etc/init.d/RTX_OpenAPI_test
RUN su rt && cd /mnt/data/orangeboard/test/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI RTX_OpenAPI_test && sed -i 's/template/test/g' RTX_OpenAPI_test
RUN su rt && cd /mnt/data/orangeboard/test/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI.start RTX_OpenAPI_test.start && sed -i 's/template/test/g' RTX_OpenAPI_test.start
RUN update-rc.d RTX_OpenAPI_test defaults

# autocomplete
RUN cat /mnt/data/orangeboard/test/RTX/code/autocomplete/RTX_Complete | sed 's/devED/test/g' > /etc/init.d/RTX_Complete
RUN chmod 700 /etc/init.d/RTX_Complete
RUN cd /mnt/data/orangeboard/test/RTX/code/autocomplete && sed -i 's/devED/test/g' RTX_Complete.start
RUN update-rc.d RTX_Complete defaults

# setup config.domain (Changed from production to test for testing purposes arax.ncats.io/test)
RUN su rt && cd /mnt/data/orangeboard/test/RTX/code/ && echo "arax.ncats.io/test" > config.domain