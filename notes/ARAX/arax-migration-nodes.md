# Migrating ARAX to a new server

NOTE: This assumes ubuntu server 18.04 and passwordless sudo access on both servers

### Ensure the correct ports are open

The ports that are needed to be open are:
- 7473
- 7474
- 7687
- 80
- 22
- 443

check that these are open using:
```
telnet <newserver> <port>
```

If it times out then the port is likely not open

### Setup the new Server

Make sure nginx is installed if it not already

Install git is this is not done already:
```
sudo apt-get update
sudo apt-get install -y git
```

Pull the RTX repository:
```
git clone https://github.com/RTXteam/RTX.git
```

Run the docker setup script:
```
sudo bash ./RTX/code/kg2/install-docker-ubuntu18.sh
```

Generate a ssh public rsa key if not already done:
```
ssh-keygen -t rsa
```
then keep hitting return until complete

Lastly, add the generated key in the new server at `<user>@<newserver>:~/.ssh/id_rsa.pub` to the authorized keys list located in the old server at `<user>@<oldserver>:~/.ssh/authorized_keys`

### Shut down neo4j and mysql

To prevent data corruption shut down the neo4j and mysql services running on the old server inside the rtx1 container

ssh into the oldserver:
```
ssh <user>@<oldserver>
```

go into the docker container:
```
sudo docker exec -ti rtx1 bash
```

Stop neo4j and mysql:
```
service neo4j stop
service mysql stop
```

### Create a image of the rtx1 container and copy to the new server

shh into the old server:
```
ssh <user>@<oldserver>
```

Generate an image of the current rtx1 container by running the following command:
```
sudo docker commit <rtx1 container name>  rtx1:<YYYYMMDD>
```

Save the image to a file:
```
sudo docker save rtx1:<YYYYMMDD> --output rtx1-<YYYY>-<MM>-<DD>-docker-image.tar rtx1:<YYYYMMDD>
```

Log back into the new server and copy over the newly gererated image file:
```
rsync -azP <user>@<oldserver>:/path/to/docker/image/rtx1-<YYYY>-<MM>-<DD>-docker-image.tar rtx1-<YYYY>-<MM>-<DD>-docker-image.tar
```

Load the image into docker:
```
sudo docker load --input rtx1-<YYYY>-<MM>-<DD>-docker-image.tar
```


### Copy over data directory

NOTE: This may take a while so it could be useful to start a screen instance, use nohup, ect...

ADDITIONAL NOTE:

Rsync over the data directory. This may be different depending on the server. On arax.rtx.ai it is at /data but on arax.ncats.io it is at /translator/data.
```
rsync -azP <user>@<oldserver>:/path/to/oldserver/data /path/to/newserver/data
```

Check that the permissions on files/directories math those on the old server. If not change them to match.

To acomplish this when moving from arax.rtx.ai->arax.ncats.io this was accomplished by running the following from the data directory:
```
sudo chown -R dnsmasq mysql
sudo chgrp -R admin mysql
sudo chown -R 1025 orangeboard
sudo chgrp -R 1025 orangeboard
sudo chown -R 999 RTX1
sudo chgrp -R adm RTX1
sudo chgrp docker RTX1/dbms/auth
sudo chgrp docker RTX1/databases/graph/store_lock
```

### Generate SSL certification

Install certbot
'''
sudo apt-get update
sudo apt-get install -y certbot
'''

Generate SSL certification using letsencrypt and change the nginx config file so that it matches (asside from paths, server names, etc...) the following:

```
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name <newserver>;
    return 302 https://$host$request_uri;
}

server {
    listen 443 ssl;
    ssl on;

    server_name <newserver>;
    root /etc/nginx/www;

    ssl_certificate             /etc/letsencrypt/live/<newserver>/fullchain.pem;
    ssl_certificate_key         /etc/letsencrypt/live/<newserver>/privkey.pem;
    ssl_protocols               TLSv1.1 TLSv1.2;
    ssl_prefer_server_ciphers   on;
    ssl_ciphers                 "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    ssl_ecdh_curve              secp384r1;
    ssl_session_timeout         1d;
    ssl_session_cache           shared:SSL:50m;
    ssl_dhparam                 /etc/nginx/dhparam.pem;
    ssl_stapling                on;
    ssl_stapling_verify         on;

    add_header    Strict-Transport-Security   max-age=15768000;

    server_tokens         off;

    location /.well-known {
    	try_files $uri $uri/ =404;
        add_header 'Access-Control-Allow-Origin' '*';
    }
    
    location / {
	proxy_read_timeout 3000s;
        add_header 'X-Frame-Options' 'SAMEORIGIN';
	proxy_buffering off;

	include proxy_params;
	proxy_pass http://localhost:8080;
	proxy_set_header  X-Forwarded-Proto $scheme;
	proxy_set_header  X-Real-IP         $remote_addr;
	proxy_set_header  X-Forwarded-For   $proxy_add_x_forwarded_for;
	proxy_set_header  X-Real-IP-AWS	    $remote_addr;
    }
}


```


### Run the docker container

Run the docker container from the loaded image:
```
sudo docker run -d -it --name rtx1 --mount type=bind,source=/path/to/newserver/data,target=/mnt/data -p 8080:80 -p 7473:7473 -p 7474:7474 -p 7687:7687 rtx1:<YYYYMMDD>
```

### Start services inside docker

Go inside the new docker container
```
sudo docker exec -ti rtx1 bash
```

Start services:
```
service apache2 start
service neo4j start
service mysql start
service RTX_Complete start
service RTX_OpenAPI_beta start
service RTX_OpenAPI_devED start
service RTX_OpenAPI_devLM start
service RTX_OpenAPI_dili start
service RTX_OpenAPI_legacy start
service RTX_OpenAPI_mvp start
service RTX_OpenAPI_production start
service RTX_OpenAPI_test start
```

Check that the services are running:
```
service --status-all
```

Check that you can log into neo4j through a browser 

Check that you can get the arax tool to display when going to the base url, /beta, /test, etc...

### Troubleshooting

##### Progress bar issues

If you have issues with the progessbar not working correctly.

Ensure that the nginx config file contains the `proxy_buffering off;` line.

##### Neo4j WebSocket connection failure

If trying to log into the neo4j browser give the following error:
```
ServiceUnavailable: WebSocket connection failure. Due to security constraints in your web browser, the reason for the failure is not available to this Neo4j Driver.
```
This is likely due to the 7687 port not being proporly open.

##### Database start fail

If neo4j (or mysql) wont start when running
```
service neo4j start
```
inside the container this is likely due to the permissions not being set correctly.

Double check that the permissions in the data directory on the new server match the permissions on the old server. 

##### Rsync permission issues

Make sure that user you are using to rsync has permissions to copy all files in the data directory

Alternatively, you can log into the oldserver and compress the data filder using sudo:
```
sudo tar -czf data.tar.gz data
```
then copy over the .gz file

Another suggestion is to add the rsync user to the old server and give it passwordless sudo privaliges. 

instructions located here: (untested as of writing)

https://www.ustrem.org/en/articles/rsync-over-ssh-as-root-en/
