var input_qg = { "edges": {}, "nodes": {} };
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
var response_cache = {};
var UIstate = {};

// defaults
var base = "";
var baseAPI = base + "api/arax/v1.1";

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

// these attributes are floats; truncate them
const attributes_to_truncate = [
    "Contribution",
    "chi_square",
    "confidence",
    "fisher_exact_test_p-value",
    "jaccard_index",
    "ln_ratio",
    "ngd",
    "normalized_google_distance",
    "observed_expected_ratio",
    "pValue",
    "paired_concept_freq",
    "paired_concept_frequency",
    "probability",
    "probability_drug_treats",
    "relative_frequency_object",
    "relative_frequency_subject"
];


function main() {
    UIstate["version"] = checkUIversion(false);
    document.getElementById("menuapiurl").href = baseAPI + "/ui/";

    get_example_questions();
    load_meta_knowledge_graph();
    populate_dsl_commands();
    display_list('A');
    display_list('B');
    add_status_divs();
    cytodata[99999] = 'dummy';

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
        pasteId(response_id);
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
    dragElement(document.getElementById('nodeeditor'));
    dragElement(document.getElementById('edgeeditor'));
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

    display_qg_popup('node','hide');
    display_qg_popup('edge','hide');

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

    display_qg_popup('node','hide');
    display_qg_popup('edge','hide');

    for (var s of ['qtext_input','qgraph_input','qjson_input','qdsl_input','qid_input','resp_input']) {
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
function clearResponse() {
    document.getElementById("responseText").value = '';
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
	document.getElementById("dslText").value = '# This program creates two query nodes and a query edge between them, looks for matching edges in the KG,\n# overlays NGD metrics, and returns the top 30 results\nadd_qnode(name=acetaminophen, key=n0)\nadd_qnode(categories=biolink:Protein, key=n1)\nadd_qedge(subject=n0, object=n1, key=e0)\nexpand()\noverlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)\nresultify()\nfilter_results(action=limit_number_of_results, max_results=30)\n';
    }
    else {
	document.getElementById("jsonText").value = '{\n   "edges": {\n      "e00": {\n         "subject":   "n00",\n         "object":    "n01",\n         "predicates": ["biolink:physically_interacts_with"]\n      }\n   },\n   "nodes": {\n      "n00": {\n         "ids":        ["CHEMBL.COMPOUND:CHEMBL112"]\n      },\n      "n01": {\n         "categories":  ["biolink:Protein"]\n      }\n   }\n}\n';
    }
}

function reset_vars() {
    add_status_divs();
    checkUIversion(true);
    if (cyobj[0]) {cyobj[0].elements().remove();}
    display_qg_popup('node','hide');
    display_qg_popup('edge','hide');
    document.getElementById("result_container").innerHTML = "";
    document.getElementById("summary_container").innerHTML = "";
    document.getElementById("provenance_container").innerHTML = "";
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
}

function viewResponse() {
    var resp = document.getElementById("responseText").value;
    if (!resp) return;

    reset_vars();

    var jsonInput;
    try {
	jsonInput = JSON.parse(resp);
    }
    catch(e) {
	statusdiv.appendChild(document.createElement("br"));
	if (e.name == "SyntaxError")
	    statusdiv.innerHTML += "<b>Error</b> parsing JSON response input. Please correct errors and resubmit: ";
	else
	    statusdiv.innerHTML += "<b>Error</b> processing response input. Please correct errors and resubmit: ";
	statusdiv.appendChild(document.createElement("br"));
	statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
	return;
    }

    render_response(jsonInput,true);
}


function postQuery(qtype,agent) {
    var queryObj= {};

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
	//queryObj.max_results = 100;

	qg_new(false,false);
    }
    else {  // qGraph
	document.getElementById("questionForm").elements["questionText"].value = '-- posted async query via graph --';
	statusdiv.innerHTML = "Posting graph.  Looking for answer...";
        statusdiv.appendChild(document.createElement("br"));

	qg_clean_up(true);
	queryObj.message = { "query_graph" :input_qg };
	//queryObj.bypass_cache = bypass_cache;
	//queryObj.max_results = 100;

	qg_new(false,false);
    }

    if (agent == 'ARS')
	postQuery_ARS(queryObj);
    else
	postQuery_ARAX(qtype,queryObj);

}

function postQuery_ARS(queryObj) {
    var ars_api = 'https://ars.ci.transltr.io/ars/api/submit';

    document.getElementById("statusdiv").innerHTML += " - contacting ARS...";
    document.getElementById("statusdiv").appendChild(document.createElement("br"));

    fetch(ars_api, {
	method: 'post',
	body: JSON.stringify(queryObj),
	headers: { 'Content-type': 'application/json' }
    }).then(response => {
	if (response.ok) return response.json();
	else throw new Error('Something went wrong');
    })
        .then(data => {
	    var message_id = data['pk'];
	    document.getElementById("statusdiv").innerHTML += " - got message_id = "+message_id;
	    document.getElementById("statusdiv").appendChild(document.createElement("br"));
	    pasteId(message_id);
	    retrieve_response('ARS',providers['ARS'].url+message_id,message_id,"all");
	})
        .catch(error => {
            document.getElementById("statusdiv").innerHTML += " - ERROR:: "+error;
        });

    return;
}


// use fetch and stream
function postQuery_ARAX(qtype,queryObj) {
    queryObj.stream_progress = true;

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
			if (jsonMsg.logs) { // was:: (jsonMsg.description) {
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
		qg_new(false,false);
	    }
	    else if (data["status"] == "OK") {
		input_qg = { "edges": {}, "nodes": {} };
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
    text.target = '_blank';
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
    link.target = '_blank';
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
	document.getElementById("respsize_"+id).innerHTML = '';
	document.getElementById("nodedges_"+id).innerHTML = '';
	document.getElementById("nsources_"+id).innerHTML = '';
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

function checkRefreshARS() {
    document.getElementById("ars_refresh").dataset.count += "x";
    var moon = 127765;
    if (document.getElementById("ars_refresh").dataset.count.length == document.getElementById("ars_refresh").dataset.total) {
	document.getElementById("ars_refresh").innerHTML = "&#"+moon;
	var timetogo = 8;
	var timeout = setInterval(countdown, 375);
	function countdown() {
	    if (timetogo == 0) {
		clearInterval(timeout);
                sendId();
		document.getElementById("ars_refresh").innerHTML = "";
	    }
	    else {
		moon--;
		if (moon == 127760) moon = 127768;
		document.getElementById("ars_refresh").innerHTML = "&#"+moon;
		timetogo--;
	    }
	}

    }
}

function sendId() {
    var id = document.getElementById("idText").value.trim();
    if (!id) return;

    reset_vars();
    if (cyobj[99999]) {cyobj[99999].elements().remove();}
    input_qg = { "edges": {}, "nodes": {} };

    if (document.getElementById("numresults_"+id)) {
	document.getElementById("numresults_"+id).innerHTML = '';
	document.getElementById("respsize_"+id).innerHTML = '';
	document.getElementById("nodedges_"+id).innerHTML = '';
        document.getElementById("nsources_"+id).innerHTML = '';
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
    input_qg = { "edges": {}, "nodes": {} };

    var bypass_cache = true;
    if (document.getElementById("useCache").checked) {
	bypass_cache = false;
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
                //queryObj.max_results = 100;

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
        document.title = "ARAX-UI [ARS Collection: "+ars_msg.message+"]";
        add_to_session('source=ARS&id='+ars_msg.message,"[ARS Collection] id="+ars_msg.message);
	history.pushState({ id: 'ARAX_UI' }, 'ARAX | source=ARS&id='+ars_msg.message, "//"+ window.location.hostname + window.location.pathname + '?source=ARS&id='+ars_msg.message);

	if (document.getElementById('ars_message_list'))
	    document.getElementById('ars_message_list').remove();
	var div = document.createElement("div");
	div.id = 'ars_message_list';

        var div2 = document.createElement("div");
	div2.className = "statushead";
        div2.appendChild(document.createTextNode("Collection Results"));
        div.appendChild(div2);

	var span = document.createElement("span");
	span.id = 'ars_refresh';
	span.style.float = 'right';
	span.style.marginRight = '20px';
	span.dataset.total = ars_msg.status == 'Done' ? 999999 : ars_msg["children"].length + 1;
	span.dataset.count = '';
	span.appendChild(document.createTextNode("Auto-reload: " + (ars_msg.status == 'Done' ? "OFF" : "ON")));
	div2.appendChild(span);

	var div2 = document.createElement("div");
	div2.id = "arsresultsdiv";
	div2.className = "status";

	table = document.createElement("table");
	table.id = 'ars_message_list_table';
	table.className = 'sumtab';

	tr = document.createElement("tr");
	for (var head of ["","Agent","Status / Code","Message Id","Size","TRAPI 1.1?","N_Results","Nodes / Edges","Sources"] ) {
	    td = document.createElement("th")
	    td.style.paddingRight = "15px";
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
    if (ars_msg.status == 'Error')
	td.className = 'error';
    else if (ars_msg.status == 'Running')
	td.className = 'essence';
    td.appendChild(document.createTextNode(ars_msg.status));
    if (ars_msg.code)
        td.appendChild(document.createTextNode(" / "+ars_msg.code));
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
    td.id = "respsize_"+ars_msg.message;
    td.style.textAlign = "right";
    tr.appendChild(td);

    td = document.createElement("td");
    td.id = "istrapi_"+ars_msg.message;
    td.style.textAlign = "center";
    tr.appendChild(td);

    td = document.createElement("td");
    td.id = "numresults_"+ars_msg.message;
    td.style.textAlign = "center";
    tr.appendChild(td);

    td = document.createElement("td");
    td.id = "nodedges_"+ars_msg.message;
    td.style.textAlign = "center";
    tr.appendChild(td);

    td = document.createElement("td");
    td.id = "nsources_"+ars_msg.message;
    td.style.textAlign = "center";
    tr.appendChild(td);

    table.appendChild(tr);

    if (go)
	getIdStats(ars_msg.message);
    else
	checkRefreshARS();

    level++;
    for (let child of ars_msg["children"].sort(function(a, b) { return a.actor.agent > b.actor.agent ? 1 : -1; }))
	process_ars_message(child, level);
}


function process_response(provider, resp_url, resp_id, type, jsonObj2) {
    if (type == "all") {
	var devdiv = document.getElementById("devdiv");
	devdiv.appendChild(document.createElement("br"));
	devdiv.appendChild(document.createTextNode('='.repeat(80)+" RESPONSE REQUEST::"));
	var link = document.createElement("a");
	link.target = '_blank';
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

    if (jsonObj2.validation_result) {
	var nr = document.createElement("span");
        if (type == "all")
	    statusdiv.innerHTML += "<br>TRAPI v"+jsonObj2.validation_result.version+" validation: <b>"+jsonObj2.validation_result.status+"</b><br>";
	if (jsonObj2.validation_result.status == "FAIL") {
	    if (type == "all")
		statusdiv.innerHTML += "<span class='error'>"+jsonObj2.validation_result.message+"</span><br>";
	    nr.innerHTML = '&cross;';
	    nr.className = 'explevel p1';
	    nr.title = 'Failed TRAPI 1.1 validation';
	}
        else if (jsonObj2.validation_result.status == "NA") {
            if (type == "all")
		statusdiv.innerHTML += "<span class='error'>"+jsonObj2.validation_result.message+"</span><br>";
	    nr.innerHTML = '&nsub;';
	    nr.className = 'explevel p0';
            nr.title = 'Response is non-TRAPI';
	}
	else {
	    nr.innerHTML = '&check;';
	    nr.className = 'explevel p9';
	    nr.title = 'Passed TRAPI 1.1 validation';
	}

	if (document.getElementById("istrapi_"+jsonObj2.araxui_response)) {
	    document.getElementById("istrapi_"+jsonObj2.araxui_response).innerHTML = '';
	    document.getElementById("istrapi_"+jsonObj2.araxui_response).appendChild(nr);

	    var num = parseFloat(jsonObj2.validation_result.size.match(/[\d\.]+/));
	    if (num && num > 2 && jsonObj2.validation_result.size.includes("MB")) {
		document.getElementById("respsize_"+jsonObj2.araxui_response).className = "error";
		document.getElementById("respsize_"+jsonObj2.araxui_response).title = "Warning: Very large responses might render slowly";
	    }
	    document.getElementById("respsize_"+jsonObj2.araxui_response).innerHTML = jsonObj2.validation_result.size;

	    if (jsonObj2.validation_result.n_nodes)
		document.getElementById("nodedges_"+jsonObj2.araxui_response).innerHTML = jsonObj2.validation_result.n_nodes+' / '+jsonObj2.validation_result.n_edges;

	    if (jsonObj2.validation_result.provenance_summary) {
		var html_node = document.getElementById("nsources_"+jsonObj2.araxui_response);
		html_node.innerHTML = jsonObj2.validation_result.provenance_summary.n_sources;

		if (jsonObj2.validation_result.n_edges > 0) {
		    var table, tr, td;
		    html_node.className = "tooltip";
		    var tnode = document.createElement("span");
		    tnode.className = 'tooltiptext';
		    table = document.createElement("table");
		    table.style.width = "100%";
		    table.style.borderCollapse = "collapse";
		    tr = document.createElement("tr");
		    td = document.createElement("th");
		    td.colSpan = "4";
		    td.style.background = "#3d6d98";
		    td.style.padding = "5px 0px";
		    td.appendChild(document.createTextNode("Provenance Counts"));
		    tr.appendChild(td);
		    table.appendChild(tr);
		    for (var prov in jsonObj2.validation_result.provenance_summary.provenance_counts) {
			tr = document.createElement("tr");
			tr.style.background = "initial";
			for (var pc of jsonObj2.validation_result.provenance_summary.provenance_counts[prov]) {
			    td = document.createElement("td");
			    td.appendChild(document.createTextNode(pc));
			    tr.appendChild(td);
			}
			td.style.textAlign = "right";  // last td is always[?] the count number
			table.appendChild(tr);
		    }
		    tnode.appendChild(table);
		    html_node.appendChild(tnode);
		    // trickery to fix FF annoying h-scrollbar issue
		    tnode.style.visibility = "visible";
		    if (tnode.scrollWidth > 440)
			tnode.style.width = tnode.scrollWidth + 15 + "px";
		    tnode.style.visibility = "";

		    // do predicates
                    html_node = document.getElementById("nodedges_"+jsonObj2.araxui_response);
		    html_node.className = "tooltip";
		    tnode = document.createElement("span");
		    tnode.className = 'tooltiptext';
		    table = document.createElement("table");
		    table.style.width = "100%";
                    table.style.borderCollapse = "collapse";
                    tr = document.createElement("tr");
		    tr.style.background = "initial";
		    td = document.createElement("th");
		    td.colSpan = "2";
                    td.style.background = "#3d6d98";
		    td.style.padding = "5px 0px";
		    td.appendChild(document.createTextNode("Predicate Counts"));
		    tr.appendChild(td);
		    table.appendChild(tr);
		    for (var pred in jsonObj2.validation_result.provenance_summary.predicate_counts) {
			tr = document.createElement("tr");
                        tr.style.background = "initial";
			td = document.createElement("td")
			td.appendChild(document.createTextNode(pred));
			tr.appendChild(td);
			td = document.createElement("td");
			td.style.textAlign = "right";
			td.appendChild(document.createTextNode(jsonObj2.validation_result.provenance_summary.predicate_counts[pred]));
			tr.appendChild(td);
			table.appendChild(tr);
		    }
		    tnode.appendChild(table);
		    html_node.appendChild(tnode);
		}
	    }
	    checkRefreshARS();
	}
    }

    if (document.getElementById("arsresultsdiv"))
	document.getElementById("arsresultsdiv").style.height = document.getElementById("arsresultsdiv").scrollHeight + "px";

    if (type == "all") {
	statusdiv.innerHTML += "<br>";
	if (jsonObj2.description)
            statusdiv.innerHTML += "<h3><i>"+jsonObj2.description+"</i></h3>";
	if (jsonObj2.status)
            statusdiv.innerHTML += "<h3><i>"+jsonObj2.status+"</i></h3>";
        statusdiv.innerHTML += "<br>";
    }
    sesame('openmax',statusdiv);

    if (type == "stats")
	render_response_stats(jsonObj2);
    else
	render_response(jsonObj2,true);

    if (!response_cache[provider+":"+resp_id])
	response_cache[provider+":"+resp_id] = jsonObj2;
}


function retrieve_response(provider, resp_url, resp_id, type) {
    if (type == null) type = "all";
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.appendChild(document.createTextNode("Retrieving "+provider+" response id = " + resp_id));

    if (response_cache[provider+":"+resp_id]) {
        if (document.getElementById("istrapi_"+resp_id))
	    document.getElementById("istrapi_"+resp_id).innerHTML = 'rendering...';
	statusdiv.appendChild(document.createTextNode(" ...from cache"));
	statusdiv.appendChild(document.createElement("hr"));
	sesame('openmax',statusdiv);
	// 50ms timeout allows css animation to start before processing locks the thread
	var timeout = setTimeout(function() { process_response(provider, resp_url, resp_id, type,response_cache[provider+":"+resp_id]); }, 50 );
	return;
    }

    statusdiv.appendChild(document.createElement("hr"));
    sesame('openmax',statusdiv);

    var xhr = new XMLHttpRequest();
    xhr.open("get",  resp_url, true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.send(null);
    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
            if (document.getElementById("istrapi_"+resp_id))
		document.getElementById("istrapi_"+resp_id).innerHTML = 'rendering...';
	    process_response(provider, resp_url, resp_id, type,JSON.parse(xhr.responseText));

	}
	else if ( xhr.status == 404 ) {
	    if (document.getElementById("numresults_"+resp_id)) {
		document.getElementById("numresults_"+resp_id).innerHTML = '';
                document.getElementById("respsize_"+resp_id).innerHTML = '---';
		document.getElementById("nodedges_"+resp_id).innerHTML = '';
		document.getElementById("nsources_"+id).innerHTML = '';
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
		document.getElementById("respsize_"+resp_id).innerHTML = '---';
		document.getElementById("nodedges_"+resp_id).innerHTML = '';
		document.getElementById("nsources_"+id).innerHTML = '';
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

    if ( !respObj.message ) {
        nr.className = 'explevel p0';
	nr.innerHTML = '&nbsp;N/A&nbsp;';
    }
    else if ( respObj.message["results"] ) {
	if (respObj.validation_result && respObj.validation_result.status == "FAIL")
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
    if (!respObj["schema_version"])
	respObj["schema_version"] = "1.1 (presumed)";
    statusdiv.appendChild(document.createTextNode("Rendering TRAPI "+respObj["schema_version"]+" message..."));

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


    if (!respObj.message) {
	statusdiv.appendChild(document.createTextNode("no message!"));
	statusdiv.appendChild(document.createElement("br"));
	var nr = document.createElement("span");
	nr.className = 'essence';
	nr.appendChild(document.createTextNode("Response contains no message, and hence no results."));
	statusdiv.appendChild(nr);
	sesame('openmax',statusdiv);
        if (document.getElementById("numresults_"+respObj.araxui_response)) {
	    document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';
	    var nr = document.createElement("span");
	    nr.className = 'explevel p0';
	    nr.innerHTML = '&nbsp;N/A&nbsp;';
	    document.getElementById("numresults_"+respObj.araxui_response).appendChild(nr);
	}
	return;
    }

    if (respObj.message["query_graph"]) {
	if (dispjson) {
	    // delete null attributes to simplify json
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
	process_graph(respObj.message["query_graph"],99999,respObj["schema_version"]);
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
	add_to_summary(["score","'guessence'"],0);

    if ( respObj.message["results"] ) {
	if (!respObj.message["knowledge_graph"] ) {
            document.getElementById("result_container").innerHTML  += "<h2 class='error'>Knowledge Graph missing in response; cannot process results.</h2>";
	    document.getElementById("summary_container").innerHTML += "<h2 class='error'>Knowledge Graph missing in response; cannot process results</h2>";
	}
	else {
	    var rtext = respObj.message.results.length == 1 ? " result" : " results";
	    var h2 = document.createElement("h2");
	    h2.appendChild(document.createTextNode(respObj.message.results.length + rtext));
	    document.getElementById("result_container").appendChild(h2);

	    document.getElementById("menunumresults").innerHTML = respObj.message.results.length;
            document.getElementById("menunumresults").classList.add("numnew");
	    document.getElementById("menunumresults").classList.remove("numold");

	    process_graph(respObj.message["knowledge_graph"],0,respObj["schema_version"]);
	    var respreas = 'n/a';
	    if (respObj.reasoner_id)
		respreas = respObj.reasoner_id;
	    process_results(respObj.message["results"],respObj.message["knowledge_graph"], respreas);

	    if (document.getElementById("numresults_"+respObj.araxui_response)) {
		document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';
		var nr = document.createElement("span");
		if (respObj.validation_result && respObj.validation_result.status == "FAIL")
		    nr.className = 'explevel p1';
		else if (respObj.message.results.length > 0)
		    nr.className = 'explevel p9';
		else
		    nr.className = 'explevel p5';
		nr.innerHTML = '&nbsp;'+respObj.message.results.length+'&nbsp;';
		document.getElementById("numresults_"+respObj.araxui_response).appendChild(nr);
	    }
	}
    }
    else {
        document.getElementById("result_container").innerHTML  += "<h2>No results...</h2>";
        document.getElementById("summary_container").innerHTML += "<h2>No results...</h2>";
	document.getElementById("provenance_container").innerHTML += "<h2>No results...</h2>";
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


    if (respObj.validation_result && respObj.validation_result.provenance_summary) {
	var div = document.createElement("div");
	div.className = 'statushead';
	div.appendChild(document.createTextNode("Provenance Summary"));
	document.getElementById("provenance_container").appendChild(div);

	div = document.createElement("div");
	div.className = 'status';
	div.id = 'provenancediv';
	div.appendChild(document.createElement("br"));

        var table = document.createElement("table");
	table.className = 'sumtab';
        var tr = document.createElement("tr");
        var td = document.createElement("th");
	td.colSpan = "2";
	td.appendChild(document.createTextNode("Provenance Counts"));
	tr.appendChild(td);
        td = document.createElement("th");
	td.appendChild(document.createTextNode("[ "+respObj.validation_result.provenance_summary["n_sources"]+" sources ]"));
	tr.appendChild(td);
	td = document.createElement("th");
	td.colSpan = "2";
	tr.appendChild(td);
	table.appendChild(tr);
	var previous0 = 'RandomTextToPurposelyTriggerThickTopBorderForFirstRowAndRepeatedDisplayOfPredicate';
	var previous1 = 'RandomTextToOmitRepatedDisplayOfPredicateProviderType';
	for (var prov in respObj.validation_result.provenance_summary.provenance_counts) {
	    var changed0 = false;
	    var changed1 = false;
	    if (previous0 != respObj.validation_result.provenance_summary.provenance_counts[prov][0]) {
		changed0 = true;
		changed1 = true;
	    }
	    else if (previous1 != respObj.validation_result.provenance_summary.provenance_counts[prov][1])
		changed1 = true;

	    previous0 = respObj.validation_result.provenance_summary.provenance_counts[prov][0];
            previous1 = respObj.validation_result.provenance_summary.provenance_counts[prov][1];

	    if (!changed0)
		respObj.validation_result.provenance_summary.provenance_counts[prov][0] = '';
	    if (!changed1)
		respObj.validation_result.provenance_summary.provenance_counts[prov][1] = '';

	    tr = document.createElement("tr");
            tr.className = 'hoverable';
	    for (var pc of respObj.validation_result.provenance_summary.provenance_counts[prov]) {
		td = document.createElement("td");
		if (changed0)
		    td.style.borderTop = "2px solid #444";
		td.appendChild(document.createTextNode(pc));
		tr.appendChild(td);
	    }
	    td.style.textAlign = "right";  // last td is always[?] the count number

	    // fancy bar bar
	    td = document.createElement("td");
            if (changed0)
		td.style.borderTop = "2px solid #444";
	    var span = document.createElement("span");
	    span.className = "bar";
	    var barw = 0.5*Number(respObj.validation_result.provenance_summary.provenance_counts[prov][3]);
	    if (barw > 500) {
		barw = 501;
		span.style.background = "#3d6d98";
	    }
	    if (respObj.validation_result.provenance_summary.provenance_counts[prov][2] == 'no provenance')
		span.style.background = "#b00";
	    span.style.width = barw + "px";
	    span.style.height = "8px";
	    td.appendChild(span);
            tr.appendChild(td);

	    table.appendChild(tr);
	}

	// use same table so it is all nicely aligned
        tr = document.createElement("tr");
	td = document.createElement("td");
	td.colSpan = "5";
	td.style.background = '#fff';
	td.style.border = '0';
	td.appendChild(document.createElement("br"));
	td.appendChild(document.createElement("br"));
        tr.appendChild(td);
	table.appendChild(tr);

	tr = document.createElement("tr");
	td = document.createElement("th");
	td.colSpan = "2";
	td.style.background = '#fff';
	td.appendChild(document.createTextNode("Predicate Counts"));
	tr.appendChild(td);
        td = document.createElement("th");
	td.style.background = '#fff';
	td.colSpan = "3";
	tr.appendChild(td);
	table.appendChild(tr);
        for (var pred in respObj.validation_result.provenance_summary.predicate_counts) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.colSpan = "3";
	    td.appendChild(document.createTextNode(pred));
	    tr.appendChild(td);
	    td = document.createElement("td");
	    td.style.textAlign = "right";
	    td.appendChild(document.createTextNode(respObj.validation_result.provenance_summary.predicate_counts[pred]));
	    tr.appendChild(td);
            // fancy bar bar
	    td = document.createElement("td");
	    var span = document.createElement("span");
	    span.className = "bar";
	    var barw = 0.5*Number(respObj.validation_result.provenance_summary.predicate_counts[pred]);
	    if (barw > 500) {
		barw = 501;
		span.style.background = "#3d6d98";
	    }
	    span.style.width = barw + "px";
	    span.style.height = "8px";
	    td.appendChild(span);
	    tr.appendChild(td);

	    table.appendChild(tr);
	}
	div.appendChild(table);
	div.appendChild(document.createElement("br"));

	document.getElementById("provenance_container").appendChild(div);
    }
    else
	document.getElementById("provenance_container").innerHTML += "<h2>Provenance information not available for this response</h2>";


    add_cyto(0);
    add_cyto(99999);
    statusdiv.appendChild(document.createTextNode("done."));
    statusdiv.appendChild(document.createElement("br"));
    var nr = document.createElement("span");
    nr.className = 'essence';
    nr.appendChild(document.createTextNode("Click on Results, Summary, Provenance, or Knowledge Graph links on the left to explore results."));
    statusdiv.appendChild(nr);
    statusdiv.appendChild(document.createElement("br"));
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
	    if (rowdata[i] == 'essence' || rowdata[i] == "'guessence'") {
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


function process_graph(gne,gid,trapi) {
    cytodata[gid] = [];
    for (var id in gne.nodes) {
	var gnode = gne.nodes[id];

	gnode.parentdivnum = gid;   // helps link node to div when displaying node info on click
	gnode.trapiversion = trapi; // support multiple versions...?

        if (!gnode.fulltextname) {
	    if (gnode.name)
		gnode.fulltextname = gnode.name;
	    else
		gnode.fulltextname = id;
	}

	//if (!gnode.id)
	//gnode.id = id;

        if (gnode.ids) {
	    gnode.id = gnode.ids[0];
	    if (gnode.ids.length > 1)
		gnode.id += " (+"+(gnode.ids.length-1)+")";

	    if (gnode.name)
		gnode.name += " ("+gnode.id+")";
	    else
		gnode.name = gnode.id;
	}

        gnode.id = id;

	if (!gnode.name) {
	    if (gnode.categories && gnode.categories[0])
		gnode.name = gnode.categories[0] + "s?";
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
        gedge.trapiversion = trapi;
        gedge.source = gedge.subject;
        gedge.target = gedge.object;
	if (gedge.predicates)
	    gedge.type = gedge.predicates[0];

        var tmpdata = { "data" : gedge };
        cytodata[gid].push(tmpdata);
    }


    if (gid == 99999) {
	for (var id in gne.nodes) {
	    var gnode = gne.nodes[id];
	    qgids.push(id);

	    var tmpdata = { "ids"        : gnode.ids ? gnode.ids : [],
			    "is_set"     : gnode.is_set,
			    "_names"     : gnode.ids ? gnode.ids.slice() : [], // make a copy!
			    "_desc"      : gnode.description,
			    "categories" : gnode.categories ? gnode.categories : [],
			    "constraints": gnode.constraints ? gnode.constraints : []
			  };

	    input_qg.nodes[id] = tmpdata;
	}

	for (var id in gne.edges) {
            var gedge = gne.edges[id];
	    qgids.push(id);

	    var tmpdata = { "subject"    : gedge.subject,
			    "object"     : gedge.object,
			    "predicates" : gedge.predicates ? gedge.predicates : [],
			    "constraints": gedge.constraints ? gedge.constraints : []
			  };
	    input_qg.edges[id] = tmpdata;
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

function process_results(reslist,kg,mainreasoner) {
    // do this only once
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
    var results_fragment = document.createDocumentFragment();

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

	var cnf = 'n/a';
	if (Number(result.score))
	    cnf = Number(result.score).toFixed(3);
	else if (Number(result.confidence))
	    cnf = Number(result.confidence).toFixed(3);
	var pcl = (cnf>=0.9) ? "p9" : (cnf>=0.7) ? "p7" : (cnf>=0.5) ? "p5" : (cnf>=0.3) ? "p3" : (cnf>0.0) ? "p1" : "p0";

        if (result.row_data)
            add_to_summary(result.row_data, num);
	else
            add_to_summary([cnf,ess], num);

	var rsrc = mainreasoner;
	if (result.reasoner_id)
	    rsrc = result.reasoner_id;
	var rscl =
	    (rsrc=="ARAX")     ? "srtx" :
	    (rsrc=="BTE")      ? "sbte" :
	    (rsrc=="Cam")      ? "scam" :
	    (rsrc=="COHD")     ? "scod" :
	    (rsrc=="Indigo")   ? "sind" :
	    (rsrc=="Robokop")  ? "srob" :
	    (rsrc=="Aragorn")  ? "sara" :
	    (rsrc=="MolePro")  ? "smol" :
	    (rsrc=="Genetics") ? "sgen" :
	    (rsrc=="Unsecret") ? "suns" :
	    (rsrc=="ImProving")? "simp" :
	    "p0";

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
	results_fragment.appendChild(div);

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
	results_fragment.appendChild(div);


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
		if (kmne.predicate)
		    kmne.type = kmne.predicate;
		//console.log("=================== kmne:"+kmne.id);
		var tmpdata = { "data" : kmne };
		cytodata[num].push(tmpdata);
	    }
	}

    }

    document.getElementById("result_container").appendChild(results_fragment);
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
		'font-size' : '12',
		'line-color': function(ele) { return mapEdgeColor(ele); } ,
		'line-style': function(ele) { return mapEdgeLineStyle(ele); } ,
		'width': function(ele) { if (ele.data().weight) { return ele.data().weight; } return 2; },
		'target-arrow-color': function(ele) { return mapEdgeColor(ele); } ,
		'target-arrow-shape': 'triangle',
		'opacity': 0.8,
		'content': function(ele) { if ((ele.data().parentdivnum > 0) && ele.data().type) { return ele.data().type; } return '';}
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
	    UIstate.shakeit = true;
	    qg_node(this.data('id'));
	});

	cyobj[i].on('tap','edge', function() {
	    UIstate.shakeit = true;
	    qg_edge(this.data('id'));
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

	if (this.data('trapiversion').startsWith("1.0"))
	    show_attributes_1point0(div, this.data('attributes'));
	else
	    show_attributes_1point1(div, this.data('attributes'));

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
		link.target = "_blank";
		link.appendChild(document.createTextNode(this.data(field)));
		div.appendChild(link);
	    }
	    else {
		div.appendChild(document.createTextNode(this.data(field)));
	    }
	    div.appendChild(document.createElement("br"));
	}

        if (this.data('trapiversion').startsWith("1.0"))
	    show_attributes_1point0(div, this.data('attributes'));
	else
	    show_attributes_1point1(div, this.data('attributes'));

	sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
    });
    cytodata[i] = null;
}


function show_attributes_1point1(html_div, atts) {
    if (atts == null)  { return; }

    // always display iri first
    var iri = atts.filter(a => a.attribute_type_id == "biolink:IriType");

    var attshtml = "<table>";
    for (var att of iri.concat(atts.filter(a => a.attribute_type_id != "biolink:IriType"))) {
	var snippet = "<tr><td colspan='2'><hr></td></tr>";
	var value = '';

	for (var nom in att) {
	    if (nom == "value") {
		value = att[nom];
		continue;
	    }
	    else if (att[nom] != null) {
		snippet += "<tr><td><b>" + nom + "</b>: </td><td>";

		if (att[nom].toString().startsWith("http")) {
		    snippet += "<a href='" + att[nom] + "'";
		    snippet += " target='_blank'>" + att[nom] + "</a>";
		}
		else
		    snippet += att[nom];

		snippet += "</td></tr>";
	    }
	}
	snippet += "<tr><td><b>value</b>: </td><td>";
	if (value) {
            var fixit = true;
	    if (Array.isArray(att.value))
		for (var val of att.value) {
		    snippet += "<br>";
		    if (val == null) {
			snippet += "--NULL--";
		    }
		    else if (typeof val === 'object') {
			snippet += "<pre>"+JSON.stringify(val,null,2)+"</pre>";
			fixit = false;
		    }
		    else if (val.toString().startsWith("PMID:")) {
			snippet += "<a href='https://www.ncbi.nlm.nih.gov/pubmed/" + val.split(":")[1] + "'";
			snippet += " title='View in PubMed' target='_blank'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("DOI:")) {
			snippet += "<a href='https://doi.org/" + val.split(":")[1] + "'";
			snippet += " title='View in doi.org' target='_blank'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("http")) {
			snippet += "<a href='" + val + "'";
			snippet += " target='_blank'>" + val + "</a>";
		    }
		    else {
			snippet += val;
		    }
		}
	    else if (typeof att.value === 'object') {
		snippet += "<pre>"+JSON.stringify(att.value,null,2)+"</pre>";
		fixit = false;
	    }
            else if (attributes_to_truncate.includes(att.original_attribute_name)) {
		snippet += Number(att.value).toPrecision(3);
		fixit = false;
	    }
	    else if (value.toString().startsWith("http")) {
		snippet += "<a href='" + value + "'";
		snippet += " target='_blank'>" + value + "</a>";
	    }
	    else
		snippet += att.value;

            if (fixit) {
		snippet = snippet.toString().replace(/-!-/g,'<br>-!-');
		snippet = snippet.toString().replace(/---/g,'<br>---');
		snippet = snippet.toString().replace( /;;/g,'<br>;;');
	    }
	}
	else {
            snippet += "<i>-- no value! --</i>";
	}
	snippet += "</td></tr>";

        attshtml += snippet;
    }
    html_div.innerHTML+= attshtml;
}

function show_attributes_1point0(html_div, atts) {
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
	    snippet += "<a target='_blank' href='" + att.url + "'>";


	if (att.value != null) {
	    var fixit = true;
            // truncate floats
	    if (attributes_to_truncate.includes(att.name)) {
		snippet += Number(att.value).toPrecision(3);
		fixit = false;
	    }
            else if (Array.isArray(att.value))
		for (var val of att.value) {
                    snippet += "<br>&nbsp;&nbsp;&nbsp;";
		    if (val == null) {
			snippet += "--NULL--";
		    }
		    else if (val.toString().startsWith("PMID:")) {
			snippet += "<a href='https://www.ncbi.nlm.nih.gov/pubmed/" + val.split(":")[1] + "'";
			snippet += " title='View in PubMed' target='_blank'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("DOI:")) {
			snippet += "<a href='https://doi.org/" + val.split(":")[1] + "'";
			snippet += " title='View in doi.org' target='_blank'>" + val + "</a>";
		    }
		    else if (val.toString().startsWith("http")) {
                        snippet += "<a href='" + val + "'";
                        snippet += " target='_blank'>" + val + "</a>";
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
    var ntype = ele.data().categories ? ele.data().categories[0] ? ele.data().categories[0] : "NA" : "NA";
    if (ntype.endsWith("microRNA"))           { return "hexagon";} //??
    if (ntype.endsWith("Metabolite"))         { return "heptagon";}
    if (ntype.endsWith("Protein"))            { return "octagon";}
    if (ntype.endsWith("Pathway"))            { return "vee";}
    if (ntype.endsWith("Disease"))            { return "triangle";}
    if (ntype.endsWith("MolecularFunction"))  { return "rectangle";} //??
    if (ntype.endsWith("CellularComponent"))  { return "ellipse";}
    if (ntype.endsWith("BiologicalProcess"))  { return "tag";}
    if (ntype.endsWith("ChemicalEntity"))  { return "diamond";}
    if (ntype.endsWith("AnatomicalEntity"))   { return "rhomboid";}
    if (ntype.endsWith("PhenotypicFeature"))  { return "star";}
    return "rectangle";
}

function mapNodeColor(ele) {
    var ntype = ele.data().categories ? ele.data().categories[0] ? ele.data().categories[0] : "NA" : "NA";
    if (ntype.endsWith("microRNA"))           { return "orange";} //??
    if (ntype.endsWith("Metabolite"))         { return "aqua";}
    if (ntype.endsWith("Protein"))            { return "black";}
    if (ntype.endsWith("Pathway"))            { return "gray";}
    if (ntype.endsWith("Disease"))            { return "red";}
    if (ntype.endsWith("MolecularFunction"))  { return "blue";} //??
    if (ntype.endsWith("CellularComponent"))  { return "purple";}
    if (ntype.endsWith("BiologicalProcess"))  { return "green";}
    if (ntype.endsWith("ChemicalEntity"))  { return "yellowgreen";}
    if (ntype.endsWith("AnatomicalEntity"))   { return "violet";}
    if (ntype.endsWith("PhenotypicFeature"))  { return "indigo";}
    return "#04c";
}

function mapEdgeLineStyle(ele) {
    if (ele.data().attributes)
	for (var att of ele.data().attributes)
	    if (att["attribute_type_id"] == "biolink:computed_value")
		return 'dashed';
    return 'solid';
}

function mapEdgeColor(ele) {
    var etype = ele.data().predicate ? ele.data().predicate : ele.data().predicates ? ele.data().predicates[0] : "NA";
    if (etype == "biolink:contraindicated_for")       { return "red";}
    if (etype == "biolink:indicated_for")             { return "green";}
    if (etype == "biolink:physically_interacts_with") { return "green";}
    return "#aaf";
}


// build-a-qGraph
function qg_new(msg,nodes) {
    if (cyobj[99999]) { cyobj[99999].elements().remove(); }
    else add_cyto(99999);
    input_qg = { "edges": {}, "nodes": {} };
    qgids = [];
    UIstate.editedgeid = null;
    UIstate.editnodeid = null;

    if (msg)
	document.getElementById("statusdiv").innerHTML = "<p>A new Query Graph has been created.</p>";
    else
	document.getElementById("showQGjson").checked = false;

    if (nodes) {
	qg_node('new',false);
	qg_node('new',false);
	qg_edge('new');
    }
}

function qg_node(id,render) {
    var daname = 'NamedThing';

    if (id == 'new') {
	id = get_qg_id('n');
	var newqnode = {};
	newqnode.ids = [];
	newqnode.categories = [];
	newqnode.constraints = [];
	newqnode.is_set = false;
	newqnode._names = [];

	input_qg.nodes[id] = newqnode;

	cyobj[99999].add( {
	    "data" : { "id"   : id,
		       "name" : daname,
		       "type" : '',
		       "set"  : newqnode.is_set,
		       "parentdivnum" : 99999 },
	} );
	if (render) {
	    cyobj[99999].reset();
	    cylayout(99999,"breadthfirst");
	}
	cyobj[99999].getElementById(id).select();
	UIstate.shakeit = true;
    }
    else {  // need to update name?
	if (input_qg.nodes[id]['_names'].length > 0) {
	    daname = input_qg.nodes[id]['_names'][0];
	    if (input_qg.nodes[id]['_names'].length == 2)
		daname = "[ "+daname+", "+input_qg.nodes[id]['_names'][1]+" ]";
	    else if (input_qg.nodes[id]['_names'].length > 2)
		daname = "[ "+daname+" +"+(input_qg.nodes[id]['_names'].length - 1)+" ]";
	}
        else if (input_qg.nodes[id]['categories'].length > 0) {
	    daname = input_qg.nodes[id]['categories'][0];

	    if (input_qg.nodes[id]['categories'].length == 2)
		daname = "[ "+daname+", "+input_qg.nodes[id]['categories'][1]+" ]";
	    else if (input_qg.nodes[id]['categories'].length > 2)
		daname = "[ "+daname+" +"+(input_qg.nodes[id]['categories'].length - 1)+" ]";
	}

	if (daname != cyobj[99999].getElementById(id).data('name'))
	    cyobj[99999].getElementById(id).data('name',daname);

    }

    display_qg_popup('node','show');

    document.getElementById('nodeeditor_id').innerHTML = id;
    document.getElementById('nodeeditor_name').innerHTML = daname;

    var htmlnode = document.getElementById('nodeeditor_ids');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].ids) {
	var theids = input_qg.nodes[id].ids.slice();  // creates a copy (instead of a reference)
	for (curie of theids.sort()) {
	    htmlnode.appendChild(document.createTextNode(curie));

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_curie_from_qnode("'+curie+'");';
	    link.title = "remove "+curie+" from Qnode ids list";
	    link.appendChild(document.createTextNode(" [ remove ] "));
	    htmlnode.appendChild(link);

	    htmlnode.appendChild(document.createElement("br"));
	}
    }
    else
	input_qg.nodes[id].ids = [];

    htmlnode = document.getElementById('nodeeditor_cat');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].categories) {
	for (category of input_qg.nodes[id].categories.sort()) {
	    htmlnode.appendChild(document.createTextNode(category));

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_category_from_qnode("'+category+'");';
	    link.title = "remove "+category+" from Qnode categories list";
	    link.appendChild(document.createTextNode(" [ remove ] "));
	    htmlnode.appendChild(link);

	    htmlnode.appendChild(document.createElement("br"));
	}
    }
    else
	input_qg.nodes[id].categories = [];

    htmlnode = document.getElementById('nodeeditor_cons');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].constraints) {
	var cindex = 0;
	for (constraint of input_qg.nodes[id].constraints) {
	    htmlnode.appendChild(document.createTextNode(constraint.name+" "));
	    if (constraint.not)
		htmlnode.appendChild(document.createTextNode("NOT "));
	    htmlnode.appendChild(document.createTextNode(constraint.operator + " " +constraint.value));
	    if (constraint.unit_name)
		htmlnode.appendChild(document.createTextNode(" ("+constraint.unit_name+")"));

            var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_constraint_from_qnode('+cindex+');';
	    link.title = "remove "+constraint.id+" from Qnode constraints list";
	    link.appendChild(document.createTextNode(" [ remove ] "));
	    htmlnode.appendChild(link);

	    htmlnode.appendChild(document.createElement("br"));
	    cindex++;
	}
    }

    document.getElementById('nodeeditor_set').checked = input_qg.nodes[id].is_set;
    UIstate.editnodeid = id;

    qg_update_qnode_list();
    qg_display_edge_predicates(false);

    if (document.getElementById("showQGjson").checked) {
	document.getElementById("statusdiv").innerHTML = "<pre>"+JSON.stringify(input_qg,null,2)+ "</pre>";
	sesame('openmax',statusdiv);
    }
}

function qg_remove_qnode() {
    var id = UIstate.editnodeid;
    if (!id) return;

    cyobj[99999].remove("#"+id);
    delete input_qg.nodes[id];

    var idx = qgids.indexOf(id);
    if (idx > -1)
	qgids.splice(idx, 1);

    var delstat = "<p>Deleted node <i>"+id+"</i>";

    for (eid in input_qg.edges) {
	var killit = false
	if (input_qg.edges[eid].subject == id)
	    killit = true;
	else if (input_qg.edges[eid].object == id)
	    killit = true;

	if (killit) {
	    delete input_qg.edges[eid];
	    delstat += ", and edge <i>"+eid+"</i>";
	    var idx = qgids.indexOf(eid);
	    if (idx > -1)
		qgids.splice(idx, 1);
	    if (UIstate.editedgeid == eid) {
		display_qg_popup('edge','hide');
		UIstate.editedgeid = null;
	    }
	}
    }
    delstat += "</p>";

    qg_update_qnode_list();
    qg_display_edge_predicates(false);

    document.getElementById("statusdiv").innerHTML = delstat;
    display_qg_popup('node','hide');
    UIstate.editnodeid = null;
}

function qg_enter_curie(ele) {
    if (event.key === 'Enter')
	qg_add_curie_to_qnode();
}

async function qg_add_curie_to_qnode() {
    var id = UIstate.editnodeid;
    if (!id) return;

    var thing = document.getElementById("newquerynode").value.trim();
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

	if (!input_qg.nodes[id]['ids'].includes(bestthing.curie)) {
	    input_qg.nodes[id]['ids'].push(bestthing.curie);
	    input_qg.nodes[id]['_names'].push(bestthing.name);
	}

	//cyobj[99999].getElementById(id).data('name', bestthing.name);

	qg_add_category_to_qnode(bestthing.type);

	document.getElementById("devdiv").innerHTML +=  "-- found a curie = " + bestthing.curie + "<br>";

	cyobj[99999].reset();
	cylayout(99999,"breadthfirst");
    }
    else {
        document.getElementById("statusdiv").innerHTML = "<p><span class='error'>" + thing + "</span> is not in our knowledge graph.</p>";
	sesame('openmax',statusdiv);
    }

}

function qg_remove_curie_from_qnode(cur) {
    var id = UIstate.editnodeid;
    if (!id) return;

    var idx = input_qg.nodes[id]['ids'].indexOf(cur);
    if (idx > -1) {
	input_qg.nodes[id]['ids'].splice(idx, 1);
	input_qg.nodes[id]['_names'].splice(idx, 1);
    }

    qg_node(id);
}

function qg_add_category_to_qnode(cat) {
    var id = UIstate.editnodeid;
    if (!id) return;

    document.getElementById("allnodetypes").value = '';
    document.getElementById("allnodetypes").blur();

    if (!input_qg.nodes[id]['categories'].includes(cat))
	input_qg.nodes[id]['categories'].push(cat);

    qg_node(id);
}

function qg_remove_category_from_qnode(cat) {
    var id = UIstate.editnodeid;
    if (!id) return;

    var idx = input_qg.nodes[id]['categories'].indexOf(cat);
    if (idx > -1)
	input_qg.nodes[id]['categories'].splice(idx, 1);

    qg_node(id);
}

function qg_add_constraint_to_qgitem(what) {
    var id = null;
    if (what == 'qedge')
	id = UIstate.editedgeid;
    else if (what == 'qnode')
	id = UIstate.editnodeid;
    if (!id) return;

    var constraint = {};

    var val = document.getElementById(what+"constraintIDbox").value.trim();
    if (!val) return;
    constraint.id = val;

    val = document.getElementById(what+"constraintNAMEbox").value.trim();
    if (!val) return;
    constraint.name = val;

    val = document.getElementById(what+"constraintVALUEbox").value.trim();
    if (!val) return;
    constraint.value = val;

    constraint.not = document.getElementById(what+"constraintNOT").checked;
    constraint.operator = document.getElementById(what+"constraintOPERATOR").value;
    constraint.unit_id = document.getElementById(what+"constraintUNITIDbox").value.trim();
    constraint.unit_name = document.getElementById(what+"constraintUNITNAMEbox").value.trim();

    document.getElementById(what+"constraintIDbox").value = '';
    document.getElementById(what+"constraintNAMEbox").value = '';
    document.getElementById(what+"constraintVALUEbox").value = '';
    document.getElementById(what+"constraintUNITIDbox").value = '';
    document.getElementById(what+"constraintUNITNAMEbox").value = '';
    document.getElementById(what+"constraintNOT").checked = false;
    document.getElementById(what+"constraintOPERATOR").value = '==';

    if (what == 'qedge') {
	input_qg.edges[id]['constraints'].push(constraint);
	qg_edge(id);
    }
    else {
	input_qg.nodes[id]['constraints'].push(constraint);
	qg_node(id);
    }
}

function qg_remove_constraint_from_qnode(idx) {
    var id = UIstate.editnodeid;
    if (!id) return;

    if (idx > -1)
	input_qg.nodes[id]['constraints'].splice(idx, 1);

    qg_node(id);
}
function qg_remove_constraint_from_qedge(idx) {
    var id = UIstate.editedgeid;
    if (!id) return;

    if (idx > -1)
	input_qg.edges[id]['constraints'].splice(idx, 1);

    qg_edge(id);
}

function qg_setset_for_qnode() {
    var id = UIstate.editnodeid;
    if (!id) return;

    input_qg.nodes[id].is_set = document.getElementById('nodeeditor_set').checked;
    qg_node(id);

    cyobj[99999].getElementById(id).data('set', input_qg.nodes[id].is_set);
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");
}

function qg_edge(id) {
    if (id == 'new') {
	var nodes = Object.keys(input_qg.nodes);
	if (nodes.length < 2) { // just add them...
	    qg_node('new',false);
	    if (nodes.length < 1)
		qg_node('new',false);

	    nodes = Object.keys(input_qg.nodes);
	}

	id = get_qg_id('e');
	var newqedge = {};
	newqedge.predicates = [];
	newqedge.constraints = [];
	// join last two nodes if not specified otherwise [ToDo: specify]
	newqedge.subject = nodes[nodes.length - 2];
	newqedge.object = nodes[nodes.length - 1];

	input_qg.edges[id] = newqedge;

	cyobj[99999].add( {
	    "data" : { "id"     : id,
		       "source" : newqedge.subject,
		       "target" : newqedge.object,
		       "npreds" : 0,
		       "parentdivnum" : 99999 },
	} );
	cyobj[99999].reset();
	cylayout(99999,"breadthfirst");
	cyobj[99999].getElementById(id).select();
	UIstate.shakeit = true;
    }
    else {  // need to update label?
	if (input_qg.edges[id]['predicates'] && input_qg.edges[id]['predicates'].length > 0) {
	    dalabel = input_qg.edges[id]['predicates'][0];
            if (input_qg.edges[id]['predicates'].length > 1)
                dalabel = "[ "+dalabel+" +"+(input_qg.edges[id]['predicates'].length - 1)+" ]";
	}
	else
	    dalabel = ' n/a ';

        if (dalabel != cyobj[99999].getElementById(id).data('type'))
	    cyobj[99999].getElementById(id).data('type',dalabel);
    }

    display_qg_popup('edge','show');

    document.getElementById('edgeeditor_id').innerHTML = id;

    UIstate.editedgeid = id;
    qg_update_qnode_list();
    qg_display_edge_predicates(false);

    var htmlnode = document.getElementById('edgeeditor_pred');
    htmlnode.innerHTML = '';
    if (input_qg.edges[id].predicates) {
	for (predicate of input_qg.edges[id].predicates.sort()) {
	    htmlnode.appendChild(document.createTextNode(predicate));

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_predicate_from_qedge("'+predicate+'");';
	    link.title = "remove "+predicate+" from Qedge predicate list";
	    link.appendChild(document.createTextNode(" [ remove ] "));
	    htmlnode.appendChild(link);

	    htmlnode.appendChild(document.createElement("br"));
	}
    }
    else
	input_qg.edges[id].predicates = [];

    htmlnode = document.getElementById('edgeeditor_cons');
    htmlnode.innerHTML = '';
    if (input_qg.edges[id].constraints) {
	var cindex = 0;
	for (constraint of input_qg.edges[id].constraints) {
	    htmlnode.appendChild(document.createTextNode(constraint.name+" "));
	    if (constraint.not)
		htmlnode.appendChild(document.createTextNode("NOT "));
	    htmlnode.appendChild(document.createTextNode(constraint.operator + " " +constraint.value));
	    if (constraint.unit_name)
		htmlnode.appendChild(document.createTextNode(" ("+constraint.unit_name+")"));

            var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_constraint_from_qedge('+cindex+');';
	    link.title = "remove "+constraint.id+" from Qedge constraints list";
	    link.appendChild(document.createTextNode(" [ remove ] "));
	    htmlnode.appendChild(link);

	    htmlnode.appendChild(document.createElement("br"));
	    cindex++;
	}
    }

    if (document.getElementById("showQGjson").checked) {
	document.getElementById("statusdiv").innerHTML = "<pre>"+JSON.stringify(input_qg,null,2)+ "</pre>";
	sesame('openmax',statusdiv);
    }
}

function qg_update_qnode_list() {
    document.getElementById('edgeeditor_subj').innerHTML = '';
    document.getElementById('edgeeditor_obj').innerHTML = '';
    for (node of Object.keys(input_qg.nodes).sort()) {
	var opt = document.createElement('option');
	opt.value = node;
	opt.innerHTML = node+":"+cyobj[99999].getElementById(node).data('name');
	document.getElementById('edgeeditor_subj').appendChild(opt);
	document.getElementById('edgeeditor_obj').appendChild(opt.cloneNode(true));
    }

    var id = UIstate.editedgeid;
    if (!id) return;

    document.getElementById('edgeeditor_subj').value = input_qg.edges[id]['subject'];
    document.getElementById('edgeeditor_obj').value = input_qg.edges[id]['object'];
}

function qg_remove_qedge() {
    var id = UIstate.editedgeid;
    if (!id) return;

    cyobj[99999].remove("#"+id);
    delete input_qg.edges[id];

    var idx = qgids.indexOf(id);
    if (idx > -1)
	qgids.splice(idx, 1);

    document.getElementById("statusdiv").innerHTML = "<p>Deleted edge <i>"+id+"</i>";

    display_qg_popup('edge','hide');
    UIstate.editedgeid = null;
}

function qg_enter_predicate(ele) {
    if (event.key === 'Enter')
	qg_add_predicate_to_qedge(ele.value);
}

function qg_add_predicate_to_qedge(pred) {
    var id = UIstate.editedgeid;
    if (!id) return;

    document.getElementById("qedgepredicatelist").value = '';
    document.getElementById("qedgepredicatelist").blur();
    document.getElementById("qedgepredicatebox").value = '';
    document.getElementById("qedgepredicatebox").blur();

    if (!input_qg.edges[id]['predicates'].includes(pred))
	input_qg.edges[id]['predicates'].push(pred);

    qg_edge(id);
}

function qg_remove_predicate_from_qedge(pred) {
    var id = UIstate.editedgeid;
    if (!id) return;

    var idx = input_qg.edges[id]['predicates'].indexOf(pred);
    if (idx > -1)
	input_qg.edges[id]['predicates'].splice(idx, 1);

    qg_edge(id);
}

function qg_update_qedge() {
    var id = UIstate.editedgeid;
    if (!id) return;

    input_qg.edges[id]['subject'] = document.getElementById('edgeeditor_subj').value;
    input_qg.edges[id]['object'] = document.getElementById('edgeeditor_obj').value;
    qg_edge(id);

    cyobj[99999].getElementById(id).move({
	'source' : input_qg.edges[id].subject,
	'target' : input_qg.edges[id].object
    });
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");
}

function qg_edit(msg) {
    cytodata[99999] = [];
    if (cyobj[99999]) {cyobj[99999].elements().remove();}
    else add_cyto(99999);
    UIstate.editedgeid = null;
    UIstate.editnodeid = null;

    for (var gid in input_qg.nodes) {
	var gnode = input_qg.nodes[gid];

        cyobj[99999].add( {
	    "data" : {
		"id"   : gid,
		"name" : 'NamedThing', // placeholder
		"type" : gnode.categories ? gnode.categories[0] : null,
		"parentdivnum" : 99999 },
	} );

	qg_node(gid);
    }

    for (var eid in input_qg.edges) {
	var gedge = input_qg.edges[eid];
	cyobj[99999].add( {
	    "data" : {
		"id"     : eid,
		"source" : gedge.subject,
		"target" : gedge.object,
		"type"   : gedge.predicates ? gedge.predicates[0] : null,
		"parentdivnum" : 99999 }
	} );

	qg_edge(eid);
    }

    cylayout(99999,"breadthfirst");

    if (msg)
	document.getElementById("statusdiv").innerHTML = "<p>Copied Query Graph to visual edit window.</p>";
    else
	document.getElementById("showQGjson").checked = false;

    document.getElementById("devdiv").innerHTML +=  "Copied query_graph to edit window<br>";
}

// unused at the moment
function qg_display_items() {
    if (!document.getElementById("qg_items"))
	return;

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

    for (nid in input_qg.nodes) {
	var result = input_qg.nodes[nid];
	nitems++;

	tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.appendChild(document.createTextNode(nid));
        tr.appendChild(td);

        td = document.createElement("td");
        td.appendChild(document.createTextNode(result["_name"] == null ? "-" : result["_name"]));
        tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode(result.is_set ? "(multiple items)" : result.ids == null ? "(any node)" : result.ids[0]));
        tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode(result.is_set ? "(set of nodes)" : result.categories == null ? "(any)" : result.categories[0]));
        tr.appendChild(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_node_from_query_graph(\"'+nid+'\")';
	link.appendChild(document.createTextNode("Remove"));
	td.appendChild(link);
        tr.appendChild(td);

	table.appendChild(tr);
    }

    for (eid in input_qg.edges) {
	var result = input_qg.edges[eid];
        tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.appendChild(document.createTextNode(eid));
	tr.appendChild(td);

	td = document.createElement("td");
        td.appendChild(document.createTextNode("-"));
        tr.appendChild(td);

        td = document.createElement("td");
	td.appendChild(document.createTextNode(result.subject+"--"+result.object));
	tr.appendChild(td);

        td = document.createElement("td");
	td.appendChild(document.createTextNode(result.predicates == null ? "(any)" : result.predicates[0]));
	tr.appendChild(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_edge_from_query_graph(\"'+eid+'\")';
	link.appendChild(document.createTextNode("Remove"));
	td.appendChild(link);
	tr.appendChild(td);

        table.appendChild(tr);
    };

    document.getElementById("qg_items").innerHTML = '';
    if (nitems > 0)
	document.getElementById("qg_items").appendChild(table);

}


function qg_display_edge_predicates(all) {
    var preds_node = document.getElementById("qedgepredicatelist");
    var subj = document.getElementById('edgeeditor_subj').value;
    var obj = document.getElementById('edgeeditor_obj').value;

    if (!all) {
	if (!input_qg.nodes[subj]['categories'] ||
	    input_qg.nodes[subj]['categories'] == null ||
	    input_qg.nodes[subj]['categories'].length != 1 ||
	    !input_qg.nodes[obj]['categories'] ||
	    input_qg.nodes[obj]['categories'] == null ||
	    input_qg.nodes[obj]['categories'].length != 1)
	    all = true;
    }

    var preds = [];
    if (all)
	preds = Object.keys(all_predicates).sort();
    else if (input_qg.nodes[obj]['categories'][0] in predicates[input_qg.nodes[subj]['categories'][0]])
	preds = predicates[input_qg.nodes[subj]['categories'][0]][input_qg.nodes[obj]['categories'][0]].sort();

    preds_node.innerHTML = '';
    var opt = document.createElement('option');
    opt.value = '';

    if (preds.length < 1) {
	opt.innerHTML = "-- No Predicates found --";
	preds_node.appendChild(opt);
    }
    else {
	opt.innerHTML = "Add Predicate to Edge&nbsp;("+preds.length+")&nbsp;&nbsp;&nbsp;&#8675;";
	preds_node.appendChild(opt);

	for (const p of preds) {
	    opt = document.createElement('option');
	    opt.value = p;
	    opt.innerHTML = p;
	    preds_node.appendChild(opt);
	}
    }
}

// unused at the moment
function add_nodeclass_to_query_graph(nodetype) {
    document.getElementById("allnodetypes").value = '';
    document.getElementById("allnodetypes").blur();

    if (nodetype.startsWith("LIST_"))
	add_nodelist_to_query_graph(nodetype);
    else
	add_nodetype_to_query_graph(nodetype);

}
// unused at the moment
function add_nodetype_to_query_graph(nodetype) {
    document.getElementById("statusdiv").innerHTML = "<p>Added a node of type <i>"+nodetype+"</i></p>";
    var qgid = get_qg_id('n');

    cyobj[99999].add( {
        "data" : { "id"   : qgid,
		   "name" : nodetype+"s",
		   "type" : nodetype,
		   "parentdivnum" : 99999 },
//        "position" : {x:100*qgid, y:50}
    } );
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");

    var tmpdata = {};
    tmpdata["is_set"] = false;
    tmpdata["_name"]  = null;
    tmpdata["_desc"]  = "Generic " + nodetype;
    if (nodetype != 'NONSPECIFIC')
	tmpdata["categories"] = [nodetype];

    input_qg.nodes[qgid] = tmpdata;
}
// unused at the moment
function add_nodelist_to_query_graph(nodetype) {
    var list = nodetype.split("LIST_")[1];

    document.getElementById("statusdiv").innerHTML = "<p>Added a set of nodes from list <i>"+list+"</i></p>";
    var qgid = get_qg_id('n');

    cyobj[99999].add( {
        "data" : { "id"   : qgid,
		   "name" : nodetype,
		   "type" : "set",
		   "parentdivnum" : 99999 }
    } );
    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");

    var tmpdata = {};
    tmpdata["ids"]    = get_list_as_curie_array(list);
    tmpdata["is_set"] = true;
    tmpdata["_name"]  = nodetype;
    tmpdata["_desc"]  = "Set of nodes from list " + list;

    input_qg.nodes[qgid] = tmpdata;
}


function qg_clean_up(xfer) {
    // clean up non-TRAPI attributes and null arrays
    for (var nid in input_qg.nodes) {
	var gnode = input_qg.nodes[nid];

	if (gnode.is_set) {
	    var list = gnode["_name"].split("LIST_")[1];
	    gnode.ids = get_list_as_curie_array(list);
	}

	for (var att of ["_names","_desc"] ) {
	    if (gnode.hasOwnProperty(att))
		delete gnode[att];
	}
	if (gnode.ids && gnode.ids[0] == null)
	    delete gnode.ids;
	if (gnode.categories && gnode.categories[0] == null)
	    delete gnode.categories;
	if (gnode.constraints && gnode.constraints[0] == null)
	    delete gnode.constraints;
    }

    for (var eid in input_qg.edges) {
	var gedge = input_qg.edges[eid];
	if (gedge.predicates && gedge.predicates[0] == null)
	    delete gedge.predicates;
	if (gedge.constraints && gedge.constraints[0] == null)
	    delete gedge.constraints;
    }

    if (xfer)
	document.getElementById("jsonText").value = JSON.stringify(input_qg,null,2);
}

function qg_select(what) {
    var id = null;

    if (what == 'node')
	id = UIstate.editnodeid;
    else if (what == 'edge')
	id = UIstate.editedgeid;

    if (id)
	cyobj[99999].getElementById(id).select();
}

function display_qg_popup(which,how) {
    var popup;
    if (which == 'edge')
	popup = document.getElementById('edgeeditor');
    else
	popup = document.getElementById('nodeeditor');

    popup.classList.remove('shake');
    if (how == 'show') {
	if (UIstate.shakeit && popup.style.visibility == 'visible')
	    var timeout = setTimeout(function() { popup.classList.add('shake'); }, 50 );
	else
	    popup.style.visibility = 'visible';
	UIstate.shakeit = false;
    }
    else if (how == 'hide')
	popup.style.visibility = 'hidden';
    else if (popup.style.visibility == 'visible')
	popup.style.visibility = 'hidden';
    else
	popup.style.visibility = 'visible';
}


function get_qg_id(prefix) {
    var new_id = 0;
    do {
	if (!qgids.includes(prefix+new_id))
	    break;
	new_id++;
    } while (new_id < 100);

    qgids.push(prefix+new_id);
    return prefix+new_id;
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


function load_meta_knowledge_graph() {
    var allnodes_node = document.getElementById("allnodetypes");
    allnodes_node.innerHTML = '';

    fetch(baseAPI + "/meta_knowledge_graph")
	.then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong with /meta_knowledge_graph');
	})
        .then(data => {
	    //add_to_dev_info("META_KNOWLEDGE_GRAPH",data);

	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.style.borderBottom = "1px solid black";
	    opt.innerHTML = "Add Category to Node&nbsp;&nbsp;&nbsp;&#8675;";
	    allnodes_node.appendChild(opt);

            for (const n in data.nodes) {
		opt = document.createElement('option');
		opt.value = n;
		opt.innerHTML = n;
		allnodes_node.appendChild(opt);
		// recreate old /predicates structure (simpler/faster lookups)
		predicates[n] = {};
		for (const o in data.nodes)
		    predicates[n][o] = [];
	    }
            for (const e of data.edges) {
		predicates[e.subject][e.object].push(e.predicate);
		all_predicates[e.predicate] = 1;
	    }
	    // clean up empty ones
            for (var s in predicates)
		for (var o in predicates[s])
		    if (predicates[s][o].length < 1)
			delete predicates[s][o];

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

	    qg_display_edge_predicates(true);
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
            listhtml += "<tr><td>"+li+".</td><td><a target='_blank' title='view this response in a new window' href='//"+ window.location.hostname + window.location.pathname;
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


function checkUIversion(compare) {
    fetch("rtx.version", {
	headers: { 'Cache-Control': 'no-cache' }
    })
        .then(response => response.text())
	.then(response => {
	    //console.log(response+"--"+UIstate["version"]);
	    if (compare && (UIstate["version"] != response))
		showVersionAlert(response);
	    else {
		UIstate["version"] = response;
		document.getElementById("uiversionstring").innerHTML = '&nbsp;&nbsp;'+response;
	    }
	})
	.catch(error => { //log and ignore...
            console.log(error);
	});
}

function showVersionAlert(version) {
    if (document.getElementById("valert"))
	return;  // just like Highlander...

    var popup = document.createElement("div");
    popup.id = "valert";
    popup.className = 'alertbox';

    var div = document.createElement("div");
    div.className = 'statushead';
    div.appendChild(document.createTextNode("Version Alert"));
    popup.appendChild(div);

    div = document.createElement("div");
    div.className = 'status error';
    div.appendChild(document.createElement("br"));
    div.appendChild(document.createTextNode("You are using an out-of-date version of this interface ("+UIstate["version"]+")"));
    div.appendChild(document.createElement("br"));
    div.appendChild(document.createElement("br"));
    div.appendChild(document.createTextNode("Please use the Reload button below to load the latest version ("+version+")"));
    div.appendChild(document.createElement("br"));
    div.appendChild(document.createElement("br"));
    div.appendChild(document.createElement("br"));
    popup.appendChild(div);

    var button = document.createElement("input");
    button = document.createElement("input");
    button.className = "questionBox button";
    button.type = "button";
    button.title = 'Reload to update';
    button.value = 'Reload';
    button.setAttribute('onclick', 'window.location.reload();');
    popup.appendChild(button);

    button = document.createElement("input");
    button.className = "questionBox button";
    button.style.float = "right";
    button.type = "button";
    button.title = 'Dismiss alert';
    button.value = 'Dismiss';
    button.setAttribute('onclick', 'document.body.removeChild(document.getElementById("valert"))');
    popup.appendChild(button);

    dragElement(popup);
    document.body.appendChild(popup);
}


// from w3schools (mostly)
function dragElement(ele) {
    ele.style.cursor = "move";
    var posx1 = 0, posx2 = 0, posy1 = 0, posy2 = 0;
    if (document.getElementById(ele.id + "header")) {
	document.getElementById(ele.id + "header").onmousedown = dragMouseDown;
    }
    else {
	ele.onmousedown = dragMouseDown;
    }

    function dragMouseDown(e) {
	e = e || window.event;
	e.preventDefault();
	posx2 = e.clientX;
	posy2 = e.clientY;
	document.onmouseup = closeDragElement;
	document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
	e = e || window.event;
	e.preventDefault();
	posx1 = posx2 - e.clientX;
	posy1 = posy2 - e.clientY;
	posx2 = e.clientX;
	posy2 = e.clientY;
	ele.style.top  = (ele.offsetTop  - posy1) + "px";
	ele.style.left = (ele.offsetLeft - posx1) + "px";
    }

    function closeDragElement() {
	document.onmouseup = null;
	document.onmousemove = null;
    }
}
