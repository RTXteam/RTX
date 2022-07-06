FROM ubuntu:20.04
MAINTAINER Stephen Ramsey (stephen.ramsey@oregonstate.edu)

RUN useradd ubuntu -m -s /bin/bash
RUN apt-get update
RUN apt-get install -y git sudo 
# give sudo privilege to user ubuntu:
RUN usermod -aG sudo ubuntu
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu
RUN touch /home/ubuntu/.sudo_as_admin_successful
RUN chown ubuntu.ubuntu /home/ubuntu/.sudo_as_admin_successful
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

RUN bash -c 'debconf-set-selections <<< "mysql-server mysql-server/root_password password <manually enter password here>"'
RUN bash -c 'debconf-set-selections <<< "mysql-server mysql-server/root_password_again password <manually enter password here>"'

RUN apt-get install -y mysql-server mysql-client libmysqlclient-dev
RUN apt-get install -y telnet emacs

# make this container persistent
CMD tail -f /dev/null


