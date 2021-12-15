# How to deploy ARAX within a new EC2 instance, for testing purposes

1. If needed, provision a new EC2 instance (for example, a `t2.small` instance) with the Ubuntu 18.04 AMI. Allocate at least 200 GiB
of space in the root file system. The EC2 security policy will need to be configured to permit traffic to/from TCP port 80 on the instance.
2. If needed, associate an elastic IP address to the instance and configure a DNS A-record for it. Let's assume that
the hostname that is DNS-associated with the elastic IP address associated with your instance is `buildarax.rtx.ai`.
3. On your laptop or dev machine, in a bash shell, run:
```
source <(curl -s -L https://raw.githubusercontent.com/RTXteam/RTX/master/DockerBuild/test-instance-scripts/remote-setup-build-test-arax-from-fresh-instance.sh)
```
You will be prompted to enter the path to your AWS key file (PEM file) that you assigned to your EC2 instance.
If you have already installed your RSA public key in the instance's `authorized_keys` file, then just hit return.
You will then be prompted to enter the instance's hostname; type the full hostname (e.g., `buildarax.rtx.ai`) and 
hit return. It will take a few hours to install and set up ARAX, mostly due to the time required to rsync the
various ARAX databases into the instance. This script will set up the key exchanges between your test instance
(e.g., `buildarax.rtx.ai`) and the two instances from which files have to be retrieved (namely, `arax.ncats.io` for
databases and `araxconfig.rtx.ai` for the ARAX main config file). The script will then run the script 
`build-test-arax-from-fresh-instance.sh` within the test instance, on your behalf, to set up and run ARAX in the instance.

4. Point your browser at the instance on port 80 via HTTP; for example, if the instance hostname is
`buildarax.rtx.ai`, then point your browser at https://buildarax.rtx.ai
5. Have fun with ARAX!

# FAQs

## How does it work?

If you look at the shell script `build-test-arax-from-fresh-instance.sh`, you
will see that it uses the Dockerfile `Merged-Dockerfile` to build a container
`arax` (constructed from a Ubuntu 20.04-based Docker image `arax:1.0`) that
contains both the ARAX and RTX-KG2 services. No TLS is configured in the host
OS, in contrast to how we set up ARAX in production (this decision was made in
order to keep things simple for deploying a test system, i.e., to avoid having
to run `certbot` to get SSL certificates).

## Can I reuse the instance without having to re-download all the database files?

Yes, you can!  What I normally do is to clear out the Docker container and image, and the RTX code repo in the host OS, as follows:
In a bash shell in the test instance (e.g., `buildarax.rtx.ai`), run
```
source <(curl -s -L https://raw.githubusercontent.com/RTXteam/RTX/master/DockerBuild/test-instance-scripts/clear-test-instance.sh)
```
and then in that same bash shell on the remote instance, run
```
source <(curl -s -L https://raw.githubusercontent.com/RTXteam/RTX/master/DockerBuild/test-instance-scripts/build-test-arax-from-fresh-instance.sh)
```

## Who can give help on how to use these?

- The shell scripts were written by Stephen Ramsey with a lot of help from Finn Womack.
- `Merged-Dockerfile` was written by Finn Womack.

## Will this work on something other than Ubuntu 18.04 in the host OS?

We have no idea. Give it a try and report back!  These scripts have only been tested under Ubuntu 18.04 for
the host OS (and running Ubuntu 20.04 inside the container).



