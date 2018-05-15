var cyobj = [];
var cytodata = [];
var fb_explvls = [];
var fb_ratings = [];
var response_id = null;

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
    cyobj = [];
    cytodata = [];

    var bypass_cache = "true";
    if (document.getElementById("useCache").checked) {
	bypass_cache = "false";
    }

    // collect the form data while iterating over the inputs
    var data = { 'text': document.getElementById("questionForm").elements["questionText"].value, 'language': 'English', 'bypass_cache' : bypass_cache };
    document.getElementById("statusdiv").innerHTML = "Interpreting your question...";
    document.getElementById("statusdiv").innerHTML+= " (bypassing cache : " + bypass_cache + ")";

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

		jsonObj.bypass_cache = bypass_cache;
		jsonObj.max_results = 100;

		sesame('openmax',statusdiv);
		var xhr2 = new XMLHttpRequest();
		xhr2.open("post", "api/rtx/v1/query", true);
		xhr2.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

		// send the collected data as JSON
		xhr2.send(JSON.stringify(jsonObj));

		xhr2.onloadend = function() {
		    if ( xhr2.status == 200 ) {
			var jsonObj2 = JSON.parse(xhr2.responseText);
			document.getElementById("devdiv").innerHTML += "================================================================= QUERY::<PRE>\n" + JSON.stringify(jsonObj2,null,2) + "</PRE>";

			document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question_text"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR><BR><I>"+jsonObj2["message"]+"</I>";
			sesame('openmax',statusdiv);

			response_id = jsonObj2.id.substr(jsonObj2.id.lastIndexOf('/') + 1);

			if ( jsonObj2["result_list"] ) {
			    add_result(jsonObj2["result_list"]);
			    add_feedback();
			    //sesame(h1_div,a1_div);
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
    document.getElementById("status_container").innerHTML = "<div onclick='sesame(null,statusdiv);' title='click to expand / collapse status' class='statushead'>Status</div><div class='status' id='statusdiv'></div>";

    document.getElementById("dev_result_json_container").innerHTML = "<div onclick='sesame(null,devdiv);' title='click to expand / collapse dev info' class='statushead'>Dev Info <i style='float:right; font-weight:normal;'>( json responses )</i></div><div class='status' id='devdiv'></div>";
}


function add_result(reslist) {
    document.getElementById("result_container").innerHTML += "<H2>Results:</H2>";

    for (var i in reslist) {
	var num = Number(i) + 1;

	var prb = Number(reslist[i].confidence).toFixed(2);
	var pcl = (prb>=0.9) ? "p9" : (prb>=0.7) ? "p7" : (prb>=0.5) ? "p5" : (prb>=0.3) ? "p3" : "p1";

	var fid = "feedback_" + reslist[i].id.substr(reslist[i].id.lastIndexOf('/') + 1);

	document.getElementById("result_container").innerHTML += "<div onclick='sesame(this,a"+num+"_div);' id='h"+num+"_div' title='Click to expand / collapse result "+num+"' class='accordion'>Result "+num+"<span title='confidence="+prb+"' class='"+pcl+" qprob'>"+prb+"</span></div>";

	if (reslist[i].result_graph == null) {
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><br>"+reslist[i].text+"<br><br><span id='"+fid+"'><i>User Feedback</i></span></div>";

	}
	else {
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><table><tr><td class='textanswer'>"+reslist[i].text+"</td><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj["+i+"].reset();'>&#8635;</a></td><td class='cytograph'><div style='height: 100%; width: 100%' id='cy"+num+"'></div></td></tr><tr><td><span id='"+fid+"'><i>User Feedback</i><hr></span></td><td></td><td><div id='d"+num+"_div'><i>Click on a node or edge to get details</i></div></td></tr></table></div>";

	    cytodata[i] = [];
	    var gd = reslist[i].result_graph;

	    for (var g in gd.node_list) {
		gd.node_list[g].parentdivnum = num; // helps link node to div when displaying node info on click
		var tmpdata = { "data" : gd.node_list[g] }; // already contains id
		cytodata[i].push(tmpdata);

		// DEBUG
		//document.getElementById("cy"+num).innerHTML += "NODE: name="+ gd.node_list[g].name + " -- accession=" + gd.node_list[g].accession + "<BR>";
	    }

	    for (var g in gd.edge_list) {
		var tmpdata = { "data" : 
				{
				    parentdivnum : num,
				    id : gd.edge_list[g].source_id + '--' + gd.edge_list[g].target_id,
				    source : gd.edge_list[g].source_id,
				    target : gd.edge_list[g].target_id,
				    type   : gd.edge_list[g].type
				}
			      };

		cytodata[i].push(tmpdata);
	    }
	}
    }

//    sesame(h1_div,a1_div);
    add_cyto();
}



function add_cyto() {

    for (var i in cytodata) {
	if (cytodata[i] == null) {
	    continue;
	}

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

	    wheelSensitivity: 0.2,

	    layout: {
		name: 'breadthfirst',
		padding: 10
	    },

	    ready: function() {
		// ready 1
	    }
	});


	cyobj[i].on('tap','node', function() {
	    var dnum = 'd'+this.data('parentdivnum')+'_div';

	    document.getElementById(dnum).innerHTML = "<b>Accession:</b> " + this.data('accession') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>Name:</b> " + this.data('name') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>ID:</b> " + this.data('id') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>Type:</b> " + this.data('type') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>Description:</b> " + this.data('description') + "<br>";

	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

	cyobj[i].on('tap','edge', function() {
	    var dnum = 'd'+this.data('parentdivnum')+'_div';

	    document.getElementById(dnum).innerHTML = this.data('source');
	    document.getElementById(dnum).innerHTML+= " <b>" + this.data('type') + "</b> ";
	    document.getElementById(dnum).innerHTML+= this.data('target') + "<br>";

	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

    }

}


function add_feedback() {
    get_feedback_fields();

    var xhr3 = new XMLHttpRequest();
    xhr3.open("get", "api/rtx/v1/response/" + response_id + "/feedback", true);
    xhr3.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr3.send(null);

    xhr3.onloadend = function() {
	if ( xhr3.status == 200 ) {
	    var jsonObj3 = JSON.parse(xhr3.responseText);
	    document.getElementById("devdiv").innerHTML += "================================================================= FEEDBACK::<PRE>\n" + JSON.stringify(jsonObj3,null,2) + "</PRE>";

	    for (var i in jsonObj3) {
		var fid = "feedback_" + jsonObj3[i].result_id.substr(jsonObj3[i].result_id.lastIndexOf('/') + 1);

		if (document.getElementById(fid)) {
		    document.getElementById(fid).innerHTML += "<b>Rating:</b> " + jsonObj3[i].rating_id +  " (" + fb_ratings[jsonObj3[i].rating_id].tag + ")<br>";
		    document.getElementById(fid).innerHTML += "<b>Expertise:</b> " + jsonObj3[i].expertise_level_id + " (" + fb_explvls[jsonObj3[i].expertise_level_id].tag + ")<br>";
		    document.getElementById(fid).innerHTML += "<b>Comment:</b> " + jsonObj3[i].comment + "<hr>";
		}
		else {
		    document.getElementById("devdiv").innerHTML += "[warn] Feedback " + fid + " does not exist in response!<br>";
		}
	    }

	}
	sesame(h1_div,a1_div);
    };


}



function get_feedback_fields() {
    var xhr4 = new XMLHttpRequest();
    xhr4.open("get", "api/rtx/v1/feedback/expertise_levels", true);
    xhr4.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr4.send(null);

    xhr4.onloadend = function() {
	if ( xhr4.status == 200 ) {
	    var jsonObj4 = JSON.parse(xhr4.responseText);
	    document.getElementById("devdiv").innerHTML += "================================================================= FEEDBACK FIELDS::<PRE>\n" + JSON.stringify(jsonObj4,null,2) + "</PRE>";

	    for (var i in jsonObj4.expertise_levels) {
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id] = {};
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].desc = jsonObj4.expertise_levels[i].description;
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].name = jsonObj4.expertise_levels[i].name;
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].tag  = jsonObj4.expertise_levels[i].tag;
	    }
	}
    };


    var xhr5 = new XMLHttpRequest();
    xhr5.open("get", "api/rtx/v1/feedback/ratings", true);
    xhr5.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr5.send(null);

    xhr5.onloadend = function() {
	if ( xhr5.status == 200 ) {
	    var jsonObj5 = JSON.parse(xhr5.responseText);
	    document.getElementById("devdiv").innerHTML += "---------------------------------- <PRE>\n" + JSON.stringify(jsonObj5,null,2) + "</PRE>";

	    for (var i in jsonObj5.ratings) {
		fb_ratings[jsonObj5.ratings[i].rating_id] = {};
		fb_ratings[jsonObj5.ratings[i].rating_id].desc = jsonObj5.ratings[i].description;
		fb_ratings[jsonObj5.ratings[i].rating_id].name = jsonObj5.ratings[i].name;
		fb_ratings[jsonObj5.ratings[i].rating_id].tag  = jsonObj5.ratings[i].tag;
	    }
	}
    };

}
