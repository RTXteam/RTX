FROM ubuntu:20.04

# add user "rt" and give sudo privilege:
RUN useradd rt -m -s /bin/bash

# install git and sudo
RUN apt-get update
RUN apt-get update  # running this twice seems to work around a weird 404 error
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
RUN export DEBIAN_FRONTEND=noninteractive && apt-get install -yq apache2
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
RUN cd /var/www && mv html html-orig && ln -s /mnt/data/orangeboard/production/RTX/code/UI/interactive html
RUN cd /var/www && a2enmod proxy && a2enmod proxy_html && a2enmod rewrite && a2enmod headers
RUN cd /var/www && /usr/sbin/apachectl configtest

# install python and packages
RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip python3-venv
RUN su rt && cd /mnt/data/orangeboard/production/RTX && pip3 install -r requirements.txt && pip3 install flask_cors

# setup services
RUN export DEVAREA=production
RUN cat /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server/RTX_OpenAPI | sed 's/template/production/g' > /etc/init.d/RTX_OpenAPI_production
RUN chmod 700 /etc/init.d/RTX_OpenAPI_production
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI RTX_OpenAPI_production && sed -i 's/template/production/g' RTX_OpenAPI_production
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/UI/OpenAPI/python-flask-server && cp -p RTX_OpenAPI.start RTX_OpenAPI_production.start && sed -i 's/template/production/g' RTX_OpenAPI_production.start
RUN update-rc.d RTX_OpenAPI_production defaults
RUN update-rc.d RTX_OpenAPI_production enable

# set production flag to false
RUN su rt && cd /mnt/data/orangeboard/production/RTX/code/ && sed -i 's/self.is_production_server = True/self.is_production_server = False/g' RTXConfiguration.py


