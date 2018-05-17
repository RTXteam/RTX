var autoWordsList, autoInputBox;
var spellWordsList, spellInputBox;

var max_suggs = 10;
var word_limit, limit_on;

window.onerror = function(msg, url, lineNo, columnNo, error){
    alert("onerror fired");
}

function remove_suggestions(element){
    element.innerHTML = '';
    //element.options.length = 0;
}

function autocomplete(){
    console.log("autocomplete");
    var text = autoTextInput.value;
    remove_suggestions(autoWordsList);
    console.log($.ajax({url: "auto?word="+text+"&limit="+max_suggs,
			cache:false,
			dataType:'jsonp',
			//jsonpCallback: "autocompleteDisplay",
			/*error: function(xhr, status, error){
			    alert(status);
			    alert(error);
			},*/
			success: function(data){
			    autocompleteDisplay(data);
			}
		       }));
}

function autocompleteDisplay(array){
    console.log("auto callback");
    console.log(array);

    for (i = 0; i < array.length; i++){
	var tmp = document.createElement("option");
	//tmp.value = array[i];
	tmp.text = array[i];
	autoWordsList.appendChild(tmp);
	//console.log("added " + array[i]);
    }
}

function spellcheck(){
    console.log("spell check");
    var text = spellTextInput.value;
    remove_suggestions(spellWordsList);
    if (text.length != 0){
	console.log($.ajax({url: "fuzzy?word="+text+"&limit="+max_suggs,
			    cache:false,
			    dataType:'jsonp',
			    //jsonpCallback: "autocompleteDisplay",
			    /*error: function(xhr, status, error){
			      alert(status);
			      alert(error);
			      },*/
			    success: function(data){
				spellcheckDisplay(data);
			    }
			   }));
    }
}

function spellcheckDisplay(array){
    console.log("spellcheck callback");
    console.log(array);

    for (i = 0; i < array.length; i++){ 
	var tmp = document.createElement("LI");
	//tmp.value = array[i];
	//tmp.value = array[i];
	tmp.innerHTML = array[i];
	spellWordsList.appendChild(tmp);
	//console.log("added " + array[i]);
    }
}

function init (){
    
    autoWordsList = document.getElementById("autoWordsList");
    autoInputBox = document.getElementById("autoTextInput");
    //autoInputBox.autocomplete = "off";
    
    spellWordsList = document.getElementById("spellWordsList");
    spellInputBox = document.getElementById("spellTextInput");
    spellInputBox.autocomplete = "off";
    
    autoInputBox.addEventListener("keyup", autocomplete);
    spellInputBox.addEventListener("keyup", spellcheck);
    
}
