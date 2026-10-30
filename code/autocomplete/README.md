# ncats-complete
Autocompletion server for prefix and fuzzy matches

To run server:
python server.py

The autocomplete database is built in the
[arax-build-automation](https://github.com/Translator-CATRAX/arax-build-automation) repo
(see `workflow/scripts/autocomplete/`).

## How to use RTXComplete

### From the frontend

#### HTML
```
  ...
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
  <script src="/data/quick_def.json"><script>
  <script src="/bootstrap.js"></script>
  <script src="/bootstrap3-typeahead.js"></script>
  <script src="/rtxcomplete.js"></script>
  ...
  <input type="text" class="typeInput" data-provide="typeahead">
  ...
```
#### JavaScript

See rtxcomplete.js

### From the backend
The two core lines are:

```
  
  with rtxcomplete.load():
    completions = rtxcomplete.prefix("NF", 10)
    matches = rtxcomplete.fuzzy("NF", 10)

```

### Quick Definitions

`quick_def_creator.py` (now in the arax-build-automation repo, under `from_rtx/code/autocomplete/`) needs the definition function implemented based on chosen data sources. It also includes the expected format of the quick definitions along with an example.

## Demonstration Link
http://rtxcomplete.ixlab.org

## HTTPS Support

### Install

Run the following commands to install certbot;

```
$ sudo apt-get update
$ sudo apt-get install software-properties-common
$ sudo add-apt-repository ppa:certbot/certbot
$ sudo apt-get update
$ sudo apt-get install certbot
```

### Create SSL Certificates

Run the following command to create the needed SSL certificates;

$ sudo certbot certonly --standalone -d rtx.ncats.io

### Server SSL Options

To point the server at the certificates using Tornado make an HTTP server with the proper SSL options as demonstrated below;

```
https_server = tornado.httpserver.HTTPServer(https_app, ssl_options={
        "certfile": "/etc/letsencrypt/live/rtx.ncats.io.ixlab.org/fullchain.pem",
	"keyfile" : "/etc/letsencrypt/live/rtx.ncats.io/privkey.pem",
	})

https_server.listen(443)
```
