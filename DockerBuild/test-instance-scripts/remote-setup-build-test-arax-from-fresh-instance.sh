#!/usr/bin/env bash

# Stephen Ramsey, Oregon State University

set -o nounset -o pipefail
# note: the standard bash "errexit" flag will not work in this script

public_key_file=id_rsa.pub
database_server=rtxconfig@arax.ncats.io
config_server=araxconfig@araxconfig.rtx.ai

echo "Enter the path to the AWS PEM file configured for the instance in which you wish to install ARAX; or if your RSA public key is already installed, just hit return: "
read aws_pem_file

echo "Enter the fully-qualified hostname of your instance (e.g., myaraxtest.rtx.ai): "
read instance_hostname
if [[ -z "${instance_hostname}" ]]
then
    >&2 echo "No hostname supplied; this is an error; exiting"
    exit 1
fi

echo "Enter the remote username for your instance (or hit enter for [ubuntu]): "
read remote_username
if [[ -z "${remote_username}" ]]
then
    remote_username=ubuntu
fi

echo "Enter the port number on the host machine you want to use for port 80 inside the conainer (or hit enter for [80]): "
read port_number
if [[ -z "${port_number}" ]]
then
    port_number=80
fi

if ! [ -z "${aws_pem_file}" ]
then
    echo "Using PEM file: ${aws_pem_file}"
else
    echo "Not using a PEM file to log into the remote instance; so we are assuming your RSA public key is already installed"
fi
  
echo "Installing in hostname: ${instance_hostname}"
echo "Installing for username: ${remote_username}"
echo "Using the port number: ${port_number}"

read -p "Are the above choices correct? [Y/N] " -n 1 -r

if ! [[ $REPLY =~ ^[Yy]$ ]]
then
    >&2 echo "User did not verify the run conditions; cancelling the run of the setup script"
    exit 0
fi

if ! [ -z "${aws_pem_file}" ]
then
    ssh-keygen -F ${instance_hostname} 

    if [ $? == 0 ]
    then
        ssh-keygen -R ${instance_hostname} >/dev/null 2>&1
    fi

    if ! ssh -q -o StrictHostKeyChecking=no ${remote_username}@${instance_hostname} exit
    then
        ## copy the id_rsa.pub file to the instance
        scp -i ${aws_pem_file} \
            -o StrictHostKeyChecking=no \
            ~/.ssh/${public_key_file} \
            ${remote_username}@${instance_hostname}:
        ## append the id_rsa.pub file to the authorized_keys file
        ssh -o StrictHostKeyChecking=no \
            -i ${aws_pem_file} \
            ${remote_username}@${instance_hostname} \
            'cat ${public_key_file} >> ~/.ssh/authorized_keys && rm ${public_key_file}'
    fi
fi
    
ssh ${remote_username}@${instance_hostname} "cat /dev/zero | ssh-keygen -q -t rsa -N '' <<< $'\ny' >/dev/null 2>&1"
temp_file_name="id_rsa_$$.pub"
temp_file_path="/tmp/${temp_file_name}"
scp ${remote_username}@${instance_hostname}:.ssh/id_rsa.pub ${temp_file_path}

scp ${temp_file_path} ${database_server}:${temp_file_name}
ssh ${database_server} "cat ${temp_file_name} >> ~/.ssh/authorized_keys"
ssh ${remote_username}@${instance_hostname} 'ssh -q -o StrictHostKeyChecking=no ${database_server} exit'

scp ${temp_file_path} ${config_server}:
ssh ${config_server} "cat ${temp_file_name} >> ~/.ssh/authorized_keys"
ssh ${remote_username}@${instance_hostname} 'ssh -q -o StrictHostKeyChecking=no ${config_server} exit'

rm ${temp_file_path}
ssh ${config_server} "rm ${temp_file_name}"
ssh ${database_server} "rm ${temp_file_name}"

ssh ${remote_username}@${instance_hostname} 'curl -s https://raw.githubusercontent.com/RTXteam/RTX/master/DockerBuild/test-instance-scripts/build-test-arax-from-fresh-instance.sh > build-test-arax-from-fresh-instance.sh'

ssh ${remote_username}@${instance_hostname} bash build-test-arax-from-fresh-instance.sh ${port_number}
