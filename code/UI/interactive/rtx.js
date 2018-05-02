var cyobj = [];
var cytodata = [];


function sesame(head,content) {
    if (head == "openmax") {
	content.style.maxHeight = content.scrollHeight + "px";
	return;
    }
    else if (head) {
	head.classList.toggle("active");
    }

    if (content.style.maxHeight) {
	content.style.maxHeight = null;
    }
    else {
	content.style.maxHeight = content.scrollHeight + "px";
    }
}


function pasteQuestion(question) {
    document.getElementById("questionForm").elements["questionText"].value = question;
    document.getElementById("qqq").value = '';
    document.getElementById("qqq").blur();
}

function sendQuestion(e) {
    add_status_divs();
    document.getElementById("result_container").innerHTML = "";

    // collect the form data while iterating over the inputs
    var data = { 'text': document.getElementById("questionForm").elements["questionText"].value, 'language': 'English' };
    document.getElementById("statusdiv").innerHTML = "Interpreting your question...";
    sesame('openmax',statusdiv);

    // construct an HTTP request
    var xhr = new XMLHttpRequest();
    xhr.open("post", "api/rtx/v1/translate", true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

    // send the collected data as JSON
    xhr.send(JSON.stringify(data));

    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj = JSON.parse(xhr.responseText);
	    document.getElementById("devdiv").innerHTML = "<PRE>\n" + JSON.stringify(jsonObj,null,2) + "</PRE>";

	    if ( jsonObj.known_query_type_id && jsonObj.terms ) {
		document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj["restated_question"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR>Looking for answer...";
		sesame('openmax',statusdiv);
		var xhr2 = new XMLHttpRequest();
		xhr2.open("post", "api/rtx/v1/query", true);
		xhr2.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

		// send the collected data as JSON
		xhr2.send(JSON.stringify(jsonObj));

		xhr2.onloadend = function() {
		    if ( xhr2.status == 200 ) {
			var jsonObj2 = JSON.parse(xhr2.responseText);
			document.getElementById("devdiv").innerHTML += "=================================================================<PRE>\n" + JSON.stringify(jsonObj2,null,2) + "</PRE>";

			document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question_text"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR><BR><I>"+jsonObj2["message"]+"</I>";
			sesame('openmax',statusdiv);
			
			if ( jsonObj2["result_list"] ) {
			    add_result(jsonObj2["result_list"] );
			}
			else {
			    document.getElementById("result_container").innerHTML += "<H2>No results...</H2>";
			}
		    }
		    else {
			document.getElementById("statusdiv").innerHTML += "<BR><BR>An error was encountered:<BR><SPAN CLASS='error'>"+jsonObj.message+"</SPAN>";
			sesame('openmax',statusdiv);
		    }
		};
	    }
	    else {
		if ( jsonObj.message ) {
		    document.getElementById("statusdiv").innerHTML = jsonObj.message;
		}
		else if ( jsonObj.error_message ) {
		    document.getElementById("statusdiv").innerHTML = jsonObj.error_message;
		}
		else {
		    document.getElementById("statusdiv").innerHTML = "ERROR: Unknown error. No message returned.";
		}
		sesame('openmax',statusdiv);
	    }

	}
	else { // responseText
	    document.getElementById("statusdiv").innerHTML += "<BR><BR>An error was encountered:<BR><SPAN CLASS='error'>"+xhr.statusText+" ("+xhr.status+")</SPAN>";
	    sesame('openmax',statusdiv);
	}
    };

}




function add_status_divs() {
    document.getElementById("status_container").innerHTML = "<div onclick='sesame(null,statusdiv);' title='click to expand / collapse status' class='statushead'>Status  <i style='float:right; font-weight:normal;'>( using /devLM/ )</i></div><div class='status' id='statusdiv'></div>";

    document.getElementById("dev_result_json_container").innerHTML = "<div onclick='sesame(null,devdiv);' title='click to expand / collapse dev info' class='statushead'>Dev Info <i style='float:right; font-weight:normal;'>( json responses )</i></div><div class='status' id='devdiv'></div>";
}


function add_result(reslist) {
    document.getElementById("result_container").innerHTML += "<H2>Results:</H2>";

    for (var i in reslist) {
	var num = Number(i) + 1;
	var prb = Number(reslist[i].confidence).toFixed(2);

	var pcl = (prb>=0.9) ? "p9" : (prb>=0.7) ? "p7" : (prb>=0.5) ? "p5" : (prb>=0.3) ? "p3" : "p1";

	var html = "<div onclick='sesame(this,a"+num+"_div);' id='h"+num+"_div' title='Click to expand / collapse result "+num+"' class='accordion'>Result "+num+"<span title='confidence="+prb+"' class='"+pcl+" qprob'>"+prb+"</span></div>";
	html += "<div id='a"+num+"_div' class='panel'><table><tr><td class='textanswer'>"+reslist[i].text+"</td><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj["+i+"].reset();'>&#8635;</a></td><td class='cytograph'><div style='height: 100%; width: 100%' id='cy"+num+"'></div></td></tr></table></div>";

	document.getElementById("result_container").innerHTML += html;


	cytodata[i] = [];
	var gd = reslist[i].result_graph;

	for (var g in gd.node_list) {
	    var tmpdata = { "data" : gd.node_list[g] }; // already contains id
	    cytodata[i].push(tmpdata);

	    // DEBUG
	    //document.getElementById("cy"+num).innerHTML += "NODE: name="+ gd.node_list[g].name + " -- accession=" + gd.node_list[g].accession + "<BR>";
	}


	for (var g in gd.edge_list) {
	    var tmpdata = { "data" : 
			    {
				id : gd.edge_list[g].source_id + '--' + gd.edge_list[g].target_id,
				source : gd.edge_list[g].source_id,
				target : gd.edge_list[g].target_id,
				type   : gd.edge_list[g].type
	                    }
			  };

	    cytodata[i].push(tmpdata);
	}



    }

    sesame(h1_div,a1_div);
    add_cyto();
}



function add_cyto() {

    for (var i in cytodata) {
	var num = Number(i) + 1;

	cyobj[i] = cytoscape({
	    container: document.getElementById('cy'+num),
	    style: cytoscape.stylesheet()
		.selector('node')
		.css({
		    'background-color': '#047',
		    'width': '20',
		    'height': '20',
		    'content': 'data(name)'
		})
		.selector('edge')
		.css({
		    'curve-style' : 'bezier',
		    'line-color': '#fff',
		    'target-arrow-color': '#fff',
		    'width': 2,
		    'target-arrow-shape': 'triangle',
		    'opacity': 0.8
		})
		.selector(':selected')
		.css({
		    'background-color': '#c40',
		    'line-color': '#c40',
		    'target-arrow-color': '#c40',
		    'source-arrow-color': '#c40',
		    'opacity': 1
		})
		.selector('.faded')
		.css({
		    'opacity': 0.25,
		    'text-opacity': 0
		}),

	    elements: cytodata[i],

	    layout: {
		name: 'breadthfirst',
		padding: 10
	    },

	    ready: function(){
		// ready 1
	    }
	});


    }


}
