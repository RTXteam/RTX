# ncats-complete
Autocompletion server for prefix and fuzzy matches

To run server:
python server.py

To create dict.db:
chmod u+x create_load_db.sh
./create_load_db.sh

## How to use RTXComplete

### From the frontend

```
  ...
  <form>
      <input id="autoTextInput" list="autoWordsList">
      <datalist id="autoWordsList">	
      </datalist>
  </form>
  ...
```

```
  ...
  var autoInputBox = document.getElementById("autoTextInput");
  var text = autoTextInput.value;
  $.ajax({url: "auto?word="+text+"&limit="+max_suggs,
          cache:false,
	  dataType:'jsonp',
	  success: function(data){
	      autocompleteDisplay(data);
          }
	 });
  ...
  ...
  var autoWordsList = document.getElementById("autoWordsList");
  autoWordsList.innerHTML = "";
  for (i = 0; i < array.length; i++){
      var tmp = document.createElement("option");
      tmp.text = array[i];
      autoWordsList.appendChild(tmp);
  }
  ...
```

### From the backend
Example code is in ```sample.py```. The two core lines are:
```
  
  with rtxcomplete.load():
    completions = rtxcomplete.prefix("NF", 10)
    matches = rtxcomplete.fuzzy("NF", 10)

```

## Demonstration Link
http://rtxcomplete.ixlab.org

## HTTPS Support

### Install

Run the following commands to install certbot;

$ sudo apt-get update
$ sudo apt-get install software-properties-common
$ sudo add-apt-repository ppa:certbot/certbot
$ sudo apt-get update
$ sudo apt-get install certbot

### Create SSL Certificates

Run the following command to create the needed SSL certificates;

$ sudo certbot certonly --standalone -d rtx.ncats.io

### Server SSL Options

To point the server at the certificates using Tornado make an HTTP server with the proper SSL options as demonstrated below;

```
https_server = tornado.httpserver.HTTPServer(https_app, ssl_options={
        "certfile": "/etc/letsencrypt/live/rtx.ncats.io.ixlab.org/fullchain.pem",
	"keyfile" : "/etc/letsencrypt/live/rtxncats.io/privkey.pem",
	})

https_server.listen(443)
```