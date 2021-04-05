var input_qg = { "edges": [], "nodes": [] };
var qgids = [];
var cyobj = [];
var cytodata = [];
var predicates = {};
var all_predicates = {};
var all_nodes = {};
var summary_table_html = '';
var summary_tsv = [];
var compare_tsv = [];
var columnlist = [];
var UIstate = {};

// defaults
var base = "";
var baseAPI = base + "api/arax/v1.0";

// possibly imported by calling page (e.g. index.html)
if (typeof config !== 'undefined') {
    if (config.base)
	base = config.base;
    if (config.baseAPI)
	baseAPI = config.baseAPI;
}

var providers = {
    "ARAX" : { "url" : baseAPI + "/response/" },
    "ARS"  : { "url" : baseAPI + "/response/" }
};


function main() {
    document.getElementById("menuapiurl").href = baseAPI + "/ui/";

    get_example_questions();
    load_nodes_and_predicates();
    populate_dsl_commands();
    display_list('A');
    display_list('B');
    add_status_divs();
    cytodata[99999] = 'dummy';
    UIstate.nodedd = 1;
    UIstate.hasNodeArray = false;

    var tab = getQueryVariable("tab") || "query";
    var syn = getQueryVariable("term") || null;
    var response_id = getQueryVariable("r") || null;
    var provider_id = getQueryVariable("source") || "ARAX";
    var rurl = null;
    if (response_id) {
	provider_id = "ARAX";
        rurl = providers[provider_id].url;
    }
    else if (provider_id) {
	rurl = providers[provider_id].url;
	response_id = getQueryVariable("id") || null;
    }

    if (rurl && response_id) {
	var statusdiv = document.getElementById("statusdiv");
	statusdiv.innerHTML = '';
	statusdiv.appendChild(document.createTextNode("You have requested "+provider_id+" response id = " + response_id));
	statusdiv.appendChild(document.createElement("br"));

	document.getElementById("devdiv").innerHTML =  "Requested "+provider_id+" response id = " + response_id + "<br>";
	retrieve_response(provider_id,rurl+response_id,response_id,"all");
    }
    else {
	add_cyto(99999);
	add_cyto(0);
    }

    if (syn) {
	tab = "synonym";
	lookup_synonym(syn,false);
    }
    openSection(tab);
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


function openSection(sect) {
    if (!document.getElementById(sect+"Menu") || !document.getElementById(sect+"Div"))
	sect = "query";

    var e = document.getElementsByClassName("menucurrent");
    if (e) e[0].className = "menuleftitem";
    document.getElementById(sect+"Menu").className = "menucurrent";

    for (var e of document.getElementsByClassName("pagesection")) {
        e.style.maxHeight = null;
        e.style.visibility = 'hidden';
    }
    document.getElementById(sect+"Div").style.maxHeight = "none";
    document.getElementById(sect+"Div").style.visibility = 'visible';
    window.scrollTo(0,0);
}

// somehow merge with above?  eh...
function selectInput (input_id) {
    var e = document.getElementsByClassName("slink_on");
    if (e[0]) { e[0].classList.remove("slink_on"); }
    document.getElementById(input_id+"_link").classList.add("slink_on");

    for (var s of ['qtext_input','qgraph_input','qjson_input','qdsl_input','qid_input']) {
	document.getElementById(s).style.maxHeight = null;
	document.getElementById(s).style.visibility = 'hidden';
    }
    document.getElementById(input_id+"_input").style.maxHeight = "100%";
    document.getElementById(input_id+"_input").style.visibility = 'visible';
}


function clearJSON() {
    document.getElementById("jsonText").value = '';
}
function clearDSL() {
    document.getElementById("dslText").value = '';
}

function pasteSyn(word) {
    document.getElementById("newsynonym").value = word;
}
function pasteId(id) {
    document.getElementById("idForm").elements["idText"].value = id;
    document.getElementById("qid").value = '';
    document.getElementById("qid").blur();
}
function pasteQuestion(question) {
    document.getElementById("questionForm").elements["questionText"].value = question;
    document.getElementById("qqq").value = '';
    document.getElementById("qqq").blur();
}
function pasteExample(type) {
    if (type == "DSL") {
	document.getElementById("dslText").value = 'add_qnode(name=acetaminophen, key=n0)\nadd_qnode(category=biolink:Protein, key=n1)\nadd_qedge(subject=n0, object=n1, key=e0)\nexpand(edge_key=e0,kp=ARAX/KG2)\noverlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)\nresultify()\nfilter_results(action=limit_number_of_results, max_results=30)\n';
    }
    else {
	document.getElementById("jsonText").value = '{\n   "edges": {\n      "e00": {\n         "subject":   "n00",\n         "object":    "n01",\n         "predicate": "biolink:physically_interacts_with"\n      }\n   },\n   "nodes": {\n      "n00": {\n         "id":        "CHEMBL.COMPOUND:CHEMBL112",\n         "category":  "biolink:ChemicalSubstance"\n      },\n      "n01": {\n         "category":  "biolink:Protein"\n      }\n   }\n}\n';
    }
}

function reset_vars() {
    add_status_divs();
    document.getElementById("result_container").innerHTML = "";
    if (cyobj[0]) {cyobj[0].elements().remove();}
    document.getElementById("summary_container").innerHTML = "";
    document.getElementById("menunummessages").innerHTML = "--";
    document.getElementById("menunummessages").className = "numold menunum";
    document.getElementById("menunumresults").innerHTML = "--";
    document.getElementById("menunumresults").className = "numold menunum";
    summary_table_html = '';
    summary_tsv = [];
    columnlist = [];
    all_nodes = {};
    cyobj = [];
    cytodata = [];
    UIstate.nodedd = 1;
    UIstate.hasNodeArray = false;
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
	queryObj["message"] = {};
	queryObj["operations"] = { "actions": dslArrayOfLines};
    }
    else if (qtype == "JSON") {
	document.getElementById("questionForm").elements["questionText"].value = '-- posted async query via direct JSON input --';
	statusdiv.innerHTML = "Posting JSON.  Looking for answer...";
	statusdiv.appendChild(document.createElement("br"));

        var jsonInput;
	try {
	    jsonInput = JSON.parse(document.getElementById("jsonText").value);
	}
	catch(e) {
            statusdiv.appendChild(document.createElement("br"));
	    if (e.name == "SyntaxError")
		statusdiv.innerHTML += "<b>Error</b> parsing JSON input. Please correct errors and resubmit: ";
	    else
		statusdiv.innerHTML += "<b>Error</b> processing input. Please correct errors and resubmit: ";
            statusdiv.appendChild(document.createElement("br"));
	    statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
	    return;
	}
	queryObj.message = { "query_graph" :jsonInput };
	queryObj.max_results = 100;

	clear_qg();
    }
    else {  // qGraph
	document.getElementById("questionForm").elements["questionText"].value = '-- posted async query via graph --';
	statusdiv.innerHTML = "Posting graph.  Looking for answer...";
        statusdiv.appendChild(document.createElement("br"));

	// ids need to start with a non-numeric character
	for (var gnode of input_qg.nodes) {
	    if (String(gnode.id).match(/^\d/))
		gnode.id = "qg" + gnode.id;

	    if (gnode.is_set) {
		var list = gnode.name.split("LIST_")[1];
		gnode.curie = get_list_as_curie_array(list);
	    }
	}
	for (var gedge of input_qg.edges) {
	    if (String(gedge.id).match(/^\d/))
		gedge.id = "qg" + gedge.id;
	    if (String(gedge.source_id).match(/^\d/))
		gedge.source_id = "qg" + gedge.source_id;
	    if (String(gedge.target_id).match(/^\d/))
		gedge.target_id = "qg" + gedge.target_id;

	}

	document.getElementById('qg_form').style.visibility = 'hidden';
	document.getElementById('qg_form').style.maxHeight = null;

	queryObj.message = { "query_graph" :input_qg };
	//queryObj.bypass_cache = bypass_cache;
	queryObj.max_results = 100;

	document.getElementById("jsonText").value = JSON.stringify(input_qg,null,2);
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
    fetch(baseAPI + "/query", {
	method: 'post',
	body: JSON.stringify(queryObj),
	headers: { 'Content-type': 'application/json' }
    }).then(function(response) {
	var reader = response.body.getReader();
	var partialMsg = '';
	var enqueue = false;
	var numCurrMsgs = 0;
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
			if (jsonMsg.description) {
			    enqueue = true;
			    respjson += msg;
			}
			else if (jsonMsg.message) {
			    if (jsonMsg.message.match(/^Parsing action: [^\#]\S+/)) {
				totalSteps++;
			    }
			    else if (totalSteps>0) {
				document.getElementById("totalSteps").innerHTML = totalSteps;
				if (numCurrMsgs < 99)
				    numCurrMsgs++;
				if (finishedSteps == totalSteps)
				    numCurrMsgs = 1;

                                document.getElementById("progressBar").style.width = (800*(finishedSteps+0.5*Math.log10(numCurrMsgs))/totalSteps)+"px";
				document.getElementById("progressBar").innerHTML = Math.round(99*(finishedSteps+0.5*Math.log10(numCurrMsgs))/totalSteps)+"%\u00A0\u00A0";

				if (jsonMsg.message.match(/^Processing action/)) {
				    finishedSteps++;
				    document.getElementById("finishedSteps").innerHTML = finishedSteps;
				    numCurrMsgs = 0;
				}
			    }

			    cmddiv.appendChild(document.createTextNode(jsonMsg.timestamp+'\u00A0'+jsonMsg.level+':\u00A0'+jsonMsg.message));
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
	    if (data.status == "OK")
		document.getElementById("progressBar").innerHTML = "Finished\u00A0\u00A0";
	    else {
		document.getElementById("progressBar").classList.add("barerror");
		document.getElementById("progressBar").innerHTML = "Error\u00A0\u00A0";
		document.getElementById("finishedSteps").classList.add("menunum","numnew","msgERROR");
		there_was_an_error();
	    }
	    statusdiv.appendChild(document.createTextNode(data["description"]));  // italics?
	    statusdiv.appendChild(document.createElement("br"));
	    sesame('openmax',statusdiv);

	    if (data["status"] == "QueryGraphZeroNodes") {
		clear_qg();
	    }
	    else if (data["status"] == "OK") {
		input_qg = { "edges": [], "nodes": [] };
		render_response(data,qtype == "DSL");
	    }
	    else if (data["logs"]) {
		process_log(data["logs"]);
	    }
	    else {
		statusdiv.innerHTML += "<br><span class='error'>An error was encountered while parsing the response from the server (no log; code:"+data.status+")</span>";
		document.getElementById("devdiv").innerHTML += "------------------------------------ error with capturing QUERY:<br>"+data;
		sesame('openmax',statusdiv);
	    }

	})
        .catch(function(err) {
	    statusdiv.innerHTML += "<br><span class='error'>An error was encountered while contacting the server ("+err+")</span>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with parsing QUERY:<br>"+err;
	    sesame('openmax',statusdiv);
	    if (err.log) {
		process_log(err.log);
	    }
	    console.log(err.message);
            there_was_an_error();
	});
}

function enter_synonym(ele) {
    if (event.key === 'Enter')
	sendSyn();
}

function lookup_synonym(syn,open) {
    document.getElementById("newsynonym").value = syn.trim();
    sendSyn();
    if (open)
	openSection("synonym");
}

async function sendSyn() {
    var word = document.getElementById("newsynonym").value.trim();
    if (!word) return;

    var syndiv = document.getElementById("synonym_result_container");
    syndiv.innerHTML = "";
    var allweknow = await check_entity(word,true);

    if (0) { // set to 1 if you just want full JSON dump instead of html tables
	syndiv.innerHTML = "<pre>"+JSON.stringify(allweknow,null,2)+"</pre>";
	return;
    }

    var div, text, table, tr, td;

    div = document.createElement("div");
    div.className = "statushead";
    div.appendChild(document.createTextNode("Synonym Results"));
    text = document.createElement("a");
    text.target = '_new';
    text.title = 'link to this synonym entry';
    text.href = "http://"+ window.location.hostname + window.location.pathname + "?term=" + word;
    text.innerHTML = "[ Direct link to this entry ]";
    text.style.float = "right";
    div.appendChild(text);
    syndiv.appendChild(div);

    div = document.createElement("div");
    div.className = "status";
    text = document.createElement("h2");
    text.className = "qprob p9";
    text.appendChild(document.createTextNode(word));
    div.appendChild(text);
    //div.appendChild(document.createElement("br"));

    if (!allweknow[word]) {
	text.className = "qprob p1";
	div.appendChild(document.createElement("br"));
	div.appendChild(document.createTextNode("Entity not found."));
	div.appendChild(document.createElement("br"));
	div.appendChild(document.createElement("br"));
	syndiv.appendChild(div);
	return;
    }

    if (allweknow[word].id) {
	table = document.createElement("table");
	table.className = 'sumtab';
	for (var syn in allweknow[word].id) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.style.fontWeight = 'bold';
	    td.appendChild(document.createTextNode(syn));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    if (syn == "identifier")
		td.appendChild(link_to_identifiers_dot_org(allweknow[word].id[syn]));
	    td.appendChild(document.createTextNode(allweknow[word].id[syn]));
	    tr.appendChild(td);
	    table.appendChild(tr);
	}

	if (allweknow[word].synonyms) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.style.fontWeight = 'bold';
	    td.appendChild(document.createTextNode('synonyms (all)'));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    var comma = '';
	    for (var syn in allweknow[word].synonyms) {
		td.appendChild(document.createTextNode(comma + syn + " (" +allweknow[word].synonyms[syn] + ")"));
		comma = ", ";
	    }
	    tr.appendChild(td);
	    table.appendChild(tr);
	}

	if (allweknow[word].categories) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.style.fontWeight = 'bold';
	    td.appendChild(document.createTextNode('categories (all)'));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    var comma = '';
	    for (var cat in allweknow[word].categories) {
		td.appendChild(document.createTextNode(comma + cat + " (" +allweknow[word].categories[cat] + ")"));
		comma = ", ";
	    }
	    tr.appendChild(td);
	    table.appendChild(tr);
	}

	div.appendChild(table);
    }

    if (allweknow[word].nodes) {
	text = document.createElement("h3");
        text.className = "qprob p5";
	text.appendChild(document.createTextNode('Nodes'));
	div.appendChild(text);

	table = document.createElement("table");
	table.className = 'sumtab';
	tr = document.createElement("tr");
	for (var head of ["Identifier","Label","Original Label","Category"] ) {
	    td = document.createElement("th")
	    td.appendChild(document.createTextNode(head));
	    tr.appendChild(td);
	}
	table.appendChild(tr);
	for (var syn of allweknow[word].nodes) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.appendChild(link_to_identifiers_dot_org(syn.identifier));
	    td.appendChild(document.createTextNode(syn.identifier));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(syn.label));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(syn.original_label));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(syn.category));
	    tr.appendChild(td);
	    table.appendChild(tr);
	}
	div.appendChild(table);
    }

    if (allweknow[word].equivalent_identifiers) {
	text = document.createElement("h3");
        text.className = "qprob p5";
	text.appendChild(document.createTextNode('Equivalent Identifiers'));
	div.appendChild(text);

	table = document.createElement("table");
	table.className = 'sumtab';
	tr = document.createElement("tr");
	for (var head of ["Identifier","Category","Source"] ) {
	    td = document.createElement("th")
	    td.appendChild(document.createTextNode(head));
	    tr.appendChild(td);
	}
	table.appendChild(tr);
	for (var syn of allweknow[word].equivalent_identifiers) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.appendChild(link_to_identifiers_dot_org(syn.identifier));
	    td.appendChild(document.createTextNode(syn.identifier));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(syn.category));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(syn.source));
	    tr.appendChild(td);
	    table.appendChild(tr);
	}
	div.appendChild(table);
    }

    if (allweknow[word].synonym_provenance) {
	text = document.createElement("h3");
	text.className = "qprob p5";
	//text.appendChild(document.createTextNode('\u25BA Synonym Provenance'));
	text.appendChild(document.createTextNode('Synonym Provenance'));
	div.appendChild(text);

	table = document.createElement("table");
	table.className = 'sumtab';
        tr = document.createElement("tr");
	for (var head of ["Name","Curie","Source"] ) {
	    td = document.createElement("th")
	    td.appendChild(document.createTextNode(head));
	    tr.appendChild(td);
	}
        table.appendChild(tr);
	for (var syn in allweknow[word].synonym_provenance) {
            tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(allweknow[word].synonym_provenance[syn].name));
	    tr.appendChild(td);
	    td = document.createElement("td")
            td.appendChild(link_to_identifiers_dot_org(allweknow[word].synonym_provenance[syn].uc_curie));
	    td.appendChild(document.createTextNode(allweknow[word].synonym_provenance[syn].uc_curie));
	    tr.appendChild(td);
	    td = document.createElement("td")
	    td.appendChild(document.createTextNode(allweknow[word].synonym_provenance[syn].source));
	    tr.appendChild(td);
	    table.appendChild(tr);
	}
	div.appendChild(table);
    }

    div.appendChild(document.createElement("br"));
    syndiv.appendChild(div);
}

function link_to_identifiers_dot_org(thing) {
    if (!thing) return;

    var link = document.createElement("a");
    link.style.marginRight = "5px";
    link.target = 'ARAXidentifiers';
    link.title = 'look up '+thing+' in identifiers.org';
    link.href = "http://identifiers.org/resolve?query=" + thing;
    var img = document.createElement('img');
    img.src = 'id_org.png';
    img.width  = "15";
    img.height = "15";
    link.appendChild(img);

    return link;
}


function getIdStats(id) {
    if (document.getElementById("numresults_"+id)) {
	document.getElementById("numresults_"+id).innerHTML = '';
	document.getElementById("istrapi_"+id).innerHTML = 'loading...';
	var wait = document.createElement("span");
	wait.className = 'loading_cell';
	var waitbar = document.createElement("span");
	waitbar.className = 'loading_bar';
	wait.appendChild(waitbar);
	document.getElementById("numresults_"+id).appendChild(wait);
    }
    retrieve_response("ARS",providers["ARS"].url+id,id,"stats");
}

function sendId() {
    var id = document.getElementById("idText").value.trim();
    if (!id) return;

    reset_vars();
    if (cyobj[99999]) {cyobj[99999].elements().remove();}
    input_qg = { "edges": [], "nodes": [] };

    if (document.getElementById("numresults_"+id)) {
	document.getElementById("numresults_"+id).innerHTML = '';
	document.getElementById("istrapi_"+id).innerHTML = 'loading...';
	var wait = document.createElement("span");
	wait.className = 'loading_cell';
	var waitbar = document.createElement("span");
	waitbar.className = 'loading_bar';
	wait.appendChild(waitbar);
	document.getElementById("numresults_"+id).appendChild(wait);
    }

    retrieve_response("ARS",providers["ARS"].url+id,id,"all");
    openSection('query');
}

function sendQuestion(e) {
    reset_vars();
    if (cyobj[99999]) {cyobj[99999].elements().remove();}
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
    xhr.open("post", baseAPI + "/translate", true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

    // send the collected data as JSON
    xhr.send(JSON.stringify(data));

    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj = JSON.parse(xhr.responseText);
	    add_to_dev_info("Posted to TRANSLATE",jsonObj);

	    if ( jsonObj.query_type_id && jsonObj.terms ) {
		document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<br>&nbsp;&nbsp;&nbsp;<b>"+jsonObj["restated_question"]+"?</b><br>Please ensure that this is an accurate restatement of the intended question.<br>Looking for answer...";

		sesame('openmax',statusdiv);
		var xhr2 = new XMLHttpRequest();
		xhr2.open("post",  baseAPI + "/query", true);
		xhr2.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

                //var queryObj = { "message" : jsonObj };
                var queryObj = jsonObj;
                queryObj["message"] = { };
                queryObj.bypass_cache = bypass_cache;
                queryObj.max_results = 100;

		add_to_dev_info("Posted to QUERY",queryObj);
		xhr2.send(JSON.stringify(queryObj));
		xhr2.onloadend = function() {
		    if ( xhr2.status == 200 ) {
			var jsonObj2 = JSON.parse(xhr2.responseText);
			document.getElementById("devdiv").innerHTML += "<br>================================================================= QUERY::<pre id='responseJSON'>\n" + JSON.stringify(jsonObj2,null,2) + "</pre>";

			document.getElementById("statusdiv").innerHTML = "Your question has been interpreted and is restated as follows:<br>&nbsp;&nbsp;&nbsp;<b>"+jsonObj2["restated_question"]+"?</b><br>Please ensure that this is an accurate restatement of the intended question.<br><br><i>"+jsonObj2["description"]+"</i><br>";
			sesame('openmax',statusdiv);

			render_message(jsonObj2,true);
		    }
		    else if ( jsonObj.message ) { // STILL APPLIES TO 0.9??  TODO
			document.getElementById("statusdiv").innerHTML += "<br><br>An error was encountered:<br><span class='error'>"+jsonObj.message+"</span>";
			sesame('openmax',statusdiv);
		    }
		    else {
			document.getElementById("statusdiv").innerHTML += "<br><span class='error'>An error was encountered while contacting the server ("+xhr2.status+")</span>";
			document.getElementById("devdiv").innerHTML += "------------------------------------ error with QUERY:<br>"+xhr2.responseText;
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
	    document.getElementById("statusdiv").innerHTML += "<br><br>An error was encountered:<br><span class='error'>"+xhr.statusText+" ("+xhr.status+")</span>";
	    sesame('openmax',statusdiv);
	}
    };

}


function process_ars_message(ars_msg, level) {
    if (level > 5)
	return; // stopgap
    var table, tr, td;
    if (level == 0) {
	if (document.getElementById('ars_message_list'))
	    document.getElementById('ars_message_list').remove();
	var div = document.createElement("div");
	div.id = 'ars_message_list';

        var div2 = document.createElement("div");
	div2.className = "statushead";
        div2.appendChild(document.createTextNode("Collection Results"));
        div.appendChild(div2);

	var div2 = document.createElement("div");
	div2.className = "status";
	table = document.createElement("table");
	table.id = 'ars_message_list_table';
	table.className = 'sumtab';

	tr = document.createElement("tr");
	for (var head of ["","Agent","Status","Message Id","N_Results","TRAPI 1.0?"] ) {
	    td = document.createElement("th")
	    td.appendChild(document.createTextNode(head));
	    tr.appendChild(td);
	}
	table.appendChild(tr);

	div2.appendChild(document.createElement("br"));
	div2.appendChild(table);
        div2.appendChild(document.createElement("br"));
        div.appendChild(div2);
	document.getElementById('qid_input').appendChild(div);
    }
    else
	table = document.getElementById('ars_message_list_table');

    tr = document.createElement("tr");
    tr.className = 'hoverable';
    td = document.createElement("td");
    td.appendChild(document.createTextNode('\u25BA'.repeat(level)));
    tr.appendChild(td);
    td = document.createElement("td");
    td.appendChild(document.createTextNode(ars_msg.actor.agent));
    tr.appendChild(td);
    td = document.createElement("td");
    td.appendChild(document.createTextNode(ars_msg.status));
    tr.appendChild(td);
    td = document.createElement("td");

    var link;
    var go = false;
    if (ars_msg.status == "Running")
	link = document.createTextNode(ars_msg.message);
    else {
	link = document.createElement("a");
	link.title='view this response';
	link.style.cursor = "pointer";
	link.setAttribute('onclick', 'pasteId("'+ars_msg.message+'");sendId();');
	link.appendChild(document.createTextNode(ars_msg.message));
	if (!ars_msg["children"] || ars_msg["children"].length == 0)
	    go = true;
    }
    td.appendChild(link);
    tr.appendChild(td);
    td = document.createElement("td");
    td.id = "numresults_"+ars_msg.message;
    tr.appendChild(td);
    td = document.createElement("td");
    td.id = "istrapi_"+ars_msg.message;
    tr.appendChild(td);
    table.appendChild(tr);

    if (go)
	getIdStats(ars_msg.message);

    level++;
    for (let child of ars_msg["children"])
	process_ars_message(child, level);
}


function retrieve_response(provider, resp_url, resp_id, type) {
    if (type == null) type = "all";
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.appendChild(document.createTextNode("Retrieving "+provider+" response id = " + resp_id));
    statusdiv.appendChild(document.createElement("hr"));
    sesame('openmax',statusdiv);

    var xhr = new XMLHttpRequest();
    xhr.open("get",  resp_url, true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.send(null);
    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj2 = JSON.parse(xhr.responseText);

	    if (type == "all") {
		var devdiv = document.getElementById("devdiv");
		devdiv.appendChild(document.createElement("br"));
		devdiv.appendChild(document.createTextNode('='.repeat(80)+" RESPONSE REQUEST::"));
		var link = document.createElement("a");
		link.target = '_NEW';
		link.href = resp_url;
		link.style.position = "relative";
		link.style.left = "30px";
		link.appendChild(document.createTextNode("[ view raw json response \u2197 ]"));
		devdiv.appendChild(link);
		var pre = document.createElement("pre");
		pre.id = 'responseJSON';
		pre.textContent = JSON.stringify(jsonObj2,null,2);
		devdiv.appendChild(pre);
	    }

            if (jsonObj2["children"]) {
		process_ars_message(jsonObj2,0);
		selectInput("qid");
		return;
	    }

	    if (jsonObj2["restated_question"]) {
		statusdiv.innerHTML += "Your question has been interpreted and is restated as follows:<br>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question"]+"?</b><br>Please ensure that this is an accurate restatement of the intended question.<br>";
		document.getElementById("questionForm").elements["questionText"].value = jsonObj2["restated_question"];
	    }
	    else {
		document.getElementById("questionForm").elements["questionText"].value = "";
	    }

	    jsonObj2.araxui_provider = provider;
	    jsonObj2.araxui_response = resp_id;

	    if (jsonObj2.description) {
		var nr = document.createElement("span");
		if (jsonObj2.description.startsWith("ERROR")) {
		    if (type == "all")
			statusdiv.innerHTML += "<br><span class='error'>"+jsonObj2.description+"</span><br>";
		    nr.innerHTML = '&cross;';
		    nr.className = 'explevel p1';
		}
		else {
                    if (type == "all")
			statusdiv.innerHTML += "<br><i>"+jsonObj2.description+"</i><br>";
		    nr.innerHTML = '&check;';
		    nr.className = 'explevel p9';
		}

	        if (document.getElementById("istrapi_"+jsonObj2.araxui_response)) {
		    document.getElementById("istrapi_"+jsonObj2.araxui_response).innerHTML = '';
		    document.getElementById("istrapi_"+jsonObj2.araxui_response).appendChild(nr);
		}
	    }
	    sesame('openmax',statusdiv);

	    if (type == "stats")
		render_response_stats(jsonObj2);
	    else
		render_response(jsonObj2,true);
	}
	else if ( xhr.status == 404 ) {
	    if (document.getElementById("numresults_"+resp_id)) {
		document.getElementById("numresults_"+resp_id).innerHTML = '';
                document.getElementById("istrapi_"+resp_id).innerHTML = '';
		var nr = document.createElement("span");
		nr.className = 'explevel p0';
		nr.innerHTML = '&nbsp;N/A&nbsp;';
		document.getElementById("numresults_"+resp_id).appendChild(nr);
	    }
	    statusdiv.innerHTML += "<br>Response with id=<span class='error'>"+resp_id+"</span> was not found (404).";
	    sesame('openmax',statusdiv);
	    there_was_an_error();
	}
	else {
            if (document.getElementById("numresults_"+resp_id)) {
		document.getElementById("numresults_"+resp_id).innerHTML = '';
		document.getElementById("istrapi_"+resp_id).innerHTML = '';
		var nr = document.createElement("span");
		nr.className = 'explevel p0';
		nr.innerHTML = '&nbsp;Error&nbsp;';
		document.getElementById("numresults_"+resp_id).appendChild(nr);
	    }
	    statusdiv.innerHTML += "<br><span class='error'>An error was encountered while contacting the server ("+xhr.status+")</span>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with RESPONSE:<br>"+xhr.responseText;
	    sesame('openmax',statusdiv);
            there_was_an_error();
	}
    };

}



// DELETE_LATER::
function render_message(respObj,dispjson) {
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.appendChild(document.createTextNode("DEPRECATED FUNCTION!  UPDATE ME..."));
    sesame('openmax',statusdiv);
}


function render_response_stats(respObj) {
    if (!document.getElementById("numresults_"+respObj.araxui_response)) return;

    var nr = document.createElement("span");
    document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';

    if ( respObj.message["results"] ) {
	if (respObj.description && respObj.description.startsWith("ERROR"))
	    nr.className = 'explevel p1';
	else if (respObj.message.results.length > 0)
	    nr.className = 'explevel p9';
	else
	    nr.className = 'explevel p5';
	nr.innerHTML = '&nbsp;'+respObj.message.results.length+'&nbsp;';
    }
    else {
	nr.className = 'explevel p0';
	nr.innerHTML = '&nbsp;n/a&nbsp;';
    }

    document.getElementById("numresults_"+respObj.araxui_response).appendChild(nr);
}

function render_response(respObj,dispjson) {
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.appendChild(document.createTextNode("Rendering message..."));
    sesame('openmax',statusdiv);

    if (respObj.id) {
	var response_id = respObj.id.substr(respObj.id.lastIndexOf('/') + 1);
	document.title = "ARAX-UI ["+response_id+"]";

	if (respObj.restated_question) {
	    add_to_session(response_id,respObj.restated_question+"?");
	    document.title += ": "+respObj.restated_question+"?";
	}
	else {
	    add_to_session(response_id,"response="+response_id);
	    document.title += ": (no restated question)";
	}
	history.pushState({ id: 'ARAX_UI' }, 'ARAX | response='+response_id, "//"+ window.location.hostname + window.location.pathname + '?r='+response_id);
    }
    else if (respObj.araxui_provider) {
        document.title = "ARAX-UI ["+respObj.araxui_provider+" : "+respObj.araxui_response+"]";
        add_to_session('source='+respObj.araxui_provider+"&id="+respObj.araxui_response,"["+respObj.araxui_provider+"] id="+respObj.araxui_response);
	history.pushState({ id: 'ARAX_UI' }, 'ARAX | source='+respObj.araxui_provider+"&id="+respObj.araxui_response, "//"+ window.location.hostname + window.location.pathname + '?source='+respObj.araxui_provider+"&id="+respObj.araxui_response);
    }
    else if (respObj.restated_question)
        document.title = "ARAX-UI [no response_id]: "+respObj.restated_question+"?";
    else
	document.title = "ARAX-UI [no response_id]";


    if (respObj.message["query_graph"]) {
	if (dispjson) {
	    for (var id in respObj.message["query_graph"].nodes) {
		var gnode = respObj.message["query_graph"].nodes[id];
		for (var att in gnode)
		    if (gnode.hasOwnProperty(att))
			if (gnode[att] == null)
			    delete gnode[att];
	    }
            for (var id in respObj.message["query_graph"].edges) {
		var gedge = respObj.message["query_graph"].edges[id];
		for (var att in gedge)
		    if (gedge.hasOwnProperty(att))
			if (gedge[att] == null)
			    delete gedge[att];
	    }
	    document.getElementById("jsonText").value = JSON.stringify(respObj.message["query_graph"],null,2);
	}
	process_graph(respObj.message["query_graph"],99999);
    }
    else
	cytodata[99999] = 'dummy'; // this enables query graph editing


    if (respObj["operations"])
	process_q_options(respObj["operations"]);


    if (respObj["logs"])
	process_log(respObj["logs"]);
    else
        document.getElementById("logdiv").innerHTML = "<h2 style='margin-left:20px;'>No log messages in this response</h2>";

    // Do this *before* processing results
    if ( respObj["table_column_names"] )
	add_to_summary(respObj["table_column_names"],0);
    else
	add_to_summary(["'Guessence'"],0);

    if ( respObj.message["results"] ) {
	if (!respObj.message["knowledge_graph"] ) {
            document.getElementById("result_container").innerHTML  += "<h2 class='error'>Knowledge Graph missing in response; cannot process results.</h2>";
	    document.getElementById("summary_container").innerHTML += "<h2 class='error'>Knowledge Graph missing in response; cannot process results</h2>";
	}
	else {
	    var rtext = respObj.message.results.length == 1 ? " result" : " results";
	    document.getElementById("result_container").innerHTML += "<h2>" + respObj.message.results.length + rtext + "</h2>";
            document.getElementById("menunumresults").innerHTML = respObj.message.results.length;
            document.getElementById("menunumresults").classList.add("numnew");
	    document.getElementById("menunumresults").classList.remove("numold");
	    if (document.getElementById("numresults_"+respObj.araxui_response)) {
		document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';
		var nr = document.createElement("span");
		if (respObj.description && respObj.description.startsWith("ERROR"))
		    nr.className = 'explevel p1';
		else if (respObj.message.results.length > 0)
		    nr.className = 'explevel p9';
		else
		    nr.className = 'explevel p5';
		nr.innerHTML = '&nbsp;'+respObj.message.results.length+'&nbsp;';
		document.getElementById("numresults_"+respObj.araxui_response).appendChild(nr);
	    }

	    process_graph(respObj.message["knowledge_graph"],0);
	    process_results(respObj.message["results"],respObj.message["knowledge_graph"]);
	}
    }
    else {
        document.getElementById("result_container").innerHTML  += "<h2>No results...</h2>";
        document.getElementById("summary_container").innerHTML += "<h2>No results...</h2>";
        if (document.getElementById("numresults_"+respObj.araxui_response)) {
	    document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';
	    var nr = document.createElement("span");
	    nr.className = 'explevel p0';
	    nr.innerHTML = '&nbsp;n/a&nbsp;';
	    document.getElementById("numresults_"+respObj.araxui_response).appendChild(nr);
	}
    }

    // table was (potentially) populated in process_results
    if (summary_tsv.length > 1) {
	var div = document.createElement("div");
	div.className = 'statushead';
	div.appendChild(document.createTextNode("Summary"));
        document.getElementById("summary_container").appendChild(div);

	div = document.createElement("div");
	div.className = 'status';
	div.id = 'summarydiv';
	div.appendChild(document.createElement("br"));

	var button = document.createElement("input");
	button.className = 'questionBox button';
	button.type = 'button';
	button.name = 'action';
	button.title = 'Get tab-separated values of this table to paste into Excel etc';
	button.value = 'Copy Summary Table to clipboard (TSV)';
	button.setAttribute('onclick', 'copyTSVToClipboard(this,summary_tsv);');
        div.appendChild(button);

        div.appendChild(document.createElement("br"));
	div.appendChild(document.createElement("br"));

	var table = document.createElement("table");
	table.className = 'sumtab';
	table.innerHTML = summary_table_html;
        div.appendChild(table);

	div.appendChild(document.createElement("br"));

	document.getElementById("summary_container").appendChild(div);
    }
    else
        document.getElementById("summary_container").innerHTML += "<h2>Summary not available for this query</h2>";

    add_cyto(0);
    if (!UIstate.hasNodeArray)
	add_cyto(99999);
    statusdiv.appendChild(document.createTextNode("done."));
    statusdiv.appendChild(document.createElement("br"));
    var nr = document.createElement("span");
    nr.className = 'essence';
    nr.appendChild(document.createTextNode("Click on Results, Summary, or Knowledge Graph links on the left to explore results."));
    statusdiv.appendChild(nr);
    sesame('openmax',statusdiv);
}


function process_q_options(q_opts) {
    if (q_opts.actions) {
	clearDSL();
	for (var act of q_opts.actions) {
	    if (act.length > 1) // skip blank lines
		document.getElementById("dslText").value += act + "\n";
	}
    }
}


function there_was_an_error() {
    document.getElementById("summary_container").innerHTML += "<h2 class='error'>Error : No results</h2>";
    document.getElementById("result_container").innerHTML  += "<h2 class='error'>Error : No results</h2>";
    document.getElementById("menunumresults").innerHTML = "E";
    document.getElementById("menunumresults").classList.add("numnew","msgERROR");
    document.getElementById("menunumresults").classList.remove("numold");
}

function process_log(logarr) {
    var status = {};
    for (var s of ["ERROR","WARNING","INFO","DEBUG"]) {
	status[s] = 0;
    }
    for (var msg of logarr) {
	if (msg.prefix) { // upconvert TRAPI 0.9.3 --> 1.0
	    msg.level = msg.level_str;
	    msg.code = null;
	}

	status[msg.level]++;

	var span = document.createElement("span");
	span.className = "hoverable msg " + msg.level;

        if (msg.level == "DEBUG") { span.style.display = 'none'; }

	var span2 = document.createElement("span");
	span2.className = "explevel msg" + msg.level;
	span2.appendChild(document.createTextNode('\u00A0'));
	span2.appendChild(document.createTextNode('\u00A0'));
        span.appendChild(span2);

	span.appendChild(document.createTextNode('\u00A0'));

	span.appendChild(document.createTextNode(msg.timestamp+" "+msg.level+": "));
	if (msg.code)
	    span.appendChild(document.createTextNode("["+msg.code+"] "));
//	span.appendChild(document.createElement("br"));

	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode('\u00A0'));
	span.appendChild(document.createTextNode(msg.message));

	document.getElementById("logdiv").appendChild(span);
    }
    document.getElementById("menunummessages").innerHTML = logarr.length;
    if (status.ERROR > 0) document.getElementById("menunummessages").classList.add('numnew','msgERROR');
    else if (status.WARNING > 0) document.getElementById("menunummessages").classList.add('numnew','msgWARNING');
    for (var s of ["ERROR","WARNING","INFO","DEBUG"]) {
	document.getElementById("count_"+s).innerHTML += ": "+status[s];
    }
}


function add_status_divs() {
    // summary
    document.getElementById("status_container").innerHTML = '';

    var div = document.createElement("div");
    div.className = 'statushead';
    div.appendChild(document.createTextNode("Status"));
    document.getElementById("status_container").appendChild(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'statusdiv';
    document.getElementById("status_container").appendChild(div);

    // results
    document.getElementById("dev_result_json_container").innerHTML = '';

    div = document.createElement("div");
    div.className = 'statushead';
    div.appendChild(document.createTextNode("Dev Info"));
    var span = document.createElement("span");
    span.style.fontStyle = "italic";
    span.style.fontWeight = 'normal';
    span.style.float = "right";
    span.appendChild(document.createTextNode("( json responses )"));
    div.appendChild(span);
    document.getElementById("dev_result_json_container").appendChild(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'devdiv';
    document.getElementById("dev_result_json_container").appendChild(div);

    // messages
    document.getElementById("messages_container").innerHTML = '';

    div = document.createElement("div");
    div.className = 'statushead';
    div.appendChild(document.createTextNode("Filter Messages:"));

    for (var status of ["Error","Warning","Info","Debug"]) {
	span = document.createElement("span");
	span.id =  'count_'+status.toUpperCase();
	span.style.marginLeft = "20px";
	span.style.cursor = "pointer";
	span.className = 'qprob msg'+status.toUpperCase();
	if (status == "Debug") span.classList.add('hide');
	span.setAttribute('onclick', 'filtermsgs(this,\"'+status.toUpperCase()+'\");');
	span.appendChild(document.createTextNode(status));
	div.appendChild(span);
    }

    document.getElementById("messages_container").appendChild(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'logdiv';
    document.getElementById("messages_container").appendChild(div);
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
	if (!columnlist[i])
	    columnlist[i] = [];

	if (cell == 'th') {
	    //columnlist[i] = [];
	    if (rowdata[i] != 'confidence') {
		listlink += "&nbsp;<a href='javascript:add_items_to_list(\"A\",\"" +i+ "\");' title='Add column items to list A'>&nbsp;[+A]&nbsp;</a>";
		listlink += "&nbsp;<a href='javascript:add_items_to_list(\"B\",\"" +i+ "\");' title='Add column items to list B'>&nbsp;[+B]&nbsp;</a>";
	    }
	}
	else {
	    columnlist[i][rowdata[i]] = 1;
	}
	summary_table_html += '<'+cell+'>' + rowdata[i] + listlink + '</'+cell+'>';
    }
    summary_table_html += '</tr>';

    summary_tsv.push(rowdata.join("\t"));
}


function process_graph(gne,gid) {
    cytodata[gid] = [];
    for (var id in gne.nodes) {
	var gnode = gne.nodes[id];

	gnode.parentdivnum = gid; // helps link node to div when displaying node info on click

        if (!gnode.fulltextname) {
	    if (gnode.name)
		gnode.fulltextname = gnode.name;
	    else
		gnode.fulltextname = id;
	}

	// NEED THIS??
	if (gnode.node_id) // deal with QueryGraphNode (QNode)
	    gnode.id = gnode.node_id;

	//if (!gnode.id)
	//gnode.id = id;

        if (gnode.id) {
	    if (Array.isArray(gnode.id)) {
		if (gnode.id.length == 1)
		    gnode.id = gnode.id[0];
		else
		    UIstate.hasNodeArray = true;
	    }

	    if (gnode.name)
		gnode.name += " ("+gnode.id+")";
	    else
		gnode.name = gnode.id;
	}

        gnode.id = id;

	if (!gnode.name) {
	    if (gnode.category)
		gnode.name = gnode.category + "s?";
	    else
		gnode.name = "(Any)";
	}

        var tmpdata = { "data" : gnode };
        cytodata[gid].push(tmpdata);
    }

    for (var id in gne.edges) {
        var gedge = gne.edges[id];

        if (!gedge.id)
	    gedge.id = id;

	gedge.parentdivnum = gid;
        gedge.source = gedge.subject;
        gedge.target = gedge.object;

        var tmpdata = { "data" : gedge }; // already contains id(?)
        cytodata[gid].push(tmpdata);
    }


    if (gid == 99999) {
	for (var id in gne.nodes) {
	    var gnode = gne.nodes[id];

	    qgids.push(gnode.id);

	    var tmpdata = { "id"     : id,
			    "is_set" : gnode.is_set,
			    "name"   : gnode.name,
			    "desc"   : gnode.description,
			    "curie"  : gnode.id,
			    "type"   : gnode.category
			  };

	    input_qg.nodes.push(tmpdata);
	}

	for (var id in gne.edges) {
            var gedge = gne.edges[id];

	    qgids.push(gedge.id);

	    var tmpdata = { "id"       : id,
			    "negated"  : null,
			    "relation" : null,
			    "source_id": gedge.subject,
			    "target_id": gedge.object,
			    "type"     : gedge.predicate
			  };
	    input_qg.edges.push(tmpdata);
	}
    }

}

// a watered-down essence, if you will...
function eau_du_essence(result) {
    var guessence = 'n/a';
    for (var nbid in result.node_bindings)
	for (var node of result.node_bindings[nbid])
	    if (all_nodes[node.id] < all_nodes[guessence])
		guessence = node.id;
    return guessence;
}

function process_results(reslist,kg) {
    if (Object.keys(all_nodes).length === 0 && all_nodes.constructor === Object) {
	for (var result of reslist)
            for (var nbid in result.node_bindings)
		for (var node of result.node_bindings[nbid]) {
		    if (all_nodes[node.id])
			all_nodes[node.id]++;
		    else
			all_nodes[node.id] = 1;
		    //console.log(node.id+" :: "+all_nodes[node.id]);
		}
    }
    all_nodes['n/a'] = 10000; // for eau_du_essence

    var num = 0;
    for (var result of reslist) {
	num++;

	var ess = '';
	if (result.essence)
	    ess = result.essence;
	else {
	    ess = eau_du_essence(result);
	    if (ess != 'n/a')
		ess = kg.nodes[ess].fulltextname;
	}

        if (result.row_data)
            add_to_summary(result.row_data, num);
	else
            add_to_summary([ess], num);

	var cnf = 0;
	if (Number(result.confidence))
	    cnf = Number(result.confidence).toFixed(3);
	var pcl = (cnf>=0.9) ? "p9" : (cnf>=0.7) ? "p7" : (cnf>=0.5) ? "p5" : (cnf>=0.3) ? "p3" : "p1";

	var rsrc = 'n/a';
	if (result.reasoner_id)
	    rsrc = result.reasoner_id;
	var rscl = (rsrc=="ARAX") ? "srtx" : (rsrc=="Indigo") ? "sind" : (rsrc=="Robokop") ? "srob" : "p0";

	var result_container = document.getElementById("result_container");

        var div = document.createElement("div");
        div.id = 'h'+num+'_div';
	div.title = 'Click to expand / collapse result '+num;
        div.className = 'accordion';
	div.setAttribute('onclick', 'add_cyto('+num+');sesame(this,a'+num+'_div);');
	div.appendChild(document.createTextNode("Result "+num));
	if (ess)
	    div.innerHTML += " :: <b>"+ess+"</b>"; // meh...

	var span100 = document.createElement("span");
	span100.className = 'r100';

        var span = document.createElement("span");
        span.className = pcl+' qprob';
	span.title = "confidence="+cnf;
        span.appendChild(document.createTextNode(cnf));
	span100.appendChild(span);

        span = document.createElement("span");
	span.className = rscl+' qprob';
	span.title = "source="+rsrc;
	span.appendChild(document.createTextNode(rsrc));
	span100.appendChild(span);

	div.appendChild(span100);
	result_container.appendChild(div);

        div = document.createElement("div");
        div.id = 'a'+num+'_div';
        div.className = 'panel';

        var table = document.createElement("table");
        table.className = 't100';

        var tr = document.createElement("tr");
	var td = document.createElement("td");
        td.className = 'textanswer';
	if (result.description)
	    td.appendChild(document.createTextNode(result.description));
	else
	    td.appendChild(document.createTextNode('No description'));
        tr.appendChild(td);

        td = document.createElement("td");
        td.className = 'cytograph_controls';

	var link = document.createElement("a");
	link.title='reset zoom and center';
        link.setAttribute('onclick', 'cyobj['+num+'].reset();');
        link.appendChild(document.createTextNode("\u21BB"));
        td.appendChild(link);
	td.appendChild(document.createElement("br"));
	tr.appendChild(td);

        link = document.createElement("a");
	link.title='breadthfirst layout';
	link.setAttribute('onclick', 'cylayout('+num+',"breadthfirst");');
	link.appendChild(document.createTextNode("B"));
	td.appendChild(link);
	td.appendChild(document.createElement("br"));

        link = document.createElement("a");
	link.title='force-directed layout';
	link.setAttribute('onclick', 'cylayout('+num+',"cose");');
	link.appendChild(document.createTextNode("F"));
	td.appendChild(link);
	td.appendChild(document.createElement("br"));

        link = document.createElement("a");
	link.title='circle layout';
	link.setAttribute('onclick', 'cylayout('+num+',"circle");');
	link.appendChild(document.createTextNode("C"));
	td.appendChild(link);
	td.appendChild(document.createElement("br"));

        link = document.createElement("a");
	link.title='random layout';
	link.setAttribute('onclick', 'cylayout('+num+',"random");');
	link.appendChild(document.createTextNode("R"));
	td.appendChild(link);

	tr.appendChild(td);

        td = document.createElement("td");
	td.className = 'cytograph';
        var div2 = document.createElement("div");
	div2.id = 'cy'+num;
	div2.style.height = '100%';
	div2.style.width  = '100%';
	td.appendChild(div2);
        tr.appendChild(td);
        table.appendChild(tr);


        tr = document.createElement("tr");
	td = document.createElement("td");
        tr.appendChild(td);
	td = document.createElement("td");
	tr.appendChild(td);

	td = document.createElement("td");
        div2 = document.createElement("div");
	div2.id = 'd'+num+'_div';
	div2.className = 'panel';
        link = document.createElement("i");
        link.appendChild(document.createTextNode("Click on a node or edge to get details"));
        div2.appendChild(link);
	td.appendChild(div2);
	tr.appendChild(td);

        table.appendChild(tr);

	div.appendChild(table);
	result_container.appendChild(div);


        cytodata[num] = [];
	//console.log("=================== CYTO num:"+num+"  #nb:"+result.node_bindings.length);

        for (var nbid in result.node_bindings) {
            for (var node of result.node_bindings[nbid]) {
		var kmne = Object.create(kg.nodes[node.id]);
		kmne.parentdivnum = num;
		//console.log("=================== kmne:"+kmne.id);
		var tmpdata = { "data" : kmne };
		cytodata[num].push(tmpdata);
	    }
	}

	for (var ebid in result.edge_bindings) {
	    for (var edge of result.edge_bindings[ebid]) {
		var kmne = Object.create(kg.edges[edge.id]);
		kmne.parentdivnum = num;
		//console.log("=================== kmne:"+kmne.id);
		var tmpdata = { "data" : kmne };
		cytodata[num].push(tmpdata);
	    }
	}

    }
}


function add_cyto(i) {
    if (cytodata[i] == null) return;

    var num = Number(i);// + 1;

    //console.log("---------------cyto i="+i);
    cyobj[i] = cytoscape({
	container: document.getElementById('cy'+num),
	style: cytoscape.stylesheet()
	    .selector('node')
	    .css({
		'background-color': function(ele) { return mapNodeColor(ele); } ,
		'shape': function(ele) { return mapNodeShape(ele); } ,
		'border-color' : '#000',
		'border-width' : '2',
		'width': '20',
		'height': '20',
		'content': 'data(name)'
	    })
	    .selector('edge')
	    .css({
		'curve-style' : 'bezier',
		'line-color': function(ele) { return mapEdgeColor(ele); } ,
		'target-arrow-color': function(ele) { return mapEdgeColor(ele); } ,
		'width': function(ele) { if (ele.data().weight) { return ele.data().weight; } return 2; },
		'target-arrow-shape': 'triangle',
		'opacity': 0.8,
		'content': function(ele) { if ((ele.data().parentdivnum > 99998) && ele.data().type) { return ele.data().type; } return '';}
	    })
	    .selector(':selected')
	    .css({
		'background-color': '#ff0',
		'border-color': '#f80',
		'line-color': '#f80',
		'target-arrow-color': '#f80',
		'source-arrow-color': '#f80',
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

    if (i > 99998) {
	cyobj[i].on('tap','node', function() {
	    document.getElementById('qg_edge_n'+UIstate.nodedd).value = this.data('id');
	    UIstate.nodedd = 3 - UIstate.nodedd;
	    get_possible_edges();
	});

	return;
    }

    cyobj[i].on('tap','node', function() {
	var div = document.getElementById('d'+this.data('parentdivnum')+'_div');
	div.innerHTML = "";

        var fields = [ "name","id", "category" ];
	for (var field of fields) {
	    if (this.data(field) == null) continue;

	    var span = document.createElement("span");
	    span.className = "fieldname";
	    span.appendChild(document.createTextNode(field+": "));
	    div.appendChild(span);
	    div.appendChild(document.createTextNode(this.data(field)));
	    div.appendChild(document.createElement("br"));
	}

	show_attributes(div, this.data('attributes'));

	sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
    });

    cyobj[i].on('tap','edge', function() {
        var div = document.getElementById('d'+this.data('parentdivnum')+'_div');
	div.innerHTML = "";

        div.appendChild(document.createTextNode(this.data('source')+" "));
        var span = document.createElement("b");
	span.appendChild(document.createTextNode(this.data('predicate')));
        div.appendChild(span);
	div.appendChild(document.createTextNode(" "+this.data('target')));
        div.appendChild(document.createElement("br"));

	var fields = [ "relation","id" ];
	for (var field of fields) {
	    if (this.data(field) == null) continue;

	    span = document.createElement("span");
	    span.className = "fieldname";
	    span.appendChild(document.createTextNode(field+": "));
	    div.appendChild(span);
	    if (this.data(field).toString().startsWith("http")) {
		var link = document.createElement("a");
		link.href = this.data(field);
		link.target = "nodeuri";
		link.appendChild(document.createTextNode(this.data(field)));
		div.appendChild(link);
	    }
	    else {
		div.appendChild(document.createTextNode(this.data(field)));
	    }
	    div.appendChild(document.createElement("br"));
	}

	show_attributes(div, this.data('attributes'));

	sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
    });
    cytodata[i] = null;
}


function show_attributes(html_div, atts) {
    if (atts == null)  { return; }

    var linebreak = "<hr>";

    // always display iri first
    var iri = atts.filter(a => a.name == "iri");

    for (var att of iri.concat(atts.filter(a => a.name != "iri"))) {
	var snippet = linebreak;

	if (att.name != null) {
	    snippet += "<b>" + att.name + "</b>";
	    if (att.type != null)
		snippet += " (" + att.type + ")";
	    snippet += ": ";
	}
	if (att.url != null)
	    snippet += "<a target='araxext' href='" + att.url + "'>";


	if (att.value != null) {
	    var fixit = true;
	    if (att.name == "normalized_google_distance" ||
		att.name == "fisher_exact_test_p-value"  ||
		att.name == "probability_drug_treats"    ||
		att.name == "observed_expected_ratio"    ||
		att.name == "paired_concept_frequency"   ||
		att.name == "paired_concept_freq"        ||
		att.name == "jaccard_index"              ||
		att.name == "Contribution"               ||
		att.name == "probability"                ||
		att.name == "confidence"                 ||
		att.name == "chi_square"                 ||
		att.name == "pValue"                     ||
		att.name == "ngd") {
		snippet += Number(att.value).toPrecision(3);
		fixit = false;
	    }
            else if (Array.isArray(att.value))
		for (var val of att.value) {
                    snippet += "<br>&nbsp;&nbsp;&nbsp;";
		    if (val.toString().startsWith("PMID:")) {
			snippet += "<a href='https://www.ncbi.nlm.nih.gov/pubmed/" + val.split(":")[1] + "'";
			snippet += " target='pubmed'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("DOI:")) {
			snippet += "<a href='https://doi.org/" + val.split(":")[1] + "'";
			snippet += " target='pubmed'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("http")) {
                        snippet += "<a href='" + val + "'";
                        snippet += " target='araxuri'>" + val + "</a>";
		    }
		    else {
			snippet += val;
		    }
		}
	    else if (typeof att.value === 'object') {
		snippet += "<pre>"+JSON.stringify(att.value,null,2)+"</pre>";

		fixit = false;
	    }
	    else
		snippet += att.value;

	    if (fixit) {
		snippet = snippet.toString().replace(/-!-/g,'<br>-!-');
		snippet = snippet.toString().replace(/---/g,'<br>---');
		snippet = snippet.toString().replace( /;;/g,'<br>;;');
	    }
	}
	else if (att.url != null)
	    snippet += att.url;
	else
	    snippet += " n/a ";


	if (att.url != null)
	    snippet += "</a>";

        if (att.source != null)
	    snippet += " [src:" + att.source + "]";

	html_div.innerHTML+= snippet;
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

function mapNodeShape(ele) {
    var ntype = ele.data().category ? ele.data().category[0] : "NA";
    if (ntype.endsWith("microRNA"))           { return "hexagon";} //??
    if (ntype.endsWith("Metabolite"))         { return "heptagon";}
    if (ntype.endsWith("Protein"))            { return "octagon";}
    if (ntype.endsWith("Pathway"))            { return "vee";}
    if (ntype.endsWith("Disease"))            { return "triangle";}
    if (ntype.endsWith("MolecularFunction")) { return "rectangle";}
    if (ntype.endsWith("CellularComponent")) { return "ellipse";}
    if (ntype.endsWith("BiologicalProcess")) { return "tag";}
    if (ntype.endsWith("ChemicalSubstance")) { return "diamond";}
    if (ntype.endsWith("AnatomicalEntity"))  { return "rhomboid";}
    if (ntype.endsWith("PhenotypicFeature")) { return "star";}
    return "rectangle";
}

function mapNodeColor(ele) {
    var ntype = ele.data().category;
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

function mapEdgeColor(ele) {
    var etype = ele.data().predicate ? ele.data().predicate : "NA";
    if (etype == "contraindicated_for")       { return "red";}
    if (etype == "indicated_for")             { return "green";}
    if (etype == "physically_interacts_with") { return "green";}
    return "#aaf";
}

function edit_qg() {
    cytodata[99999] = [];
    if (cyobj[99999]) {cyobj[99999].elements().remove();}

    for (var gnode of input_qg.nodes) {
	var name = "";

	if (gnode.name)       { name = gnode.name;}
	else if (gnode.curie) { name = gnode.curie;}
	else if (gnode.type)  { name = gnode.type + "s?";}
	else                  { name = "(Any)";}

        cyobj[99999].add( {
	    "data" : {
		"id"   : gnode.id,
		"name" : name,
		"type" : gnode.type,
		"parentdivnum" : 99999 },
//	    "position" : {x:100*(qgid-nn), y:50+nn*50}
	} );
    }

    for (var gedge of input_qg.edges) {
	cyobj[99999].add( {
	    "data" : {
		"id"     : gedge.id,
		"source" : gedge.source_id,
		"target" : gedge.target_id,
		"type"   : gedge.type,
		"parentdivnum" : 99999 }
	} );
    }

    cylayout(99999,"breadthfirst");
    document.getElementById('qg_form').style.visibility = 'visible';
    document.getElementById('qg_form').style.maxHeight = "100%";
    update_kg_edge_input();
    display_query_graph_items();

    document.getElementById("devdiv").innerHTML +=  "Copied query_graph to edit window<br>";
}


function display_query_graph_items() {
    var table = document.createElement("table");
    table.className = 'sumtab';

    var tr = document.createElement("tr");
    for (var head of ["Id","Name","Item","Category","Action"] ) {
	var th = document.createElement("th")
	th.appendChild(document.createTextNode(head));
	tr.appendChild(th);
    }
    table.appendChild(tr);

    var nitems = 0;

    input_qg.nodes.forEach(function(result, index) {
	nitems++;

	tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.appendChild(document.createTextNode(result.id));
        tr.appendChild(td);

        td = document.createElement("td");
        td.appendChild(document.createTextNode(result.name == null ? "-" : result.name));
        tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode(result.is_set ? "(multiple items)" : result.curie == null ? "(any node)" : result.curie));
        tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode(result.is_set ? "(set of nodes)" : result.type == null ? "(any)" : result.type));
        tr.appendChild(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_node_from_query_graph(\"'+result.id+'\")';
	link.appendChild(document.createTextNode("Remove"));
	td.appendChild(link);
        tr.appendChild(td);

	table.appendChild(tr);
    });

    input_qg.edges.forEach(function(result, index) {
        tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.appendChild(document.createTextNode(result.id));
	tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode("-"));
        tr.appendChild(td);

        td = document.createElement("td");
	td.appendChild(document.createTextNode(result.source_id+"--"+result.target_id));
	tr.appendChild(td);

        td = document.createElement("td");
	td.appendChild(document.createTextNode(result.type == null ? "(any)" : result.type));
	tr.appendChild(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_edge_from_query_graph(\"'+result.id+'\")';
	link.appendChild(document.createTextNode("Remove"));
	td.appendChild(link);
	tr.appendChild(td);

        table.appendChild(tr);
    });

    document.getElementById("qg_items").innerHTML = '';
    if (nitems > 0)
	document.getElementById("qg_items").appendChild(table);

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

    cyobj[99999].add( {
	"data" : { "id"     : qgid,
		   "source" : n1,
		   "target" : n2,
		   "type"   : et,
		   "parentdivnum" : 99999 }
    } );
    cylayout(99999,"breadthfirst");

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


function add_nodeclass_to_query_graph(nodetype) {
    document.getElementById("allnodetypes").value = '';
    document.getElementById("allnodetypes").blur();

    if (nodetype.startsWith("LIST_"))
	add_nodelist_to_query_graph(nodetype);
    else
	add_nodetype_to_query_graph(nodetype);

    update_kg_edge_input();
    display_query_graph_items();
}


function add_nodetype_to_query_graph(nodetype) {
    document.getElementById("statusdiv").innerHTML = "<p>Added a node of type <i>"+nodetype+"</i></p>";
    var qgid = get_qg_id();

    var nt = nodetype;

    cyobj[99999].add( {
        "data" : { "id"   : qgid,
		   "name" : nodetype+"s",
		   "type" : nt,
		   "parentdivnum" : 99999 },
//        "position" : {x:100*qgid, y:50}
    } );
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");

    if (nodetype=='NONSPECIFIC') { nt = null; }
    var tmpdata = { "id"     : qgid,
		    "is_set" : null,
		    "name"   : null,
		    "desc"   : "Generic " + nodetype,
		    "curie"  : null,
		    "type"   : nt
		  };

    input_qg.nodes.push(tmpdata);
}

function add_nodelist_to_query_graph(nodetype) {
    var list = nodetype.split("LIST_")[1];

    document.getElementById("statusdiv").innerHTML = "<p>Added a set of nodes from list <i>"+list+"</i></p>";
    var qgid = get_qg_id();

    cyobj[99999].add( {
        "data" : { "id"   : qgid,
		   "name" : nodetype,
		   "type" : "set",
		   "parentdivnum" : 99999 }
    } );
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");

    var tmpdata = { "id"     : qgid,
		    "is_set" : true,
		    "name"   : nodetype,
		    "desc"   : "Set of nodes from list " + list,
		    "curie"  : null,
		    "type"   : null
		  };

    input_qg.nodes.push(tmpdata);
}


function enter_node(ele) {
    if (event.key === 'Enter')
	add_node_to_query_graph();
}

async function add_node_to_query_graph() {
    var thing = document.getElementById("newquerynode").value;
    document.getElementById("newquerynode").value = '';

    if (thing == '') {
        document.getElementById("statusdiv").innerHTML = "<p class='error'>Please enter a node value</p>";
	return;
    }

    var bestthing = await check_entity(thing,false);
    document.getElementById("devdiv").innerHTML +=  "-- best node = " + JSON.stringify(bestthing,null,2) + "<br>";

    if (bestthing.found) {
        document.getElementById("statusdiv").innerHTML = "<p>Found entity with name <b>"+bestthing.name+"</b> that best matches <i>"+thing+"</i> in our knowledge graph.</p>";
	sesame('openmax',statusdiv);

	var qgid = get_qg_id();

	cyobj[99999].add( {
	    "data" : { "id"   : qgid,
		       "name" : bestthing.name,
		       "type" : bestthing.type,
		       "parentdivnum" : 99999 },
	    //		"position" : {x:100*(qgid-nn), y:50+nn*50}
	} );

	var tmpdata = { "id"     : qgid,
			"is_set" : null,
			"name"   : bestthing.name,
			"curie"  : bestthing.curie,
			"type"   : bestthing.type
		      };

	document.getElementById("devdiv").innerHTML +=  "-- found a curie = " + bestthing.curie + "<br>";
	input_qg.nodes.push(tmpdata);

	cyobj[99999].reset();
	cylayout(99999,"breadthfirst");

	update_kg_edge_input();
	display_query_graph_items();
    }
    else {
        document.getElementById("statusdiv").innerHTML = "<p><span class='error'>" + thing + "</span> is not in our knowledge graph.</p>";
	sesame('openmax',statusdiv);
    }
}


function remove_edge_from_query_graph(edgeid) {
    cyobj[99999].remove("#"+edgeid);

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
    cyobj[99999].remove("#"+nodeid);

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
    if (cyobj[99999]) { cyobj[99999].elements().remove(); }
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


function populate_dsl_commands() {
    var dsl_node = document.getElementById("dsl_command");
    dsl_node.innerHTML = '';

    var opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = '';
    opt.innerHTML = "Select DSL Command&nbsp;&nbsp;&nbsp;&#8675;";
    dsl_node.appendChild(opt);

    for (var com in araxi_commands) {
	opt = document.createElement('option');
	opt.value = com;
	opt.innerHTML = com;
	dsl_node.appendChild(opt);
    }
}

function show_dsl_command_options(command) {
    document.getElementById("dsl_command").value = '';
    document.getElementById("dsl_command").blur();

    var com_node = document.getElementById("dsl_command_form");
    com_node.innerHTML = '';
    com_node.appendChild(document.createElement('hr'));

    var h2 = document.createElement('h2');
    h2.style.marginBottom = 0;
    h2.innerHTML = command;
    com_node.appendChild(h2);

    if (araxi_commands[command].description) {
	com_node.appendChild(document.createTextNode(araxi_commands[command].description));
	com_node.appendChild(document.createElement('br'));
    }

    var skipped = '';
    for (var par in araxi_commands[command].parameters) {
        if (araxi_commands[command].parameters[par]['UI_display'] &&
	    araxi_commands[command].parameters[par]['UI_display'] == 'false') {
	    if (skipped) skipped += ", ";
	    skipped += par;
	    continue;
	}
	com_node.appendChild(document.createElement('br'));

	var span = document.createElement('span');
	if (araxi_commands[command].parameters[par]['is_required'])
	    span.className = 'essence';
	span.appendChild(document.createTextNode(par+":"));
	com_node.appendChild(span);

	span = document.createElement('span');
	span.className = 'tiny';
	span.style.position = "relative";
	span.style.left = "50px";
	span.appendChild(document.createTextNode(araxi_commands[command].parameters[par].description));
	com_node.appendChild(span);

	com_node.appendChild(document.createElement('br'));

        if (araxi_commands[command].parameters[par]['type'] == 'boolean') {
	    araxi_commands[command].parameters[par]['enum'] = ['true','false'];
	}
	else if (araxi_commands[command].parameters[par]['type'] == 'ARAXnode') {
	    araxi_commands[command].parameters[par]['enum'] = [];
            for (const p in predicates) {
		araxi_commands[command].parameters[par]['enum'].push(p);
	    }
	}
        else if (araxi_commands[command].parameters[par]['type'] == 'ARAXedge') {
	    araxi_commands[command].parameters[par]['enum'] = [];
	    for (const p of Object.keys(all_predicates).sort()) {
		araxi_commands[command].parameters[par]['enum'].push(p);
	    }
	}

	if (araxi_commands[command].parameters[par]['enum']) {
	    var span = document.createElement('span');
	    span.className = 'qgselect';

	    var sel = document.createElement('select');
	    sel.id = "__param__"+par;

	    var opt = document.createElement('option');
	    opt.style.borderBottom = "1px solid black";
	    opt.value = '';
	    opt.innerHTML = "Select&nbsp;&nbsp;&nbsp;&#8675;";
	    sel.appendChild(opt);

	    for (var val of araxi_commands[command].parameters[par]['enum']) {
		opt = document.createElement('option');
		opt.value = val;
		opt.innerHTML = val;
		sel.appendChild(opt);
	    }

	    span.appendChild(sel);
	    com_node.appendChild(span);

	    if (araxi_commands[command].parameters[par]['default'])
		sel.value = araxi_commands[command].parameters[par]['default'];

	}
	else {
	    var i = document.createElement('input');
	    i.id = "__param__"+par;
	    i.className = 'questionBox';
	    i.size = 60;
	    com_node.appendChild(i);

	    if (araxi_commands[command].parameters[par]['default'])
		i.value = araxi_commands[command].parameters[par]['default'];
	}
    }

    com_node.appendChild(document.createElement('br'));

    if (skipped) {
	com_node.appendChild(document.createElement('br'));
	com_node.appendChild(document.createTextNode('The following advanced parameters are also available: '+skipped+'. Please consult the full documentation for more information.'));
	com_node.appendChild(document.createElement('br'));
	com_node.appendChild(document.createElement('br'));
    }

    var button = document.createElement("input");
    button.className = 'questionBox button';
    button.type = 'button';
    button.name = 'action';
    button.title = 'Append new DSL command to list above';
    button.value = 'Add';
    button.setAttribute('onclick', 'add_dsl_command("'+command+'");');
    com_node.appendChild(button);

    var link = document.createElement("a");
    link.style.marginLeft = "20px";
    link.href = 'javascript:abort_dsl();';
    link.appendChild(document.createTextNode(" Cancel "));
    com_node.appendChild(link);

    com_node.appendChild(document.createElement('hr'));
}

function add_dsl_command(command) {
    var params = document.querySelectorAll('[id^=__param__]');

    var comma = ',';
    if (command.endsWith("()"))
	comma = '';

    command = command.slice(0, -1); // remove ")"

    for (var p of params) {
	if (p.value.length == 0) continue;
	command += comma + p.id.split("__param__")[1]+"="+p.value;
	comma = ",";
    }
    command += ")\n";


    //document.getElementById("dslText").value += command;

    var dslbox = document.getElementById("dslText");
    var dslval = dslbox.value;
    var doc = dslbox.ownerDocument;

    if (typeof dslbox.selectionStart == "number" &&
	typeof dslbox.selectionEnd   == "number") {
	var endIndex = dslbox.selectionEnd;

	while (endIndex>0) {
	    if (dslval.slice(endIndex-1, endIndex) == "\n")
		break;
	    endIndex--;
	}

	dslbox.value = dslval.slice(0, endIndex) + command + dslval.slice(endIndex);
	dslbox.selectionStart = dslbox.selectionEnd = endIndex + command.length;
    }
    else if (doc.selection != "undefined" && doc.selection.createRange) {
	dslbox.focus();
	var range = doc.selection.createRange();
	range.collapse(false);
	range.text = command;
	range.select();
    }

    abort_dsl();
}

function abort_dsl() {
    document.getElementById("dsl_command_form").innerHTML = '';
}


function get_example_questions() {
    fetch(baseAPI + "/exampleQuestions")
        .then(response => response.json())
        .then(data => {
	    //add_to_dev_info("EXAMPLE Qs",data);

	    var qqq = document.getElementById("qqq");
	    qqq.innerHTML = '';

            var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "Example Questions&nbsp;&nbsp;&nbsp;&#8675;";
	    qqq.appendChild(opt);

	    for (var exq of data) {
		opt = document.createElement('option');
		opt.value = exq.question_text;
		opt.innerHTML = exq.query_type_id+": "+exq.question_text;
		qqq.appendChild(opt);
	    }
	})
        .catch(error => { //ignore...
	});
}


function load_nodes_and_predicates() {
    var allnodes_node = document.getElementById("allnodetypes");
    allnodes_node.innerHTML = '';

    fetch(baseAPI + "/predicates")
	.then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong');
	})
        .then(data => {
	    //add_to_dev_info("PREDICATES",data);
	    predicates = data;

	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "Add Node by Type&nbsp;&nbsp;&nbsp;&#8675;";
	    allnodes_node.appendChild(opt);

            for (const p in predicates) {
		opt = document.createElement('option');
		opt.value = p;
		opt.innerHTML = p;
		allnodes_node.appendChild(opt);

		for (const n in predicates[p])
		    for (const r of predicates[p][n])
			all_predicates[r] = 1;
	    }
            opt = document.createElement('option');
	    opt.value = 'NONSPECIFIC';
	    opt.innerHTML = "Unspecified/Non-specific";
	    allnodes_node.appendChild(opt);

            opt = document.createElement('option');
	    opt.id = 'nodesetA';
	    opt.value = 'LIST_A';
	    opt.title = "Set of Nodes from List [A]";
	    opt.innerHTML = "List [A]";
	    allnodes_node.appendChild(opt);

            opt = document.createElement('option');
	    opt.id = 'nodesetB';
	    opt.value = 'LIST_B';
            opt.title = "Set of Nodes from List [B]";
	    opt.innerHTML = "List [B]";
	    allnodes_node.appendChild(opt);
	})
        .catch(error => {
	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "-- Error Loading Node Types --";
	    allnodes_node.appendChild(opt);
        });
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


function togglecolor(obj,tid) {
    var col = '#888';
    if (obj.checked == true) {
	col = '#047';
    }
    document.getElementById(tid).style.color = col;
}


// adapted from http://www.activsoftware.com/
function getQueryVariable(variable) {
    for (var qsv of window.location.search.substring(1).split("&")) {
	var pair = qsv.split("=");
	if (decodeURIComponent(pair[0]) == variable)
	    return decodeURIComponent(pair[1]);
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
	    listhtml += "<tr class='hoverable'>";

	    if (entities.hasOwnProperty(li)) {
		listhtml += "<td>"+entities[li].checkHTML+"</td>";
		listhtml += "<td title='view ARAX synonyms' class='clq' onclick='lookup_synonym(this.nextSibling.innerHTML,true);'>\u2139</td>";
		listhtml += "<td>"+entities[li].name+"</td>";
		if (entities[li].isvalid)
		    listhtml += "<td title='view ARAX synonyms' class='clq' onclick='lookup_synonym(this.nextSibling.innerHTML,true);'>\u2139</td>";
		else
		    listhtml += "<td></td>";
		listhtml += "<td>"+entities[li].curie+"</td>";
		listhtml += "<td>"+entities[li].type+"</td>";
	    }
	    else {
		listhtml += "<td id='list"+listId+"_entitycheck_"+li+"'>--</td>";
		listhtml += "<td title='view ARAX synonyms' class='clq' onclick='lookup_synonym(this.nextSibling.innerHTML,true);'>\u2139</td>";
		listhtml += "<td id='list"+listId+"_entityname_"+li+"'>"+li+"</td>";
		listhtml += "<td title='view ARAX synonyms' class='clq' onclick='lookup_synonym(this.nextSibling.innerHTML,true);'>\u2139</td>";
		listhtml += "<td id='list"+listId+"_entitycurie_"+li+"'>looking up...</td>";
		listhtml += "<td id='list"+listId+"_entitytype_"+li+"'>looking up...</td>";
		entities[li] = {};
		entities[li].checkHTML = '--';
	    }

	    listhtml += "<td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/>Remove</a></td></tr>";
	}
    }


    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("menunumlistitems"+listId).innerHTML = numitems;

    if (document.getElementById("nodeset"+listId))
	document.getElementById("nodeset"+listId).innerHTML = "List [" + listId + "] -- (" + numitems + " items)";

    if (numitems > 0) {
	listhtml = "<table class='sumtab'><tr><th></th><th></th><th>Name</th><th></th><th>Item</th><th>Type</th><th>Action</th></tr>" + listhtml + "</table><br><br>";
	document.getElementById("menunumlistitems"+listId).classList.add("numnew");
	document.getElementById("menunumlistitems"+listId).classList.remove("numold");
    }
    else {
	document.getElementById("menunumlistitems"+listId).classList.remove("numnew");
	document.getElementById("menunumlistitems"+listId).classList.add("numold");
    }

    listhtml = "Items in this list can be passed as input to queries that support list input, by specifying <b>["+listId+"]</b> as a query parameter.<br><br>" + listhtml + "<hr>Enter new list item or items (space and/or comma-separated; use &quot;double quotes&quot; for multi-word items):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' onkeydown='enter_item(this, \""+listId+"\");' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>";

//    listhtml += "<hr>Enter new list item or items (space and/or comma-separated):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>";

    if (numitems > 0)
	listhtml += "<a style='margin-left:20px;' href='javascript:delete_list(\""+listId+"\");'/>Delete List</a>";

    listhtml += "<br><br>";

    document.getElementById("listdiv"+listId).innerHTML = listhtml;
    //check_entities();
    check_entities_batch(99);
    compare_lists(false);
}


function compare_lists(uniqueonly) {
    if (!uniqueonly || uniqueonly == "false")
	uniqueonly = false;
    else
	uniqueonly = true;

    // assume only listA and listB, for now...
    var keysA = Object.keys(listItems['A']);
    var keysB = Object.keys(listItems['B']);
    compare_tsv = [];

    var comparediv = document.getElementById("comparelists");
    comparediv.innerHTML = "";

    if (keysA.length == 0 || keysB.length == 0) {
	comparediv.appendChild(document.createElement("br"));
	comparediv.appendChild(document.createTextNode("Items in lists A and B will be automatically displayed side-by-side for ease of comparison."));
        comparediv.appendChild(document.createElement("br"));
	comparediv.appendChild(document.createElement("br"));
	comparediv.appendChild(document.createTextNode("At least one item is required in each list."));
        comparediv.appendChild(document.createElement("br"));
	comparediv.appendChild(document.createElement("br"));
	return;
    }

    compare_tsv.push("List A\tList B");
    var button = document.createElement("input");
    button.className = 'questionBox button';
    button.type = 'button';
    button.name = 'action';
    button.title = 'Get tab-separated values of this table to paste into Excel etc';
    button.value = 'Copy Comparison Table to clipboard (TSV)';
    button.setAttribute('onclick', 'copyTSVToClipboard(this,compare_tsv);');
    comparediv.appendChild(button);

    var span = document.createElement("span");
    span.className = 'qgselect';
    span.style.marginLeft = "100px";

    var sel = document.createElement('select');
    sel.setAttribute('onchange', 'compare_lists(this.value);');
    var opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = "false";
    if (!uniqueonly) opt.selected = true;
    opt.innerHTML = "Show all items in lists";
    sel.appendChild(opt);
    opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = "true";
    if (uniqueonly) opt.selected = true;
    opt.innerHTML = "Show only unique items";
    sel.appendChild(opt);
    span.appendChild(sel);
    comparediv.appendChild(span);

    comparediv.appendChild(document.createElement("br"));
    comparediv.appendChild(document.createElement("br"));

    var comptable = document.createElement("table");
    comptable.className = 'sumtab';
    var tr = document.createElement("tr");
    var td = document.createElement("th");
    tr.appendChild(td);
    td = document.createElement("th");
    td.appendChild(document.createTextNode("List A"));
    tr.appendChild(td);
    td = document.createElement("th");
    tr.appendChild(td);
    td = document.createElement("th");
    td.appendChild(document.createTextNode("List B"));
    tr.appendChild(td);
    comptable.appendChild(tr);

    if (uniqueonly) {
	var onlyA = keysA.filter(x => !keysB.includes(x));
	keysB = keysB.filter(x => !keysA.includes(x));
	keysA = onlyA;
    }

    var maxkeys = (keysA.length > keysB.length) ? keysA : keysB;
    for (var idx in maxkeys) {
	tr = document.createElement("tr");
	tr.className = 'hoverable';

	td = document.createElement("td");
	span = document.createElement("span");
        if (keysA[idx] == keysB[idx]) {
	    span.className = "explevel p9";
	    span.innerHTML = "&check;";
	}
        else if (listItems['B'][keysA[idx]]) {
	    span.className = "explevel p5";
	    span.innerHTML = "&check;";
	}
	else {
            span.className = "explevel p1";
	    span.innerHTML = "&cross;";
	}
        td.appendChild(span);
        tr.appendChild(td);
        td = document.createElement("td");
	td.innerHTML = keysA[idx]?keysA[idx]:'--n/a--';
	tr.appendChild(td);

        td = document.createElement("td");
	span = document.createElement("span");
	if (keysA[idx] == keysB[idx]) {
	    span.className = "explevel p9";
	    span.innerHTML = "&check;";
	}
	else if (listItems['A'][keysB[idx]]) {
	    span.className = "explevel p5";
	    span.innerHTML = "&check;";
	}
	else {
	    span.className = "explevel p1";
	    span.innerHTML = "&cross;";
	}
	td.appendChild(span);
	tr.appendChild(td);
	td = document.createElement("td");
	td.innerHTML = keysB[idx]?keysB[idx]:'--n/a--';
	tr.appendChild(td);

	comptable.appendChild(tr);
	compare_tsv.push(keysA[idx]+"\t"+keysB[idx]);
    }

    comparediv.appendChild(comptable);
    comparediv.appendChild(document.createElement("br"));
    comparediv.appendChild(document.createElement("br"));
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


function get_list_as_curie_array(listId) {
    var carr = [];
    for (var li in listItems[listId])
	if (listItems[listId].hasOwnProperty(li) && listItems[listId][li] == 1)
	    carr.push(entities[li].curie);

    return carr;
}


function add_items_to_list(listId,indx) {
    for (var nitem in columnlist[indx])
	if (columnlist[indx][nitem]) {
            nitem = nitem.replace(/['"]+/g,''); // remove all manner of quotes
	    listItems[listId][nitem] = 1;
	}
    display_list(listId);
}

function enter_item(ele, listId) {
    if (event.key === 'Enter')
	add_new_to_list(listId);
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
    add_to_dev_info("ALL_ENTITIES:",entities);
}

function remove_item(listId,item) {
    delete listItems[listId][item];
    display_list(listId);
}

function delete_list(listId) {
    listItems[listId] = {};
    display_list(listId);
}


function check_entities_batch(batchsize) {
    var batches = [];
    var thisbatch = '';
    var items = 0;
    for (var entity in entities) {
	if (entities[entity].checkHTML != '--') continue;
	if (items == batchsize) {
	    batches.push(thisbatch);
	    thisbatch = '';
	    items = 0;
	}
	thisbatch += "&q="+entity;
	items++;
    }
    // last one
    if (thisbatch) batches.push(thisbatch);

    for (let batch of batches) {
        fetch(baseAPI + "/entity?output_mode=minimal" + batch)
	    .then(response => response.json())
	    .then(data => {
		add_to_dev_info("ENTITIES:"+batch,data);
		for (var entity in data) {
                    if (entities[entity] && data[entity] && data[entity].id && data[entity].id.identifier) {
			entities[entity].curie = data[entity].id.identifier;
			entities[entity].name  = data[entity].id.name;
			entities[entity].type  = data[entity].id.category;
			//entities[entity].name = data[entity].id.label.replace(/['"]/g, '&apos;');  // might need this?

			entities[entity].isvalid   = true;
			entities[entity].checkHTML = "<span class='explevel p9'>&check;</span>&nbsp;";
			document.getElementById("devdiv").innerHTML += data[entity].id.type+"<br>";
		    }
		    else if (entities[entity]) {
			entities[entity].curie = "<span class='error'>unknown</span>";
			entities[entity].name  = entity;
			entities[entity].type  = "<span class='error'>unknown</span>";
			entities[entity].isvalid   = false;
			entities[entity].checkHTML = "<span class='explevel p1'>&cross;</span>&nbsp;";
		    }
		    else {
			console.warn("Could not find entity: "+entity);
		    }
		    // in case of a 404...?? entstr = "<span class='explevel p0'>&quest;</span>&nbsp;n/a";

		    for (var elem of document.querySelectorAll("[id$='_entitycurie_"+entity+"']"))
			elem.innerHTML = entities[entity].curie;
		    for (var elem of document.querySelectorAll("[id$='_entityname_"+entity+"']"))
			elem.innerHTML = entities[entity].name;
		    for (var elem of document.querySelectorAll("[id$='_entitytype_"+entity+"']"))
			elem.innerHTML = entities[entity].type;
		    for (var elem of document.querySelectorAll("[id$='_entitycheck_"+entity+"']"))
			elem.innerHTML = entities[entity].checkHTML;
		}
	    });
    }
}



function check_entities() {
    for (let entity in entities) {
	if (entities[entity].checkHTML != '--') continue;

	fetch(baseAPI + "/entity?q=" + entity)
	    .then(response => response.json())
	    .then(data => {
                add_to_dev_info("ENTITIES:"+entity,data);

		if (data[entity] && data[entity].id && data[entity].id.identifier) {
		    entities[entity].curie = data[entity].id.identifier;
		    entities[entity].name  = data[entity].id.name;
		    entities[entity].type  = data[entity].id.category;
		    //entities[entity].name = data[entity].id.label.replace(/['"]/g, '&apos;');  // might need this?

		    entities[entity].isvalid   = true;
		    entities[entity].checkHTML = "<span class='explevel p9'>&check;</span>&nbsp;";
		    document.getElementById("devdiv").innerHTML += data[entity].id.type+"<br>";
		}
		else {
		    entities[entity].curie = "<span class='error'>unknown</span>";
		    entities[entity].name  = entity;
		    entities[entity].type  = "<span class='error'>unknown</span>";
		    entities[entity].isvalid   = false;
		    entities[entity].checkHTML = "<span class='explevel p1'>&cross;</span>&nbsp;";
		}

		// in case of a 404...?? entstr = "<span class='explevel p0'>&quest;</span>&nbsp;n/a";

		for (var elem of document.querySelectorAll("[id$='_entitycurie_"+entity+"']"))
		    elem.innerHTML = entities[entity].curie;
		for (var elem of document.querySelectorAll("[id$='_entityname_"+entity+"']"))
		    elem.innerHTML = entities[entity].name;
		for (var elem of document.querySelectorAll("[id$='_entitytype_"+entity+"']"))
		    elem.innerHTML = entities[entity].type;
		for (var elem of document.querySelectorAll("[id$='_entitycheck_"+entity+"']"))
		    elem.innerHTML = entities[entity].checkHTML;

	    })
	    .catch(error => {
                add_to_dev_info("ENTITIES(error):"+entity,error);
		entities[entity].name = "n/a";
		entities[entity].type = "n/a";
                entities[entity].isvalid   = false;
		entities[entity].checkHTML = "<span class='explevel p0'>&quest;</span>&nbsp;";
                for (var elem of document.querySelectorAll("[id$='_entityname_"+entity+"']"))
		    elem.innerHTML = entities[entity].name;
                for (var elem of document.querySelectorAll("[id$='_entitytype_"+entity+"']"))
		    elem.innerHTML = entities[entity].typecheckHTML;
                for (var elem of document.querySelectorAll("[id$='_entitycheck_"+entity+"']"))
		    elem.innerHTML = entities[entity].checkHTML;
		console.log(error);
	    });
    }
}


async function check_entity(term,wantall) {
    var data = {};
    var ent  = {};
    ent.found = false;

    if (!wantall && entities[term]) {
        if (!entities[term].isvalid)
            return ent; // contains found=false

	data = entities[term];
    }
    else {
	var response = await fetch(baseAPI + "/entity?q=" + term);
	var fulldata = await response.json();

	add_to_dev_info("ENTITY:"+term,fulldata);
	if (wantall)
	    return fulldata;
	else if (!fulldata[term].id)
	    return ent; // contains found=false

	data.curie = fulldata[term].id.identifier;
	data.name  = fulldata[term].id.name;
	data.type  = fulldata[term].id.category;
    }

    ent.found = true;
    ent.curie = data.curie;
    ent.name  = data.name;
    ent.type  = data.type;

    if (!entities[data.curie]) {
	entities[data.curie] = {}; //xob[i].name + "::" + xob[i].type;
	entities[data.curie].curie = data.curie;
	entities[data.curie].name  = data.name;
	entities[data.curie].type  = data.type;
        entities[data.curie].isvalid   = true;
	entities[data.curie].checkHTML = "<span class='explevel p9'>&check;</span>&nbsp;";
    }

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
            listhtml += "<tr><td>"+li+".</td><td><a target='_new' title='view this response in a new window' href='//"+ window.location.hostname + window.location.pathname;
	    if (listItems[listId][li].startsWith("source")) // hacky
		listhtml += "?"+listItems[listId][li];
	    else
		listhtml += "?r="+listItems[listId][li];

	    listhtml +="'>" + listItems['SESSION']["qtext_"+li] + "</a></td><td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/>Remove</a></td></tr>";
        }
    }
    if (numitems > 0) {
        listhtml += "<tr style='background-color:unset;'><td style='border-bottom:0;'></td><td style='border-bottom:0;'></td><td style='border-bottom:0;'><a href='javascript:delete_list(\""+listId+"\");'/> Delete Session History </a></td></tr>";
    }


    if (numitems == 0) {
        listhtml = "<br>Your query history will be displayed here. It can be edited or re-set.<br><br>";
    }
    else {
        listhtml = "<table class='sumtab'><tr><th></th><th>Query</th><th>Action</th></tr>" + listhtml + "</table><br><br>";
    }

    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("menunumlistitems"+listId).innerHTML = numitems;
    document.getElementById("listdiv"+listId).innerHTML = listhtml;
}


function copyJSON(ele) {
    var containerid = "responseJSON";

    if (document.selection) {
	var range = document.body.createTextRange();
	range.moveToElementText(document.getElementById(containerid));
	range.select().createTextRange();
	document.execCommand("copy");
	addCheckBox(ele,true);
    }
    else if (window.getSelection) {
	var range = document.createRange();
	range.selectNode(document.getElementById(containerid));
        window.getSelection().removeAllRanges();
	window.getSelection().addRange(range);
	document.execCommand("copy");
	addCheckBox(ele,true);
	//alert("text copied")
    }
}

function copyTSVToClipboard(ele,tsv) {
    var dummy = document.createElement("textarea");
    document.body.appendChild(dummy);
    dummy.setAttribute("id", "dummy_id");
    for (var line of tsv)
	document.getElementById("dummy_id").value+=line+"\n";
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);

    addCheckBox(ele,true);
}

function addCheckBox(ele,remove) {
    var check = document.createElement("span");
    check.className = 'explevel p9';
    check.innerHTML = '&check;';
    ele.parentNode.insertBefore(check, ele.nextSibling);

    if (remove)
	var timeout = setTimeout(function() { check.remove(); }, 1500 );
}
