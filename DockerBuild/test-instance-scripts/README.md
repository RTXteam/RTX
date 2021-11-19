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
various ARAX database into the instance. This script will set up key exchange between your test instance
(e.g., `buildarax.rtx.ai`) and the two instances from which files have to be retrieved (namely, `arax.ncats.io` for
databases and `araxconfig.rtx.ai` for the ARAX main config file). The script will then run the script 
`build-test-arax-from-fresh-instance.sh` within the test instance, on your behalf, to set up and run ARAX in the instance.
4. Point your browser at the instance on port 80 via HTTP; for example, if the instance hostname is
`buildarax.rtx.ai`, then point your browser at https://buildarax.rtx.ai
5. Have fun with ARAX!

# How does it work?

If you look at the shell script `build-test-arax-from-fresh-instance.sh`, you
will see that it uses the Dockerfile `Merged-Dockerfile` to build a container
that contains both the ARAX and RTX-KG2 services. No TLS is configured in the
host OS, in contrast to how we set up ARAX in production (this decision was made
in order to keep things simple for deploying a test system, i.e., to avoid having
to run `certbot` to get SSL certificates).

# Can I reuse the instance without having to re-download all the database files?

Yes, you can!  In a bash shell in the remote instance, run
```
source <(curl -s -L https://github.com/RTXteam/RTX/blob/master/DockerBuild/test-instance-scripts/clear-test-instance.sh)
```
and then run
```
source <(curl -s -L https://github.com/RTXteam/RTX/blob/master/DockerBuild/test-instance-scripts/build-test-arax-from-fresh-instance.sh)
```

