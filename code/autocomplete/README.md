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


## Task Specification from Oregon State
```
Assumptions:
 
PI Ramsey will provide (a) medical dictionary (TSV format) and 
                       (b) workload (TSV format) to simulate function calls to modules D1 and D2 
                       (c) ways to validate that APIs are working correctly (e.g. [ ‘cyto’ , ‘cytoplasm’ ] to denote input, and expected output)
 
Deliverables:
 
(D1) a software module (exposing an API that we can call from python) that would detect and suggest replacements for
misspelled words in the user’s query (and that is backed with a medical dictionary).
 
(D2) a software module (exposing an API that we can call from python) that would provide some partial-word autocomplete capability, and that would be backed by a medical dictionary.
 
(D3) consulting on how to improve usability of the UI in April (once in Mid-April, once at end-april) as the UI is developed.

(D4) participate in a team X-ray teleconference every other week for April and May 
 
(D5) send 1 student (Ben Strauss, or David Palzer, or both) to the DC Hackathon on May 21
 
```
