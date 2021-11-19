# How to deploy ARAX within a new EC2 instance, for testing purposes

1. If needed, provision a new EC2 instance (for example, a `t2.small` instance) with the Ubuntu 18.04 AMI. Allocate at least 200 GiB
of space in the root file system.
2. If needed, associate an elastic IP address to the instance and configure a DNS A-record for it. Let's assume the
hostname of your instance is `buildarax.rxt.ai`.
3. On your laptop or dev machine, in a bash shell, run:
```
source <(curl -s -L https://github.com/RTXteam/RTX/blob/master/DockerBuild/test-instance-scripts/remote-setup-build-test-arax-from-fresh-instance.sh)
```
You will be prompted to enter the path to your AWS key file (PEM file) that you assigned to your EC2 instance.
If you have already installed your RSA public key in the instance's `authorized_keys` file, then just hit return.
You will then be prompted to enter the instance's hostname; type the full hostname (e.g., `buildarax.rtx.ai`) and 
hit return. It will take a few hours to install and set up ARAX, mostly due to the time required to rsync the
various ARAX database into the instance.

