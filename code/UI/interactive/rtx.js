var input_qg = { "edges": [], "nodes": [] };
var qgids = [];
var cyobj = [];
var cytodata = [];
var fb_explvls = [];
var fb_ratings = [];
var predicates = {};
var message_id = null;
var summary_table_html = '';
var columnlist = [];
var UIstate = {};

var baseAPI = "";
//var baseAPI = "http://localhost:5001/devED/";

function main() {
    get_example_questions();
    load_nodes_and_predicates();
    display_list('A');
    display_list('B');
    add_status_divs();
    cytodata[999] = 'dummy';
    UIstate.nodedd = 1;

    message_id = getQueryVariable("m") || null;
    if (message_id) {
	document.getElementById("statusdiv").innerHTML = "You have requested RTX message id = " + message_id;
	document.getElementById("devdiv").innerHTML =  "requested RTX message id = " + message_id + "<br>";
	retrieve_message();
	openSection(null,'queryDiv');
    }
    else {
	openSection(null,'queryDiv');
	add_cyto();
   }
}

function sesame(head,content) {
    if (head == "openmax") {
	content.style.maxHeight = content.scrollHeight + "px";
	return;
    }
    else if (head == "collapse") {
        content.style.maxHeight = null;
	return;
    }
    else if (head) {
	head.classList.toggle("openaccordion");
    }

    if (content.style.maxHeight) {
	content.style.maxHeight = null;
    }
    else {
	content.style.maxHeight = content.scrollHeight + "px";
    }
}


function openSection(obj, sect) {
    if (obj != null) {
	var e = document.getElementsByClassName("menucurrent");
	e[0].className = "menuleftitem";
	obj.className = "menucurrent";
    }
    e = document.getElementsByClassName("pagesection");
    for (var i = 0; i < e.length; i++) {
        e[i].style.maxHeight = null;
        e[i].style.visibility = 'hidden';
	//e[i].style.display = "none";
    }
    document.getElementById(sect).style.maxHeight = "100%";
    document.getElementById(sect).style.visibility = 'visible';
    window.scrollTo(0,0);
    //document.getElementById(sect).style.display = "block";
}

// somehow merge with above?  eh...
function selectInput (obj, input_id) {
    var e = document.getElementsByClassName("slink_on");
    if (e[0]) { e[0].classList.remove("slink_on"); }
    obj.classList.add("slink_on");

    for (var s of ['qtext_input','qgraph_input','qdsl_input']) {
	document.getElementById(s).style.maxHeight = null;
	document.getElementById(s).style.visibility = 'hidden';
    }
    document.getElementById(input_id).style.maxHeight = "100%";
    document.getElementById(input_id).style.visibility = 'visible';
}


function clearDSL() {
    document.getElementById("dslText").value = '';
}

function pasteQuestion(question) {
    document.getElementById("questionForm").elements["questionText"].value = question;
    document.getElementById("qqq").value = '';
    document.getElementById("qqq").blur();
}

function reset_vars() {
    add_status_divs();
    document.getElementById("result_container").innerHTML = "";
    //    document.getElementById("kg_container").innerHTML = "";
    if (cyobj[0]) {cyobj[0].elements().remove();}
    document.getElementById("summary_container").innerHTML = "";
    document.getElementById("menunummessages").innerHTML = "--";
    document.getElementById("menunumresults").innerHTML = "--";
    document.getElementById("menunumresults").classList.remove("numnew");
    document.getElementById("menunumresults").classList.add("numold");
    summary_table_html = '';
    cyobj = [];
    cytodata = [];
    UIstate.nodedd = 1;
}



// use fetch and stream
function postQuery(qtype) {
    var queryObj= {};
    queryObj.asynchronous = "stream";

    reset_vars();
    var statusdiv = document.getElementById("statusdiv");

    // assemble QueryObject
    if (qtype == "DSL") {
	document.getElementById("questionForm").elements["questionText"].value = '-- posted async query via DSL input --';
	statusdiv.innerHTML = "Posting DSL.  Looking for answer...";
	statusdiv.appendChild(document.createElement("br"));

	var dslArrayOfLines = document.getElementById("dslText").value.split("\n");
	queryObj["previous_message_processing_plan"] = { "processing_actions": dslArrayOfLines};
    }
    else {  // qGraph
	document.getElementById("questionForm").elements["questionText"].value = '-- posted async query via graph --';
	statusdiv.innerHTML = "Posting graph.  Looking for answer...";
        statusdiv.appendChild(document.createElement("br"));

	// ids need to start with a non-numeric character...
	for (var gnode of input_qg.nodes) {
	    if (String(gnode.id).match(/^\d/)) {
		gnode.id = "qg" + gnode.id;
	    }
	}
	for (var gedge of input_qg.edges) {
	    if (String(gedge.id).match(/^\d/)) {
		gedge.id = "qg" + gedge.id;
	    }
	    if (String(gedge.source_id).match(/^\d/)) {
		gedge.source_id = "qg" + gedge.source_id;
	    }
	    if (String(gedge.target_id).match(/^\d/)) {
		gedge.target_id = "qg" + gedge.target_id;
	    }
	}

	document.getElementById('qg_form').style.visibility = 'hidden';
	document.getElementById('qg_form').style.maxHeight = null;

	queryObj.message = { "query_graph" :input_qg };
	//queryObj.bypass_cache = bypass_cache;
	queryObj.max_results = 100;

	clear_qg();
    }

    var cmddiv = document.createElement("div");
    cmddiv.id = "cmdoutput";
    statusdiv.appendChild(cmddiv);
//    statusdiv.appendChild(document.createElement("br"));

    statusdiv.appendChild(document.createTextNode("Processing step "));
    var span = document.createElement("span");
    span.id = "finishedSteps";
    span.style.fontWeight= "bold";
//    span.className = "menunum numnew";
    span.appendChild(document.createTextNode("0"));
    statusdiv.appendChild(span);
    statusdiv.appendChild(document.createTextNode(" of "));
    span = document.createElement("span");
    span.id = "totalSteps";
//    span.className = "menunum";
    span.appendChild(document.createTextNode("??"));
    statusdiv.appendChild(span);

    span = document.createElement("span");
    span.className = "progress";

    var span2 = document.createElement("span");
    span2.id = "progressBar";
    span2.className = "bar";
    span2.appendChild(document.createTextNode("0%"));
    span.appendChild(span2);

    statusdiv.appendChild(span);
    statusdiv.appendChild(document.createElement("br"));
    statusdiv.appendChild(document.createElement("br"));
    sesame('openmax',statusdiv);

    add_to_dev_info("Posted to QUERY",queryObj);
    fetch(baseAPI + "api/rtx/v1/query", {
	method: 'post',
	body: JSON.stringify(queryObj),
	headers: { 'Content-type': 'application/json' }
    }).then(function(response) {
	var reader = response.body.getReader();
	var partialMsg = '';
	var enqueue = false;
	var countingSteps = false;
	var totalSteps = 0;
	var finishedSteps = 0;
	var decoder = new TextDecoder();
	var respjson = '';

	function scan() {
	    return reader.read().then(function(result) {
		partialMsg += decoder.decode(result.value || new Uint8Array, {
		    stream: !result.done
		});

		var completeMsgs = partialMsg.split("\n");
		//console.log("================ completeMsgs::");
		//console.log(completeMsgs);

		if (!result.done) {
		    // Last msg is likely incomplete; hold it for next time
		    partialMsg = completeMsgs[completeMsgs.length - 1];
		    // Remove it from our complete msgs
		    completeMsgs = completeMsgs.slice(0, -1);
		}

		for (var msg of completeMsgs) {
		    msg = msg.trim();
		    if (msg == null) continue;

		    //console.log("================ msg::");
		    //console.log(msg);

		    if (enqueue) {
			respjson += msg;
		    }
		    else {
			var jsonMsg = JSON.parse(msg);
			if (jsonMsg.code_description) {
			    enqueue = true;
			    respjson += msg;
			}
			else if (jsonMsg.message) {
			    if (jsonMsg.message.match(/^Parsing action: [^\#]\S+/)) {
				totalSteps++;
			    }
			    else if (totalSteps>0) {
				document.getElementById("totalSteps").innerHTML = totalSteps;
				if (jsonMsg.message.match(/^Processing action/)) {
				    document.getElementById("progressBar").style.width = (800*finishedSteps/totalSteps)+"px";
				    document.getElementById("progressBar").innerHTML = Math.round(99*finishedSteps/totalSteps)+"%\u00A0\u00A0";
				    finishedSteps++;
				    document.getElementById("finishedSteps").innerHTML = finishedSteps;
				}
			    }
			    cmddiv.appendChild(document.createTextNode(jsonMsg.prefix+'\u00A0'+jsonMsg.message));
			    cmddiv.appendChild(document.createElement("br"));
			    cmddiv.scrollTop = cmddiv.scrollHeight;
			}
			else {
			    console.log("bad msg:"+jsonMsg);
			}
		    }
		}

		if (result.done) {
		    //console.log(respjson);
		    return respjson;
		}

		return scan();
	    })
	}
	return scan();
    })
        .then(response => {
	    var data = JSON.parse(response);

	    var dev = document.getElementById("devdiv");
            dev.appendChild(document.createElement("br"));
	    dev.appendChild(document.createTextNode('='.repeat(80)+" RESPONSE MESSAGE::"));
	    var pre = document.createElement("pre");
	    pre.id = "responseJSON";
	    pre.appendChild(document.createTextNode(JSON.stringify(data,null,2)));
	    dev.appendChild(pre);

	    document.getElementById("progressBar").style.width = "800px";
	    if (data.message_code == "OK")
		document.getElementById("progressBar").innerHTML = "Finished\u00A0\u00A0";
	    else {
		document.getElementById("progressBar").classList.add("barerror");
		document.getElementById("progressBar").innerHTML = "Error\u00A0\u00A0";
		document.getElementById("finishedSteps").classList.add("menunum");
		document.getElementById("finishedSteps").classList.add("numnew");
	    }
	    statusdiv.appendChild(document.createTextNode(data["code_description"]));  // italics?
	    statusdiv.appendChild(document.createElement("br"));
	    sesame('openmax',statusdiv);

	    if (data["message_code"] == "QueryGraphZeroNodes") {
		clear_qg();
	    }
	    else if (data["message_code"] == "OK") {
		input_qg = { "edges": [], "nodes": [] };
		render_message(data);
	    }
	    else if (data["log"]) {
		process_log(data["log"]);
	    }
	    else {
		statusdiv.innerHTML += "<BR><SPAN CLASS='error'>An error was encountered while parsing the response from the server (no log; code:"+data.message_code+")</SPAN>";
		document.getElementById("devdiv").innerHTML += "------------------------------------ error with capturing QUERY:<BR>"+data;
		sesame('openmax',statusdiv);
	    }

	})
        .catch(function(err) {
	    statusdiv.innerHTML += "<BR><SPAN CLASS='error'>An error was encountered while contacting the server ("+err+")</SPAN>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with parsing QUERY:<BR>"+err;
	    sesame('openmax',statusdiv);
	    if (err.log) {
		process_log(err.log);
	    }
	    console.log(err.message);
	});
}


function sendQuestion(e) {
    reset_vars();
    if (cyobj[999]) {cyobj[999].elements().remove();}
    input_qg = { "edges": [], "nodes": [] };

    var bypass_cache = "true";
    if (document.getElementById("useCache").checked) {
	bypass_cache = "false";
    }

    // collect the form data while iterating over the inputs
    var q = document.getElementById("questionForm").elements["questionText"].value;
    var question = q.replace("[A]", get_list_as_string("A"));
    question = question.replace("[B]", get_list_as_string("B"));
    question = question.replace("[]", get_list_as_string("A"));
    question = question.replace(/\$\w+_list/, get_list_as_string("A"));  // e.g. $protein_list
    var data = { 'text': question, 'language': 'English', 'bypass_cache' : bypass_cache };
    document.getElementById("statusdiv").innerHTML = "Interpreting your question...";
    document.getElementById("devdiv").innerHTML = " (bypassing cache : " + bypass_cache + ")";

    sesame('openmax',statusdiv);
    document.getElementById('qg_form').style.visibility = 'hidden';
    document.getElementById('qg_form').style.maxHeight = null;

    // construct an HTTP request
    var xhr = new XMLHttpRequest();
    xhr.open("post", baseAPI + "api/rtx/v1/translate", true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

    // send the collected data as JSON
    xhr.send(JSON.stringify(data));

    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj = JSON.parse(xhr.responseText);
	    add_to_dev_info("Posted to TRANSLATE",jsonObj);

	    if ( jsonObj.query_type_id && jsonObj.terms ) {
		document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj["restated_question"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR>Looking for answer...";

		sesame('openmax',statusdiv);
		var xhr2 = new XMLHttpRequest();
		xhr2.open("post",  baseAPI + "api/rtx/v1/query", true);
		xhr2.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

                var queryObj = { "message" : jsonObj };
                queryObj.bypass_cache = bypass_cache;
                queryObj.max_results = 100;

		add_to_dev_info("Posted to QUERY",queryObj);
		xhr2.send(JSON.stringify(queryObj));
		xhr2.onloadend = function() {
		    if ( xhr2.status == 200 ) {
			var jsonObj2 = JSON.parse(xhr2.responseText);
			document.getElementById("devdiv").innerHTML += "<br>================================================================= QUERY::<PRE id='responseJSON'>\n" + JSON.stringify(jsonObj2,null,2) + "</PRE>";

			document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR><BR><I>"+jsonObj2["code_description"]+"</I>";
			sesame('openmax',statusdiv);

			render_message(jsonObj2);

		    }
		    else if ( jsonObj.message ) { // STILL APPLIES TO 0.9??  TODO
			document.getElementById("statusdiv").innerHTML += "<BR><BR>An error was encountered:<BR><SPAN CLASS='error'>"+jsonObj.message+"</SPAN>";
			sesame('openmax',statusdiv);
		    }
		    else {
			document.getElementById("statusdiv").innerHTML += "<BR><SPAN CLASS='error'>An error was encountered while contacting the server ("+xhr2.status+")</SPAN>";
			document.getElementById("devdiv").innerHTML += "------------------------------------ error with QUERY:<BR>"+xhr2.responseText;
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


function retrieve_message() {
    document.getElementById("statusdiv").innerHTML = "Retrieving RTX message id = " + message_id + "<hr>";

    sesame('openmax',statusdiv);
    var xhr = new XMLHttpRequest();
    xhr.open("get",  baseAPI + "api/rtx/v1/message/" + message_id, true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.send(null);
    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj2 = JSON.parse(xhr.responseText);
	    document.getElementById("devdiv").innerHTML += "<br>================================================================= RESPONSE REQUEST::<PRE id='responseJSON'>\n" + JSON.stringify(jsonObj2,null,2) + "</PRE>";

	    document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<BR>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question"]+"?</B><BR>Please ensure that this is an accurate restatement of the intended question.<BR><BR><I>"+jsonObj2["code_description"]+"</I><br>";
	    document.getElementById("questionForm").elements["questionText"].value = jsonObj2["restated_question"];

	    sesame('openmax',statusdiv);

	    render_message(jsonObj2);
	}
	else if ( xhr.status == 404 ) {
	    document.getElementById("statusdiv").innerHTML += "<BR>The following message id was not found:<SPAN CLASS='error'>"+message_id+"</SPAN>";
	    sesame('openmax',statusdiv);
	}
	else {
	    document.getElementById("statusdiv").innerHTML += "<BR><SPAN CLASS='error'>An error was encountered while contacting the server ("+xhr.status+")</SPAN>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with RESPONSE:<BR>"+xhr.responseText;
	    sesame('openmax',statusdiv);
	}
    };
}



function render_message(respObj) {
    document.getElementById("statusdiv").appendChild(document.createTextNode("Rendering message..."));
    sesame('openmax',statusdiv);

    message_id = respObj.id.substr(respObj.id.lastIndexOf('/') + 1);

    add_to_session(message_id,respObj.restated_question+"?");

    document.title = "RTX-UI ["+message_id+"]: "+respObj.restated_question+"?";
    history.pushState({ id: 'RTX_UI' }, 'RTX | message='+message_id, "//"+ window.location.hostname + window.location.pathname + '?m='+message_id);

    if ( respObj["table_column_names"] ) {
	add_to_summary(respObj["table_column_names"],0);
    }
    if ( respObj["results"] ) {
        document.getElementById("result_container").innerHTML += "<H2>" + respObj["n_results"] + " results</H2>";
        document.getElementById("menunumresults").innerHTML = respObj["n_results"];
        document.getElementById("menunumresults").classList.add("numnew");
	document.getElementById("menunumresults").classList.remove("numold");

	if ( respObj["knowledge_graph"] ) {
//	    process_kg(respObj["knowledge_graph"]);
//	    add_kg_html();
	    process_graph(respObj["knowledge_graph"],0);
	    process_results(respObj["results"],respObj["knowledge_graph"]);
	}
	else {  // fallback to old style
            add_result(respObj["results"]);
	}
        add_feedback();
        //sesame(h1_div,a1_div);
    }
    else {
        document.getElementById("result_container").innerHTML += "<H2>No results...</H2>";
        document.getElementById("summary_container").innerHTML += "<H2>No results...</H2>";
    }

    if (respObj["query_graph"]) {
	process_graph(respObj["query_graph"],999);
    }
    else {
	cytodata[999] = 'dummy'; // this enables query graph editing
    }

    if ( respObj["table_column_names"] ) {
        document.getElementById("summary_container").innerHTML = "<div onclick='sesame(null,summarydiv);' class='statushead'>Summary</div><div class='status' id='summarydiv'><br><table class='sumtab'>" + summary_table_html + "</table><br></div>";
    }

    if (respObj["query_options"]) {
	process_q_options(respObj["query_options"]);
    }

    if (respObj["log"]) {
	process_log(respObj["log"]);
    }

    add_cyto();
    document.getElementById("statusdiv").appendChild(document.createTextNode("done."));
    sesame('openmax',statusdiv);
}

function process_q_options(q_opts) {

    if (q_opts.processing_actions) {
	clearDSL();
	for (var act of q_opts.processing_actions) {
	    document.getElementById("dslText").value += act + "\n";
	}
    }

}

function process_log(logarr) {
    var errors = 0;
    for (var msg of logarr) {
	if (msg.level_str == "ERROR") { errors++; }

	var span = document.createElement("span");
	span.className = "hoverable msg " + msg.level_str;

        if (msg.level_str == "DEBUG") { span.style.display = 'none'; }

	var span2 = document.createElement("span");
	span2.className = "explevel msg" + msg.level_str;
	span2.appendChild(document.createTextNode('\u00A0'));
	span2.appendChild(document.createTextNode('\u00A0'));
        span.appendChild(span2);

	span.appendChild(document.createTextNode('\u00A0'));

	span.appendChild(document.createTextNode(msg.prefix));
//	span.appendChild(document.createElement("br"));

	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode(msg.message));

	document.getElementById("logdiv").appendChild(span);
    }
    document.getElementById("menunummessages").innerHTML = logarr.length;

}


function add_status_divs() {
    document.getElementById("status_container").innerHTML = "<div class='statushead'>Status</div><div class='status' id='statusdiv'></div>";

    document.getElementById("dev_result_json_container").innerHTML = "<div class='statushead'>Dev Info <i style='float:right; font-weight:normal;'>( json responses )</i></div><div class='status' id='devdiv'></div>";

    document.getElementById("messages_container").innerHTML = "<div class='statushead'>Filter Messages :&nbsp;&nbsp;&nbsp;<span onclick='filtermsgs(this,\"ERROR\")' style='cursor:pointer;' class='qprob msgERROR'>Error</span>&nbsp;&nbsp;&nbsp;<span onclick='filtermsgs(this,\"WARNING\")' style='cursor:pointer;' class='qprob msgWARNING'>Warning</span>&nbsp;&nbsp;&nbsp;<span onclick='filtermsgs(this,\"INFO\")' style='cursor:pointer;' class='qprob msgINFO'>Info</span>&nbsp;&nbsp;&nbsp;<span onclick='filtermsgs(this,\"DEBUG\")' style='cursor:pointer;' class='qprob msgDEBUG hide'>Debug</span></div><div class='status' id='logdiv'></div>";
}

function filtermsgs(span, type) {
    var disp = 'none';
    if (span.classList.contains('hide')) {
	disp = '';
	span.classList.remove('hide');
    }
    else {
	span.classList.add('hide');
    }

    for (var msg of document.getElementById("logdiv").children) {
	if (msg.classList.contains(type)) {
	    msg.style.display = disp;
	}
    }
}


function add_to_summary(rowdata, num) {
    var cell = 'td';
    if (num == 0) {
	cell = 'th';
	summary_table_html += "<tr><th>&nbsp;</th>";
    }
    else {
	summary_table_html += "<tr class='hoverable'><td>"+num+".</td>";
    }

    for (var i in rowdata) {
	var listlink = '';
	if (cell == 'th') {
	columnlist[i] = [];
	listlink += "&nbsp;<a href='javascript:add_items_to_list(\"A\",\"" +i+ "\");' title='Add column items to list A'>&nbsp;[+A]&nbsp;</a>";
	listlink += "&nbsp;<a href='javascript:add_items_to_list(\"B\",\"" +i+ "\");' title='Add column items to list B'>&nbsp;[+B]&nbsp;</a>";
	}
	else {
	columnlist[i][rowdata[i]] = 1;
	}
	summary_table_html += '<'+cell+'>' + rowdata[i] + listlink + '</'+cell+'>';
    }
    summary_table_html += '</tr>';
}


function add_kg_html() {  // was: process_kg(kg) {
    // knowledge graph is stored in position zero of cytodata
    document.getElementById("kg_container").innerHTML += "<div onclick='sesame(this,a0_div);' id='h0_div' title='Click to expand / collapse Knowledge Graph' class='accordion'>KNOWLEDGE GRAPH<span class='r100'><span title='Knowledge Graph' class='qprob'>KG</span></span></div>";

    document.getElementById("kg_container").innerHTML += "<div id='a0_div' class='panel'><table class='t100'><tr><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj[0].reset();'>&#8635;</a><br><a title='breadthfirst layout' onclick='cylayout(0,\"breadthfirst\");'>B</a><br><a title='force-directed layout' onclick='cylayout(0,\"cose\");'>F</a><br><a title='circle layout' onclick='cylayout(0,\"circle\");'>C</a><br><a title='random layout' onclick='cylayout(0,\"random\");'>R</a>  </td><td class='cytograph_kg' style='width:100%;'><div style='height: 100%; width: 100%' id='cy0'></div></td></tr><tr><td></td><td><div id='d0_div'><i>Click on a node or edge to get details</i></div></td></tr></table></div>";

}



function process_graph(gne,gid) {
    cytodata[gid] = [];
    for (var gnode of gne.nodes) {
	gnode.parentdivnum = gid; // helps link node to div when displaying node info on click
	if (gnode.node_id) { // deal with QueryGraphNode (QNode)
	    gnode.id = gnode.node_id;
	}
	if (gnode.curie) {
	    if (gnode.name) {
		gnode.name += " ("+gnode.curie+")";
	    }
	    else {
		gnode.name = gnode.curie;
	    }
	}
	if (!gnode.name) {
	    if (gnode.type)
		gnode.name = gnode.type + "s?";
	    else
		gnode.name = "(Any)";
	}

        var tmpdata = { "data" : gnode };
        cytodata[gid].push(tmpdata);
    }

    for (var gedge of gne.edges) {
	gedge.parentdivnum = gid;
        gedge.source = gedge.source_id;
        gedge.target = gedge.target_id;

        var tmpdata = { "data" : gedge }; // already contains id(?)
        cytodata[gid].push(tmpdata);
    }


    if (gid == 999) {
	for (var gnode of gne.nodes) {
	    qgids.push(gnode.id);

	    var tmpdata = { "id"     : gnode.id,
			    "is_set" : gnode.is_set,
			    "name"   : gnode.name,
			    "desc"   : gnode.description,
			    "curie"  : gnode.curie,
			    "type"   : gnode.type
			  };

	    input_qg.nodes.push(tmpdata);
	}

	for (var gedge of gne.edges) {
	    qgids.push(gedge.id);

	    var tmpdata = { "id"       : gedge.id,
			    "negated"  : null,
			    "relation" : null,
			    "source_id": gedge.source_id,
			    "target_id": gedge.target_id,
			    "type"     : gedge.type
			  };
	    input_qg.edges.push(tmpdata);
	}
    }

}


function process_results(reslist,kg) {
    for (var i = 0; i < reslist.length; i++) {
	var num = Number(i) + 1;

        if ( reslist[i].row_data ) {
            add_to_summary(reslist[i].row_data, num);
	}

	var ess = '';
	if (reslist[i].essence) {
	    ess = reslist[i].essence;
	}
	var cnf = 0;
	if (Number(reslist[i].confidence)) {
	    cnf = Number(reslist[i].confidence).toFixed(2);
	}
	var pcl = (cnf>=0.9) ? "p9" : (cnf>=0.7) ? "p7" : (cnf>=0.5) ? "p5" : (cnf>=0.3) ? "p3" : "p1";

	var rsrc = '';
	if (reslist[i].reasoner_id) {
	    rsrc = reslist[i].reasoner_id;
	}
	var rscl = (rsrc=="RTX") ? "srtx" : (rsrc=="Indigo") ? "sind" : (rsrc=="Robokop") ? "srob" : "p0";

	var rid = reslist[i].id.substr(reslist[i].id.lastIndexOf('/') + 1);
	var fid = "feedback_" + rid;
	var fff = "feedback_form_" + rid;
	
        document.getElementById("result_container").innerHTML += "<div onclick='sesame(this,a"+num+"_div);' id='h"+num+"_div' title='Click to expand / collapse result "+num+"' class='accordion'>Result "+num+" :: <b>"+ess+"</b><span class='r100'><span title='confidence="+cnf+"' class='"+pcl+" qprob'>"+cnf+"</span><span title='source="+rsrc+"' class='"+rscl+" qprob'>"+rsrc+"</span></span></div>";

	document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><table class='t100'><tr><td class='textanswer'>"+reslist[i].description+"</td><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj["+num+"].reset();'>&#8635;</a><br><a title='breadthfirst layout' onclick='cylayout("+num+",\"breadthfirst\");'>B</a><br><a title='force-directed layout' onclick='cylayout("+num+",\"cose\");'>F</a><br><a title='circle layout' onclick='cylayout("+num+",\"circle\");'>C</a><br><a title='random layout' onclick='cylayout("+num+",\"random\");'>R</a>	</td><td class='cytograph'><div style='height: 100%; width: 100%' id='cy"+num+"'></div></td></tr><tr><td><span id='"+fid+"'><i>User Feedback</i><hr><span id='"+fff+"'><a href='javascript:add_fefo(\""+rid+"\",\"a"+num+"_div\");'>Add Feedback</a></span><hr></span></td><td></td><td><div id='d"+num+"_div'><i>Click on a node or edge to get details</i></div></td></tr></table></div>";

        cytodata[num] = [];

	//console.log("=================== CYTO i:"+i+"  #nb:"+reslist[i].node_bindings.length);

        for (var nb of reslist[i].node_bindings) {
	    //console.log("=================== i:"+i+"  item:"+nb);
	    var kmne = Object.create(kg.nodes.find(item => item.id == nb.kg_id));
            kmne.parentdivnum = num;
            //console.log("=================== kmne:"+kmne.id);
	    var tmpdata = { "data" : kmne };
	    cytodata[num].push(tmpdata);
	}

	for (var eb of reslist[i].edge_bindings) {
	    if (Array.isArray(eb.kg_id)) {
		for (var kgid of eb.kg_id) {
                    var kmne = Object.create(kg.edges.find(item => item.id == kgid));
		    kmne.parentdivnum = num;
		    //console.log("=================== kmne:"+kmne.id);

		    var tmpdata = { "data" : kmne };
		    cytodata[num].push(tmpdata);
		}
	    }
	    else {
		var kmne = Object.create(kg.edges.find(item => item.id == eb.kg_id));
		kmne.parentdivnum = num;
		//console.log("=================== kmne:"+kmne.id);

		var tmpdata = { "data" : kmne };
		cytodata[num].push(tmpdata);
	    }
	}
    }
}



function add_result(reslist) {
    document.getElementById("result_container").innerHTML += "<H2>Results:</H2>";

    for (var i in reslist) {
	var num = Number(i) + 1;

        var ess = '';
        if (reslist[i].essence) {
            ess = reslist[i].essence;
        }
	var prb = 0;
	if (Number(reslist[i].confidence)) {
	    prb = Number(reslist[i].confidence).toFixed(2);
	}
	var pcl = (prb>=0.9) ? "p9" : (prb>=0.7) ? "p7" : (prb>=0.5) ? "p5" : (prb>=0.3) ? "p3" : "p1";

	if (reslist[i].result_type == "neighborhood graph") {
	    prb = "Neighborhood Graph";
	    pcl = "p0";
	}

	var rsrc = '';
	if (reslist[i].reasoner_id) {
	    rsrc = reslist[i].reasoner_id;
	}
	var rscl = (rsrc=="RTX") ? "srtx" : (rsrc=="Indigo") ? "sind" : (rsrc=="Robokop") ? "srob" : "p0";

	var rid = reslist[i].id.substr(reslist[i].id.lastIndexOf('/') + 1);
	var fid = "feedback_" + rid;
	var fff = "feedback_form_" + rid;

	document.getElementById("result_container").innerHTML += "<div onclick='sesame(this,a"+num+"_div);' id='h"+num+"_div' title='Click to expand / collapse result "+num+"' class='accordion'>Result "+num+" :: <b>"+ess+"</b><span class='r100'><span title='confidence="+prb+"' class='"+pcl+" qprob'>"+prb+"</span><span title='source="+rsrc+"' class='"+rscl+" qprob'>"+rsrc+"</span></span></div>";


	if (reslist[i].result_graph == null) {
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><br>"+reslist[i].description+"<br><br><span id='"+fid+"'><i>User Feedback</i></span></div>";

	}
	else {
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><table class='t100'><tr><td class='textanswer'>"+reslist[i].description+"</td><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj["+i+"].reset();'>&#8635;</a><br><a title='breadthfirst layout' onclick='cylayout("+i+",\"breadthfirst\");'>B</a><br><a title='force-directed layout' onclick='cylayout("+i+",\"cose\");'>F</a><br><a title='circle layout' onclick='cylayout("+i+",\"circle\");'>C</a><br><a title='random layout' onclick='cylayout("+i+",\"random\");'>R</a>	</td><td class='cytograph'><div style='height: 100%; width: 100%' id='cy"+num+"'></div></td></tr><tr><td><span id='"+fid+"'><i>User Feedback</i><hr><span id='"+fff+"'><a href='javascript:add_fefo(\""+rid+"\",\"a"+num+"_div\");'>Add Feedback</a></span><hr></span></td><td></td><td><div id='d"+num+"_div'><i>Click on a node or edge to get details</i></div></td></tr></table></div>";


	    if ( reslist[i].row_data ) {
		add_to_summary(reslist[i].row_data, num);
	    }

	    cytodata[i] = [];
	    var gd = reslist[i].result_graph;

	    for (var node of gd.nodes) {
		node.parentdivnum = num; // helps link node to div when displaying node info on click
		var tmpdata = { "data" : node }; // already contains id
		cytodata[i].push(tmpdata);

		// DEBUG
		//document.getElementById("cy"+num).innerHTML += "NODE: name="+ node.name + " -- accession=" + node.accession + "<BR>";
	    }

	    for (var g of gd.edges) {
		var edge = JSON.parse(JSON.stringify(g)); // cheap and deep copy
		edge.parentdivnum = num;
                edge.id     = g.source_id + '--' + g.target_id;
		edge.source = g.source_id;
		edge.target = g.target_id;
		edge.source_id = null;
		edge.target_id = null;

		var tmpdata = { "data" : edge };
		cytodata[i].push(tmpdata);
	    }
	}
    }

    // sesame(h1_div,a1_div);
    // add_cyto();
}



function add_cyto() {

    for (var i in cytodata) {
	if (cytodata[i] == null) continue;

	var num = Number(i);// + 1;

//	console.log("---------------cyto i="+i);
	cyobj[i] = cytoscape({
	    container: document.getElementById('cy'+num),
	    style: cytoscape.stylesheet()
		.selector('node')
		.css({
		    'background-color': function(ele) { return mapNodeColor(ele); } ,
		    'shape': function(ele) { return mapNodeShape(ele); } ,
		    'width': '20',
		    'height': '20',
		    'content': 'data(name)'
		})
		.selector('edge')
		.css({
		    'curve-style' : 'bezier',
		    'line-color': '#aaf',
		    'target-arrow-color': '#aaf',
		    'width': function(ele) { if (ele.data().weight) { return ele.data().weight; } return 2; },
                    'content': 'data(name)',
		    'target-arrow-shape': 'triangle',
		    'opacity': 0.8,
		    'content': function(ele) { if ((ele.data().parentdivnum > 900) && ele.data().type) { return ele.data().type; } return '';}
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

	if (i > 900) {
	    cyobj[i].on('tap','node', function() {
		document.getElementById('qg_edge_n'+UIstate.nodedd).value = this.data('id');
		UIstate.nodedd = 3 - UIstate.nodedd;
		get_possible_edges();
	    });

	    return;
	}

	cyobj[i].on('tap','node', function() {
	    var dnum = 'd'+this.data('parentdivnum')+'_div';

	    document.getElementById(dnum).innerHTML = "<b>Name:</b> " + this.data('name') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>ID:</b> " + this.data('id') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>URI:</b> <a target='_blank' href='" + this.data('uri') + "'>" + this.data('uri') + "</a><br>";
	    document.getElementById(dnum).innerHTML+= "<b>Type:</b> " + this.data('type') + "<br>";

	    if (this.data('description') !== 'UNKNOWN' && this.data('description') !== 'None') {
		document.getElementById(dnum).innerHTML+= "<b>Description:</b> " + this.data('description') + "<br>";
	    }

	    show_attributes(dnum, this.data('node_attributes'));

	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

	cyobj[i].on('tap','edge', function() {
	    var dnum = 'd'+this.data('parentdivnum')+'_div';

	    document.getElementById(dnum).innerHTML = this.data('source');
	    document.getElementById(dnum).innerHTML+= " <b>" + this.data('type') + "</b> ";
	    document.getElementById(dnum).innerHTML+= this.data('target') + "<br>";

	    if(this.data('provided_by').startsWith("http"))
            	document.getElementById(dnum).innerHTML+= "<b>Provenance:</b> <a target='_blank' href='" + this.data('provided_by') + "'>" + this.data('provided_by') + "</a><br>";
	    else
            	document.getElementById(dnum).innerHTML+= "<b>Provenance:</b> " + this.data('provided_by') + "<br>";


	    if(this.data('confidence'))
                document.getElementById(dnum).innerHTML+= "<b>Confidence:</b> " + Number(this.data('confidence')).toPrecision(3) + "<br>";

            if(this.data('weight'))
                document.getElementById(dnum).innerHTML+= "<b>Weight:</b> " + Number(this.data('weight')).toPrecision(3) + "<br>";


	    var fields = [ "evidence_type","qualifiers","negated","relation","is_defined_by","defined_datetime","publications","id","qedge_id" ];
	    for (var field of fields) {
		if(this.data(field)) {
		    var span = document.createElement("span");
		    span.className = "fieldname";
		    span.appendChild(document.createTextNode(field+": "));
		    document.getElementById(dnum).appendChild(span);
		    document.getElementById(dnum).appendChild(document.createTextNode(this.data(field)));
		    document.getElementById(dnum).appendChild(document.createElement("br"));
		}
	    }

	    show_attributes(dnum, this.data('edge_attributes'));

	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

    }

}

function show_attributes(html_id, atts) {
    if (atts == null)  { return; }

    var linebreak = "<hr>";

    for (var att of atts) {
	var snippet = linebreak;

	if (att.name != null) {
	    snippet += "<b>" + att.name + "</b>";
	    if (att.type != null) {
		snippet += " (" + att.type + ")";
	    }
	    snippet += " : ";
	}
	if (att.url != null) {
	    snippet += "<a target='rtxext' href='" + att.url + "'>";
	}
	if (att.value != null) {
	    var val = att.value;
	    if (att.name == "probability_drug_treats" |
		att.name == "jaccard_index" |
		att.name == "ngd" |
		att.name == "paired_concept_freq" |
		att.name == "observed_expected_ratio" |
		att.name == "chi_square") {
		val = Number(val);
		val = val.toPrecision(3);
	    }
	    snippet += val;
	}
	else if (att.url != null) {
	    snippet += "[ url ]";
	}
	if (att.url != null) {
	    snippet += "</a>";
	}

	document.getElementById(html_id).innerHTML+= snippet;
	linebreak = "<br>";
    }

}


function cylayout(index,layname) {
    var layout = cyobj[index].layout({
	idealEdgeLength: 100,
        nodeOverlap: 20,
	refresh: 20,
        fit: true,
        padding: 30,
        componentSpacing: 100,
        nodeRepulsion: 10000,
        edgeElasticity: 100,
        nestingFactor: 5,
	name: layname,
	animationDuration: 500,
	animate: 'end'
    });

    layout.run();
}

function mapNodeShape (ele) {
    var ntype = ele.data().type;
    if (ntype == "microRNA")           { return "hexagon";}
    if (ntype == "metabolite")         { return "heptagon";}
    if (ntype == "protein")            { return "octagon";}
    if (ntype == "pathway")            { return "vee";}
    if (ntype == "disease")            { return "triangle";}
    if (ntype == "molecular_function") { return "rectangle";}
    if (ntype == "cellular_component") { return "ellipse";}
    if (ntype == "biological_process") { return "tag";}
    if (ntype == "chemical_substance") { return "diamond";}
    if (ntype == "anatomical_entity")  { return "rhomboid";}
    if (ntype == "phenotypic_feature") { return "star";}
    return "rectangle";
}

function mapNodeColor (ele) {
    var ntype = ele.data().type;
    if (ntype == "microRNA")           { return "orange";}
    if (ntype == "metabolite")         { return "aqua";}
    if (ntype == "protein")            { return "black";}
    if (ntype == "pathway")            { return "gray";}
    if (ntype == "disease")            { return "red";}
    if (ntype == "molecular_function") { return "blue";}
    if (ntype == "cellular_component") { return "purple";}
    if (ntype == "biological_process") { return "green";}
    if (ntype == "chemical_substance") { return "yellowgreen";}
    if (ntype == "anatomical_entity")  { return "violet";}
    if (ntype == "phenotypic_feature") { return "indigo";}
    return "#04c";
}




function edit_qg() {
    cytodata[999] = [];
    if (cyobj[999]) {cyobj[999].elements().remove();}

    for (var gnode of input_qg.nodes) {
	var name = "";

	if (gnode.name) {
	    name = gnode.name;
	}
	else if (gnode.curie) {
	    name = gnode.curie;
	}
	else if (gnode.type) {
	    name = gnode.type + "s?";
	}
	else {
	    name = "(Any)";
	}

        cyobj[999].add( {
	    "data" : {
		"id"   : gnode.id,
		"name" : name,
		"type" : gnode.type,
		"parentdivnum" : 999 },
//	    "position" : {x:100*(qgid-nn), y:50+nn*50}
	} );
    }

    for (var gedge of input_qg.edges) {
	cyobj[999].add( {
	    "data" : {
		"id"     : gedge.id,
		"source" : gedge.source_id,
		"target" : gedge.target_id,
		"type"   : gedge.type,
		"parentdivnum" : 999 }
	} );
    }

    cylayout(999,"breadthfirst");
    document.getElementById('qg_form').style.visibility = 'visible';
    document.getElementById('qg_form').style.maxHeight = "100%";
    update_kg_edge_input();
    display_query_graph_items();

    document.getElementById("devdiv").innerHTML +=  "Copied query_graph to edit window<br>";
}


function display_query_graph_items() {
    var kghtml = '';
    var nitems = 0;

    input_qg.nodes.forEach(function(result, index) {
	nitems++;
        kghtml += "<tr class='hoverable'><td>"+result.id+"</td><td title='"+result.desc+"'>"+(result.name==null?"-":result.name)+"</td><td>"+(result.curie==null?"<i>(any node)</i>":result.curie)+"</td><td>"+(result.type==null?"<i>(any)</i>":result.type)+"</td><td><a href='javascript:remove_node_from_query_graph(\"" + result.id +"\");'/> Remove </a></td></tr>";
    });

    input_qg.edges.forEach(function(result, index) {
        kghtml += "<tr class='hoverable'><td>"+result.id+"</td><td>-</td><td>"+result.source_id+"--"+result.target_id+"</td><td>"+(result.type==null?"<i>(any)</i>":result.type)+"</td><td><a href='javascript:remove_edge_from_query_graph(\"" + result.id +"\");'/> Remove </a></td></tr>";
    });


    if (nitems > 0) {
	kghtml = "<table class='sumtab'><tr><th>Id</th><th>Name</th><th>Item</th><th>Type</th><th>Action</th></tr>" + kghtml + "</table>";
    }

    document.getElementById("qg_items").innerHTML = kghtml;
}


function add_edge_to_query_graph() {
    var n1 = document.getElementById("qg_edge_n1").value;
    var n2 = document.getElementById("qg_edge_n2").value;
    var et = document.getElementById("qg_edge_type").value;

    if (n1=='' || n2=='' || et=='') {
	document.getElementById("statusdiv").innerHTML = "<p class='error'>Please select two nodes and a valid edge type</p>";
	return;
    }

    document.getElementById("statusdiv").innerHTML = "<p>Added an edge of type <i>"+et+"</i></p>";
    var qgid = get_qg_id();

    if (et=='NONSPECIFIC') { et = null; }

    cyobj[999].add( {
	"data" : { "id"     : qgid,
		   "source" : n1,
		   "target" : n2,
		   "type"   : et,
		   "parentdivnum" : 999 }
    } );
    cylayout(999,"breadthfirst");

    var tmpdata = { "id"       : qgid,
		    "negated"  : null,
		    "relation" : null,
		    "source_id": n1,
		    "target_id": n2,
		    "type"     : et
		  };

    input_qg.edges.push(tmpdata);    
    display_query_graph_items();
}


function update_kg_edge_input() {
    document.getElementById("qg_edge_n1").innerHTML = '';
    document.getElementById("qg_edge_n2").innerHTML = '';

    var opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = '';
    opt.innerHTML = "Source Node ("+input_qg.nodes.length+")&nbsp;&nbsp;&nbsp;&#8675;";
    document.getElementById("qg_edge_n1").appendChild(opt);

    opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = '';
    opt.innerHTML = "Target Node ("+input_qg.nodes.length+")&nbsp;&nbsp;&nbsp;&#8675;";
    document.getElementById("qg_edge_n2").appendChild(opt);

    if (input_qg.nodes.length < 2) {
	opt = document.createElement('option');
	opt.value = '';
	opt.innerHTML = "Must have 2 nodes minimum";
	document.getElementById("qg_edge_n1").appendChild(opt);
	document.getElementById("qg_edge_n2").appendChild(opt.cloneNode(true));
	return;
    }

    input_qg.nodes.forEach(function(qgnode) {
	for (var x = 1; x <=2; x++) {
            opt = document.createElement('option');
	    opt.value = qgnode["id"];
	    opt.innerHTML = qgnode["curie"] ? qgnode["curie"] : qgnode["type"] ? qgnode["type"] : qgnode["id"];
	    document.getElementById("qg_edge_n"+x).appendChild(opt);
	}
    });
    get_possible_edges();
}

function get_possible_edges() {
    var qet_node = document.getElementById("qg_edge_type");
    qet_node.innerHTML = '';

    var opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = '';
    opt.innerHTML = "Edge Type&nbsp;&nbsp;&nbsp;&#8675;";
    qet_node.appendChild(opt);

    var edge1 = document.getElementById("qg_edge_n1").value;
    var edge2 = document.getElementById("qg_edge_n2").value;

    if (!(edge1 && edge2) || (edge1 == edge2)) {
	opt = document.createElement('option');
	opt.value = '';
	opt.innerHTML = "Please select 2 different nodes";
	qet_node.appendChild(opt);
	return;
    }

    var nt1 = input_qg.nodes.filter(function(node){
	return node["id"] == edge1;
    });
    var nt2 = input_qg.nodes.filter(function(node){
	return node["id"] == edge2;
    });

    qet_node.innerHTML = '';
    opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = '';
    opt.innerHTML = "Populating edges...";
    qet_node.appendChild(opt);

    if (nt1[0].type == null || nt2[0].type == null) {
	// NONSPECIFIC nodes only get NONSPECIFIC edges...for now
        qet_node.innerHTML = '';
        opt = document.createElement('option');
	opt.value = 'NONSPECIFIC';
	opt.innerHTML = "Unspecified/Non-specific";
	qet_node.appendChild(opt);
	return;
    }

    var relation = "A --> B";
    if (!(nt2[0].type in predicates[nt1[0].type])) {
	[nt1, nt2] = [nt2, nt1]; // swap
	relation = "B --> A";
    }

    if (nt2[0].type in predicates[nt1[0].type]) {
	if (predicates[nt1[0].type][nt2[0].type].length == 1) {
	    qet_node.innerHTML = '';
	    opt = document.createElement('option');
	    opt.value = predicates[nt1[0].type][nt2[0].type][0];
	    opt.innerHTML = predicates[nt1[0].type][nt2[0].type][0] + " ["+relation+"]";
	    qet_node.appendChild(opt);
	}
	else {
	    qet_node.innerHTML = '';
	    opt = document.createElement('option');
	    opt.style.borderBottom = "1px solid black";
	    opt.value = '';
            opt.innerHTML = "Edge Type ["+relation+"]&nbsp; ("+predicates[nt1[0].type][nt2[0].type].length+")&nbsp;&nbsp;&nbsp;&#8675;";
	    qet_node.appendChild(opt);

	    for (var pred of predicates[nt1[0].type][nt2[0].type]) {
		var opt = document.createElement('option');
		opt.value = pred;
		opt.innerHTML = pred;
		qet_node.appendChild(opt);
	    }

            opt = document.createElement('option');
	    opt.value = 'NONSPECIFIC';
	    opt.innerHTML = "Unspecified/Non-specific";
	    qet_node.appendChild(opt);
	}

    }
    else {
        qet_node.innerHTML = '';
	opt = document.createElement('option');
	opt.value = '';
	opt.innerHTML = "-- No edge types found --";
	qet_node.appendChild(opt);
    }
}


function add_nodetype_to_query_graph(nodetype) {
    document.getElementById("allnodetypes").value = '';
    document.getElementById("allnodetypes").blur();

    document.getElementById("statusdiv").innerHTML = "<p>Added a node of type <i>"+nodetype+"</i></p>";
    var qgid = get_qg_id();

    var nt = nodetype;

    cyobj[999].add( {
        "data" : { "id"   : qgid,
		   "name" : nodetype+"s",
		   "type" : nt,
		   "parentdivnum" : 999 },
//        "position" : {x:100*qgid, y:50}
    } );
    cyobj[999].reset();
    cylayout(999,"breadthfirst");

    if (nodetype=='NONSPECIFIC') { nt = null; }
    var tmpdata = { "id"     : qgid,
		    "is_set" : null,
		    "name"   : null,
		    "desc"   : "Generic " + nodetype,
		    "curie"  : null,
		    "type"   : nt
		  };

    input_qg.nodes.push(tmpdata);
    update_kg_edge_input();
    display_query_graph_items();
}

function enter_node(ele) {
    if (event.key === 'Enter') {
	add_node_to_query_graph();
    }
}

function add_node_to_query_graph() {
    var thing = document.getElementById("newquerynode").value;
    document.getElementById("newquerynode").value = '';

    if (thing == '') {
        document.getElementById("statusdiv").innerHTML = "<p class='error'>Please enter a node value</p>";
	return;
    }

    var things = check_entity(thing);
    document.getElementById("devdiv").innerHTML +=  "-- found " + things.num + " nodes in graph<br>";

    if (things.num > 0) {
	if (things.num == 1) {
            document.getElementById("statusdiv").innerHTML = "<p>Found <b>" + things.num + "</b> node that matches <i>"+thing+"</i> in our knowledge graph.</p>";
	}
	else {
            document.getElementById("statusdiv").innerHTML = "<p>Found <b>" + things.num + "</b> nodes that match <i>"+thing+"</i> in our knowledge graph.</p><span class='error'>Please choose node(s) of interest by removing unwanted ones from the query graph.</span>";
	}
	sesame('openmax',statusdiv);
	for (var nn = 0; nn < things.num; nn++) {
	    var qgid = get_qg_id();

	    cyobj[999].add( {
		"data" : { "id"   : qgid,
			   "name" : thing,
			   "type" : things[nn].type,
			   "parentdivnum" : 999 },
//		"position" : {x:100*(qgid-nn), y:50+nn*50}
	    } );

	    var tmpdata = { "id"     : qgid,
			    "is_set" : null,
			    "name"   : thing,
			    "desc"   : things[nn].desc,
			    "curie"  : things[nn].curie,
			    "type"   : things[nn].type
			  };

	    document.getElementById("devdiv").innerHTML +=  "-- found a curie = " + things[nn].curie + "<br>";

	    input_qg.nodes.push(tmpdata);
	}
	cyobj[999].reset();
	cylayout(999,"breadthfirst");

	update_kg_edge_input();
	display_query_graph_items();
    }
    else {
        document.getElementById("statusdiv").innerHTML = "<p><span class='error'>" + thing + "</span> is not in our knowledge graph.</p>";
	sesame('openmax',statusdiv);
    }

}


function remove_edge_from_query_graph(edgeid) {
    cyobj[999].remove("#"+edgeid);

    input_qg.edges.forEach(function(result, index) {
	if (result["id"] == edgeid) {
	    //Remove from array
	    input_qg.edges.splice(index, 1);
	}
    });

    var idx = qgids.indexOf(edgeid);
    if (idx > -1)
	qgids.splice(idx, 1);

    display_query_graph_items();
}

function remove_node_from_query_graph(nodeid) {
    cyobj[999].remove("#"+nodeid);

    input_qg.nodes.forEach(function(result, index) {
	if (result["id"] == nodeid) {
	    //Remove from array
	    input_qg.nodes.splice(index, 1);
	}
    });

    var idx = qgids.indexOf(nodeid);
    if (idx > -1)
	qgids.splice(idx, 1);

    // remove items starting from end of array...
    for (var k = input_qg.edges.length - 1; k > -1; k--){
	if (input_qg.edges[k].source_id == nodeid) {
	    input_qg.edges.splice(k, 1);
	}
	else if (input_qg.edges[k].target_id == nodeid) {
	    input_qg.edges.splice(k, 1);
	}
    }

    update_kg_edge_input();
    display_query_graph_items();
}

function clear_qg(m) {
    if (cyobj[999]) { cyobj[999].elements().remove(); }
    input_qg = { "edges": [], "nodes": [] };
    update_kg_edge_input();
    get_possible_edges();
    display_query_graph_items();
    qgids = [];
    if (m==1){
	document.getElementById("statusdiv").innerHTML = "<p>Query Graph has been cleared.</p>";
    }
    document.getElementById('qg_form').style.visibility = 'visible';
    document.getElementById('qg_form').style.maxHeight = "100%";
}

function get_qg_id() {
    var new_id = 0;
    do {
	if (!qgids.includes("qg"+new_id))
	    break;
	new_id++;
    } while (new_id < 100);

    qgids.push("qg"+new_id);
    return "qg"+new_id;
}


function rem_fefo(res_id,res_div_id) {
    var fff = "feedback_form_" + res_id;

    document.getElementById(fff).innerHTML = "<a href='javascript:add_fefo(\""+res_id+"\",\""+res_div_id+"\");'>Add Feedback</a>";

    sesame('openmax',document.getElementById(res_div_id));
}

function add_fefo(res_id,res_div_id) {
    var fff = "feedback_form_" + res_id;
    var uuu = getCookie('RTXuser');

    document.getElementById(fff).innerHTML = "Please provide feedback on this result:<br>";

    document.getElementById(fff).innerHTML+= "<table><tr><td><b>Rating:</b></td><td><span class='ratings'><select id='"+fff+"_rating'><option value=''>Please select a rating&nbsp;&nbsp;&nbsp;&#8675;</option></select></span></td></tr><tr><td><b>Expertise:</b></td><td><span class='ratings'><select id='"+fff+"_expertise'><option value=''>What is your expertise on this subject?&nbsp;&nbsp;&nbsp;&#8675;</option></select></span></td></tr><tr><td><b>Full Name:</b></td><td><input type='text' id='"+fff+"_fullname' value='"+uuu+"' maxlength='60' size='60'></input></td</tr><tr><td><b>Comment:</b></td><td><textarea id='"+fff+"_comment' maxlength='60000' rows='7' cols='60'></textarea></td</tr><tr><td></td><td><input type='button' class='questionBox button' name='action' value='Submit' onClick='javascript:submitFeedback(\""+res_id+"\",\""+res_div_id+"\");'/>&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:rem_fefo(\""+res_id+"\",\""+res_div_id+"\");'>Cancel</a></td></tr></table><span id='"+fff+"_msgs' class='error'></span>";

    for (var i in fb_ratings) {
	var opt = document.createElement('option');
	opt.value = i;
	opt.innerHTML = fb_ratings[i].tag+" :: "+fb_ratings[i].desc;
	document.getElementById(fff+"_rating").appendChild(opt);
    }

    for (var i in fb_explvls) {
	var opt = document.createElement('option');
	opt.value = i;
	opt.innerHTML = fb_explvls[i].tag+" :: "+fb_explvls[i].desc;
	document.getElementById(fff+"_expertise").appendChild(opt);
    } 

    sesame('openmax',document.getElementById(res_div_id));
}

function submitFeedback(res_id,res_div_id) {
    var fff = "feedback_form_" + res_id;

    var rat = document.getElementById(fff+"_rating").value;
    var exp = document.getElementById(fff+"_expertise").value;
    var nom = document.getElementById(fff+"_fullname").value;
    var cmt = document.getElementById(fff+"_comment").value;

    if (!rat || !exp || !nom) {
	document.getElementById(fff+"_msgs").innerHTML = "Please provide a <u>rating</u>, <u>expertise level</u>, and <u>name</u> in your feedback on this result";
	return;
    }

    var feedback = {};
    feedback.rating_id = parseInt(rat);
    feedback.expertise_level_id = parseInt(exp);
    feedback.comment = cmt;
    feedback.commenter_full_name = nom;

    // feedback.commenter_id = 1;


    var xhr6 = new XMLHttpRequest();
    xhr6.open("post",  baseAPI + "api/rtx/v1/result/" + res_id + "/feedback", true);
    xhr6.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr6.send(JSON.stringify(feedback));

    xhr6.onloadend = function() {
	var jsonObj6 = JSON.parse(xhr6.responseText);
	document.getElementById("devdiv").innerHTML += "<br>================================================================= FEEDBACK-POST::<PRE>\nPOST to " +  baseAPI + "api/rtx/v1/result/" + res_id + "/feedback ::<br>" + JSON.stringify(feedback,null,2) + "<br>------<br>" + JSON.stringify(jsonObj6,null,2) + "</PRE>";

	if ( xhr6.status == 200 ) {
	    document.getElementById(fff+"_msgs").innerHTML = "Your feedback has been recorded...";
	    setRTXUserCookie(nom);

	    var xhr7 = new XMLHttpRequest();
	    xhr7.open("get",  baseAPI + "api/rtx/v1/result/" + res_id + "/feedback", true);
	    xhr7.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
	    xhr7.send(null);

	    xhr7.onloadend = function() {
		var jsonObj7 = JSON.parse(xhr7.responseText);
		if ( xhr7.status == 200 ) {
		    var fid = "feedback_" + res_id;
		    document.getElementById(fid).innerHTML = "<i>User Feedback (updated)</i><hr><span class='error'>Your feedback has been recorded.  Thank you, "+nom+"!</span><hr>";

		    for (var i in jsonObj7) {
			insert_feedback_item(fid, jsonObj7[i]);
		    }
		    sesame('openmax',document.getElementById(res_div_id));
		}
		else {
		    document.getElementById(fff+"_msgs").innerHTML = "There was an error with this ("+jsonObj7.detail+"). Please try again.";
		}
	    }

	}
	else {
	    document.getElementById(fff+"_msgs").innerHTML = "There was an error with this submission ("+jsonObj6.detail+"). Please try again.";
	}

    }

}


function add_feedback() {
    if (fb_explvls.length == 0 || fb_ratings.length == 0) {
	get_feedback_fields();
    }

    var xhr3 = new XMLHttpRequest();
    xhr3.open("get",  baseAPI + "api/rtx/v1/message/" + message_id + "/feedback", true);
    xhr3.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr3.send(null);

    xhr3.onloadend = function() {
	if ( xhr3.status == 200 ) {
	    var jsonObj3 = JSON.parse(xhr3.responseText);
            add_to_dev_info("FEEDBACK",jsonObj3);

	    for (var i in jsonObj3) {
		var fid = "feedback_" + jsonObj3[i].result_id.substr(jsonObj3[i].result_id.lastIndexOf('/') + 1);

		if (document.getElementById(fid)) {
		    insert_feedback_item(fid, jsonObj3[i]);
		}
		else {
		    document.getElementById("devdiv").innerHTML += "[warn] Feedback " + fid + " does not exist in response!<br>";
		}
	    }

	}
	sesame(h1_div,a1_div);
//	sesame(h0_div,a0_div);
    };


}


function insert_feedback_item(el_id, feed_obj) {
    var prb = feed_obj.rating_id;
    var pcl = (prb<=2) ? "p9" : (prb<=4) ? "p7" : (prb<=5) ? "p5" : (prb<=6) ? "p3" : (prb<=7) ? "p0" : "p1";
    var pex = feed_obj.expertise_level_id;
    var pxl = (pex==1) ? "p9" : (pex==2) ? "p7" : (pex==3) ? "p5" : (pex==4) ? "p3" : "p1";

    document.getElementById(el_id).innerHTML += "<table><tr><td><b>Rating:</b></td><td style='width:100%'><span class='"+pcl+" frating' title='" + fb_ratings[feed_obj.rating_id].desc +  "'>" + fb_ratings[feed_obj.rating_id].tag + "</span>&nbsp;<span class='tiny'>by <b>" + feed_obj.commenter_full_name + "</b> <span class='"+pxl+" explevel' title='" + fb_explvls[feed_obj.expertise_level_id].tag + " :: " + fb_explvls[feed_obj.expertise_level_id].desc + "'>&nbsp;</span></span><i class='tiny' style='float:right'>" + feed_obj.datetime + "</i></td></tr><tr><td><b>Comment:</b></td><td>" + feed_obj.comment + "</td></tr></table><hr>";

}


function get_feedback_fields() {
    var xhr4 = new XMLHttpRequest();
    xhr4.open("get",  baseAPI + "api/rtx/v1/feedback/expertise_levels", true);
    xhr4.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr4.send(null);

    xhr4.onloadend = function() {
	if ( xhr4.status == 200 ) {
	    var jsonObj4 = JSON.parse(xhr4.responseText);
	    add_to_dev_info("FEEDBACK FIELDS",jsonObj4);

	    for (var i in jsonObj4.expertise_levels) {
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id] = {};
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].desc = jsonObj4.expertise_levels[i].description;
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].name = jsonObj4.expertise_levels[i].name;
		fb_explvls[jsonObj4.expertise_levels[i].expertise_level_id].tag  = jsonObj4.expertise_levels[i].tag;
	    }
	}
    };


    var xhr5 = new XMLHttpRequest();
    xhr5.open("get",  baseAPI + "api/rtx/v1/feedback/ratings", true);
    xhr5.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr5.send(null);

    xhr5.onloadend = function() {
	if ( xhr5.status == 200 ) {
	    var jsonObj5 = JSON.parse(xhr5.responseText);
	    add_to_dev_info("RATINGS",jsonObj5);

	    for (var i in jsonObj5.ratings) {
		fb_ratings[jsonObj5.ratings[i].rating_id] = {};
		fb_ratings[jsonObj5.ratings[i].rating_id].desc = jsonObj5.ratings[i].description;
		fb_ratings[jsonObj5.ratings[i].rating_id].name = jsonObj5.ratings[i].name;
		fb_ratings[jsonObj5.ratings[i].rating_id].tag  = jsonObj5.ratings[i].tag;
	    }
	}
    };
}


function get_example_questions() {
    var xhr8 = new XMLHttpRequest();
    xhr8.open("get",  baseAPI + "api/rtx/v1/exampleQuestions", true);
    xhr8.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr8.send(null);

    xhr8.onloadend = function() {
	if ( xhr8.status == 200 ) {
	    var ex_qs = JSON.parse(xhr8.responseText);

            var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "Example Questions&nbsp;&nbsp;&nbsp;&#8675;";
            document.getElementById("qqq").appendChild(opt);

	    for (var i in ex_qs) {
		opt = document.createElement('option');
		opt.value = ex_qs[i].question_text;
		opt.innerHTML = ex_qs[i].query_type_id+": "+ex_qs[i].question_text;
		document.getElementById("qqq").appendChild(opt);
	    }
	}
    };
}


function load_nodes_and_predicates() {
    var xhr11 = new XMLHttpRequest();
    xhr11.open("get",  baseAPI + "api/rtx/v1/predicates", true);
    xhr11.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr11.send(null);

    var allnodes_node = document.getElementById("allnodetypes");
    allnodes_node.innerHTML = '';

    xhr11.onloadend = function() {
        if ( xhr11.status == 200 ) {
            predicates = JSON.parse(xhr11.responseText);
            add_to_dev_info("PREDICATES",predicates);

	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "Add Node by Type&nbsp;&nbsp;&nbsp;&#8675;";
	    allnodes_node.appendChild(opt);

            for (const p in predicates) {
		opt = document.createElement('option');
		opt.value = p;
		opt.innerHTML = p;
		document.getElementById("allnodetypes").appendChild(opt);
	    }
            var opt = document.createElement('option');
	    opt.value = 'NONSPECIFIC';
	    opt.innerHTML = "Unspecified/Non-specific";
	    document.getElementById("allnodetypes").appendChild(opt);
	}
	else {
	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "-- Error Loading Node Types --";
	    allnodes_node.appendChild(opt);
	}
    };
}


function add_to_dev_info(title,jobj) {
    var dev = document.getElementById("devdiv");
    dev.appendChild(document.createElement("br"));
    dev.appendChild(document.createTextNode('='.repeat(80)+" "+title+"::"));
    var pre = document.createElement("pre");
    //pre.id = "responseJSON";
    pre.appendChild(document.createTextNode(JSON.stringify(jobj,null,2)));
    dev.appendChild(pre);
}


function setRTXUserCookie(fullname) {
    var cname = "RTXuser";
    var exdays = 7;
    var d = new Date();
    d.setTime(d.getTime()+(exdays*24*60*60*1000));
    var expires = "expires="+d.toGMTString();
    document.cookie = cname+"="+fullname+"; "+expires;
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
	var c = ca[i].trim();
	if (c.indexOf(name)==0) return c.substring(name.length,c.length);
    }
    return "";
}

function togglecolor(obj,tid) {
    var col = '#888';
    if (obj.checked == true) {
	col = '#047';
    }
    document.getElementById(tid).style.color = col;

}


// taken from http://www.activsoftware.com/
function getQueryVariable(variable) {
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i=0;i<vars.length;i++) {
	var pair = vars[i].split("=");
	if (decodeURIComponent(pair[0]) == variable) {
	    return decodeURIComponent(pair[1]);
	}
    } 
    return false;
}

// LIST FUNCTIONS
var entities  = {};
var listItems = {};
listItems['A'] = {};
listItems['B'] = {};
listItems['SESSION'] = {};
var numquery = 0;

function display_list(listId) {
    if (listId == 'SESSION') {
	display_session();
	return;
    }
    var listhtml = '';
    var numitems = 0;

    for (var li in listItems[listId]) {
	if (listItems[listId].hasOwnProperty(li)) { // && listItems[listId][li] == 1) {
	    numitems++;
	    listhtml += "<tr class='hoverable'><td>" + li + "</td><td id='list"+listId+"_entity_"+li+"'>";

	    if (entities.hasOwnProperty(li)) {
		listhtml += entities[li];
	    }
	    else {
		listhtml += "looking up...";
		entities[li] = '--';
	    }

	    listhtml += "</td><td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/> Remove </a></td></tr>";
	}
    }


    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("menunumlistitems"+listId).innerHTML = numitems;

    if (numitems > 0) {
	listhtml = "<table class='sumtab'><tr><th>Item</th><th>Entity Type(s)</th><th>Action</th></tr>" + listhtml + "</table>";
	document.getElementById("menunumlistitems"+listId).classList.add("numnew");
	document.getElementById("menunumlistitems"+listId).classList.remove("numold");
    }
    else {
	document.getElementById("menunumlistitems"+listId).classList.remove("numnew");
	document.getElementById("menunumlistitems"+listId).classList.add("numold");
    }

    listhtml = "Items in this list can be passed as input to queries that support list input, by specifying <b>["+listId+"]</b> as a query parameter.<br><br>" + listhtml + "<hr>Enter new list item or items (space and/or comma-separated; use &quot;double quotes&quot; for multi-word items):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' onkeydown='enter_item(this, \""+listId+"\");' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>";

//    listhtml += "<hr>Enter new list item or items (space and/or comma-separated):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>";

    if (numitems > 0) {
    	listhtml += "&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:delete_list(\""+listId+"\");'/> Delete List </a>";
    }

    listhtml += "<br><br>";

    document.getElementById("listdiv"+listId).innerHTML = listhtml;
//    setTimeout(function() {check_entities();sesame('openmax',document.getElementById("listdiv"+listId));}, 500);
    check_entities();
}


function get_list_as_string(listId) {
    var liststring = '[';
    var comma = '';
    for (var li in listItems[listId]) {
	if (listItems[listId].hasOwnProperty(li) && listItems[listId][li] == 1) {
	    liststring += comma + li;
	    comma = ',';
	}
    }
    liststring += ']';
    return liststring;
}



function add_items_to_list(listId,indx) {
    for (var nitem in columnlist[indx]) {
	if (columnlist[indx][nitem]) {
	    listItems[listId][nitem] = 1;
	}
    }
    display_list(listId);
}

function enter_item(ele, listId) {
    if (event.key === 'Enter') {
	add_new_to_list(listId);
    }
}

function add_new_to_list(listId) {
    //var itemarr = document.getElementById("newlistitem"+listId).value.split(/[\t ,]/);
    var itemarr = document.getElementById("newlistitem"+listId).value.match(/\w+|"[^"]+"/g);

    document.getElementById("newlistitem"+listId).value = '';
    for (var item in itemarr) {
	itemarr[item] = itemarr[item].replace(/['"]+/g,''); // remove all manner of quotes
        //console.log("=================== item:"+itemarr[item]);
	if (itemarr[item]) {
	    listItems[listId][itemarr[item]] = 1;
	}
    }
    display_list(listId);
}


function remove_item(listId,item) {
    delete listItems[listId][item];
    display_list(listId);
}


function delete_list(listId) {
    listItems[listId] = {};
    display_list(listId);
}

function check_entities() {
    for (var entity in entities) {
	if (entities[entity] == '--') {

            var xhr = new XMLHttpRequest();
            xhr.open("get",  baseAPI + "api/rtx/v1/entity/" + entity, false);
            xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
            xhr.onloadend = function() {
                var xob = JSON.parse(xhr.responseText);
		add_to_dev_info("ENTITIES",xob);

		var entstr = "";
                if ( xhr.status == 200 ) {
		    var comma = "";
                    for (var i in xob) {
                        entstr += comma + xob[i].type;
			document.getElementById("devdiv").innerHTML += comma + xob[i].type;
			comma = ", ";
                    }
	            if (entstr != "") { entstr = "<span class='explevel p9'>&check;</span>&nbsp;" + entstr; }
                }
                else {
		    entstr = "<span class='explevel p0'>&quest;</span>&nbsp;n/a";
                }

	    	if (entstr == "") { entstr = "<span class='explevel p1'>&cross;</span>&nbsp;<span class='error'>unknown</span>"; }

	    	entities[entity] = entstr;

	    	var e = document.querySelectorAll("[id$='_entity_"+entity+"']");
	    	var i = 0;
	    	for (i = 0; i < e.length; i++) {
		    e[i].innerHTML = entities[entity];
	    	}
            };

            xhr.send(null);
	}
    }
}

function check_entity(term) {
    var ent = [];
    ent.num = 0;
    if (entities[term]) { ent.num = -1; return ent; }

    var xhr = new XMLHttpRequest();
    xhr.open("get",  baseAPI + "api/rtx/v1/entity/" + term, false);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.onloadend = function() {
        var xob = JSON.parse(xhr.responseText);
        add_to_dev_info("ENTITY:"+term,xob);

        if ( xhr.status == 200 ) {
            for (var i in xob) {
		ent.num++;
		ent[i] = [];
		ent[i].curie = xob[i].curie;
		ent[i].type  = xob[i].type;
		ent[i].desc  = xob[i].description.replace(/['"]/g, '&apos;');
                entities[xob[i].curie] = xob[i].name + "::" + xob[i].type;
	    }
	}
    };

    xhr.send(null);
    return ent;
}


function add_to_session(resp_id,text) {
    numquery++;
    listItems['SESSION'][numquery] = resp_id;
    listItems['SESSION']["qtext_"+numquery] = text;
    display_session();
}

function display_session() {
    var listId = 'SESSION';
    var listhtml = '';
    var numitems = 0;

    for (var li in listItems[listId]) {
        if (listItems[listId].hasOwnProperty(li) && !li.startsWith("qtext_")) {
            numitems++;
            listhtml += "<tr><td>"+li+".</td><td><a target='_new' title='view this message in a new window' href='//"+ window.location.hostname + window.location.pathname + "?m="+listItems[listId][li]+"'>" + listItems['SESSION']["qtext_"+li] + "</a></td><td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/> Remove </a></td></tr>";
        }
    }
    if (numitems > 0) {
        listhtml += "<tr><td></td><td></td><td><a href='javascript:delete_list(\""+listId+"\");'/> Delete Session History </a></td></tr>";
    }


    if (numitems == 0) {
        listhtml = "<br>Your query history will be displayed here. It can be edited or re-set.<br><br>";
    }
    else {
        listhtml = "<table class='sumtab'><tr><td></td><th>Query</th><th>Action</th></tr>" + listhtml + "</table>";
    }

    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("menunumlistitems"+listId).innerHTML = numitems;
    document.getElementById("listdiv"+listId).innerHTML = listhtml;
}


function copyJSON() {
    var containerid = "responseJSON";

    if (document.selection) {
	var range = document.body.createTextRange();
	range.moveToElementText(document.getElementById(containerid));
	range.select().createTextRange();
	document.execCommand("copy");

    } else if (window.getSelection) {
	var range = document.createRange();
	range.selectNode(document.getElementById(containerid));
        window.getSelection().removeAllRanges();
	window.getSelection().addRange(range);
	document.execCommand("copy");
	//alert("text copied")
    }
}
