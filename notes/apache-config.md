# Installation

    apt-get update
    apt-get install apache2

# Configuring the reverse proxy

    ProxyPass /api/rtx/v1 http://localhost:5000/api/rtx/v1
    
# Configuring an apache2 reverse-proxy for basic web authentication on Ubuntu

This assumes you want a single global (username,password) pair for the website,
where the username is `rtx`.  All commands below to be performed as user `root`.

### Set the username,password pair 

    htpasswd -c /etc/apache2/.htpasswd rtx

### Enable basic authentication on the reverse proxy

Add the following to /etc/apache2/sites-enabled/000-default.conf:

    <Location />
    AuthType Basic
    AuthName "For RTX Team and NCATS Only"
    AuthUserFile /etc/apache2/.htpasswd
    Require valid-user
    </Location>

before the `ProxyPass` statement.  Then test your configuration changes using:

    apache2ctl configtest

### You need to restart Apache2 for the changes to take effect:

    service apache2 restart
