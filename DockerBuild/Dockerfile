FROM ubuntu:20.04

# suppress debconf error messages:
ARG DEBIAN_FRONTEND=noninteractive

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

# clone RTX repo
RUN mkdir -p /mnt/data/orangeboard/production
RUN chown -R rt.rt /mnt/data/orangeboard/production
RUN su rt && cd /mnt/data/orangeboard/production && git clone https://github.com/RTXteam/RTX.git
RUN chown -R rt.rt /mnt/data/orangeboard/production/RTX

# install apache2 and copy config file
RUN export DEBIAN_FRONTEND=noninteractive && apt-get update && apt-get install -yq apache2
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
RUN cd /var/www && mv html html-orig && ln -s /mnt/data/orangeboard/production/RTX/code/UI/interactive html
RUN cd /var/www && a2enmod proxy && a2enmod proxy_html && a2enmod proxy_http && a2enmod rewrite && a2enmod headers
RUN a2enmod remoteip
COPY remoteip.conf /etc/apache2/conf-available/remoteip.conf
RUN a2enconf remoteip
RUN cd /var/www && /usr/sbin/apachectl configtest

# install python and packages
RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.7 python3.7-dev python3.7-venv
RUN rm /usr/bin/python3 && ln -s /usr/bin/python3.7 /usr/bin/python3
RUN su rt && cd /mnt/data/orangeboard/production/RTX && python3.7 -m pip install click==7.1.2 && python3.7 -m pip install -r requirements.txt

# setup services
RUN export DEVAREA=production
RUN cat /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server/RTX_OpenAPI | sed 's/template/production/g' > /etc/init.d/RTX_OpenAPI_production
RUN chmod 700 /etc/init.d/RTX_OpenAPI_production
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI RTX_OpenAPI_production && sed -i 's/template/production/g' RTX_OpenAPI_production
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI.start RTX_OpenAPI_production.start && sed -i 's/template/production/g' RTX_OpenAPI_production.start
RUN update-rc.d RTX_OpenAPI_production defaults

# autocomplete
RUN cat /mnt/data/orangeboard/production/RTX/code/autocomplete/RTX_Complete | sed 's/devED/production/g' > /etc/init.d/RTX_Complete
RUN chmod 700 /etc/init.d/RTX_Complete
RUN cd /mnt/data/orangeboard/production/RTX/code/autocomplete && sed -i 's/devED/production/g' RTX_Complete.start
RUN update-rc.d RTX_Complete defaults

# setup config.domain
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/ && echo "arax.ci.transltr.io" > config.domain
