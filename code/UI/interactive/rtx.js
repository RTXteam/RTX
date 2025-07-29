var input_qg = { "edges": {}, "nodes": {} };
var workflow = { 'workflow' : [], 'message' : {} };
var qgids = [];
var cyobj = [];
var cytodata = {};
var predicates = {};
var all_predicates = [];
var all_nodes = {};
var summary_table_html = '';
var summary_score_histogram = {};
var summary_tsv = [];
var compare_tsv = [];
var columnlist = [];
var response_cache = {};
var UIstate = {};

// defaults
var base = "";
var baseAPI = base + "api/arax/v1.4";
var araxQuery = '';

// possibly imported by calling page (e.g. index.html)
if (typeof config !== 'undefined') {
    if (config.base)
	base = config.base;
    if (config.query_endpoint)
	araxQuery = config.query_endpoint;
    if (config.baseAPI)
	baseAPI = config.baseAPI;
}
if (!araxQuery)
    araxQuery = baseAPI + '/query';

var providers = {
    "ARAX" : { "url" : baseAPI },
    "ARAXQ": { "url" : araxQuery },
    "ARS"  : { "url" : "https://ars-prod.transltr.io/ars/api/submit" },
    "EXT"  : { "url" : "https://kg2cploverdb.ci.transltr.io" }
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
    UIstate["submitter"] = 'ARAX GUI';
    UIstate['autorefresh'] = true;
    UIstate["timeout"] = '30';
    UIstate["pruning"] = '50';
    UIstate["pid"] = null;
    UIstate["viewing"] = null;
    UIstate["version"] = checkUIversion(false);
    UIstate["scorestep"] = 0.1;
    UIstate["maxresults"] = 1000;
    UIstate["maxsyns"] = 1000;
    UIstate["prevtimestampobj"] = null;
    UIstate["curiefilter"] = [];
    document.getElementById("menuapiurl").href = providers["ARAX"].url + "/ui/";

    load_meta_knowledge_graph();
    populate_dsl_commands();
    populate_wf_operations();
    populate_wfjson();
    display_list('A');
    display_list('B');
    add_status_divs();
    cytodata['QG'] = 'dummy';

    if (window.chrome)
	document.getElementById("kg_collapse_edges").remove();

    for (var prov in providers) {
	document.getElementById(prov+"_url").value = providers[prov].url;
	document.getElementById(prov+"_url_button").disabled = true;
    }
    for (var setting of ["submitter","timeout","pruning","maxresults","maxsyns"]) {
	document.getElementById(setting+"_url").value = UIstate[setting];
	document.getElementById(setting+"_url_button").disabled = true;
    }
    var tab = getQueryVariable("tab") || "query";
    var syn = getQueryVariable("term") || null;
    var rec = getQueryVariable("recent") || null;
    var pks = getQueryVariable("latest") || null;
    var sys = getQueryVariable("systest") || null;
    var sai = getQueryVariable("smartapi") || getQueryVariable("smartAPI") || null;

    retrieveTestRunnerResultsList(sys);

    var response_id = getQueryVariable("r") || getQueryVariable("id") || null;
    if (response_id) {
	response_id.trim();
	var statusdiv = document.getElementById("statusdiv");
	statusdiv.innerHTML = '';
	statusdiv.append("You have requested response id = " + response_id);
	statusdiv.append(document.createElement("br"));

	document.getElementById("devdiv").innerHTML =  "Requested response id = " + response_id + "<br>";
	var meh_id = isNaN(response_id) ? "X"+response_id : response_id;
	retrieve_response(providers['ARAX'].url+'/response/'+meh_id,response_id,"all");
        pasteId(response_id);
	selectInput("qid");
    }
    else {
	add_cyto(99999,"QG");
    }

    if (syn) {
	tab = "synonym";
	lookup_synonym(syn,false);
    }
    else if (rec) {
	document.getElementById("qftime").value = rec;
	tab = "recentqs";
	retrieveRecentQs(false);
    }
    else if (pks) {
	document.getElementById("howmanylatest").value = pks;
	var from = getQueryVariable("from") || 'test';
	if (!from.startsWith("ars"))
	    from = 'ars.' + from;
	if (!from.endsWith(".transltr.io"))
	    from += '.transltr.io';
        document.getElementById("wherefromlatest").value = from;
	selectInput("qnew");
	retrieveRecentResps();
    }
    else if (sai) {
	tab = "kpinfo";
	retrieveKPInfo();
    }
    else if (sys) {
	tab = "systest";
	if (sys != "1")
	    var timeout = setTimeout(function() { retrieveSysTestResults("ARSARS_"+sys); }, 50 );  // give it time...
	else
	    retrieveSysTestResults();
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

    if (content.style.maxHeight)
	content.style.maxHeight = null;
    else
	content.style.maxHeight = content.scrollHeight + "px";
}


function openSection(sect) {
    if (!document.getElementById(sect+"Menu") || !document.getElementById(sect+"Div"))
	sect = "query";

    display_qg_popup('node','hide');
    display_qg_popup('edge','hide');
    display_qg_popup('filters','hide');

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
    display_qg_popup('filters','hide');

    for (var s of ['qgraph_input','qjson_input','qdsl_input','qwf_input','qpf_input','qid_input','resp_input','qnew_input']) {
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
function pasteExample(type) {
    if (type == "DSL") {
	document.getElementById("dslText").value = '# This program creates two query nodes and a query edge between them, looks for matching edges in the KG,\n# overlays NGD metrics, and returns the top 30 results\nadd_qnode(name=acetaminophen, key=n0)\nadd_qnode(categories=biolink:Protein, key=n1)\nadd_qedge(subject=n0, object=n1, key=e0)\nexpand()\noverlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)\nresultify()\nfilter_results(action=limit_number_of_results, max_results=30)\n';
    }
    else if (type == "JSON1") {
	document.getElementById("jsonText").value = '{\n   "edges": {\n      "e00": {\n         "subject":   "n00",\n         "object":    "n01",\n         "predicates": ["biolink:interacts_with"]\n      }\n   },\n   "nodes": {\n      "n00": {\n         "ids":        ["CHEMBL.COMPOUND:CHEMBL112"]\n      },\n      "n01": {\n         "categories":  ["biolink:Protein"]\n      }\n   }\n}\n';
    }
    else if (type == "JSON2") {
	document.getElementById("jsonText").value = '{\n  "edges": {\n    "t_edge": {\n      "attribute_constraints": [],\n      "knowledge_type": "inferred",\n      "object": "on",\n      "predicates": [\n        "biolink:treats"\n      ],\n      "qualifier_constraints": [],\n      "subject": "sn"\n    }\n  },\n  "nodes": {\n    "on": {\n      "categories": [\n        "biolink:Disease"\n      ],\n      "constraints": [],\n      "ids": [\n        "MONDO:0015564"\n      ],\n      "is_set": false\n    },\n    "sn": {\n      "categories": [\n        "biolink:ChemicalEntity"\n      ],\n      "constraints": [],\n      "is_set": false\n    }\n  }\n}\n';
    }
    else if (type == "JSON3") {
	document.getElementById("jsonText").value = '{\n  "edges": {\n    "t_edge": {\n      "knowledge_type": "inferred",\n      "object": "on",\n      "predicates": [\n        "biolink:affects"\n      ],\n      "qualifier_constraints": [\n        {\n          "qualifier_set": [\n            {\n              "qualifier_type_id": "biolink:object_aspect_qualifier",\n              "qualifier_value": "activity_or_abundance"\n            },\n            {\n              "qualifier_type_id": "biolink:object_direction_qualifier",\n              "qualifier_value": "increased"\n            }\n          ]\n        }\n      ],\n      "subject": "sn"\n    }\n  },\n  "nodes": {\n    "on": {\n      "categories": [\n        "biolink:Gene"\n      ],\n      "ids": [\n        "NCBIGene:51341"\n      ]\n    },\n    "sn": {\n      "categories": [\n        "biolink:ChemicalEntity"\n      ]\n    }\n  }\n}\n';
    }
    else if (type == "PATH1") {
	document.getElementById("jsonText").value = '{\n   "nodes": {\n      "n0": {\n         "ids": [ "MONDO:0005011" ]\n      },\n      "n1": {\n         "ids": [ "MONDO:0005180" ]\n      }\n   },\n   "paths": {\n      "p0": {\n         "subject":   "n0",\n         "object":    "n1",\n         "predicates": [ "biolink:related_to" ]\n      }\n   }\n}\n';
    }

}

function reset_vars() {
    add_status_divs();
    checkUIversion(true);
    if (cyobj[0]) {cyobj[0].elements().remove();}
    display_qg_popup('node','hide');
    display_qg_popup('edge','hide');
    display_qg_popup('filters','hide');
    document.getElementById("queryplan_container").innerHTML = "";
    if (document.getElementById("queryplan_stream")) {
	document.getElementById("queryplan_streamhead").remove();
	document.getElementById("queryplan_stream").remove();
    }
    document.getElementById("filter_container").style.display = 'none';
    document.getElementById("filter_nodelist").innerHTML = "";
    document.getElementById("result_container").style.marginLeft = '';
    document.getElementById("result_container").innerHTML = "";
    document.getElementById("summary_container").innerHTML = "";
    document.getElementById("provenance_container").innerHTML = "";
    document.getElementById("menunummessages").innerHTML = "--";
    document.getElementById("menunummessages").className = "numold menunum";
    document.getElementById("menunumresults").innerHTML = "--";
    document.getElementById("menunumresults").className = "numold menunum";
    summary_table_html = '';
    summary_score_histogram = {};
    summary_tsv = [];
    columnlist = [];
    all_nodes = {};
    UIstate["curiefilter"] = [];
    cyobj = [];
    cytodata['QG'] = 'dummy';
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
        var statusdiv = document.getElementById("statusdiv");
	statusdiv.append(document.createElement("br"));
	if (e.name == "SyntaxError")
	    statusdiv.innerHTML += "<b>Error</b> parsing JSON response input. Please correct errors and resubmit: ";
	else
	    statusdiv.innerHTML += "<b>Error</b> processing response input. Please correct errors and resubmit: ";
	statusdiv.append(document.createElement("br"));
	statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
        add_user_msg("Error processing input","ERROR",false);
	return;
    }

    render_response(jsonInput,true);
}


async function postPathfinder(agent) {
    var pf_query_graph = { "nodes": {}, "paths": {} };
    pf_query_graph.nodes['n0'] = {};
    pf_query_graph.nodes['n0'].ids = [];
    pf_query_graph.nodes['n1'] = {};
    pf_query_graph.nodes['n1'].ids = [];
    pf_query_graph.paths['p0'] = {};
    pf_query_graph.paths['p0'].subject = 'n0';
    pf_query_graph.paths['p0'].object = 'n1';
    pf_query_graph.paths['p0'].predicates = ['biolink:related_to'];

    var statusdiv = document.getElementById("statusdiv");

    try {
	var pf_subject = document.getElementById("pf_subject").value.trim();
	var pf_object = document.getElementById("pf_object").value.trim();
	var pf_inter = document.getElementById("pf_inter").value.trim();

	if (!pf_subject)
	    throw new Error("Pathfinder Subject missing; please add.");
	else if (!pf_object)
	    throw new Error("Pathfinder Object missing; please add.");
	else if (pf_subject == pf_object)
	    throw new Error("Subject and Object cannot be the same; please edit and resubmit.");

	statusdiv.innerHTML = 'Pre-validating nodes...';

	var bestthing = await check_entity(pf_subject,false);
	document.getElementById("devdiv").innerHTML +=  "-- best node = " + JSON.stringify(bestthing,null,2) + "<br>";
	if (bestthing.found) {
            statusdiv.innerHTML += "<p>Found entity with name <b>"+bestthing.name+"</b> that best matches <i>"+pf_subject+"</i> in our knowledge graph.</p>";
            sesame('openmax',statusdiv);
	    pf_query_graph.nodes['n0'].ids.push(bestthing.curie);
	}

	bestthing = await check_entity(pf_object,false);
        document.getElementById("devdiv").innerHTML +=  "-- best node = " + JSON.stringify(bestthing,null,2) + "<br>";
        if (bestthing.found) {
            statusdiv.innerHTML += "<p>Found entity with name <b>"+bestthing.name+"</b> that best matches <i>"+pf_object+"</i> in our knowledge graph.</p>";
            sesame('openmax',statusdiv);
            pf_query_graph.nodes['n1'].ids.push(bestthing.curie);
        }

        if (pf_inter) {
	    var constraint = {};
	    constraint.intermediate_categories = [pf_inter];
	    pf_query_graph.paths['p0'].constraints = [constraint];
	}

	document.getElementById("jsonText").value = JSON.stringify(pf_query_graph,null,2);
	postQuery('JSON','ARAX');
    }
    catch(e) {
	console.error(e);
        statusdiv.append(document.createElement("br"));
        statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
        add_user_msg("Error processing Pathfinder input","ERROR",false);
    }
}


function postQuery(qtype,agent) {
    var queryObj = {};

    reset_vars();
    var statusdiv = document.getElementById("statusdiv");

    // assemble QueryObject
    if (qtype == "DSL") {
	statusdiv.innerHTML = "Posting DSL.  Looking for answer...";
	statusdiv.append(document.createElement("br"));

	var dslArrayOfLines = document.getElementById("dslText").value.split("\n");
	queryObj["message"] = {};
	queryObj["operations"] = { "actions": dslArrayOfLines};
    }
    else if (qtype == "WorkFlow") {
        statusdiv.innerHTML = "Posting Workflow JSON.  Awaiting response...";
	statusdiv.append(document.createElement("br"));
	update_wfjson();
	queryObj = workflow;
    }
    else if (qtype == "JSON") {
	statusdiv.innerHTML = "Posting JSON.  Looking for answer...";
	statusdiv.append(document.createElement("br"));

        var jsonInput;
	try {
	    jsonInput = JSON.parse(document.getElementById("jsonText").value);
	}
	catch(e) {
            statusdiv.append(document.createElement("br"));
	    if (e.name == "SyntaxError")
		statusdiv.innerHTML += "<b>Error</b> parsing JSON input. Please correct errors and resubmit: ";
	    else
		statusdiv.innerHTML += "<b>Error</b> processing input. Please correct errors and resubmit: ";
            statusdiv.append(document.createElement("br"));
	    statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
            add_user_msg("Error parsing input","ERROR",false);
	    return;
	}

	if (jsonInput.message)
	    queryObj = jsonInput;
	else
	    queryObj.message = { "query_graph": jsonInput };

	//queryObj.max_results = 100;

	qg_new(false,false);
    }
    else {  // qGraph
	statusdiv.innerHTML = "Posting graph.  Looking for answer...";
        statusdiv.append(document.createElement("br"));

	qg_clean_up(true);
	queryObj.message = { "query_graph": input_qg };
	//queryObj.bypass_cache = bypass_cache;
	//queryObj.max_results = 100;

	qg_new(false,false);
    }

    queryObj.submitter = UIstate["submitter"];

    if (agent == 'ARS')
	postQuery_ARS(queryObj);
    else if (agent == 'EXT')
	postQuery_EXT(queryObj);
    else
	postQuery_ARAX(qtype,queryObj);

}

function postQuery_ARS(queryObj) {
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.append(" - contacting ARS...");
    statusdiv.append(document.createElement("br"));

    fetch(providers["ARS"].url, {
	method: 'post',
	body: JSON.stringify(queryObj),
	headers: { 'Content-type': 'application/json' }
    }).then(response => {
	if (response.ok) return response.json();
	else throw new Error('Something went wrong');
    })
        .then(data => {
	    var message_id = data['pk'];
	    statusdiv.append(" - got message_id = "+message_id);
	    statusdiv.append(document.createElement("br"));
	    pasteId(message_id);
	    selectInput("qid");
	    var meh_id = isNaN(message_id) ? "X"+message_id : message_id;
	    retrieve_response(providers['ARAX'].url+"/response/"+meh_id,message_id,"all");
	})
        .catch(error => {
            statusdiv.append(" - ERROR:: "+error);
            add_user_msg("Error:"+error,"ERROR",false);
        });

    return;
}


function postQuery_EXT(queryObj) {
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.append(" - contacting 3rd party API...");
    statusdiv.append(document.createElement("br"));

    fetch(providers["EXT"].url + "/query", {
	method: 'post',
	body: JSON.stringify(queryObj),
	headers: { 'Content-type': 'application/json' }

    }).then(response => {
	if (response.ok) return response.json();
	else throw new Error('Something went wrong');

    }).then(data => {
	var dev = document.getElementById("devdiv");
        dev.append(document.createElement("br"));
	dev.append('='.repeat(80)+" RESPONSE MESSAGE::");
	var pre = document.createElement("pre");
	pre.id = "responseJSON";
	pre.append(JSON.stringify(data,null,2));
	dev.append(pre);

	if (data["description"])
	    statusdiv.append(data["description"]);
	else
	    statusdiv.append(" - JSON response received");
	statusdiv.append(document.createElement("br"));
	sesame('openmax',statusdiv);

	if (!data["status"] || data["status"] == "OK" || data["status"] == "Success") {
	    input_qg = { "edges": {}, "nodes": {} };
	    render_response(data, true);
	}
	else if (data["status"] == "QueryGraphZeroNodes") {
	    qg_new(false,false);
	}
	else if (data["logs"]) {
	    process_log(data["logs"]);
	}
	else {
	    statusdiv.innerHTML += "<br><span class='error'>An error was encountered while parsing the response from the remote server (no log; code:"+data.status+")</span>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with capturing QUERY:<br>"+data;
	    sesame('openmax',statusdiv);
            add_user_msg("Error parsing response from the remote server","ERROR",false);
	}

    }).catch(error => {
	statusdiv.append(" - ERROR:: "+error);
        add_user_msg("Error:"+error,"ERROR",false);
    });

    return;
}


// use fetch and stream
function postQuery_ARAX(qtype,queryObj) {
    var statusdiv = document.getElementById("statusdiv");

    queryObj.stream_progress = true;
    if (UIstate["timeout"]) {
	if (!queryObj.query_options)
	    queryObj.query_options = {};
	queryObj.query_options['kp_timeout'] = UIstate["timeout"];
    }
    if (UIstate["pruning"]) {
	if (!queryObj.query_options)
	    queryObj.query_options = {};
	queryObj.query_options['prune_threshold'] = UIstate["pruning"];
    }
    var cmddiv = document.createElement("div");
    cmddiv.id = "cmdoutput";
    statusdiv.append(cmddiv);
//    statusdiv.appendChild(document.createElement("br"));

    statusdiv.append("Processing step ");
    var span = document.createElement("span");
    span.id = "finishedSteps";
    span.style.fontWeight = "bold";
//    span.className = "menunum numnew";
    span.append("0");
    statusdiv.append(span);
    statusdiv.append(" of ");
    span = document.createElement("span");
    span.id = "totalSteps";
//    span.className = "menunum";
    span.append("??");
    statusdiv.append(span);

    span = document.createElement("span");
    span.className = "progress";

    var span2 = document.createElement("span");
    span2.id = "progressBar";
    span2.className = "bar";
    span2.append("0%");
    span.append(span2);

    statusdiv.append(span);
    statusdiv.append(document.createElement("br"));
    statusdiv.append(document.createElement("br"));
    sesame('openmax',statusdiv);

    add_to_dev_info("Posted to QUERY",queryObj);
    fetch(providers["ARAXQ"].url, {
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

		var completeMsgs = partialMsg.split("}\n");
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
			msg += "}"; // lost in the split, above

			var jsonMsg = JSON.parse(msg);
			if (jsonMsg.logs) { // was:: (jsonMsg.description) {
			    enqueue = true;
			    respjson += msg;
			}
			else if (jsonMsg.message) {
			    if (jsonMsg.message.match(/^Parsing action: [^\#]\S+/)) {
				totalSteps++;
			    }
			    else if (jsonMsg.message.match(/triggering pathfinder subsystem.$/)) {
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

			    cmddiv.append(jsonMsg.timestamp+'\u00A0'+jsonMsg.level+':\u00A0'+jsonMsg.message);
			    cmddiv.append(document.createElement("br"));
			    cmddiv.scrollTop = cmddiv.scrollHeight;
			}
                        else if (jsonMsg.qedge_keys) {
			    var div;
			    if (document.getElementById("queryplan_stream"))
				div = document.getElementById("queryplan_stream");
			    else {
				div = document.createElement("div");
				div.id = "queryplan_streamhead";
				div.className = 'statushead';
				div.append("Expansion Progress");
				document.getElementById("status_container").before(div);

				div = document.createElement("div");
				div.id = "queryplan_stream";
				div.className = 'status';
				document.getElementById("status_container").before(div);
			    }

			    div.innerHTML = '';
			    div.append(document.createElement("br"));
			    div.append(render_queryplan_table(jsonMsg));
			    div.append(document.createElement("br"));
			}
                        else if (jsonMsg.pid) {
			    UIstate["pid"] = jsonMsg;
			    display_kill_button();
			}
			else if (jsonMsg.detail) {
			    cmddiv.append(document.createElement("br"));
                            cmddiv.append("ERROR:\u00A0"+jsonMsg.detail);
			    throw new Error(jsonMsg.detail);
			}
			else {
			    console.log("bad msg:"+JSON.stringify(jsonMsg,null,2));
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
            dev.append(document.createElement("br"));
	    dev.append('='.repeat(80)+" RESPONSE MESSAGE::");
	    var pre = document.createElement("pre");
	    pre.id = "responseJSON";
	    pre.append(JSON.stringify(data,null,2));
	    dev.append(pre);

	    if (document.getElementById("killquerybutton"))
		document.getElementById("killquerybutton").remove();

	    document.getElementById("progressBar").style.width = "800px";
	    if (data.status == "OK" || data.status == "Success")
		document.getElementById("progressBar").innerHTML = "Finished\u00A0\u00A0";
	    else {
		document.getElementById("progressBar").classList.add("barerror");
		document.getElementById("progressBar").innerHTML = "Error\u00A0\u00A0";
		document.getElementById("finishedSteps").classList.add("menunum","numnew","msgERROR");
		there_was_an_error(data.description);
	    }
	    statusdiv.append(data["description"]);
	    statusdiv.append(document.createElement("br"));
	    sesame('openmax',statusdiv);

	    if (data["status"] == "QueryGraphZeroNodes") {
		qg_new(false,false);
	    }
	    else if (data["status"] == "OK" || data["status"] == "Success") {
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
            if (document.getElementById("killquerybutton"))
		document.getElementById("killquerybutton").remove();

	    statusdiv.innerHTML += "<br><span class='error'>An error was encountered while contacting the server ("+err+")</span>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with parsing QUERY:<br>"+err;
	    sesame('openmax',statusdiv);
	    if (err.log)
		process_log(err.log);
	    console.log(err.message);

            there_was_an_error("An error was encountered while contacting the server ("+err+")");
	});
}

function display_kill_button() {
    var button = document.createElement("input");
    button.id = 'killquerybutton';
    button.className = 'questionBox button';
    button.style.background = "#c40";
    button.type = 'button';
    button.name = 'action';
    button.value = 'Terminate Query!';
    button.title = 'Kill this request (pid='+UIstate["pid"].pid+')';
    button.setAttribute('onclick', 'kill_query();');

    document.getElementById("status_container").before(button);
}

function kill_query() {
    if (!UIstate["pid"].pid || !UIstate["pid"].authorization) {
        document.getElementById("killquerybutton").replaceWith('No PID or authorization; cannot terminate query');
	return;
    }

    fetch(providers["ARAX"].url + "/status?terminate_pid="+UIstate["pid"].pid+"&authorization="+UIstate["pid"].authorization)
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong with termination...');
	})
        .then(data => {
            if (data.status == 'OK' || data.status == 'Success') {
		document.getElementById("killquerybutton").id = 'killquerybuttondead';
		addCheckBox(document.getElementById("killquerybuttondead"),true);
		var timeout = setTimeout(function() { document.getElementById("killquerybuttondead").remove(); } , 1500 );
		document.getElementById("statusdiv").innerHTML += "<br><span class='error'>Query terminated by user</span>";
		add_user_msg("Query terminated by user");
		if (document.getElementById("cmdoutput")) {
                    var cmddiv = document.getElementById("cmdoutput");
		    cmddiv.append(document.createElement("br"));
		    cmddiv.append(data.description);
                    cmddiv.append(document.createElement("br"));
		    cmddiv.scrollTop = cmddiv.scrollHeight;
		    for (var e of document.getElementsByClassName("working")) {
			e.classList.remove('working');
			e.classList.remove('p5');
			e.classList.add('barerror');
		    }
		    document.getElementById("progressBar").classList.add("barerror");
		    document.getElementById("progressBar").innerHTML += " (terminated)\u00A0\u00A0";
		}
	    }
            else if (data.status == 'ERROR') {
		document.getElementById("killquerybutton").after('Cannot terminate query');
		console.warn('Query termination attempt error: '+data.description);
	    }
	    else throw new Error('Something went wrong while attempting to terminate query...');
	})
        .catch(error => {
	    var span = document.createElement("span");
	    span.className = 'error';
	    span.innerHTML = error;
	    document.getElementById("killquerybutton").after(span);
	});
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

    var maxsyn = UIstate["maxsyns"];
    var allweknow = await check_entity(word,true,maxsyn,document.getElementById("showConceptGraph").checked);

    if (0) { // set to 1 if you just want full JSON dump instead of html tables
	syndiv.innerHTML = "<pre>"+JSON.stringify(allweknow,null,2)+"</pre>";
	return;
    }

    var div, text, table, tr, td;

    div = document.createElement("div");
    div.className = "statushead";
    div.append("Synonym Results");
    text = document.createElement("a");
    text.target = '_blank';
    text.title = 'link to this synonym entry';
    text.href = "http://"+ window.location.hostname + window.location.pathname + "?term=" + word;
    text.innerHTML = "[ Direct link to this entry ]";
    text.style.float = "right";
    div.append(text);
    syndiv.append(div);

    div = document.createElement("div");
    div.className = "status";
    text = document.createElement("h2");
    text.className = "qprob p9";
    text.append(word);
    div.append(text);
    //div.appendChild(document.createElement("br"));

    if (!allweknow[word]) {
	text.className = "qprob p1";
	div.append(document.createElement("br"));
	div.append("Entity not found.");
	div.append(document.createElement("br"));
	div.append(document.createElement("br"));
	syndiv.append(div);
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
	    td.append(syn);
	    tr.append(td);
	    td = document.createElement("td")
	    if (syn == "identifier")
		td.append(link_to_identifiers_dot_org(allweknow[word].id[syn]));
	    td.append(allweknow[word].id[syn]);
	    tr.append(td);
	    table.append(tr);
	}

	if (allweknow[word].synonyms) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.style.fontWeight = 'bold';
	    td.append('synonyms (all)');
	    tr.append(td);
	    td = document.createElement("td")
	    var comma = '';
	    for (var syn in allweknow[word].synonyms) {
		td.append(comma + syn + " (" +allweknow[word].synonyms[syn] + ")");
		comma = ", ";
	    }
	    tr.append(td);
	    table.append(tr);
	}

	if (allweknow[word].categories) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.style.fontWeight = 'bold';
	    td.append('categories (all)');
	    tr.append(td);
	    td = document.createElement("td")
	    var comma = '';
	    for (var cat in allweknow[word].categories) {
		td.append(comma + cat + " (" +allweknow[word].categories[cat] + ")");
		comma = ", ";
	    }
	    tr.append(td);
	    table.append(tr);
	}

	div.append(table);
    }

    if (allweknow[word].nodes) {
	text = document.createElement("h3");
        text.className = "qprob p5";
	text.append('Nodes');
	if (allweknow[word].total_synonyms > maxsyn) {
	    text.append(' (truncated to '+maxsyn+' from a total of '+allweknow[word].total_synonyms+")");
	    text.title = "* You can change this value in the Settings section on the left menu";
	    var span = document.createElement("span");
	    span.className = "qprob p9";
	    span.style.marginLeft = '20px';
	    span.append('New!');
	    text.append(span);

	    span = document.createElement("span");
	    span.className = 'tiny';
	    span.style.marginLeft = '15px';
	    span.append('[ Go to ');
	    var link =document.createElement("a");
	    link.href="javascript:openSection('settings');"
	    link.append('Settings');
	    span.append(link);
	    span.append(' to change this value ]');
            text.append(span);
	}
	else
	    text.append(' ('+allweknow[word].total_synonyms+")");

	div.append(text);

	table = document.createElement("table");
	table.className = 'sumtab';
	tr = document.createElement("tr");
	for (var head of ["Identifier","Label","Category","KG2pre","KG2pre Name","KG2pre Category","SRI_NN","SRI Name","SRI Category"] ) {
	    td = document.createElement("th")
	    td.append(head);
	    tr.append(td);
	}
	table.append(tr);
	for (var syn of allweknow[word].nodes) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td")
	    td.append(link_to_identifiers_dot_org(syn.identifier));
	    td.append(syn.identifier);
	    tr.append(td);
	    td = document.createElement("td")
	    td.append(syn.label);
	    tr.append(td);
	    td = document.createElement("td")
	    td.append(syn.category);
	    tr.append(td);

	    td = document.createElement("td")
	    text = document.createElement("span");
	    if (syn.in_kg2pre) {
		text.innerHTML = '&check;';
		text.className = 'explevel p9';
		text.title = 'Found in KG2pre';
	    }
	    else {
		text.innerHTML = '&cross;';
		text.className = 'explevel p0';
		text.title = 'NOT found in KG2pre';
	    }
	    td.append(text);
	    tr.append(td);

            td = document.createElement("td")
	    td.append(syn.name_kg2pre);
	    tr.append(td);
	    td = document.createElement("td")
	    td.append(syn.category_kg2pre);
	    tr.append(td);

	    td = document.createElement("td")
            text = document.createElement("span");
	    if (syn.in_sri) {
		text.innerHTML = '&check;';
		text.className = 'explevel p9';
		text.title = 'Found in SRI NodeNormalizer';
	    }
	    else {
		text.innerHTML = '&cross;';
		text.className = 'explevel p0';
		text.title = 'NOT found in SRI NodeNormalizer';
	    }
            td.append(text);
            tr.append(td);

            td = document.createElement("td")
	    td.append(syn.name_sri);
	    tr.append(td);
	    td = document.createElement("td")
	    td.append(syn.category_sri);
	    tr.append(td);

	    table.append(tr);
	}
	div.append(table);
    }

    if (allweknow[word].equivalent_identifiers) {
	text = document.createElement("h3");
        text.className = "qprob p5";
	text.append('Equivalent Identifiers');
	div.append(text);

	table = document.createElement("table");
	table.className = 'sumtab';
	tr = document.createElement("tr");
	for (var head of ["Identifier","Category","Source"] ) {
	    td = document.createElement("th")
	    td.append(head);
	    tr.append(td);
	}
	table.append(tr);
	for (var syn of allweknow[word].equivalent_identifiers) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td");
	    td.append(link_to_identifiers_dot_org(syn.identifier));
	    td.append(syn.identifier);
	    tr.append(td);
	    td = document.createElement("td");
	    td.append(syn.category);
	    tr.append(td);
	    td = document.createElement("td");
	    td.append(syn.source);
	    tr.append(td);
	    table.append(tr);
	}
	div.append(table);
    }

    if (allweknow[word].synonym_provenance) {
	text = document.createElement("h3");
	text.className = "qprob p5";
	//text.appendChild(document.createTextNode('\u25BA Synonym Provenance'));
	text.append('Synonym Provenance');
	div.append(text);

	table = document.createElement("table");
	table.className = 'sumtab';
        tr = document.createElement("tr");
	for (var head of ["Name","Curie","Source"] ) {
	    td = document.createElement("th");
	    td.append(head);
	    tr.append(td);
	}
        table.append(tr);
	for (var syn in allweknow[word].synonym_provenance) {
            tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td");
	    td.append(allweknow[word].synonym_provenance[syn].name);
	    tr.append(td);
	    td = document.createElement("td");
            td.append(link_to_identifiers_dot_org(allweknow[word].synonym_provenance[syn].uc_curie));
	    td.append(allweknow[word].synonym_provenance[syn].uc_curie);
	    tr.append(td);
	    td = document.createElement("td");
	    td.append(allweknow[word].synonym_provenance[syn].source);
	    tr.append(td);
	    table.append(tr);
	}
	div.append(table);
    }

    div.append(document.createElement("br"));
    syndiv.append(div);

    if (allweknow[word]["knowledge_graph"]) {
	process_graph(allweknow[word]["knowledge_graph"],'SYN',"1.4");

	div = document.createElement("div");
	div.className = "statushead";
	div.append("Concept Graph");
	syndiv.append(div);

	div = document.createElement("div");
        div.className = "status";
	div.id = "a88888_div";
	table = document.createElement("table");
	table.className = 't100';
        add_graph_to_table(table,88888);
        div.append(table);
        syndiv.append(div);

        add_cyto(88888,"SYN");
    }

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
    link.append(img);

    return link;
}


function getIdStats(id) {
    if (document.getElementById("numresults_"+id)) {
	document.getElementById("numresults_"+id).innerHTML = '';
	document.getElementById("respsize_"+id).innerHTML = '';
	document.getElementById("nodedges_"+id).innerHTML = '';
	document.getElementById("nsources_"+id).innerHTML = '';
	document.getElementById("numaux_"+id).innerHTML = '';
	document.getElementById("cachelink_"+id).innerHTML = '';
	document.getElementById("istrapi_"+id).innerHTML = 'loading...';
	document.getElementById("numresults_"+id).append(getAnimatedWaitBar(null));
    }
    var meh_id = isNaN(id) ? "X"+id : id;
    retrieve_response(providers["ARAX"].url+"/response/"+meh_id,id,"stats");
}

function checkRefreshARS() {
    document.getElementById("ars_refresh").dataset.count += "x";
    var moon = 127765;
    if (UIstate['autorefresh'] && document.getElementById("ars_refresh").dataset.count.length == document.getElementById("ars_refresh").dataset.total) {
	document.getElementById("ars_refresh_anim").innerHTML = "&#"+moon;
	var timetogo = 8;
	var timeout = setInterval(countdown, 375);
	function countdown() {
	    if (timetogo == 0) {
		clearInterval(timeout);
		if (UIstate['autorefresh'])
                    sendId(true);
		document.getElementById("ars_refresh_anim").innerHTML = "";
	    }
	    else {
		moon--;
		if (moon == 127760) moon = 127768;
                if (UIstate['autorefresh'])
		    document.getElementById("ars_refresh_anim").innerHTML = "&#"+moon;
		else
		    timetogo = 1; // stop reloads
		timetogo--;
	    }
	}
    }
}

function sendId(is_ars_refresh) {
    var id;
    if (is_ars_refresh)
	id = document.getElementById("ars_refresh").dataset.msgid;
    else {
	id = document.getElementById("idText").value.trim();
	pasteId(id);
	if (!id) return;

	UIstate['autorefresh'] = true;
	reset_vars();
	if (cyobj[99999]) {cyobj[99999].elements().remove();}
	input_qg = { "edges": {}, "nodes": {} };

	for (var item of document.querySelectorAll('[id^="resparrow_"]'))
	    item.className = '';
	if (document.getElementById("resparrow_"+id)) {
	    document.getElementById("resparrow_"+id).className = 'p7';
	    UIstate["viewing"] = id;
	}
    }

    if (document.getElementById("numresults_"+id)) {
	document.getElementById("numresults_"+id).innerHTML = '';
	document.getElementById("respsize_"+id).innerHTML = '';
	document.getElementById("nodedges_"+id).innerHTML = '';
        document.getElementById("nsources_"+id).innerHTML = '';
        document.getElementById("numaux_"+id).innerHTML = '';
        document.getElementById("cachelink_"+id).innerHTML = '';
	document.getElementById("istrapi_"+id).innerHTML = 'loading...';
	document.getElementById("numresults_"+id).append(getAnimatedWaitBar(null));
    }

    if (id.startsWith("http")) {
	var urlid = id.replace(/\//g,"$");
        retrieve_response(providers["ARAX"].url+"/response/"+urlid,urlid,"all");
    }
    else if (id.startsWith("hhttp"))
	retrieve_response(id.substring(1),id.substring(1),"all");
    else {
        var meh_id = isNaN(id) ? "X"+id : id;
	retrieve_response(providers["ARAX"].url+"/response/"+meh_id,id,"all");
    }
    if (!is_ars_refresh)
	openSection('query');
}


function process_ars_message(ars_msg, level) {
    if (level > 5)
	return; // stopgap
    var table, tr, td;
    if (level == 0) {
        document.title = "ARAX-UI [ARS Collection: "+ars_msg.message+"]";
        add_to_session(ars_msg.message,"[ARS Collection] id="+ars_msg.message);
	history.pushState({ id: 'ARAX_UI' }, 'ARAX | id='+ars_msg.message, "//"+ window.location.hostname + window.location.pathname + '?r='+ars_msg.message);

	if (document.getElementById('ars_message_list'))
	    document.getElementById('ars_message_list').remove();
	var div = document.createElement("div");
	div.id = 'ars_message_list';

        var div2 = document.createElement("div");
	div2.className = "statushead";
        div2.append("Collection Results");
        div.append(div2);

	var span = document.createElement("span");
	span.id = 'ars_refresh';
	span.style.float = 'right';
	span.style.marginRight = '20px';
	span.dataset.total = ars_msg.status == 'Done' ? 999999 : ars_msg["children"].length + 1;
	span.dataset.count = '';
	span.dataset.msgid = ars_msg.message;
        if (UIstate['autorefresh'])
	    span.append("Auto-reload: " + (ars_msg.status == 'Done' ? "OFF" : "ON"));
	if (ars_msg.status != 'Done') {
	    span.title = "Click to Stop Auto-Refresh";
	    span.className = "clq";
	    span.setAttribute('onclick', 'UIstate["autorefresh"] = false; document.getElementById("ars_refresh").innerHTML = "";');
	}
	div2.append(span);

	span = document.createElement("span");
	span.id = 'ars_refresh_anim';
	span.style.float = 'right';
	span.style.marginRight = '20px';
	div2.append(span);

	var div2 = document.createElement("div");
	div2.id = "arsresultsdiv";
	div2.className = "status";

	table = document.createElement("table");
	table.id = 'ars_message_list_table';
	table.className = 'sumtab';

	tr = document.createElement("tr");
	for (var head of ["","Agent","Status / Code","Message Id","Size","TRAPI 1.5?","N_Results","Nodes / Edges","Sources","Aux","Cache"] ) {
	    td = document.createElement("th")
	    td.style.paddingRight = "15px";
	    td.append(head);
	    tr.append(td);
	}
	table.append(tr);

	div2.append(document.createElement("br"));
	div2.append(table);
        div2.append(document.createElement("br"));
        div.append(div2);
	document.getElementById('qid_input').append(div);
    }
    else
	table = document.getElementById('ars_message_list_table');

    tr = document.createElement("tr");
    tr.className = 'hoverable';
    td = document.createElement("td");
    if (level) {
	td.id = "resparrow_"+ars_msg.message;
	if (UIstate["viewing"] == ars_msg.message)
	    td.className = 'p7';
    }
    td.append('\u25BA'.repeat(level));
    tr.append(td);
    td = document.createElement("td");
    td.append(ars_msg.actor.agent);
    tr.append(td);
    td = document.createElement("td");
    if (ars_msg.status == 'Error')
	td.className = 'error';
    else if (ars_msg.status == 'Running')
	td.className = 'essence';
    td.append(ars_msg.status);
    if (ars_msg.code)
        td.append(" / "+ars_msg.code);
    tr.append(td);
    td = document.createElement("td");

    var link;
    var go = false;
    if (ars_msg.status == "Running")
	link = document.createTextNode(ars_msg.message);
    else {
	link = document.createElement("a");
	link.title = 'view this response';
	link.style.cursor = "pointer";
	link.style.fontFamily = "monospace";
	link.setAttribute('onclick', 'pasteId("'+ars_msg.message+'");sendId(false);');
	link.append(ars_msg.message);
	if (!ars_msg["children"] || ars_msg["children"].length == 0)
	    go = true;
    }
    td.append(link);
    tr.append(td);


    if (ars_msg.actor.agent == 'ars-default-agent') {
	td = document.createElement("td");
	td.colSpan = "7";
	link = document.createElement("a");
	link.className = "button";
        link.style.marginLeft = "20px";
        link.style.padding = "3px 20px";
        link.style.color = "white";
	link.title = '(opens a new tab)';
	var ui_host = ars_msg.ui_host ? ars_msg.ui_host : "ui.ci.transltr.io";
	link.href = "https://"+ui_host+"/results?l=&t=&q="+ars_msg.message;
	link.target = '_TxUI';
	link.append("Open in Translator UI");
	td.append(link);
	tr.append(td);
    }
    else {
	td = document.createElement("td");
	td.id = "respsize_"+ars_msg.message;
	td.style.textAlign = "right";
	tr.append(td);

	td = document.createElement("td");
	td.id = "istrapi_"+ars_msg.message;
	td.style.textAlign = "center";
	tr.append(td);

	td = document.createElement("td");
	td.id = "numresults_"+ars_msg.message;
	td.style.textAlign = "center";
	tr.append(td);

	td = document.createElement("td");
	td.id = "nodedges_"+ars_msg.message;
	td.style.textAlign = "center";
	tr.append(td);

	td = document.createElement("td");
	td.id = "nsources_"+ars_msg.message;
	td.style.textAlign = "center";
	tr.append(td);

	td = document.createElement("td");
	td.id = "numaux_"+ars_msg.message;
	td.style.textAlign = "center";
	tr.append(td);

	td = document.createElement("td");
	td.id = "cachelink_"+ars_msg.message;
	td.style.textAlign = "right";
	tr.append(td);
    }
    table.append(tr);

    if (go)
	getIdStats(ars_msg.message);
    else
	checkRefreshARS();

    level++;
    if (ars_msg["children"])
	for (let child of ars_msg["children"].sort(function(a, b) { return a.actor.agent > b.actor.agent ? 1 : -1; }))
	    process_ars_message(child, level);
}


function process_response(resp_url, resp_id, type, jsonObj2) {
    var statusdiv = document.getElementById("statusdiv");
    if (type == "all") {
	var devdiv = document.getElementById("devdiv");
	devdiv.append(document.createElement("br"));
	devdiv.append('='.repeat(80)+" RESPONSE REQUEST::");
	var link = document.createElement("a");
	link.target = '_blank';
	link.href = resp_url;
	link.style.position = "relative";
	link.style.left = "30px";
	link.append("[ view raw json response \u2197 ]");
	devdiv.append(link);
	devdiv.append(document.createElement("br"));
    }

    if (jsonObj2["children"]) {
	process_ars_message(jsonObj2,0);
	return;
    }

    if (jsonObj2["restated_question"])
	statusdiv.innerHTML += "Your question has been interpreted and is restated as follows:<br>&nbsp;&nbsp;&nbsp;<B>"+jsonObj2["restated_question"]+"?</b><br>Please ensure that this is an accurate restatement of the intended question.<br>";

    jsonObj2.araxui_response = resp_id;

    if (jsonObj2.validation_result) {
	var nr = document.createElement("span");
        if (type == "all") {
	    statusdiv.append(document.createElement("br"));
	    statusdiv.append("TRAPI v"+jsonObj2.validation_result.version+" validation: ");
	    var vares  = document.createElement("b");
            vares.append(jsonObj2.validation_result.status);
	    statusdiv.append(vares);

	    if (jsonObj2.validation_result.validation_messages) {
		statusdiv.append(". View full report: [ ");
		vares = document.createElement("a");
		vares.style.fontWeight = "bold";
                vares.style.cursor = "pointer";
		vares.title = "JSON report";
		vares.append("JSON ");
		var valink = document.createElement("a");
                valink.target = '_validator';
                valink.href = "https://ncatstranslator.github.io/reasoner-validator/validation_codes_dictionary.html";
                valink.append('Validation Codes Dictionary');
		vares.onclick = function () { showJSONpopup("Validation results for: "+jsonObj2.araxui_response, jsonObj2.validation_result.validation_messages, valink); };
		statusdiv.append(vares);
		statusdiv.append(" ] -- [ ");

		vares = document.createElement("a");
		vares.style.fontWeight = "bold";
                vares.style.cursor = "pointer";
		vares.title = "text report";
                vares.append("text ");
		var valink = document.createElement("a");
                valink.target = '_validator';
                valink.href = "https://ncatstranslator.github.io/reasoner-validator/validation_codes_dictionary.html";
                valink.append('Validation Codes Dictionary');
		vares.onclick = function () { showJSONpopup("Validation results for: "+jsonObj2.araxui_response, jsonObj2.validation_result.validation_messages_text, valink); };
		statusdiv.append(vares);
		statusdiv.append(" ]");
	    }

	    statusdiv.append(document.createElement("br"));
	}
	if (jsonObj2.validation_result.status == "FAIL") {
	    if (type == "all") {
		var span = document.createElement("span");
		span.className = 'error';
		span.append(jsonObj2.validation_result.message);
		statusdiv.append(span);
		statusdiv.append(document.createElement("br"));
	    }
	    nr.innerHTML = '&cross;';
	    nr.className = 'explevel p1';
	    nr.title = 'Failed TRAPI 1.5 validation';
	}
        else if (jsonObj2.validation_result.status == "ERROR") {
            if (type == "all") {
                var span = document.createElement("span");
                span.className = 'error';
                span.append(jsonObj2.validation_result.message);
                statusdiv.append(span);
                statusdiv.append(document.createElement("br"));
	    }
	    nr.innerHTML = '&#x2755;';
	    nr.className = 'explevel p3';
            nr.title = 'There were TRAPI 1.5 validation errors';
	}
        else if (jsonObj2.validation_result.status == "NA") {
            if (type == "all") {
                var span = document.createElement("span");
                span.className = 'error';
                span.append(jsonObj2.validation_result.message);
                statusdiv.append(span);
                statusdiv.append(document.createElement("br"));
	    }
	    nr.innerHTML = '&nsub;';
	    nr.className = 'explevel p0';
            nr.title = 'Response is non-TRAPI';
	}
        else if (jsonObj2.validation_result.status == "DISABLED") {
            if (type == "all") {
		var span = document.createElement("span");
		span.className = 'error';
		span.append(jsonObj2.validation_result.message);
		statusdiv.append(span);
		statusdiv.append(document.createElement("br"));
	    }
	    nr.innerHTML = '&#10067;';
	    nr.className = 'explevel';
	    nr.title = 'TRAPI validation has been temporarily DISABLED';
	}
	else {
	    nr.innerHTML = '&check;';
	    nr.className = 'explevel p9';
	    nr.title = 'Passed TRAPI 1.5 validation';
	}

	if (document.getElementById("istrapi_"+jsonObj2.araxui_response)) {
	    document.getElementById("istrapi_"+jsonObj2.araxui_response).innerHTML = '';
	    document.getElementById("istrapi_"+jsonObj2.araxui_response).append(nr);

	    var num = parseFloat(jsonObj2.validation_result.size.match(/[\d\.]+/));
	    if (num && num > 2 && jsonObj2.validation_result.size.includes("MB")) {
		document.getElementById("respsize_"+jsonObj2.araxui_response).className = "error";
		document.getElementById("respsize_"+jsonObj2.araxui_response).title = "Warning: Very large responses might render slowly";
	    }
	    document.getElementById("respsize_"+jsonObj2.araxui_response).innerHTML = jsonObj2.validation_result.size;

            if (jsonObj2.validation_result.validation_messages) {
                var table, tr, td;
                var html_node = document.getElementById("istrapi_"+jsonObj2.araxui_response);
                html_node.className += " tooltip";
                var tnode = document.createElement("span");
                tnode.className = 'tooltiptext';
                table = document.createElement("table");
		table.title = "Click for more details";
                table.style.width = "100%";
                table.style.borderCollapse = "collapse";

		for (var vtype of ["critical","error","warning","info","skipped"]) {
                    if (Object.keys(jsonObj2.validation_result.validation_messages[vtype]).length > 0) {
			tr = document.createElement("tr");
			td = document.createElement("th");
			td.style.background = "#3d6d98";
			td.style.padding = "5px 0px";
			td.append("Validation "+vtype);
			tr.append(td);
			table.append(tr);
			for (var vmsg in jsonObj2.validation_result.validation_messages[vtype]) {
                            tr = document.createElement("tr");
                            tr.style.background = "initial";
                            td = document.createElement("td");
                            td.append(vmsg);
                            tr.append(td);
                            table.append(tr);
			}
		    }
		}

		tnode.append(table);
                html_node.append(tnode);
		var valink = document.createElement("a");
		valink.target = '_validator';
		valink.href = "https://ncatstranslator.github.io/reasoner-validator/validation_codes_dictionary.html";
		valink.innerHTML = 'Validation Codes Dictionary';
		var showthis = jsonObj2.validation_result.validation_messages_text ? jsonObj2.validation_result.validation_messages_text : jsonObj2.validation_result.validation_messages;
                html_node.onclick = function () { showJSONpopup("Validation results for: "+jsonObj2.araxui_response, showthis, valink); };
	    }
            else if (jsonObj2.validation_result.message) {
                var tnode = document.createElement("span");
                tnode.className = 'tooltiptext';
		tnode.style.padding = "10px";
		tnode.append(jsonObj2.validation_result.message);
                var html_node = document.getElementById("istrapi_"+jsonObj2.araxui_response);
                html_node.className += " tooltip";
                html_node.append(tnode);
	    }

	    if (jsonObj2.message && jsonObj2.message["auxiliary_graphs"] && Object.keys(jsonObj2.message["auxiliary_graphs"]).length > 0)
		document.getElementById("numaux_"+jsonObj2.araxui_response).innerHTML = Object.keys(jsonObj2.message["auxiliary_graphs"]).length;

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
		    td.append("Provenance Counts");
		    tr.append(td);
		    table.append(tr);
		    for (var prov in jsonObj2.validation_result.provenance_summary.provenance_counts) {
			tr = document.createElement("tr");
			tr.style.background = "initial";
			for (var pc of jsonObj2.validation_result.provenance_summary.provenance_counts[prov]) {
			    td = document.createElement("td");
			    td.append(pc);
			    tr.append(td);
			}
			td.style.textAlign = "right";  // last td is always[?] the count number
			table.append(tr);
		    }
		    tnode.append(table);
		    html_node.append(tnode);
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
		    td.append("Predicate Counts");
		    tr.append(td);
		    table.append(tr);
		    for (var pred in jsonObj2.validation_result.provenance_summary.predicate_counts) {
			tr = document.createElement("tr");
                        tr.style.background = "initial";
			td = document.createElement("td")
			td.append(pred);
			tr.append(td);
			td = document.createElement("td");
			td.style.textAlign = "right";
			td.append(jsonObj2.validation_result.provenance_summary.predicate_counts[pred]);
			tr.append(td);
			table.append(tr);
		    }
		    tnode.append(table);
		    html_node.append(tnode);
		}
	    }
	    checkRefreshARS();
	}
    }
    else if (!jsonObj2.message)
        update_response_stats_on_error(jsonObj2.araxui_response,'&nsub;',true);

    if (document.getElementById("arsresultsdiv"))
	document.getElementById("arsresultsdiv").style.height = document.getElementById("arsresultsdiv").scrollHeight + "px";

    if (type == "all") {
	var h3 = document.createElement("h3");
	h3.style.fontStyle = "italic";
	if (jsonObj2.description)
            h3.append(jsonObj2.description);
	h3.append(document.createElement("br"));
	h3.append(document.createElement("br"));
	if (jsonObj2.status)
            h3.append(jsonObj2.status);
        statusdiv.append(h3);
        statusdiv.append(document.createElement("br"));
    }
    sesame('openmax',statusdiv);

    if (type == "stats")
	render_response_stats(jsonObj2);
    else
	render_response(jsonObj2,true);

    if (!response_cache[resp_id])
	response_cache[resp_id] = jsonObj2;
    display_cache();
}


function retrieve_response(resp_url, resp_id, type) {
    if (type == null) type = "all";
    var statusdiv = document.getElementById("statusdiv");
    statusdiv.append("Retrieving response id = " + resp_id);

    if (resp_id.startsWith("http"))
	resp_id = "URL:"+hashCode(resp_id);

    if (response_cache[resp_id]) {
        if (document.getElementById("istrapi_"+resp_id))
	    document.getElementById("istrapi_"+resp_id).innerHTML = 'rendering...';
	statusdiv.append(" ...from cache ("+resp_id+")");
	statusdiv.append(document.createElement("hr"));
	sesame('openmax',statusdiv);
	// 50ms timeout allows css animation to start before processing locks the thread
	var timeout = setTimeout(function() { process_response(resp_url, resp_id, type,response_cache[resp_id]); }, 50 );
	return;
    }

    statusdiv.append(document.createElement("hr"));
    sesame('openmax',statusdiv);

    var xhr = new XMLHttpRequest();
    xhr.open("get",  resp_url, true);
    //xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.send(null);
    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
            if (document.getElementById("istrapi_"+resp_id))
		document.getElementById("istrapi_"+resp_id).innerHTML = 'rendering...';
	    process_response(resp_url, resp_id, type, JSON.parse(xhr.responseText));
	}
	else if ( xhr.status == 404 ) {
	    update_response_stats_on_error(resp_id,'N/A',true);
	    var msg = "Response with id="+resp_id+" was not found";
	    try {
		var jsonResp = JSON.parse(xhr.responseText);
		if (!jsonResp.detail) throw new Error('no detail');
                statusdiv.innerHTML += "<br><span class='error'>"+jsonResp.detail+"</span>";
		msg = jsonResp.detail;
	    }
	    catch(e) {
		if (resp_id.startsWith("URL:"))
		    statusdiv.innerHTML += "<br>No response found at <span class='error'>"+resp_url+"</span> (404).";
		else
		    statusdiv.innerHTML += "<br>Response with id=<span class='error'>"+resp_id+"</span> was not found (404).";

	    }
	    sesame('openmax',statusdiv);
	    there_was_an_error(msg);
	}
	else {
            update_response_stats_on_error(resp_id,'Error',true);
	    statusdiv.innerHTML += "<br><span class='error'>An error was encountered while contacting the server ("+xhr.status+")</span>";
	    document.getElementById("devdiv").innerHTML += "------------------------------------ error with RESPONSE:<br>"+xhr.responseText;
	    sesame('openmax',statusdiv);
            there_was_an_error("An error was encountered while contacting the server");
	}
    };

}


function render_response_stats(respObj) {
    if (!document.getElementById("numresults_"+respObj.araxui_response)) return;

    var nr = document.createElement("span");
    document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';

    if ( !respObj.message ) {
        nr.className = 'explevel p0';
	nr.innerHTML = '&nbsp;&nsub;&nbsp;';
    }
    else if ( respObj.message["results"] ) {
	if (respObj.validation_result && respObj.validation_result.status == "FAIL")
	    nr.className = 'explevel p1';
	else if (respObj.validation_result && respObj.validation_result.status == "ERROR")
	    nr.className = 'explevel p3';
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

    document.getElementById("numresults_"+respObj.araxui_response).append(nr);
}

function update_response_stats_on_error(rid,msg,clearall) {
    if (!document.getElementById("numresults_"+rid)) return;

    document.getElementById("numresults_"+rid).innerHTML = '';
    var nr = document.createElement("span");
    nr.className = 'explevel p0';
    nr.innerHTML = '&nbsp;'+msg+'&nbsp;';
    document.getElementById("numresults_"+rid).append(nr);

    if (clearall) {
	document.getElementById("respsize_"+rid).innerHTML = '---';
	document.getElementById("nodedges_"+rid).innerHTML = '';
	document.getElementById("nsources_"+rid).innerHTML = '';
	document.getElementById("numaux_"+rid).innerHTML = '';
	document.getElementById("istrapi_"+rid).innerHTML = '';
	document.getElementById("cachelink_"+rid).innerHTML = '';
    }
}

function render_response(respObj,dispjson) {
    var statusdiv = document.getElementById("statusdiv");
    if (!respObj["schema_version"])
	respObj["schema_version"] = "1.5 (presumed)";
    statusdiv.append("Rendering TRAPI "+respObj["schema_version"]+" message...");

    sesame('openmax',statusdiv);

    if (respObj.araxui_response) {
        document.title = "ARAX-UI ["+respObj.araxui_response+"]";
        add_to_session(respObj.araxui_response,"id="+respObj.araxui_response);
	history.pushState({ id: 'ARAX_UI' }, "ARAX | id="+respObj.araxui_response, "//"+ window.location.hostname + window.location.pathname + "?r="+respObj.araxui_response);
    }
    else if (respObj.id) {
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
    else if (respObj.restated_question)
        document.title = "ARAX-UI [no response_id]: "+respObj.restated_question+"?";
    else
	document.title = "ARAX-UI [no response_id]";


    if (!respObj.message) {
	statusdiv.append("no message!");
	statusdiv.append(document.createElement("br"));
	var nr = document.createElement("span");
	nr.className = 'essence';
	nr.append("Response contains no message, and hence no results.");
	statusdiv.append(nr);
	sesame('openmax',statusdiv);
        update_response_stats_on_error(respObj.araxui_response,'&nsub;',false);
	add_user_msg("Response contains no message, and hence no results","ERROR",false);
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
	process_graph(respObj.message["query_graph"],'QG',respObj["schema_version"]);
    }
    else {
	cytodata['QG'] = 'dummy'; // this enables query graph editing
    }

    if (respObj["operations"])
	process_q_options(respObj["operations"]);


    if (respObj["logs"])
	process_log(respObj["logs"]);
    else
        document.getElementById("logdiv").innerHTML = "<h2 style='margin-left:20px;'>No log messages in this response</h2>";

    // Do this *before* processing results
    let isPathFinder = false;
    if ( respObj["table_column_names"] )
	add_to_summary(respObj["table_column_names"],0);
    else if (respObj.message.results && respObj.message.results.length == 1) {
	isPathFinder = true; // might need refining...
	add_to_summary(["Node","Curie","Count"],0);
    }
    else
	add_to_summary(["score","'guessence'"],0);

    if (respObj.message["results"]) {
	if (!respObj.message["knowledge_graph"] ) {
            document.getElementById("result_container").innerHTML  += "<h2 class='error'>Knowledge Graph missing in response; cannot process results.</h2>";
	    document.getElementById("summary_container").innerHTML += "<h2 class='error'>Knowledge Graph missing in response; cannot process results</h2>";
	    document.getElementById("provenance_container").innerHTML += "<h2 class='error'>Knowledge Graph missing in response; cannot process results</h2>";
            update_response_stats_on_error(respObj.araxui_response,'n/a',false);
            add_user_msg("Knowledge Graph missing in response; cannot process results","ERROR",false);
	}
	else {
	    var h2 = document.createElement("h2");

	    var rtext = respObj.message.results.length == 1 ? " result" : " results";
	    if (isPathFinder) {
		rtext += " [ triggering PathFinder mode ]";
		h2.className = 'statushead';
		h2.style.marginBottom = "-15px";
	    }

	    if (respObj.total_results_count && respObj.total_results_count > respObj.message.results.length)
		rtext += " (truncated from a total of " + respObj.total_results_count + ")";

	    h2.append(respObj.message.results.length + rtext);
	    if (respObj.message.results.length > UIstate["maxresults"]) {
		h2.append(" (*only showing first "+UIstate["maxresults"]+") [ ? ]");
		h2.title = "* You can change this value in the Settings section on the left menu";
	    }
	    document.getElementById("result_container").append(h2);

	    document.getElementById("menunumresults").innerHTML = respObj.message.results.length;
            if (respObj.message.results.length > UIstate["maxresults"])
		document.getElementById("menunumresults").innerHTML += '*';
            document.getElementById("menunumresults").classList.add("numnew");
	    document.getElementById("menunumresults").classList.remove("numold");


	    process_graph(respObj.message["knowledge_graph"],'KG',respObj["schema_version"]);
	    var respreas = 'n/a';
	    if (respObj.resource_id)
		respreas = respObj.resource_id;
	    else if (respObj.reasoner_id)
		respreas = respObj.reasoner_id;

	    var auxiliary_graphs = respObj.message["auxiliary_graphs"] ? respObj.message["auxiliary_graphs"] : null;
	    try {
		if (isPathFinder)
		    process_pathfinder(respObj.message["results"][0],respObj.message["knowledge_graph"],auxiliary_graphs,respObj["schema_version"],respreas);
		else
		    process_results(respObj.message["results"],respObj.message["knowledge_graph"],auxiliary_graphs,respObj["schema_version"],respreas);
	    }
	    catch(e) {
		var span = document.createElement("span");
		span.className = 'error';
		span.append("ERROR:: "+e);
		statusdiv.append(span);
		console.error("Bad Response:"+e);
		update_response_stats_on_error(respObj.araxui_response,'n/a',false);
		add_user_msg("Bad response:"+e,"ERROR",false);
		return;
	    }

            if (respObj.message.results.length > UIstate["maxresults"])
		document.getElementById("result_container").append(h2.cloneNode(true));

	    if (document.getElementById("numresults_"+respObj.araxui_response)) {
		document.getElementById("numresults_"+respObj.araxui_response).innerHTML = '';
		var nr = document.createElement("span");
		if (respObj.validation_result && respObj.validation_result.status == "FAIL")
		    nr.className = 'explevel p1';
		else if (respObj.validation_result && respObj.validation_result.status == "ERROR")
		    nr.className = 'explevel p3';
		else if (respObj.message.results.length > 0)
		    nr.className = 'explevel p9';
		else
		    nr.className = 'explevel p5';
		nr.innerHTML = '&nbsp;'+respObj.message.results.length+'&nbsp;';
		document.getElementById("numresults_"+respObj.araxui_response).append(nr);
	    }
	}
    }
    else {
        document.getElementById("result_container").innerHTML  += "<h2>No results...</h2>";
        document.getElementById("summary_container").innerHTML += "<h2>No results...</h2>";
	document.getElementById("provenance_container").innerHTML += "<h2>No results...</h2>";
        update_response_stats_on_error(respObj.araxui_response,'n/a',false);
        add_user_msg("Response contains no results","WARNING",false);
    }

    // table was (potentially) populated in process_results
    if (summary_tsv.length > 1) {
	var div = document.createElement("div");
	div.className = 'statushead';
	div.append("Summary");
        document.getElementById("summary_container").append(div);

	div = document.createElement("div");
	div.className = 'status';
	div.id = 'summarydiv';
	div.append(document.createElement("br"));

	var button = document.createElement("input");
	button.className = 'questionBox button';
	button.type = 'button';
	button.name = 'action';
	button.title = 'Get tab-separated values of this table to paste into Excel etc';
	button.value = 'Copy Summary Table to clipboard (TSV)';
	button.setAttribute('onclick', 'copyTSVToClipboard(this,summary_tsv);');
        div.append(button);


	if (Object.keys(summary_score_histogram).length > 0) {
	    var table = document.createElement("table");
	    table.style.display = "inline-table";
            table.style.marginLeft = "80px";

	    var tr = document.createElement("tr");
            var td = document.createElement("th");
	    td.style.borderBottom = "1px solid black";
	    td.colSpan = Object.keys(summary_score_histogram).length;
            td.append("SCORE DISTRIBUTION");
            tr.append(td);
            table.append(tr);

	    var tr = document.createElement("tr");
	    for (var s in summary_score_histogram) {
		td = document.createElement("td");
		td.className = 'hoverable';
		td.style.verticalAlign = "bottom";
		td.style.textAlign = "center";
		td.style.padding = "0px";
                td.append(summary_score_histogram[s]);
		td.append(document.createElement("br"));

		var span = document.createElement("span");
		span.className = "bar";
		var barh = Number(summary_score_histogram[s]);
		span.style.height = barh + "px";
		span.style.width = "25px";
		td.append(span);
		td.append(document.createElement("br"));

		td.append(s);
		tr.append(td);
	    }
	    table.append(tr);
            div.append(table);
	    div.append(document.createElement("br"));
            div.append(document.createElement("br"));
	}

	var table = document.createElement("table");
	table.className = 'sumtab';
	table.innerHTML = summary_table_html;
        div.append(table);
	div.append(document.createElement("br"));

	document.getElementById("summary_container").append(div);
    }
    else
        document.getElementById("summary_container").innerHTML += "<h2>Summary not available for this query</h2>";


    if (respObj.query_options && respObj.query_options.query_plan) {
        var div = document.createElement("div");
	div.className = 'statushead';
	div.append("Expansion Results");
	document.getElementById("queryplan_container").append(div);

	div = document.createElement("div");
	div.className = 'status';
	div.append(document.createElement("br"));
        document.getElementById("queryplan_container").append(div);

	div.append(render_queryplan_table(respObj.query_options.query_plan));
	div.append(document.createElement("br"));
    }

    if (respObj.validation_result && respObj.validation_result.provenance_summary) {
	var div = document.createElement("div");
	div.className = 'statushead';
	div.append("Provenance Summary");
	document.getElementById("provenance_container").append(div);

	div = document.createElement("div");
	div.className = 'status';
	div.id = 'provenancediv';
	div.append(document.createElement("br"));

        var table = document.createElement("table");
	table.className = 'sumtab';
        var tr = document.createElement("tr");
        var td = document.createElement("th");
	td.colSpan = "2";
        td.style.fontSize = 'x-large';
	td.append("Provenance Counts");
	tr.append(td);
        td = document.createElement("th");
	td.append("[ "+respObj.validation_result.provenance_summary["n_sources"]+" sources ]");
	tr.append(td);
	td = document.createElement("th");
	td.colSpan = "2";
	tr.append(td);
	table.append(tr);

        var semmeddb_counts = {};

	var previous0 = 'RandomTextToPurposelyTriggerThickTopBorderForFirstRowAndRepeatedDisplayOfPredicate';
	var previous1 = 'RandomTextToOmitRepatedDisplayOfPredicateProviderType';
	for (var prov in respObj.validation_result.provenance_summary.provenance_counts) {
	    var provdata = respObj.validation_result.provenance_summary.provenance_counts[prov].slice();  // creates a copy (instead of a reference)
	    var changed0 = false;
	    var changed1 = false;
	    if (previous0 != provdata[0]) {
		changed0 = true;
		changed1 = true;
	    }
	    else if (previous1 != provdata[1])
		changed1 = true;

	    previous0 = provdata[0];
            previous1 = provdata[1];

	    if (!changed0)
		provdata[0] = '';
	    else
		semmeddb_counts[previous0] = 0;
	    if (provdata[2] == 'infores:semmeddb')
		semmeddb_counts[previous0] += provdata[3];

	    if (!changed1)
		provdata[1] = '';

	    tr = document.createElement("tr");
            tr.className = 'hoverable';
	    for (var pc of provdata) {
		td = document.createElement("td");
		if (changed0)
		    td.style.borderTop = "2px solid #444";
		td.append(pc);
		tr.append(td);
	    }
	    td.style.textAlign = "right";  // last td is always[?] the count number

	    // fancy bar bar
	    td = document.createElement("td");
            if (changed0)
		td.style.borderTop = "2px solid #444";
	    var span = document.createElement("span");
	    span.className = "bar";
	    var barw = 0.5*Number(provdata[3]);
	    if (barw > 500) {
		barw = 501;
		span.style.background = "#3d6d98";
	    }
	    if (provdata[2] == 'no provenance')
		span.style.background = "#b00";
	    span.style.width = barw + "px";
	    span.style.height = "8px";
	    td.append(span);
            tr.append(td);

	    table.append(tr);
	}

	// use same table so it is all nicely aligned
        tr = document.createElement("tr");
	td = document.createElement("td");
	td.colSpan = "5";
	td.style.background = '#fff';
	td.style.border = '0';
	td.append(document.createElement("br"));
	td.append(document.createElement("br"));
        tr.append(td);
	table.append(tr);

	tr = document.createElement("tr");
	td = document.createElement("th");
	td.colSpan = "2";
	td.style.background = '#fff';
        td.style.fontSize = 'x-large';
	td.append("Predicate Counts");
	tr.append(td);
        td = document.createElement("th");
	td.style.background = '#fff';
	td.colSpan = "3";
	tr.append(td);

	td = document.createElement("th");
	td.style.background = '#fff';
	td.style.color = '#666';
	td.append("SEMMEDDB Sub-Counts");
	td.colSpan = "3";
	//td.style.textAlign = "left";
	td.style.borderLeft = "2px solid black";
	tr.append(td);


	table.append(tr);
        for (var pred in respObj.validation_result.provenance_summary.predicate_counts) {
	    tr = document.createElement("tr");
	    tr.className = 'hoverable';
	    td = document.createElement("td");
	    td.colSpan = "3";
	    td.append(pred);
	    tr.append(td);
	    td = document.createElement("td");
	    td.style.textAlign = "right";
	    td.append(respObj.validation_result.provenance_summary.predicate_counts[pred]);
	    tr.append(td);
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
	    td.append(span);
	    tr.append(td);


	    td = document.createElement("td");
	    td.style.textAlign = "right";
	    td.style.borderLeft = "2px solid black";
	    td.append(semmeddb_counts[pred]);
	    tr.append(td);
            // fancy bar bar
	    td = document.createElement("td");
	    var span = document.createElement("span");
	    span.className = "bar";
	    var barw = Math.round(100*Number(semmeddb_counts[pred]/respObj.validation_result.provenance_summary.predicate_counts[pred]));
	    if (barw > 100) {
		barw = 101;
		span.style.background = "#3d6d98";
	    }
	    else
		span.style.background = "#f80";
	    span.style.width = barw + "px";
	    span.style.height = "8px";
	    td.append(span);
	    tr.append(td);

	    td = document.createElement("td");
	    td.style.textAlign = "right";
	    td.append(" "+barw+"%");

	    tr.append(td);
	    table.append(tr);
	}
	div.append(table);
	div.append(document.createElement("br"));

	document.getElementById("provenance_container").append(div);
    }
    else
	document.getElementById("provenance_container").innerHTML += "<h2>Provenance information not available for this response</h2>";


    add_cyto(99999,"QG");
    statusdiv.append("done.");
    statusdiv.append(document.createElement("br"));
    if (respObj["submitter"]) {
	statusdiv.append("Submitted by: "+respObj.submitter);
	statusdiv.append(document.createElement("br"));
    }

    // add stats
    statusdiv.append("Number of results: ");
    if (respObj.message["results"] && respObj.message["results"].length > 0)
	statusdiv.append(respObj.message["results"].length);
    else
	statusdiv.append("none");
    statusdiv.append(document.createElement("br"));

    statusdiv.append("Number of nodes: ");
    if (respObj.message["knowledge_graph"] && respObj.message["knowledge_graph"]["nodes"] && Object.keys(respObj.message["knowledge_graph"]["nodes"]).length > 0)
	statusdiv.append(Object.keys(respObj.message["knowledge_graph"]["nodes"]).length);
    else
	statusdiv.append("none");
    statusdiv.append(document.createElement("br"));

    statusdiv.append("Number of edges: ");
    if (respObj.message["knowledge_graph"] && respObj.message["knowledge_graph"]["edges"] && Object.keys(respObj.message["knowledge_graph"]["edges"]).length > 0)
	statusdiv.append(Object.keys(respObj.message["knowledge_graph"]["edges"]).length);
    else
	statusdiv.append("none");
    statusdiv.append(document.createElement("br"));

    statusdiv.append("Number of aux graphs: ");
    if (respObj.message["auxiliary_graphs"] && Object.keys(respObj.message["auxiliary_graphs"]).length > 0)
        statusdiv.append(Object.keys(respObj.message["auxiliary_graphs"]).length);
    else
        statusdiv.append("none");
    statusdiv.append(document.createElement("br"));


    var nr = document.createElement("span");
    nr.className = 'essence';
    nr.append("Click on Results, Summary, Provenance, or Knowledge Graph links on the left to explore results.");
    statusdiv.append(nr);
    statusdiv.append(document.createElement("br"));
    sesame('openmax',statusdiv);
    add_user_msg("TRAPI response rendered successfully","INFO",true);
}

function render_queryplan_table(qp) {
    var status_map = {};
    status_map["Done"] = 'p9';
    status_map["Expanding"] = 'p5 working';
    status_map["Waiting"] = 'p5';
    status_map["Timed out"] = 'p3';
    status_map["Warning"] = 'p3';
    status_map["Error"] = 'p1';
    status_map["Skipped"] = 'p0';

    var table = document.createElement("table");
    table.className = 'sumtab';
    var tr = document.createElement("tr");
    var td = document.createElement("td");
    td.append(" No Expansion data in response ");
    tr.append(td);
    table.append(tr);

    for (let edge in qp.qedge_keys) {
	var ep = null;
	if (qp.qedge_keys[edge].edge_properties) {
	    ep = qp.qedge_keys[edge].edge_properties;
	    delete qp.qedge_keys[edge].edge_properties;
	}

	tr = document.createElement("tr");
	td = document.createElement("td");
	td.rowSpan = Object.keys(qp.qedge_keys[edge]).length;
	td.style.backgroundColor = "white";
	td.style.borderRight = "1px solid #aaa";
	td.style.textAlign = "center";
	td.style.padding = "0px 20px";
	if (ep && ep.status) {
            var span = document.createElement("span");
	    span.style.position = "relative";
	    span.style.left = "-10px";
	    span.className = "explevel " + status_map[ep["status"]];
	    span.append('\u00A0');
	    span.append('\u00A0');
            td.append(span);
	    td.title = ep.status;
	}
	var text = document.createElement("h2");
	text.style.display = "inline-block";
	text.append(edge);
	td.append(text);
	if (ep) {
	    td.append(document.createElement("br"));
	    td.append(document.createElement("br"));
	    var span = document.createElement("span");
	    span.className = 'qprob p7';
            span.style.display = "inline-block";
            if (ep.subject == null)
		span.append('--any--');
	    else {
		for (var s of ep.subject) {
		    span.append(s);
		    span.append(document.createElement("br"));
		}
	    }
            td.append(span);
	    td.append(document.createElement("br"));
            td.append("|");
            td.append(document.createElement("br"));
	    span = document.createElement("span");
            span.className = 'qprob scam';
            span.style.display = "inline-block";
	    if (ep.predicate == null)
                span.append('--any--');
            else {
		for (var p of ep.predicate) {
		    span.append(p);
                    span.append(document.createElement("br"));
		}
	    }
	    td.append(span);
	    td.append(document.createElement("br"));
            td.append("|");
	    td.append(document.createElement("br"));
            span = document.createElement("span");
            span.className = 'qprob p7';
            span.style.display = "inline-block";
            if (ep.object == null)
		span.append('--any--');
	    else {
		for (var o of ep.object) {
		    span.append(o);
                    span.append(document.createElement("br"));
		}
	    }
	    td.append(span);
	}

	tr.append(td);

	var is_first = true;
	for (let kp in qp.qedge_keys[edge]) {
            if (!is_first)
		tr = document.createElement("tr");
            td = document.createElement("td");
            td.append(kp);
            tr.append(td);

	    td = document.createElement("td");
            var span = document.createElement("span");
	    span.className = "explevel " + status_map[qp.qedge_keys[edge][kp]["status"]];
	    span.append('\u00A0');
	    span.append('\u00A0');
	    td.append(span);
            td.append('\u00A0');
	    td.append(qp.qedge_keys[edge][kp]["status"]);
	    tr.append(td);

	    td = document.createElement("td");
	    if (qp.qedge_keys[edge][kp]["status"] == "Skipped")
		td.className = "DEBUG";
            td.append(qp.qedge_keys[edge][kp]["description"]);
	    tr.append(td);

	    td = document.createElement("td");
            if (qp.qedge_keys[edge][kp]["query"] && qp.qedge_keys[edge][kp]["query"] != null) {
                var link = document.createElement("a");
		link.title = 'view the posted query (JSON)';
		link.style.cursor = "pointer";
		link.onclick = function () { showJSONpopup("Query sent to "+kp, qp.qedge_keys[edge][kp]["query"], false); };
		link.append("query");
		td.append(link);
	    }
            tr.append(td);

	    table.append(tr);
	    is_first = false;
	}

	tr = table.deleteRow(0);
	tr = table.insertRow(0);
	for (var head of ["Query Edge","KP","Status","Description","Query"] ) {
            td = document.createElement("th")
            td.append(head);
            tr.append(td);
	}
    }

    return table;
}

function showJSONpopup(wtitle,query,footer) {
    var popup;
    if (document.getElementById("kpq"))
	popup = document.getElementById("kpq");
    else {
	popup = document.createElement("div");
	popup.id = "kpq";
	popup.className = 'alertbox';
    }
    popup.innerHTML = '';

    var span = document.createElement("span");
    span.className = 'clq clwin2';
    span.title = 'Close this window';
    span.setAttribute('onclick', 'document.body.removeChild(document.getElementById("kpq"))');
    span.append("\u2573");
    popup.append(span);

    var div = document.createElement("div");
    div.className = 'statushead';
    div.style.marginTop = "-40px";
    div.append(wtitle);
    popup.append(div);

    div = document.createElement("div");
    div.className = 'status';
    div.onmousedown = function () { event.stopPropagation(); };
    div.style.cursor = "auto";
    div.style.overflowY = "auto";
    div.style.maxHeight = "70vh";
    var pre = document.createElement("pre");
    pre.style.color = "#000";
    if (query && typeof query === 'object' && query.constructor === Object)
	pre.append(JSON.stringify(query,null,2));
    else
	pre.innerText = query;
    div.append(pre);
    popup.append(div);

    if (footer) {
	div = document.createElement("div");
	div.className = 'statusfoot';
	div.append(footer);
	popup.append(div);
    }

    dragElement(popup);
    var timeout = setTimeout(function() { popup.classList.add('shake'); }, 50 );
    document.body.append(popup);
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


function there_was_an_error(msg="An error was encountered") {
    document.getElementById("summary_container").innerHTML += "<h2 class='error'>Error : No results</h2>";
    document.getElementById("result_container").innerHTML  += "<h2 class='error'>Error : No results</h2>";
    document.getElementById("menunumresults").innerHTML = "E";
    document.getElementById("menunumresults").classList.add("numnew","msgERROR");
    document.getElementById("menunumresults").classList.remove("numold");
    add_user_msg(msg,"ERROR",false);
}


function calc_timespan(obj) {
    if (!obj.dataset.timestamp)
	return;

    obj.style.background = "#ff0";

    if (UIstate["prevtimestampobj"]) {
	let units = " seconds";
	let diff = Math.abs(obj.dataset.timestamp - UIstate["prevtimestampobj"].dataset.timestamp)/1000;
	if (diff>66) {
	    diff = (diff/60).toFixed(4);
	    units = " minutes";
	}
	showJSONpopup("Elapsed Time","Elapsed time is: "+diff+units,false);

	obj.style.background = null;
	UIstate["prevtimestampobj"].style.background = null;
	UIstate["prevtimestampobj"] = null;
    }
    else {
	UIstate["prevtimestampobj"] = obj;
    }
}

function process_log(logarr) {
    var status = {};
    for (var s of ["ERROR","WARNING","INFO","DEBUG"]) {
	status[s] = 0;
    }
    let starttime = null;
    for (var msg of logarr) {
	if (msg.prefix) { // upconvert TRAPI 0.9.3 --> 1.0
	    msg.level = msg.level_str;
	    msg.code = null;
	}

	status[msg.level]++;

	// TOFIX when TIMESTAMP not present
	var span = document.createElement("span");
	span.title = "Click to display elapsed time between two events";
	span.className = "hoverable msg " + msg.level;
	span.dataset.timestamp = Date.parse(msg.timestamp);
	span.setAttribute('onclick', 'calc_timespan(this);');

	if (!starttime)
	    starttime = span.dataset.timestamp;

        if (msg.level == "DEBUG") { span.style.display = 'none'; }

	var span2 = document.createElement("span");
	span2.className = "explevel msg" + msg.level;
	span2.append('\u00A0\u00A0');
	span.append(span2);

        span2 = document.createElement("span");
	span2.append('\u00A0');
	span2.append(msg.timestamp+" "+msg.level+": ");
	if (msg.code)
	    span2.append("["+msg.code+"] ");

	span2.append('\u00A0\u00A0\u00A0');
	span2.append(msg.message);
	span.append(span2);

        let units = " s";
	let diff = Math.abs(span.dataset.timestamp - starttime)/1000;
	if (diff>66) {
            diff = (diff/60).toFixed(4);
	    units = " m";
	}
	span2 = document.createElement("span");
	span2.style.float = 'right';
        span2.append(diff+units);
        span.append(span2);

	document.getElementById("logdiv").append(span);
    }
    document.getElementById("menunummessages").innerHTML = logarr.length;
    if (status.ERROR > 0)
	document.getElementById("menunummessages").classList.add('numnew','msgERROR');
    else if (status.WARNING > 0)
	document.getElementById("menunummessages").classList.add('numnew','msgWARNING');
    for (var s of ["ERROR","WARNING","INFO","DEBUG"]) {
	document.getElementById("count_"+s).innerHTML += ": "+status[s];
    }
}


function add_status_divs() {
    // summary
    document.getElementById("status_container").innerHTML = '';

    var div = document.createElement("div");
    div.className = 'statushead';
    div.append("Status");
    document.getElementById("status_container").append(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'statusdiv';
    document.getElementById("status_container").append(div);

    // results
    document.getElementById("dev_result_json_container").innerHTML = '';

    div = document.createElement("div");
    div.className = 'statushead';
    div.append("Dev Info");
    var span = document.createElement("span");
    span.style.fontStyle = "italic";
    span.style.fontWeight = 'normal';
    span.style.float = "right";
    span.append("( json responses )");
    div.append(span);
    document.getElementById("dev_result_json_container").append(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'devdiv';
    document.getElementById("dev_result_json_container").append(div);

    // messages
    document.getElementById("messages_container").innerHTML = '';

    div = document.createElement("div");
    div.className = 'statushead';
    div.append("Filter Messages:");

    for (var status of ["Error","Warning","Info","Debug"]) {
	span = document.createElement("span");
	span.id =  'count_'+status.toUpperCase();
	span.style.marginLeft = "20px";
	span.style.cursor = "pointer";
	span.className = 'qprob msg'+status.toUpperCase();
	if (status == "Debug") span.classList.add('hide');
	span.setAttribute('onclick', 'filtermsgs(this,\"'+status.toUpperCase()+'\");');
	span.append(status);
	div.append(span);
    }

    document.getElementById("messages_container").append(div);

    div = document.createElement("div");
    div.className = 'status';
    div.id = 'logdiv';
    document.getElementById("messages_container").append(div);
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


function add_to_score_histogram(score) {
    if (score == 'n/a')
	return;

    if (Object.keys(summary_score_histogram).length == 0) {
        for (var s = 0; s < 1; s+=UIstate["scorestep"]) {
	    summary_score_histogram[s.toFixed(1)] = 0;
	}
    }

    var p = 0;
    var missedit = true;
    for (var s in summary_score_histogram) {
	if (score < Number(s)) {
	    summary_score_histogram[p]++;
	    missedit = false;
	    break;
	}
	p = s;
    }
    if (missedit)
	summary_score_histogram[p]++;

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


function display_QG_from_JSON() {
    var statusdiv = document.getElementById("statusdiv");
    var jsonInput;
    try {
        jsonInput = JSON.parse(document.getElementById("jsonText").value);
    }
    catch(e) {
        statusdiv.append(document.createElement("br"));
        if (e.name == "SyntaxError")
            statusdiv.innerHTML += "<b>Error</b> parsing JSON input. Please correct errors and try again: ";
        else
            statusdiv.innerHTML += "<b>Error</b> processing input. Please correct errors and try again: ";
        statusdiv.append(document.createElement("br"));
        statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
        sesame('openmax',statusdiv);
        return;
    }

    if ("message" in jsonInput)
	jsonInput = jsonInput['message'];
    if ("query_graph" in jsonInput)
	jsonInput = jsonInput['query_graph'];

    if ("nodes" in jsonInput &&
	"edges" in jsonInput) {
	process_graph(jsonInput,'QG',"1.5");

	if (cyobj[99999]) { cyobj[99999].elements().remove(); }
	else add_cyto(99999,'QG');

	qg_edit(true);
	selectInput('qgraph');
    }
    else {
        statusdiv.innerHTML += "<span class='error'>Error: no nodes and edges detected: cannot use input as a query_graph</span>";
        add_user_msg("Error: no nodes and edges detected: cannot use input as a query_graph","ERROR",false);
    }
}


// used for gid = 0 [KG] and 99999 [QG]
function process_graph(gne,graphid,trapi) {
    cytodata[graphid] = [];
    var gid = graphid == "KG" ? 0 : graphid == "SYN" ? 88888 : 99999;
    for (var id in gne.nodes) {
	var gnode = Object.create(gne['nodes'][id]); // make a copy!

	gnode.parentdivnum = gid;   // helps link node to div when displaying node info on click
	gnode.trapiversion = trapi; // deprecate??

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

	if (graphid == 'SYN')
	    gnode.idname = id;

	var tmpdata = { "data" : gnode };
        cytodata[graphid].push(tmpdata);
    }

    for (var id in gne.edges) {
        var gedge = Object.create(gne['edges'][id]); // make a copy!

        if (!gedge.id)
	    gedge.id = id;

	gedge.parentdivnum = gid;
        gedge.trapiversion = trapi;
        gedge.source = gedge.subject;
        gedge.target = gedge.object;
	if (gedge.predicates)
	    gedge.type = gedge.predicates[0];

        var tmpdata = { "data" : gedge };
        cytodata[graphid].push(tmpdata);
    }


    if (graphid == 'QG') {
	for (var id in gne.nodes) {
	    var gnode = gne.nodes[id];
	    qgids.push(id);

	    var tmpdata = { "ids"        : gnode.ids ? gnode.ids : [],
			    "is_set"     : gnode.is_set,
			    "_names"     : gnode.ids ? gnode.ids.slice() : [], // make a copy!
			    "_desc"      : gnode.description,
			    "categories" : gnode.categories ? gnode.categories : [],
			    "option_group_id" : gnode.option_group_id ? gnode.option_group_id : null,
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
			    "exclude"    : gedge.exclude ? gedge.exclude : false,
			    "option_group_id" : gedge.option_group_id ? gedge.option_group_id : null,
			    "attribute_constraints": gedge.attribute_constraints ? gedge.attribute_constraints : [],
			    "qualifier_constraints": gedge.qualifier_constraints ? gedge.qualifier_constraints : []
			  };
	    input_qg.edges[id] = tmpdata;
	}
    }

}


function process_pathfinder(result,kg,aux,trapi,mainreasoner) {
    if (!result.analyses || result.analyses.length < 1)
	throw new Error('No analyses found in result[0]');

    if (!result.node_bindings || Object.keys(result.node_bindings).length < 2)
        throw new Error('Not enough node_bindings found in result[0]');

    var div = document.createElement("h3");
    div.id = 'pathfilterstatus';
    div.className = 'status';
    div.style.padding = '15px';
    div.append("loading...");
    document.getElementById("result_container").append(div);

    var results_fragment = document.createDocumentFragment();

    // deal with multiple curie/ids per binding?  ToDo?
    var path_src = result.node_bindings[Object.keys(result.node_bindings)[0]][0].id;
    var path_end = result.node_bindings[Object.keys(result.node_bindings)[1]][0].id;

    if ('n0' in result.node_bindings)
	path_src = result.node_bindings['n0'][0].id;
    else if ('sn' in result.node_bindings)
	path_src = result.node_bindings['sn'][0].id;

    if ('n1' in result.node_bindings)
	path_end = result.node_bindings['n1'][0].id;
    else if ('on' in result.node_bindings)
	path_end = result.node_bindings['on'][0].id;

    var num = 0;
    for (var ranal of result.analyses) {
	num++;

	div = document.createElement("div");
        div.id = 'pathdivhead_'+num;
	div.title = 'Click to expand / collapse analysis '+num;
        div.className = 'accordion';

	var auxgraph = ranal.path_bindings[Object.keys(ranal.path_bindings)[0]][0]['id'];  // TODO: deal with more than one path_binding...?
        add_aux_graph(kg,auxgraph,aux[auxgraph]["edges"],num,trapi);
	div.setAttribute('onclick', 'add_cyto('+num+',"AUX'+auxgraph+'","grid");sesame(this,a'+num+'_div);');

	div.dataset.pnodes = "|filter|";
        div.append(" Analysis "+num+" :: ");

        var span = document.createElement("span");
        span.className = 'filtertag p0';
        span.title = "Source node";
        span.append(kg.nodes[path_src]["name"]);
        div.append(span);

	for (var pnode of get_node_list_in_paths(ranal.path_bindings,kg,aux).sort((a, b) => kg.nodes[a]['name'].localeCompare(kg.nodes[b]['name'], 'en', {'sensitivity': 'base'}))) {
	    if (all_nodes[pnode]) {
                all_nodes[pnode]['total']++;
                all_nodes[pnode]['filtered']++;
	    }
            else {
                all_nodes[pnode] = {};
                all_nodes[pnode]['name'] = kg.nodes[pnode]["name"];
		all_nodes[pnode]['total'] = 1;
		all_nodes[pnode]['filtered'] = 1;
	    }

	    if (pnode == path_src || pnode == path_end)
		continue;

	    span = document.createElement("span");
            span.className = 'filterbutton';
	    span.title = "Filter for all Paths that contain ["+pnode+"]";
            span.append(kg.nodes[pnode]["name"]);
	    span.setAttribute('onclick', 'filter_results("paths","'+pnode+'");');
	    span.dataset.curie = pnode;
	    div.append(span);

	    div.dataset.pnodes += "|"+pnode+"|";
	}

	span = document.createElement("span");
        span.className = 'filtertag p0';
        span.title = "Target node";
        span.append(kg.nodes[path_end]["name"]);
        div.append(span);


	var cnf = 'n/a';
        if (Number(ranal.score))
            cnf = Number(ranal.score).toFixed(3);
        var pcl = (cnf>=0.9) ? "p9" : (cnf>=0.7) ? "p7" : (cnf>=0.5) ? "p5" : (cnf>=0.3) ? "p3" : (cnf>0.0) ? "p1" : "p0";

        var rsrc = 'n/a';
        if (ranal.resource_id)
            rsrc = ranal.resource_id;
        else if (ranal.reasoner_id)
            rsrc = ranal.reasoner_id;

        var rscl = get_css_class_from_reasoner(rsrc);

        var span100 = document.createElement("span");
        span100.style.float = 'right';
        span100.style.marginRight = '70px';

        var span = document.createElement("span");
        span.className = pcl+' qprob';
        span.title = "score = "+cnf;
        span.append(cnf);
        span100.append(span);

        span = document.createElement("span");
        span.className = rscl+' qprob';
        span.title = "source = "+rsrc;
        span.append(rsrc.replace("infores:",""));
        span100.append(span);

	div.append(span100);

        results_fragment.append(div);

        div = document.createElement("div");
        div.id = 'a'+num+'_div';
        div.className = 'panel';

        var table = document.createElement("table");
        table.className = 't100';

        add_graph_to_table(table,num);

        div.append(table);
        results_fragment.append(div);
    }

    document.getElementById("result_container").append(results_fragment);

    var num = 1;
    for (let pnode of Object.keys(all_nodes).sort(function(a, b) { return all_nodes[a]['total'] > all_nodes[b]['total'] ? -1 : 1; }))
        add_to_summary([kg.nodes[pnode]["name"], pnode,
			//all_nodes[pnode]]
			"<a title='display all paths that contain this node' href='javascript:filter_results(\"paths\", \""+pnode+"\",true)'>"+all_nodes[pnode]['total']+"</a>"]
		       ,num++);


    document.getElementById("pathfilterstatus").innerHTML = '';
    document.getElementById("pathfilterstatus").append(result.analyses.length+' total analyses  (Click on the node bubbles below to set/remove filters)');
    filter_results("paths");
}

function filter_results(which, what="CURRENT", only=false) {
    var fstat_node = document.getElementById("pathfilterstatus");
    fstat_node.innerHTML = '';

    if (event)
	event.stopPropagation();
    else
	openSection('results');

    var wait = getAnimatedWaitBar("100px");
    wait.style.marginRight = "10px";
    fstat_node.append(wait);
    fstat_node.append('Filtering...');
    window.scrollTo(0,0);

    var timeout = setTimeout(function() {
	var howmany = filter_paths(what, only);

	fstat_node.innerHTML = '';
	fstat_node.append('Displaying '+howmany+' analyses');

	if (UIstate["curiefilter"].length == 0)
	    fstat_node.append(' (all)');
	else
	    fstat_node.append(display_pathfilter());
	display_filterbar();

	var span = document.createElement("span");
	//span.className = 'filterbutton';
	span.className = 'questionBox button';
	span.style.marginLeft = '15px';
	span.title = "Show all filter-nodes";
	span.append('Node Filters');
	span.setAttribute('onclick', 'display_qg_popup("filters");');
	fstat_node.append(span);

    }, 150 );  // give it time so animation can start

}

function display_filternodes(howmany=null) {
    document.getElementById('nodefilter_div').style.gridTemplateRows = 'repeat('+Math.ceil(Object.keys(all_nodes).length/5)+', auto)';
    for (let fnode of Object.keys(all_nodes).sort((a, b) => all_nodes[a]['name'].localeCompare(all_nodes[b]['name'], 'en', {'sensitivity': 'base'}))) {
	let htmlnode;
	if (document.getElementById("nodefilter_"+fnode))
	    htmlnode = document.getElementById("nodefilter_"+fnode);
	else {
	    htmlnode = document.createElement("span");
	    htmlnode.id = "nodefilter_"+fnode;
	    document.getElementById('nodefilter_div').append(htmlnode);
	}
	htmlnode.innerHTML = '';

        var count = document.createElement("span");
	count.style.float = 'right';
        count.className = 'filtertag';
        count.style.padding = '0px 4px';
        count.style.border = '0';

	if (UIstate["curiefilter"].includes("X::"+fnode)) {
            count.className = 'filtertag p3';
	    htmlnode.className = 'filterbutton p1';
            htmlnode.title = "Remove this filter";
            htmlnode.setAttribute('onclick', 'filter_paths("'+"X::"+fnode+'", false, false);');
	}
	else if (UIstate["curiefilter"].includes(fnode)) {
            count.className = 'filtertag p7';
	    htmlnode.className = 'filterbutton p9';
            htmlnode.title = "Remove this filter";
            htmlnode.setAttribute('onclick', 'filter_paths("'+fnode+'", false, false);');
	}
	else {
	    htmlnode.className = 'filtertag simp';
	    htmlnode.setAttribute('onclick', '');

	    var minus = document.createElement("span");
            minus.className = 'filtertag simp';
            minus.style.float = 'right';
            minus.style.padding = '0px 4px';
            minus.style.border = '0';
            minus.title = "filter inactive";
            //minus.innerHTML = '&minus;';
            minus.innerHTML = '&times;';
	    htmlnode.append(minus);

	    var check = document.createElement("span");
	    check.className = 'filtertag simp';
	    check.style.float = 'right';
            check.style.padding = '0px 4px';
            check.style.border = '0';
            check.title = "filter inactive";
            check.append('+');
	    htmlnode.append(check);

	    if (all_nodes[fnode]['filtered'] > 0) {
		htmlnode.className = 'filtertag';
		minus.className = 'filterbutton p1';
		minus.title = "EXCLUDE paths with this node";
		check.className = 'filterbutton p9';
		check.title = "Add this filter";
		minus.setAttribute('onclick', 'filter_paths("X::'+fnode+'", false, false);');
		check.setAttribute('onclick', 'filter_paths("'+fnode+'", false, false);');
	    }
	    else {
		count.className = 'filtertag simp';
		count.style.color = '#98afc7';
	    }
	}

	count.append(all_nodes[fnode]['filtered']);
        htmlnode.append(count);

	htmlnode.append(all_nodes[fnode]['name']);
    }

    if (howmany!=null)
	document.getElementById("nodefilterbutton").value = "View " + howmany + " Results";
}


function display_pathfilter() {
    var filterspan = document.createElement("span");
    filterspan.append('. Filters (click to remove) : ');

    for (var fcur of UIstate["curiefilter"]) {
	var span = document.createElement("span");
        if (fcur.startsWith("X::")) {
            span.className = 'filterbutton p1';
            span.append(all_nodes[fcur.replace("X::","")]['name']);
	}
	else {
            span.className = 'filterbutton p9';
            span.append(all_nodes[fcur]['name']);
	}
        span.title = "Remove this filter";
        span.setAttribute('onclick', 'filter_results("paths","'+fcur+'");');
	filterspan.append(span);
    }
    return filterspan;
}


function display_filterbar(howmany=4000) {
    var filterbar = document.getElementById("filter_nodelist");
    filterbar.innerHTML = '';

    var num = 0;
    for (let pnode of Object.keys(all_nodes).sort(function(a, b) { return all_nodes[a]['filtered'] > all_nodes[b]['filtered'] ? -1 : 1; })) {
	if (UIstate["curiefilter"].includes(pnode))
	    continue;
        if ((num++ == howmany) || (all_nodes[pnode]['filtered'] == 0))
	    break;

	var fnode = document.createElement("a");
	fnode.className = 'hoverable';
	fnode.href = "javascript:filter_results(\"paths\", \""+pnode+"\")";
	fnode.title = pnode;
        fnode.append(all_nodes[pnode]['name']+" ("+all_nodes[pnode]['filtered']+")");
	filterbar.append(fnode);
	filterbar.append(document.createElement("br"));
    }
    if (num > 0) {
	document.getElementById("filter_container").style.display = 'block';
	document.getElementById("result_container").style.marginLeft = '240px';
    }
    else {
	document.getElementById("filter_container").style.display = 'none';
	document.getElementById("result_container").style.marginLeft = '';
    }
}


function cancel_filter_paths() {
    if ('curiefilter_prev' in UIstate) {
	UIstate["curiefilter"] = UIstate["curiefilter_prev"].slice();
	delete UIstate["curiefilter_prev"];
    }
    filter_paths("CURRENT",false, false);
}

function filter_paths(curie="CURRENT",only=false, display=true) {
    if (event)
        event.stopPropagation();

    if (display)
	delete UIstate["curiefilter_prev"];
    else if (!('curiefilter_prev' in UIstate))
	UIstate["curiefilter_prev"] = UIstate["curiefilter"].slice(); // creates a new array

    if (only)
	UIstate["curiefilter"] = [];
    if (UIstate["curiefilter"].includes(curie))
	UIstate["curiefilter"].splice(UIstate["curiefilter"].indexOf(curie),1);
    else if (curie != "CURRENT")
	UIstate["curiefilter"].push(curie);

    for (var pnode in all_nodes)
        all_nodes[pnode]['filtered'] = 0;

    var showing = 0;
    for (var pathhead of document.querySelectorAll('[id^="pathdivhead_"]')) {
	var showit = true;

        for (var curiefilter of UIstate["curiefilter"]) {

            if (curiefilter.startsWith("X::")) {
		if (pathhead.dataset.pnodes.includes("|"+curiefilter.replace("X::","")+"|")) {
                    showit = false;
                    break;
		}
	    }
	    else if (!pathhead.dataset.pnodes.includes("|"+curiefilter+"|")) {
		showit = false;
		break;
	    }
	}

	if (showit) {
	    showing++;
	    if (display)
		pathhead.style.display = '';
            for (var curielabel of pathhead.children) {
                if (curielabel.dataset && curielabel.dataset.curie) {
                    all_nodes[curielabel.dataset.curie]['filtered']++;

		    if (display) {
			if (UIstate["curiefilter"].includes(curielabel.dataset.curie))
			    curielabel.classList.add('p9');
			else
			    curielabel.classList.remove('p9');
		    }
		}
	    }
	}
	else if (display) {
	    if (pathhead.classList.contains('openaccordion'))
		pathhead.click();
	    pathhead.style.display = 'none';
	}
    }

    display_filternodes(showing);

    return showing;
}

function get_node_list_in_paths(path_bindings,kg,aux) {
    var pathnodes = {};
    for (var pb in path_bindings) {
	for (var path in path_bindings[pb]) {
	    for (var edgeid of aux[path_bindings[pb][path]["id"]]["edges"]) {
		pathnodes[kg.edges[edgeid]["subject"]] = 1;
		pathnodes[kg.edges[edgeid]["object"]] = 1;
	    }
	}
    }

    return Object.keys(pathnodes);
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

function process_results(reslist,kg,aux,trapi,mainreasoner) {
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
		ess = kg.nodes[ess].name ? kg.nodes[ess].name : kg.nodes[ess].id;
	}

	var cnf = 'n/a';
	var maxcnf = 1;
	if (Number(result.normalized_score)) {
	    cnf = Number(result.normalized_score).toFixed(3);
	    maxcnf = 100;
	}
	else if (Number(result.score))
	    cnf = Number(result.score).toFixed(3);
	else if (Number(result.confidence))
	    cnf = Number(result.confidence).toFixed(3);
        else if (result.analyses && result.analyses.length > 0) {
	    var maxscore = -1;
	    for (var ranal in result.analyses) {
                if (Number(result.analyses[ranal].score) && Number(result.analyses[ranal].score) > maxscore)
		    maxscore = Number(result.analyses[ranal].score).toFixed(3);
	    }
	    if (maxscore >= 0)
		cnf = maxscore;
	}
	var pcl = (cnf>=0.9*maxcnf) ? "p9" : (cnf>=0.7*maxcnf) ? "p7" : (cnf>=0.5*maxcnf) ? "p5" : (cnf>=0.3*maxcnf) ? "p3" : (cnf>0.0) ? "p1" : "p0";

        if (result.row_data)
            add_to_summary(result.row_data, num);
	else
            add_to_summary([cnf,ess], num);

	// avoid madness
	if (num > UIstate["maxresults"]) continue;

	var rsrc = mainreasoner;
	if (result.resource_id)
	    rsrc = result.resource_id;
	else if (result.reasoner_id)
	    rsrc = result.reasoner_id;
	var rscl = get_css_class_from_reasoner(rsrc);

	if (rsrc=="ARAX")
	    add_to_score_histogram(cnf);

	var div = document.createElement("div");
        div.id = 'h'+num+'_div';
	div.title = 'Click to expand / collapse result '+num;
        div.className = 'accordion';
	div.setAttribute('onclick', 'add_cyto('+num+',"R'+num+'A0");sesame(this,a'+num+'_div);');
	div.append("Result "+num);
	if (ess)
	    div.innerHTML += " :: <b>"+ess+"</b>"; // meh...

	var span100 = document.createElement("span");
	span100.className = 'r100';

        var span = document.createElement("span");
        span.className = pcl+' qprob';
	span.title = "score="+cnf;
	if (maxcnf == 100) {
            span.className += ' cytograph_controls';
            span.title = "NORMALIZED "+span.title;
	}
        span.append(cnf);
	span100.append(span);

        span = document.createElement("span");
	span.className = rscl+' qprob';
	span.title = "source="+rsrc;
	span.append(rsrc);
	span100.append(span);

	div.append(span100);
	results_fragment.append(div);

        div = document.createElement("div");
        div.id = 'a'+num+'_div';
        div.className = 'panel';

        var table = document.createElement("table");
        table.className = 't100';

        cytodata['R'+num+'A0'] = [];
        var tr,td,link;
	var ranal = -1;

	if (result.analyses && result.analyses.length > 0) {
            for (var ranal in result.analyses) {
		cytodata['R'+num+'A'+ranal] = [];

		tr = document.createElement("tr");
		td = document.createElement("td");
		td.className = 'cytograph_controls';
		td.colSpan = "2";
		td.style.paddingLeft = "40px";
                td.append(" Analysis "+ranal+" :: ");

		link = document.createElement("a");
		link.style.fontWeight = "bold";
		link.style.fontSize = "larger";
		link.style.marginRight = "20px";
		link.title = 'View Main Result Graph';
		link.setAttribute('onclick', 'add_cyto('+num+',"R'+num+'A'+ranal+'");');
		link.append("Result Graph");
		td.append(link);

                if (result.analyses[ranal].support_graphs && result.analyses[ranal].support_graphs.length > 0) {
		    td.append(" Analysis Support Graphs: ");

		    for (var sg in result.analyses[ranal].support_graphs) {
			link = document.createElement("a");
			link.style.fontWeight = "bold";
			link.style.fontSize = "larger";
			link.style.marginLeft = "20px";
			var sgid = result.analyses[ranal].support_graphs[sg];
			link.title = 'Graph ID: '+ sgid;
			link.setAttribute('onclick', 'add_cyto('+num+',"AUX'+sgid+'");');
			link.append(Number(sg)+1);
			td.append(link);
		    }
		}
		else {
                    td.append(" No Analysis Support Graphs found");
		}

                var cnf = 'n/a';
		if (Number(result.analyses[ranal].score))
		    cnf = Number(result.analyses[ranal].score).toFixed(3);
		var pcl = (cnf>=0.9) ? "p9" : (cnf>=0.7) ? "p7" : (cnf>=0.5) ? "p5" : (cnf>=0.3) ? "p3" : (cnf>0.0) ? "p1" : "p0";

		var rsrc = 'n/a';
		if (result.analyses[ranal].resource_id)
		    rsrc = result.analyses[ranal].resource_id;
		else if (result.analyses[ranal].reasoner_id)
		    rsrc = result.analyses[ranal].reasoner_id;

		var rscl = get_css_class_from_reasoner(rsrc);

		var span100 = document.createElement("span");
		span100.style.float = 'right';
		span100.style.marginRight = '70px';
		span100.style.marginTop = '5px';

                var span = document.createElement("span");
		span.className = pcl+' qprob';
		span.title = "score = "+cnf;
		span.append(cnf);
		span100.append(span);

		span = document.createElement("span");
		span.className = rscl+' qprob';
		span.title = "source = "+rsrc;
		span.append(rsrc.replace("infores:",""));
		span100.append(span);

		//td = document.createElement("td");
		td.append(span100);

		tr.append(td);
		table.append(tr);
	    }
	}

	add_graph_to_table(table,num);

	div.append(table);
	results_fragment.append(div);

	//console.log("=================== CYTO num:"+num+"  #nb:"+result.node_bindings.length);

        for (var nbid in result.node_bindings) {
            for (var node of result.node_bindings[nbid]) {
		var kmne = Object.create(kg.nodes[node.id]);
		kmne.parentdivnum = num;
		kmne.trapiversion = trapi;
		kmne.id = node.id;
		if (node.attributes)
		    kmne.node_binding_attributes = node.attributes;
		else if (node.detail_lookup)
		    kmne.node_binding_attributes_lookup_key = node.detail_lookup;
		var tmpdata = { "data" : kmne };

		if (ranal >= 0) {
		    for (var rraa in result.analyses)
			cytodata['R'+num+'A'+rraa].push(tmpdata);
		}
		else
		    cytodata['R'+num+'A0'].push(tmpdata);
	    }
	}

	//FIXed? for multiple result.analyses...
	var full_edge_bindings_collection = [];
	if (ranal >= 0) {
	    for (var rraa in result.analyses)
		full_edge_bindings_collection[rraa] = result.analyses[rraa].edge_bindings;
	}
	else
	    full_edge_bindings_collection[0] = result.edge_bindings;

        for (var ebcidx in full_edge_bindings_collection) {
	    for (var ebid in full_edge_bindings_collection[ebcidx]) {
		for (var edge of full_edge_bindings_collection[ebcidx][ebid]) {

		    // console.log("ebcidx:"+ebcidx+"  ebid:"+ebid+"  edge:"+JSON.stringify(edge));
		    if (!(edge.id in kg.edges))
			throw Error("Result graph edge not defined in KG: "+edge.id);

		    var kmne = Object.create(kg.edges[edge.id]);
		    kmne.parentdivnum = num;
		    kmne.trapiversion = trapi;
		    kmne.id = edge.id;
		    kmne.source = kmne.subject;
		    kmne.target = kmne.object;
		    if (kmne.predicate)
			kmne.type = kmne.predicate;
		    if (kmne.qualifiers && kmne.qualifiers.length == 0)
			kmne.qualifiers = null;
		    if (edge.attributes)
			kmne.edge_binding_attributes = edge.attributes;
                    else if (edge.detail_lookup)
			kmne.edge_binding_attributes_lookup_key = edge.detail_lookup;

		    // confirm...
		    if (kmne.has_these_support_graphs && kmne.has_these_support_graphs.length > 0) {
			kmne.__has_sgs = true;
			for (var sgid of kmne.has_these_support_graphs) {
			    if (!(sgid in aux))
				throw Error("Aux graph not found: "+sgid);

			    add_aux_graph(kg,sgid,aux[sgid]["edges"],num,trapi);
			}
		    }
		    else if (kmne.attributes) {
			for (var att of kmne.attributes) {
			    if (att.attribute_type_id == "biolink:support_graphs" && att.value && att.value.length > 0) {
				kmne.__has_sgs = true;
				for (var sgid of att.value)
				    add_aux_graph(kg,sgid,aux[sgid]["edges"],num,trapi);
			    }
			}
		    }

		    var tmpdata = { "data" : kmne };
		    cytodata['R'+num+'A'+ebcidx].push(tmpdata);
		}
	    }
	}

	//FIX THIS for multiple result.analyses...
	if (result.analyses && result.analyses[0] && result.analyses[0].support_graphs && result.analyses[0].support_graphs.length > 0) {
            for (var sg in result.analyses[0].support_graphs) {
		var sgid = result.analyses[0].support_graphs[sg];
		add_aux_graph(kg,sgid,aux[sgid]["edges"],num,trapi);
	    }
	}

    }

    document.getElementById("result_container").append(results_fragment);
}

function add_aux_graph(kg,sgid,auxedges,parentnum,trapi) {
    cytodata['AUX'+sgid] = [];
    var nodes = {};

    for (var edgeid of auxedges) {
	if (!(edgeid in kg.edges))
	    throw Error("AUX graph edge not defined in KG: "+edgeid);

	var kmne = Object.create(kg.edges[edgeid]);
	kmne.parentdivnum = parentnum;
	kmne.trapiversion = trapi;
	kmne.id = edgeid;
	kmne.source = kmne.subject;
	kmne.target = kmne.object;
	nodes[kmne.subject] = 1;
	nodes[kmne.object] = 1;
	if (kmne.predicate)
	    kmne.type = kmne.predicate;
	if (kmne.qualifiers && kmne.qualifiers.length == 0)
	    kmne.qualifiers = null;
	//if (edge.attributes)
	//kmne.edge_binding_attributes = edge.attributes;
	var tmpdata = { "data" : kmne };
	cytodata['AUX'+sgid].push(tmpdata);
    }

    for (var nodeid in nodes) {
        //console.log("---- aux node::"+nodeid);
	var kmne = Object.create(kg.nodes[nodeid]);
	kmne.parentdivnum = parentnum;
	kmne.trapiversion = trapi;
	kmne.id = nodeid;
	//if (node.attributes)
	//kmne.node_binding_attributes = node.attributes;
	var tmpdata = { "data" : kmne };
	cytodata['AUX'+sgid].push(tmpdata);
    }
}


function get_css_class_from_reasoner(r) {
    try {
	if (r.toUpperCase().includes("IMPROVING"))
	    return "simp";
	if (r.toUpperCase().includes("UNSECRET"))
	    return "suns";
	if (r.toUpperCase().includes("MOLEPRO"))
	    return "smol";
	if (r.toUpperCase().includes("ROBOKOP"))
	    return "srob";
	if (r.toUpperCase().includes("ARAGORN"))
	    return "sara";
	if (r.toUpperCase().includes("INDIGO"))
	    return "sind";
	if (r.toUpperCase().includes("GENETICS"))
	    return "sgen";
	if (r.toUpperCase().includes("COHD"))
	    return "scod";
	if (r.toUpperCase().includes("ARAX") ||
	    r.toUpperCase().includes("RTX"))
	    return "srtx";
	if (r.toUpperCase().includes("BTE") ||
	    r.toUpperCase().includes("BIOTHINGS"))
	    return"sbte";
	if (r.toUpperCase().includes("CAM"))
	    return "scam";
	if (r.toUpperCase().includes("CHP"))
	    return "schp";
    }
    catch(e) {}
    return "p0";
}


function add_graph_to_table(table,num) {
    var tr = document.createElement("tr");
    var td = document.createElement("td");
    td.className = 'cytograph_controls';

    var link = document.createElement("a");
    link.title = 'reset zoom and center';
    link.setAttribute('onclick', 'cyobj['+num+'].reset();');
    link.append("\u21BB");
    td.append(link);
    td.append(document.createElement("br"));
    tr.append(td);

    link = document.createElement("a");
    link.title = 'breadthfirst layout';
    link.setAttribute('onclick', 'cylayout('+num+',"breadthfirst");');
    link.append("B");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'force-directed layout';
    link.setAttribute('onclick', 'cylayout('+num+',"cose");');
    link.append("F");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'circle layout';
    link.setAttribute('onclick', 'cylayout('+num+',"circle");');
    link.append("C");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'grid layout';
    link.setAttribute('onclick', 'cylayout('+num+',"grid");');
    link.append("G");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.style.marginTop = "40px";
    link.title = 'small graph';
    link.setAttribute('onclick', 'cyresize('+num+',"s");');
    link.append("s");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'medium-sized graph';
    link.setAttribute('onclick', 'cyresize('+num+',"m");');
    link.append("M");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.style.fontWeight = "bold";
    link.style.fontSize = "larger";
    link.title = 'Large graph';
    link.setAttribute('onclick', 'cyresize('+num+',"L");');
    link.append("L");
    td.append(link);
    td.append(document.createElement("br"));

    if (!window.chrome) {
	link = document.createElement("a");
	link.style.marginTop = "40px";
	link.title = 'collapse edges';
	link.setAttribute('onclick', 'cyedges('+num+',"collapse");');
	link.append("c");
	td.append(link);
	td.append(document.createElement("br"));

	link = document.createElement("a");
	link.title = 'expand edges';
	link.setAttribute('onclick', 'cyedges('+num+',"expand");');
	link.append("E");
	td.append(link);
	td.append(document.createElement("br"));
    }

    link = document.createElement("span");
    link.className = "explevel msgINFO";
    link.style.display = "inline-block";
    link.style.marginTop = "30px";
    link.append('New!');
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'export PNG image of this view';
    link.setAttribute('onclick', 'downloadCyto('+num+',"png");');
    link.append("P");
    td.append(link);
    td.append(document.createElement("br"));

    link = document.createElement("a");
    link.title = 'export JSON file of this network for import into Cytoscape';
    link.setAttribute('onclick', 'downloadCyto('+num+',"json");');
    link.append("J");
    td.append(link);
    td.append(document.createElement("br"));


    tr.append(td);

    td = document.createElement("td");
    td.className = 'cytograph';
    var div = document.createElement("div");
    div.id = 'cy'+num;
    div.style.height = '100%';
    div.style.width  = '100%';
    td.append(div);
    tr.append(td);
    table.append(tr);

    tr = document.createElement("tr");

    td = document.createElement("td");
    td.colSpan = '2';
    div = document.createElement("div");
    div.id = 'd'+num+'_div';
    div.className = 'panel';
    link = document.createElement("i");
    link.append("Click on a node or edge to get details, or click on graph background to see a full list of nodes and edges for this result");
    div.append(link);

    td.append(div);
    tr.append(td);

    table.append(tr);
}



function add_cyto(i,dataid, layout='breadthfirst') {
    // once rendered, data is set to null so as to only do this once per graph
    // //////if (cytodata[i] == null) return;

    var num = Number(i);// + 1;

    //console.log("---------------cyto i="+i);
    cyobj[i] = cytoscape({
	container: document.getElementById('cy'+num),
	style: cytoscape.stylesheet()
	    .selector('node')
	    .css({
		'background-image': function(ele) { return mapNodeIcon(ele); } ,
		'background-fit': 'contain',
		'background-opacity': '0',
		'shape': 'rectangle',
		'width': '40',
		'height': '40',
		'content': function(ele) { return ele.data().idname ? ele.data().idname : ele.data().name ? ele.data().name : ele.data().id; }
	    })
	    .selector('edge')
	    .css({
		'curve-style' : 'bezier',
		'font-size' : '12',
		'line-color': function(ele) { return mapEdgeColor(ele,num); } ,
		'line-style': function(ele) { return mapEdgeLineStyle(ele); } ,
		'width': function(ele) { if (ele.data().weight) { return ele.data().weight; } return 2; },
		'target-arrow-color': function(ele) { return mapEdgeColor(ele,num); } ,
		'target-arrow-shape': 'triangle',
		'opacity': 0.8,
		'content': function(ele) {
		    if ((ele.data().parentdivnum > 0) && ele.data().type) {
			var types = '';
			types += ele.data().qualifiers ? ' [q]' : '';
			types += ele.data().__has_sgs ? ' [sg]' : '';
			return ele.data().type + types;
		    }
		    return '';
		}
	    })
            .selector('edge.cy-expand-collapse-collapsed-edge')
            .css({
		"text-outline-color": "#ffffff",
		"text-outline-width": "2px",
		'label': (ele) => {
		    return '(' + ele.data('collapsedEdges').length + ')';
		},
		'width': function (ele) {
		    const n = ele.data('collapsedEdges').length;
		    //return n + 'px';
		    return (1 + Math.log2(n)) + 'px';
		},
                'line-color': '#aaa',
		'line-style': 'dashed'
            })
	    .selector(':selected')
	    .css({
		'background-color': '#ff0',
		'border-color': '#f80',
		'border-width' : '2',
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

	elements: cytodata[dataid],

	wheelSensitivity: 0.2,

	layout: {
	    name: layout,
	    padding: 10
	},

	ready: function() {
	    // ready 1
	}
    });
    if (!window.chrome)
	cyobj[i].expandCollapse();

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

    cyobj[i].on('tap', function(evt, forcetextgraph=false) {
	if (evt.target === cyobj[i] || forcetextgraph) {
            var div = document.getElementById('d'+i+'_div');
	    div.innerHTML = "";

	    var ne_table = document.createElement("table");
	    var tr = document.createElement("tr");
	    var td = document.createElement("td");
	    td.colSpan = '3';
	    td.append("All nodes and edges:");
	    tr.append(td);
	    ne_table.append(tr);

	    var allnodes = cyobj[i].nodes();
	    for (var n = 0; n < allnodes.length; n++) {
		tr = document.createElement("tr");
		td = document.createElement("td");
		td.colSpan = '3';
		td.append(document.createElement("hr"));
		tr.append(td);
		ne_table.append(tr);

		tr = document.createElement("tr");
		td = document.createElement("td");

                var link = document.createElement("a");
                link.className = "attvalue";
                link.style.cursor = "pointer";
		link.dataset.nn = allnodes[n].id();
		link.title = 'View node details';
		link.onclick = function () {
		    cyobj[i].getElementById(this.dataset.nn).emit("tap");
		    cyobj[i].getElementById(this.dataset.nn).select();
		};
		link.append(allnodes[n].data('id'));
		td.append(link);

		tr.append(td);
		td = document.createElement("td");
                td.colSpan = '2';
		td.style.paddingLeft = "15px";
		td.style.fontStyle = "italic";
		if (allnodes[n].data('name') != null)
		    td.append(' '+allnodes[n].data('name'));
		tr.append(td);
		ne_table.append(tr);

		var nodedges = cyobj[i].edges('[source = "'+allnodes[n].data("id")+'"]');
		for (var e = 0; e < nodedges.length; e++) {
		    tr = document.createElement("tr");
		    td = document.createElement("td");
		    tr.append(td);
		    td = document.createElement("td");
                    var link = document.createElement("a");
		    link.style.cursor = "pointer";
		    link.dataset.ee = nodedges[e].id();

		    if (nodedges[e].data('collapsedEdges')) {
			link.append(nodedges[e].data('collapsedEdges').length + " edges");
			link.onclick = function () {
			    cyobj[i].getElementById(this.dataset.ee).emit("tap");
			    cyobj[i].emit("tap", [true]);
			};
		    }
		    else {
			link.append(nodedges[e].data('predicate'));
			link.onclick = function () {
			    cyobj[i].getElementById(this.dataset.ee).emit("tap");
			    cyobj[i].getElementById(this.dataset.ee).select();
			};
		    }

		    if (nodedges[e].data('__has_sgs'))
			link.append(' [sg]');
		    if (nodedges[e].data('qualifiers')) {
			link.append(' [q]');
			link.title = 'View QUALIFIED edge details';
		    }
		    else
			link.title = 'View edge details';
		    td.append(link);
		    td.append(" \u{1F87A} ");
		    tr.append(td);
		    td = document.createElement("td");
		    td.append(nodedges[e].data('target'));
		    tr.append(td);
		    ne_table.append(tr);
		}

		nodedges = cyobj[i].edges('[target = "'+allnodes[n].data("id")+'"]');
		for (var e = 0; e < nodedges.length; e++) {
		    tr = document.createElement("tr");
		    td = document.createElement("td");
		    tr.append(td);
		    td = document.createElement("td");
		    td.append(" \u{1F878} ");
                    var link = document.createElement("a");
		    link.style.cursor = "pointer";
		    link.dataset.ee = nodedges[e].id();

                    if (nodedges[e].data('collapsedEdges')) {
                        link.append(nodedges[e].data('collapsedEdges').length + " edges");
                        link.onclick = function () {
                            cyobj[i].getElementById(this.dataset.ee).emit("tap");
                            cyobj[i].emit("tap", [true]);
                        };
                    }
                    else {
                        link.append(nodedges[e].data('predicate'));
			link.onclick = function () {
			    cyobj[i].getElementById(this.dataset.ee).emit("tap");
			    cyobj[i].getElementById(this.dataset.ee).select();
			};
		    }

                    if (nodedges[e].data('__has_sgs'))
			link.append(' [sg]');
		    if (nodedges[e].data('qualifiers')) {
			link.append(' [q]');
			link.title = 'View QUALIFIED edge details';
		    }
		    else
			link.title = 'View edge details';
		    td.append(link);
		    tr.append(td);
		    td = document.createElement("td");
		    td.append(nodedges[e].data('source'));
		    tr.append(td);
		    ne_table.append(tr);
		}
	    }

	    div.append(ne_table);
	    sesame('openmax',document.getElementById('a'+i+'_div'));
	}
    });


    cyobj[i].on('tap','node', function() {
	var div = document.getElementById('d'+this.data('parentdivnum')+'_div');
	div.innerHTML = "";

	var span = document.createElement("span");
	span.style.float = "right";
	span.style.fontStyle = "italic";
	span.append("Click on graph background to see a full list of nodes and edges");
	div.append(span);

	var fields = [ "name","id","categories" ];
	for (var field of fields) {
	    if (this.data(field) == null) continue;

	    var span = document.createElement("span");
	    span.className = "fieldname";
	    span.append(field+": ");
	    div.append(span);

            var a = document.createElement("a");
	    a.title = 'view ARAX synonyms';
	    a.href = "javascript:lookup_synonym('"+this.data(field)+"',true)";
	    a.innerHTML = this.data(field);
	    div.append(a);

	    div.append(document.createElement("br"));
	}


	if (this.data('attributes'))
	    show_attributes(i,div, this.data('attributes'),null,"value");
	else if (this.data('detail_lookup'))
	    retrieve_attributes(i,div, this,null,"value");


	if (this.data('node_binding_attributes')) {
	    div.append(document.createElement("br"));
	    show_attributes(i,div, this.data('node_binding_attributes'),"Node Binding Attributes:","value");
	}

	sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
    });

    cyobj[i].on('tap','edge', function() {
	if (this.data('collapsedEdges')) {
	    var api = cyobj[i].expandCollapse('get');
	    api.expandEdges(this);
	    return;
	}

	var div = document.getElementById('d'+this.data('parentdivnum')+'_div');
	div.innerHTML = "";

	var span = document.createElement("span");
	span.style.float = "right";
	span.style.fontStyle = "italic";
	span.append("Click on graph background to see a full list of nodes and edges");
	div.append(span);

	var a = document.createElement("a");
	a.className = 'attvalue';
	a.title = 'view ARAX synonyms';
	a.href = "javascript:lookup_synonym('"+this.data('source')+"',true)";
	a.innerHTML = this.data('source');
	div.append(a);

        var span = document.createElement("span");
	span.className = 'attvalue';
        span.append("----");
	span.append(this.data('predicate'));
        span.append("----");
        div.append(span);

        a = document.createElement("a");
	a.className = 'attvalue';
        a.style.marginRight = "20px";
	a.title = 'view ARAX synonyms';
	a.href = "javascript:lookup_synonym('"+this.data('target')+"',true)";
	a.innerHTML = this.data('target');
	div.append(a);

	UIstate["edgesg"] = 0;
        span = document.createElement("span");
	if (!this.data('__has_sgs'))
	    span.style.display = 'none';
	span.id = 'd'+this.data('parentdivnum')+'_div_edge';
	span.append(" Edge Support Graphs: ");
        div.append(span);

	div.append(document.createElement("br"));

	var fields = [ "relation","id" ];
	for (var field of fields) {
	    if (this.data(field) == null) continue;

	    span = document.createElement("span");
	    span.className = "fieldname";
	    span.append(field+": ");
	    div.append(span);
	    if (this.data(field).toString().startsWith("http")) {
		var link = document.createElement("a");
		link.href = this.data(field);
		link.target = "_blank";
		link.append(this.data(field));
		div.append(link);
	    }
	    else {
		div.append(this.data(field));
	    }
	    div.append(document.createElement("br"));
	}

	show_qualifiers(div,
			this.data('qualifiers'),
			this.data('source'),
			cyobj[i].nodes("[id='"+this.data('source')+"']").data('name'),
			this.data('predicate'),
			this.data('target'),
			cyobj[i].nodes("[id='"+this.data('target')+"']").data('name')
		       );


        if (this.data('attributes')) {
	    show_attributes(i,div, this.data('attributes'),null,"value");
	    if (this.data('sources')) {
		div.append(document.createElement("br"));
		show_attributes(i,div, this.data('sources'),"Edge Sources:","resource_id");
		//show_attributes(i,div, this.data('sources'),"Edge Sources:","upstream_resource_ids");
	    }
	}
	else if (this.data('detail_lookup'))
	    retrieve_attributes(i,div, this,null,"value");


	if (this.data('edge_binding_attributes')) {
            div.append(document.createElement("br"));
            show_attributes(i,div, this.data('edge_binding_attributes'),"Edge Binding Attributes:","value");
	}

	sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
    });
    // //////cytodata[i] = null;
}


function show_qualifiers(html_div, quals, subj, sname, pred, obj, oname) {
    if (quals == null)
	return;

    var qtable = document.createElement("table");
    qtable.className = 'numold explevel';
    var row = document.createElement("tr");
    var cell = document.createElement("td");
    cell.className = 'attvalue';
    cell.colSpan = '2';
    cell.append("Qualified Statement");
    row.append(cell);
    qtable.append(row);

    var qsentence = document.createElement("span");
    qsentence.className = 'explevel attvalue p9';

    var orderedquals = [
	'subject_direction_qualifier',
	'subject_aspect_qualifier',
	'subject',
	'subject_context_qualifier',
	'qualified_predicate',
	'predicate',
	'mechanism_qualifier',
	'object_direction_qualifier',
	'object_aspect_qualifier',
	'object',
	'object_context_qualifier',
	'pathway_context_qualifier'
    ];

    var hadsubjq = false;
    var hadqpred = false;
    for (var oq of orderedquals) {
	var hasdup = false;
	var qual = quals.filter(a => a.qualifier_type_id == "biolink:"+oq);
	if (oq != 'subject' && oq != 'object' && oq != 'predicate' && qual[0] == null) {
	    //console.log("nothing found for: "+oq);
	    continue;
	}
	if (qual.length > 1) {
            console.error("duplicate value found for: "+oq);
	    hasdup = true;
	}

	var pretext = '';
	var postext = '';
	var celltext = '';
	var frag = document.createElement("span");
	frag.title = oq;
        if (oq == 'subject') {
	    frag.innerHTML = (hadsubjq ? 'of ' : '') + sname + " ";
	    celltext = subj;
	}
        else if (oq == 'object') {
	    frag.innerHTML = "of " + oname + " ";
	    celltext = obj;
	}
        else if (oq == 'predicate') {
	    if (hadqpred) continue;
	    frag.innerHTML = pred + " ";
	    celltext = pred;
	}
	else {
	    if (oq == 'subject_direction_qualifier' || oq == 'subject_aspect_qualifier')
		hadsubjq = true;
	    if (oq == 'qualified_predicate')
		hadqpred = true;
	    if (oq == 'mechanism_qualifier') {
		pretext = "(";
		postext = ")";
	    }
	    if (oq.includes('context_qualifier'))
		pretext = "in ";

	    frag.innerHTML = pretext + qual[0]['qualifier_value'] + postext + " ";
	    celltext = qual[0]['qualifier_value'];
	    if (hasdup)
		celltext += " ** has duplicate values!";
	}
	qsentence.append(frag);

	var row = document.createElement("tr");
	var cell = document.createElement("td");
        cell.style.fontWeight = "bold";
	cell.append(oq+":");
	row.append(cell);
	cell = document.createElement("td");
        cell.append(celltext);
	row.append(cell);
	qtable.append(row);
    }

    var addbar = true;
    for (var oqual of quals) {
	var qtid = oqual['qualifier_type_id'].replace("biolink:","");
	if (orderedquals.includes(qtid))
	    continue;

        var row = document.createElement("tr");
	var cell = document.createElement("td");
	cell.style.fontWeight = "bold";
	if (addbar) {
	    cell.colSpan = '2';
	    cell.append(document.createElement("hr"));
	    row.append(cell);
	    qtable.append(row);
	    addbar = false;
	    row = document.createElement("tr");
	    cell = document.createElement("td");
	    cell.style.fontWeight = "bold";
	}
        cell.append(oqual['qualifier_type_id']+":");
	row.append(cell);
	cell = document.createElement("td");
	cell.append(oqual['qualifier_value']);
	row.append(cell);
	qtable.append(row);
    }

    html_div.append(qsentence);
    html_div.append(qtable);
}


async function retrieve_attributes(num,html_div, cytobject, title, mainvalue) {
    if (!cytobject.data('detail_lookup'))
	return;

    var wait = getAnimatedWaitBar("100px");
    wait.style.marginTop = "20px";
    wait.style.marginBottom = "20px";
    html_div.append(wait);

    response = await fetch(providers["ARAX"].url + "/response/" + cytobject.data('detail_lookup'));
    var respjson = await response.json();

    if (respjson) {
	wait.remove();
	if (respjson.attributes) {
	    cytobject.data('attributes', respjson.attributes);
	    show_attributes(num,html_div, cytobject.data('attributes'),title,mainvalue);
	}
	if (respjson.sources) {
	    cytobject.data('sources', respjson.sources);
            html_div.append(document.createElement("br"));
            show_attributes(num,html_div, cytobject.data('sources'),"Edge Sources:","resource_id");
	}
	sesame('openmax',document.getElementById('a'+cytobject.data('parentdivnum')+'_div'));
    }
    else
	wait.remove();
}


function show_attributes(num,html_div, atts, title, mainvalue) {
    if (atts == null)
	return;

    var semmeddb_sentences = atts.filter(a => a.attribute_type_id == "biolink:supporting_text");

    // always display iri first
    var iri = atts.filter(a => a.attribute_type_id == "biolink:IriType");

    var atts_table = document.createElement("table");
    if (title) {
	atts_table.className = 'numold explevel';
	var row = document.createElement("tr");
	var cell = document.createElement("td");
        cell.className = 'attvalue';
	cell.colSpan = '2';
	cell.append(title);
	row.append(cell);
	atts_table.append(row);
    }

    for (var att of iri.concat(atts.filter(a => a.attribute_type_id != "biolink:IriType"))) {
	display_attribute(num,atts_table, att, semmeddb_sentences, mainvalue);
    }

    html_div.append(atts_table);
}

function display_attribute(num,tab, att, semmeddb, mainvalue) {
    var row = document.createElement("tr");
    var cell = document.createElement("td");

    cell.colSpan = '2';
    cell.append(document.createElement("hr"));
    row.append(cell);
    tab.append(row);

    var sub_atts = null;

    var value = null;
    var flagifmainvaluenull = true;
    for (var nom in att) {
	if (nom == mainvalue) {
	    value = att[nom];
	    continue;
	}
	else if (nom == "attributes") {
	    sub_atts = att[nom];
	    continue;
	}
	else if (att[nom] != null) {
	    row = document.createElement("tr");
	    cell = document.createElement("td");
	    cell.style.fontWeight = "bold";
            cell.append(nom+":");
	    row.append(cell);
            cell = document.createElement("td");

	    // handle all as arrays  (hope no objects creep in...)
	    if (!Array.isArray(att[nom]))
		att[nom] = [ att[nom] ];

	    var br = false;
	    for (var val of att[nom]) {
		if (br)
		    cell.append(document.createElement("br"));

		if (val == null)
		    cell.append("--NULL--");

		if (val.toString().startsWith("http")) {
		    var a = document.createElement("a");
		    a.target = '_blank';
		    a.href = val;
		    a.innerHTML = val;
		    cell.append(a);
		}
		else
		    cell.append(val);

		br = true;
	    }

	    row.append(cell);
	    tab.append(row);

	    if (att[nom] == "primary_knowledge_source")
		flagifmainvaluenull = false;
	}
    }

    row = document.createElement("tr");
    cell = document.createElement("td");
    cell.style.fontWeight = "bold";
    cell.append(mainvalue+":");
    row.append(cell);
    cell = document.createElement("td");
    cell.style.overflowWrap = "anywhere"; //??

    if (value != null && value != '' || value == false) {
	if (Array.isArray(att[mainvalue])) {
	    if (att.attribute_type_id != "biolink:publications")
                cell.className = 'attvalue';

	    var br = false;
	    for (var val of att[mainvalue]) {
		if (br)
		    cell.append(document.createElement("br"));

		if (val == null) {
                    cell.append("--NULL--");
		}
		else if (typeof val === 'object') {
		    var pre = document.createElement("pre");
		    pre.append(JSON.stringify(val,null,2));
		    cell.append(pre);
		}
		else if (val.toString().startsWith("PMID:")) {
                    var a = document.createElement("a");
                    a.className = 'attvalue';
                    a.target = '_blank';
                    a.href = "https://pubmed.ncbi.nlm.nih.gov/" + val.split(":")[1] + '/';
		    a.title = 'View in PubMed';
                    a.innerHTML = val;
                    cell.append(a);

		    if (semmeddb && semmeddb[0] && semmeddb[0]["value"][val]) {
			cell.append(" : ");
			var quote = document.createElement("i");
			quote.append(semmeddb[0]["value"][val]["sentence"]);
			cell.append(quote);
			cell.append(' ('+semmeddb[0]["value"][val]["publication date"]+')');
		    }
		}
		else if (val.toString().startsWith("DOI:")) {
                    var a = document.createElement("a");
		    a.className = 'attvalue';
		    a.target = '_blank';
		    a.href = "https://doi.org/" + val.split(":")[1];
		    a.title = 'View in doi.org';
		    a.innerHTML = val;
		    cell.append(a);
		}
		else if (val.toString().startsWith("http")) {
                    var a = document.createElement("a");
		    a.className = 'attvalue';
		    a.target = '_blank';
		    a.href = val;
		    a.innerHTML = val;
		    cell.append(a);
		}

		else if (att.attribute_type_id == "biolink:support_graphs") {
		    UIstate["edgesg"]++;
                    var a = document.createElement("a");
                    a.className = 'attvalue';
                    a.style.cursor = "pointer";
		    a.title = 'View Aux Graph: '+ val;
		    a.setAttribute('onclick', 'add_cyto('+num+',"AUX'+val+'");');
                    a.append(val);
		    cell.append(a);

		    a = document.createElement("a");
                    a.className = 'graphlink';
		    a.style.fontWeight = "bold";
		    a.style.fontSize = "larger";
		    a.style.marginLeft = "20px";
		    a.title = 'View Edge Aux Graph: '+ val;
		    a.setAttribute('onclick', 'add_cyto('+num+',"AUX'+val+'");');
		    a.append(UIstate["edgesg"]);
		    document.getElementById('d'+num+'_div_edge').append(a);
		    document.getElementById('d'+num+'_div_edge').style.display = ''; // display it
		}

		else {
                    cell.append(val);
		}

		br = true;
	    }
	}
	else if (typeof att[mainvalue] === 'object') {
            var pre = document.createElement("pre");
	    pre.append(JSON.stringify(att[mainvalue],null,2));
	    cell.append(pre);
	}
        else if (attributes_to_truncate.includes(att.original_attribute_name)) {
            cell.className = 'attvalue';
            if (isNaN(att[mainvalue]))
		cell.append(att[mainvalue]);
	    else
		cell.append(Number(att[mainvalue]).toPrecision(3));
	}
	else if (value.toString().startsWith("http")) {
	    cell.className = 'attvalue';
            var a = document.createElement("a");
	    a.target = '_blank';
	    a.href = value;
	    a.innerHTML = value;
	    cell.append(a);
	}
	else {
            cell.className = 'attvalue';

	    var multi = att[mainvalue].toString().split(/(-!-|---|\;\;)/);
	    if (multi.length > 1) {
		for (var line of multi) {
		    cell.append('\u25BA');
                    cell.append(line);
		    cell.append(document.createElement("br"));
		}
	    }
	    else
		cell.append(att[mainvalue]);
	}
    }
    else {
        var text = document.createElement("i");
	text.append("-- empty / no value! --");
	cell.append(text);
	if (flagifmainvaluenull)
	    row.className = 'p1 qprob';
    }

    row.append(cell);
    tab.append(row);

    if (sub_atts && Array.isArray(sub_atts) && sub_atts.length >0) {
	row = document.createElement("tr");
	cell = document.createElement("td");
        cell.style.fontWeight = "bold";
	cell.append("(sub)attributes:");
	row.append(cell);

	cell = document.createElement("td");
	cell.className = 'subatts';
	var subatts_table = document.createElement("table");
	subatts_table.className = 't100';

	for (var sub_att of sub_atts)
	    display_attribute(num,subatts_table, sub_att, semmeddb, mainvalue);

	cell.append(subatts_table);
        row.append(cell);
        tab.append(row);
    }
}


function cyedges(index,what) {
    var api = cyobj[index].expandCollapse('get');

    if (what == 'collapse')
	api.collapseAllEdges();
    else
	api.expandAllEdges();

}

function cyresize(index,size) {
    var height = 400;
    if (size == 'm')
	height = 600;
    else if (size == 'L')
	height = 1000;

    document.getElementById('cy'+index).parentNode.style.height = height+'px';
    cyobj[index].resize();
    cyobj[index].fit();
    sesame('openmax',document.getElementById('a'+index+'_div'));
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

// unused in favor of icons
function mapNodeShape(ele) {
    var ntype = ele.data().categories ? ele.data().categories[0] ? ele.data().categories[0] : "NA" : "NA";
    if (ntype.endsWith("microRNA"))           { return "hexagon";} //??
    if (ntype.endsWith("Metabolite"))         { return "heptagon";}
    if (ntype.endsWith("XXProtein"))            { return "octagon";}
    if (ntype.endsWith("Pathway"))            { return "vee";}
    if (ntype.endsWith("XXDisease"))            { return "triangle";}
    if (ntype.endsWith("MolecularFunction"))  { return "rectangle";} //??
    if (ntype.endsWith("CellularComponent"))  { return "ellipse";}
    if (ntype.endsWith("BiologicalProcess"))  { return "tag";}
    if (ntype.endsWith("ChemicalEntity"))     { return "diamond";}
    if (ntype.endsWith("AnatomicalEntity"))   { return "rhomboid";}
    if (ntype.endsWith("XXPhenotypicFeature"))  { return "star";}
    return "rectangle";
}
// unused in favor of icons
function mapNodeColor(ele) {
    var ntype = ele.data().categories ? ele.data().categories[0] ? ele.data().categories[0] : "NA" : "NA";
    if (ntype.endsWith("BehavioralFeature"))  { return "white";}
    if (ntype.endsWith("Cell"))               { return "white";}
    if (ntype.endsWith("ChemicalOrDrugOrTreatment")) { return "white";}
    if (ntype.endsWith("Disease"))            { return "white";}
    if (ntype.endsWith("Gene"))               { return "white";}
    if (ntype.endsWith("PhenotypicFeature"))  { return "white";}
    if (ntype.endsWith("Protein"))            { return "white";}
    if (ntype.endsWith("SmallMolecule"))      { return "white";}

    if (ntype.endsWith("microRNA"))           { return "orange";} //??
    if (ntype.endsWith("Metabolite"))         { return "aqua";}
    if (ntype.endsWith("Pathway"))            { return "gray";}
    if (ntype.endsWith("MolecularFunction"))  { return "blue";} //??
    if (ntype.endsWith("CellularComponent"))  { return "purple";}
    if (ntype.endsWith("BiologicalProcess"))  { return "green";}
    if (ntype.endsWith("ChemicalEntity"))     { return "yellowgreen";}
    if (ntype.endsWith("AnatomicalEntity"))   { return "violet";}
    return "#04c";
}

function mapNodeIcon(ele) {
    var ntype = ele.data().categories ? ele.data().categories[0] ? ele.data().categories[0] : "NA" : "NA";
    if (ntype.endsWith("AnatomicalEntity"))   { return "./ui_icons/humanoid.png";}
    if (ntype.endsWith("BehavioralFeature"))  { return "./ui_icons/behavior.png";}
    if (ntype.endsWith("BiologicalProcess"))  { return "./ui_icons/biological.png";}
    if (ntype.endsWith("Cell"))               { return "./ui_icons/cell.png";}
    if (ntype.endsWith("ChemicalEntity"))     { return "./ui_icons/chemical.png";}
    if (ntype.endsWith("ChemicalMixture"))    { return "./ui_icons/blend.png";}
    if (ntype.endsWith("ChemicalOrDrugOrTreatment"))  { return "./ui_icons/drugs.png";}
    if (ntype.endsWith("Disease"))            { return "./ui_icons/iv.png";}
    if (ntype.endsWith("Drug"))               { return "./ui_icons/drug.png";}
    if (ntype.endsWith("Food"))               { return "./ui_icons/food.png";}
    if (ntype.endsWith("Gene"))               { return "./ui_icons/gene.png";}
    if (ntype.endsWith("GeneOrGeneProduct"))  { return "./ui_icons/gene.png";}
    if (ntype.endsWith("GrossAnatomicalStructure"))   { return "./ui_icons/humanoid.png";}
    if (ntype.endsWith("MolecularActivity"))  { return "./ui_icons/molecular.png";}
    if (ntype.endsWith("MolecularEntity"))    { return "./ui_icons/molecule.png";}
    if (ntype.endsWith("MolecularMixture"))   { return "./ui_icons/blend.png";}
    if (ntype.endsWith("OntologyClass"))      { return "./ui_icons/map.png";}
    if (ntype.endsWith("OrganismTaxon"))      { return "./ui_icons/taxonomy.png";}
    if (ntype.endsWith("Pathway"))            { return "./ui_icons/pathways.png";}
    if (ntype.endsWith("PhenotypicFeature"))  { return "./ui_icons/pheno.png";}
    if (ntype.endsWith("PhysiologicalProcess"))       { return "./ui_icons/physiology.png";}
    if (ntype.endsWith("Protein"))            { return "./ui_icons/protein.png";}
    if (ntype.endsWith("SmallMolecule"))      { return "./ui_icons/molecule.png";}
    return "./ui_icons/generic.png";
}

function mapEdgeLineStyle(ele) {
    if (ele.data().attributes)
	for (var att of ele.data().attributes)
	    if (att["attribute_type_id"] == "biolink:computed_value")
		return 'dashed';
    return 'solid';
}

function mapEdgeColor(ele,num) {
    if (ele.data().qualifiers)
	return '#291';

    if (num == 88888 && ele.data().sources) {
        for (var src of ele.data().sources) {
	    if (src["resource_role"] && src["resource_role"] == "primary_knowledge_source") {
		if (src["resource_id"] == "infores:arax")
		    return '#aaa';
		if (src["resource_id"] == "infores:sri-node-normalizer")
		    return '#8250df';
		return '#5596d0';
	    }
	}
    }

    return "#aaf";

    // old:
    var etype = ele.data().predicate ? ele.data().predicate : ele.data().predicates ? ele.data().predicates[0] : "NA";
    if (etype == "biolink:contraindicated_for")       { return "red";}
    if (etype == "biolink:indicated_for")             { return "green";}
    if (etype == "biolink:physically_interacts_with") { return "green";}
    if (etype == "biolink:interacts_with")            { return "green";}
    return "#aaf";
}


// build-a-qGraph
function qg_new(msg,nodes,type='basic') {
    if (cyobj[99999]) { cyobj[99999].elements().remove(); }
    else add_cyto(99999,'QG');
    input_qg = { "edges": {}, "nodes": {} };
    qgids = [];
    UIstate.editedgeid = null;
    UIstate.editnodeid = null;

    if (msg) {
	document.getElementById("statusdiv").innerHTML = "<p>A new "+type+" Query Graph has been created.</p>";
        add_user_msg("A new "+type+" Query Graph has been created");
    }
    else
	document.getElementById("showQGjson").checked = false;

    if (nodes) {
	var n0 = qg_node('new',false);
	qg_node('new',false);
	qg_edge('new');

	// UNUSED :: may revisit if want to extend "edge" definitions to include "paths"
	if (type == "Pathfinder") {
            qg_add_category_to_qnode('biolink:NamedThing');
	    qg_add_predicate_to_qedge('biolink:related_to');
	    qg_add_property_to_qedge('knowledge_type','inferred');

	    var n2 = qg_node('new',false);
	    qg_edge('new');
	    qg_add_predicate_to_qedge('biolink:related_to');
	    qg_add_property_to_qedge('knowledge_type','inferred');

            qg_edge('new',n0,n2);
	    qg_add_predicate_to_qedge('biolink:related_to');
	    qg_add_property_to_qedge('knowledge_type','inferred');

	    display_qg_popup('edge','hide');
	}
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
	newqnode.option_group_id = null;
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
	if (input_qg.nodes[id]['_names'] && input_qg.nodes[id]['_names'].length > 0) {
	    daname = input_qg.nodes[id]['_names'][0];
	    if (input_qg.nodes[id]['_names'].length == 2)
		daname = "[ "+daname+", "+input_qg.nodes[id]['_names'][1]+" ]";
	    else if (input_qg.nodes[id]['_names'].length > 2)
		daname = "[ "+daname+" +"+(input_qg.nodes[id]['_names'].length - 1)+" ]";
	}
        else if (input_qg.nodes[id]['categories'] && input_qg.nodes[id]['categories'].length > 0) {
	    daname = input_qg.nodes[id]['categories'][0];

	    if (input_qg.nodes[id]['categories'].length == 2)
		daname = "[ "+daname+", "+input_qg.nodes[id]['categories'][1]+" ]";
	    else if (input_qg.nodes[id]['categories'].length > 2)
		daname = "[ "+daname+" +"+(input_qg.nodes[id]['categories'].length - 1)+" ]";
	}

	if (input_qg.nodes[id].is_set)
	    daname = "{ "+daname+" }";

	if (daname != cyobj[99999].getElementById(id).data('name'))
	    cyobj[99999].getElementById(id).data('name',daname);
	cyobj[99999].getElementById(id).data('categories',input_qg.nodes[id]['categories']);
    }

    display_qg_popup('node','show');

    document.getElementById('nodeeditor_id').innerHTML = id;
    document.getElementById('nodeeditor_name').innerHTML = daname;

    var htmlnode = document.getElementById('nodeeditor_ids');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].ids) {
	var theids = input_qg.nodes[id].ids.slice();  // creates a copy (instead of a reference)
	for (var curie of theids.sort()) {
	    htmlnode.append(curie);

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_curie_from_qnode("'+curie+'");';
	    link.title = "remove "+curie+" from Qnode ids list";
	    link.append(" [ remove ] ");
	    htmlnode.append(link);

	    htmlnode.append(document.createElement("br"));
	}
    }
    else
	input_qg.nodes[id].ids = [];

    htmlnode = document.getElementById('nodeeditor_cat');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].categories) {
	for (var category of input_qg.nodes[id].categories.sort()) {
	    htmlnode.append(category);

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_category_from_qnode("'+category+'");';
	    link.title = "remove "+category+" from Qnode categories list";
	    link.append(" [ remove ] ");
	    htmlnode.append(link);

	    htmlnode.append(document.createElement("br"));
	}
    }
    else
	input_qg.nodes[id].categories = [];

    htmlnode = document.getElementById('nodeeditor_cons');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].constraints) {
	var cindex = 0;
	for (var constraint of input_qg.nodes[id].constraints) {
	    htmlnode.append(constraint.name+" ");
	    if (constraint.not)
		htmlnode.append("NOT ");
	    htmlnode.append(constraint.operator + " " +constraint.value);
	    if (constraint.unit_name)
		htmlnode.append(" ("+constraint.unit_name+")");

            var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_constraint_from_qnode('+cindex+');';
	    link.title = "remove "+constraint.id+" from Qnode constraints list";
	    link.append(" [ remove ] ");
	    htmlnode.append(link);

	    htmlnode.append(document.createElement("br"));
	    cindex++;
	}
    }

    document.getElementById('nodeeditor_set').checked = input_qg.nodes[id].is_set;

    htmlnode = document.getElementById('nodeeditor_optgpid');
    htmlnode.innerHTML = '';
    if (input_qg.nodes[id].option_group_id) {
	htmlnode.append(input_qg.nodes[id].option_group_id);

	var link = document.createElement("a");
	link.style.float = "right";
	link.href = 'javascript:qg_remove_optgpid_from_qnode();';
	link.title = "remove Option Group ID from this Qnode";
	link.append(" [ remove ] ");
	htmlnode.append(link);
    }
    else
	input_qg.nodes[id].option_group_id = null;

    UIstate.editnodeid = id;

    qg_update_qnode_list();
    qg_display_edge_predicates(false);
    show_qgjson();

    return id;
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

    for (var eid in input_qg.edges) {
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
    add_user_msg("Deleted node="+id);
    display_qg_popup('node','hide');
    UIstate.editnodeid = null;
}


async function qg_add_curie_to_qnode() {
    var statusdiv = document.getElementById("statusdiv");

    var id = UIstate.editnodeid;
    if (!id) return;

    var thing = document.getElementById("newquerynode").value.trim();
    document.getElementById("newquerynode").value = '';

    if (thing == '') {
        statusdiv.innerHTML = "<p class='error'>Please enter a node value</p>";
	return;
    }

    var bestthing = await check_entity(thing,false);
    document.getElementById("devdiv").innerHTML +=  "-- best node = " + JSON.stringify(bestthing,null,2) + "<br>";

    if (bestthing.found) {
        statusdiv.innerHTML = "<p>Found entity with name <b>"+bestthing.name+"</b> that best matches <i>"+thing+"</i> in our knowledge graph.</p>";
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
        statusdiv.innerHTML = "<p><span class='error'>" + thing + "</span> is not in our knowledge graph.</p>";
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

function qg_add_curielist_to_qnode(list) {
    var listId = list.split("LIST_")[1];
    var id = UIstate.editnodeid;
    if (!id) return;

    var added = 0;
    for (var li in listItems[listId]) {
	if (listItems[listId].hasOwnProperty(li) && listItems[listId][li] == 1) {
            if (!input_qg.nodes[id]['ids'].includes(entities[li].curie)) {
		input_qg.nodes[id]['ids'].push(entities[li].curie);
		input_qg.nodes[id]['_names'].push(entities[li].name);
		added++;
	    }
	    qg_add_category_to_qnode(entities[li].type);
	}
    }

    document.getElementById("statusdiv").innerHTML = "<p>Added <b>"+added+"</b> curies to node <b>"+id+"</b> from list <i>"+listId+"</i></p>";

    cyobj[99999].reset();
    cylayout(99999,"breadthfirst");
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
	input_qg.edges[id]['attribute_constraints'].push(constraint);
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
	input_qg.edges[id]['attribute_constraints'].splice(idx, 1);

    qg_edge(id);
}

function qg_update_optgpid_to_qgitem(what) {
    var id = null;
    if (what == 'qedge')
	id = UIstate.editedgeid;
    else if (what == 'qnode')
	id = UIstate.editnodeid;
    if (!id) return;

    var val = document.getElementById(what+"optgpidbox").value.trim();
    document.getElementById(what+"optgpidbox").value = '';
    if (!val) return;

    if (what == 'qedge') {
	input_qg.edges[id]['option_group_id'] = val;
	qg_edge(id);
    }
    else {
	input_qg.nodes[id]['option_group_id'] = val;
	qg_node(id);
    }
}
function qg_remove_optgpid_from_qnode() {
    var id = UIstate.editnodeid;
    if (!id) return;
    input_qg.nodes[id]['option_group_id'] = null;
    qg_node(id);
}
function qg_remove_optgpid_from_qedge() {
    var id = UIstate.editedgeid;
    if (!id) return;
    input_qg.edges[id]['option_group_id'] = null;
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

function qg_edge(id,node1=null,node2=null) {
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
	newqedge.attribute_constraints = [];
	newqedge.qualifier_constraints = [];
        newqedge.exclude = false;
	newqedge.option_group_id = null;
	// join last two nodes if not specified otherwise
	if (node1&&node2) {
	    newqedge.subject = node1;
	    newqedge.object = node2;
	}
	else {
	    newqedge.subject = nodes[nodes.length - 2];
	    newqedge.object = nodes[nodes.length - 1];
	}

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
	for (var predicate of input_qg.edges[id].predicates.sort()) {
	    htmlnode.append(predicate);

	    var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_predicate_from_qedge("'+predicate+'");';
	    link.title = "remove "+predicate+" from Qedge predicate list";
	    link.append(" [ remove ] ");
	    htmlnode.append(link);

	    htmlnode.append(document.createElement("br"));
	}
    }
    else
	input_qg.edges[id].predicates = [];

    htmlnode = document.getElementById('edgeeditor_cons');
    htmlnode.innerHTML = '';
    if (input_qg.edges[id].attribute_constraints) {
	var cindex = 0;
	for (var constraint of input_qg.edges[id].attribute_constraints) {
	    htmlnode.append(constraint.name+" ");
	    if (constraint.not)
		htmlnode.append("NOT ");
	    htmlnode.append(constraint.operator + " " +constraint.value);
	    if (constraint.unit_name)
		htmlnode.append(" ("+constraint.unit_name+")");

            var link = document.createElement("a");
	    link.style.float = "right";
	    link.href = 'javascript:qg_remove_constraint_from_qedge('+cindex+');';
	    link.title = "remove "+constraint.id+" from Qedge constraints list";
	    link.append(" [ remove ] ");
	    htmlnode.append(link);

	    htmlnode.append(document.createElement("br"));
	    cindex++;
	}
    }

    htmlnode = document.getElementById('edgeeditor_quals');
    htmlnode.innerHTML = '';
    var showhr = false;
    var prevqb = '';
    if (input_qg.edges[id].qualifier_constraints) {
	for (var qset of input_qg.edges[id].qualifier_constraints) {
	    if (showhr) {
		htmlnode.append(document.createElement("hr"));
		htmlnode.append(document.createElement("hr"));
		htmlnode.append(document.createElement("hr"));
		prevqb = '';
	    }
	    showhr = true;
            for (var qualifier of qset.qualifier_set) {
		currqb = qualifier['qualifier_type_id'].split("_")[0];
		var span0 = document.createElement("span");
		var span1 = document.createElement("span");
		var span2 = document.createElement("span");
		if (prevqb && prevqb != currqb) {
		    span0.style.borderTop = '1px solid #ccc';
		    span1.style.borderTop = '1px solid #ccc';
		    span2.style.borderTop = '1px solid #ccc';
		}
		prevqb = currqb;
		span0.style.color = "#aaa";
		span0.append(qualifier['qualifier_type_id'].split(":")[0]+":");
		htmlnode.append(span0);
		span1.append(qualifier['qualifier_type_id'].split(":")[1]);
		htmlnode.append(span1);

		span2.style.fontWeight = "bold";
		span2.style.paddingLeft = "10px";
		span2.append(qualifier.qualifier_value);
		htmlnode.append(span2);
	    }
	}
    }


    document.getElementById('edgeeditor_xcl').checked = input_qg.edges[id].exclude;

    htmlnode = document.getElementById('edgeeditor_optgpid');
    htmlnode.innerHTML = '';
    if (input_qg.edges[id].option_group_id) {
	htmlnode.append(input_qg.edges[id].option_group_id);

	var link = document.createElement("a");
	link.style.float = "right";
	link.href = 'javascript:qg_remove_optgpid_from_qedge();';
	link.title = "remove Option Group ID from this Qedge";
	link.append(" [ remove ] ");
	htmlnode.append(link);
    }
    else
	input_qg.edges[id].option_group_id = null;

    show_qgjson();
    return id;
}

function qg_update_qnode_list() {
    document.getElementById('edgeeditor_subj').innerHTML = '';
    document.getElementById('edgeeditor_obj').innerHTML = '';
    for (var node of Object.keys(input_qg.nodes).sort()) {
	var opt = document.createElement('option');
	opt.value = node;
	opt.innerHTML = node+":"+cyobj[99999].getElementById(node).data('name');
	document.getElementById('edgeeditor_subj').append(opt);
	document.getElementById('edgeeditor_obj').append(opt.cloneNode(true));
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
    add_user_msg("Deleted edge="+id);

    display_qg_popup('edge','hide');
    UIstate.editedgeid = null;
}

function qg_add_property_to_qedge(prop,val) {
    var id = UIstate.editedgeid;
    if (!id || !prop || !val) return;

    input_qg.edges[id][prop] = val
    qg_edge(id);
}

function qg_add_predicate_to_qedge(pred) {
    var id = UIstate.editedgeid;
    if (!id) return;

    document.getElementById("fullpredicatelist").value = '';
    document.getElementById("fullpredicatelist").blur();
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

function qg_setxcl_for_qedge() {
    var id = UIstate.editedgeid;
    if (!id) return;

    input_qg.edges[id].exclude = document.getElementById('edgeeditor_xcl').checked;
    qg_edge(id);
}

function qg_edge_swap_obj_subj() {
    var tmp = document.getElementById('edgeeditor_subj').value;
    document.getElementById('edgeeditor_subj').value = document.getElementById('edgeeditor_obj').value;
    document.getElementById('edgeeditor_obj').value = tmp;
    qg_update_qedge();
}

function qg_edit(msg) {
    cytodata['QG'] = [];
    if (cyobj[99999]) {cyobj[99999].elements().remove();}
    else add_cyto(99999,"QG");
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

    if (msg) {
	document.getElementById("statusdiv").innerHTML = "<p>Copied Query Graph to visual edit window.</p>";
	add_user_msg("Copied Query Graph to visual edit window", "INFO");
    }
    else
	document.getElementById("showQGjson").checked = false;

    document.getElementById("devdiv").innerHTML +=  "Copied query_graph to edit window<br>";
}

function show_qgjson() {
    if (document.getElementById("showQGjson").checked) {
	var statusdiv = document.getElementById("statusdiv");
	statusdiv.innerHTML = "<pre>"+JSON.stringify(input_qg,null,2)+ "</pre>";
	sesame('openmax',statusdiv);
    }
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
	th.append(head);
	tr.append(th);
    }
    table.append(tr);

    var nitems = 0;

    for (var nid in input_qg.nodes) {
	var result = input_qg.nodes[nid];
	nitems++;

	tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.append(nid);
        tr.append(td);

        td = document.createElement("td");
        td.append(result["_name"] == null ? "-" : result["_name"]);
        tr.append(td);

	td = document.createElement("td");
        td.append(result.is_set ? "(multiple items)" : result.ids == null ? "(any node)" : result.ids[0]);
        tr.append(td);

	td = document.createElement("td");
        td.append(result.is_set ? "(set of nodes)" : result.categories == null ? "(any)" : result.categories[0]);
        tr.append(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_node_from_query_graph(\"'+nid+'\")';
	link.append("Remove");
	td.append(link);
        tr.append(td);

	table.append(tr);
    }

    for (var eid in input_qg.edges) {
	var result = input_qg.edges[eid];
        tr = document.createElement("tr");
	tr.className = 'hoverable';

	var td = document.createElement("td");
        td.append(eid);
	tr.append(td);

	td = document.createElement("td");
        td.append("-");
        tr.append(td);

        td = document.createElement("td");
	td.append(result.subject+"--"+result.object);
	tr.append(td);

        td = document.createElement("td");
	td.append(result.predicates == null ? "(any)" : result.predicates[0]);
	tr.append(td);

        td = document.createElement("td");
	var link = document.createElement("a");
	link.href = 'javascript:remove_edge_from_query_graph(\"'+eid+'\")';
	link.append("Remove");
	td.append(link);
	tr.append(td);

        table.append(tr);
    };

    document.getElementById("qg_items").innerHTML = '';
    if (nitems > 0)
	document.getElementById("qg_items").append(table);

}


function qg_display_edge_predicates(all) {
    var preds_node = document.getElementById("qedgepredicatelist");
    var subj = document.getElementById('edgeeditor_subj').value;
    var obj = document.getElementById('edgeeditor_obj').value;

    if (!all) {
	if (!subj || !obj ||
	    !input_qg.nodes[subj]['categories'] ||
	    input_qg.nodes[subj]['categories'] == null ||
	    input_qg.nodes[subj]['categories'].length != 1 ||
	    !input_qg.nodes[obj]['categories'] ||
	    input_qg.nodes[obj]['categories'] == null ||
	    input_qg.nodes[obj]['categories'].length != 1)
	    all = true;
    }

    var preds = [];
    if (all)
	preds = all_predicates.sort();
    else if (predicates[input_qg.nodes[subj]['categories'][0]] && input_qg.nodes[obj]['categories'][0] in predicates[input_qg.nodes[subj]['categories'][0]])
	preds = predicates[input_qg.nodes[subj]['categories'][0]][input_qg.nodes[obj]['categories'][0]].sort();

    preds_node.innerHTML = '';
    var opt = document.createElement('option');
    opt.value = '';

    if (preds.length < 1) {
	opt.innerHTML = "-- No Predicates found --";
	preds_node.append(opt);
    }
    else {
	opt.innerHTML = "Add Predicate to Edge&nbsp;("+preds.length+")&nbsp;&nbsp;&nbsp;&#8675;";
	preds_node.append(opt);

	for (const p of preds) {
	    opt = document.createElement('option');
	    opt.value = p;
	    opt.innerHTML = p;
	    preds_node.append(opt);
	}
    }
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
    tmpdata["option_group_id"] = null;
    if (nodetype != 'NONSPECIFIC')
	tmpdata["categories"] = [nodetype];

    input_qg.nodes[qgid] = tmpdata;
}

function qg_clean_up(xfer) {
    // clean up non-TRAPI attributes and null arrays
    for (var nid in input_qg.nodes) {
	var gnode = input_qg.nodes[nid];

	if (gnode.ids) {
	    if (gnode.ids[0] == null)
		delete gnode.ids;
	    else if (gnode.ids.length == 1)
		if (gnode['_names'] && gnode['_names'][0] != null)
		    gnode.name = gnode['_names'][0];
	}
	if (gnode.categories && gnode.categories[0] == null)
	    delete gnode.categories;
	if (gnode.constraints && gnode.constraints[0] == null)
	    delete gnode.constraints;
	if (gnode.option_group_id == null)
	    delete gnode.option_group_id;

	for (var att of ["_names","_desc"] ) {
	    if (gnode.hasOwnProperty(att))
		delete gnode[att];
	}
    }

    for (var eid in input_qg.edges) {
	var gedge = input_qg.edges[eid];
	if (gedge.predicates && gedge.predicates[0] == null)
	    delete gedge.predicates;
	if (gedge.attribute_constraints && gedge.attribute_constraints[0] == null)
	    delete gedge.attribute_constraints;
	if (gedge.qualifier_constraints && gedge.qualifier_constraints[0] == null)
	    delete gedge.qualifier_constraints;
        if (gedge.option_group_id == null)
	    delete gedge.option_group_id;
        if (!gedge.exclude)
	    delete gedge.exclude;
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
    if (which == 'filters')
	popup = document.getElementById('nodefilter_container');
    else if (which == 'edge')
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


// DSL-RELATED FUNCTIONS
function populate_dsl_commands() {
    var dsl_node = document.getElementById("dsl_command");
    dsl_node.innerHTML = '';

    var opt = document.createElement('option');
    opt.value = '';
    opt.innerHTML = "Select DSL Command&nbsp;&nbsp;&nbsp;&#8675;";
    dsl_node.append(opt);

    for (var com in araxi_commands) {
	opt = document.createElement('option');
	opt.value = com;
	opt.append(com);
	dsl_node.append(opt);
    }
}

function show_dsl_command_options(command) {
    document.getElementById("dsl_command").value = '';
    document.getElementById("dsl_command").blur();

    var com_node = document.getElementById("dsl_command_form");
    com_node.innerHTML = '';
    com_node.append(document.createElement('hr'));

    var h2 = document.createElement('h2');
    h2.style.marginBottom = 0;
    h2.innerHTML = command;
    com_node.append(h2);

    if (araxi_commands[command].description) {
	com_node.append(araxi_commands[command].description);
	com_node.append(document.createElement('br'));
    }

    var skipped = '';
    for (var par in araxi_commands[command].parameters) {
        if (araxi_commands[command].parameters[par]['UI_display'] &&
	    araxi_commands[command].parameters[par]['UI_display'] == 'false') {
	    if (skipped) skipped += ", ";
	    skipped += par;
	    continue;
	}
	com_node.append(document.createElement('br'));

	var span = document.createElement('span');
	if (araxi_commands[command].parameters[par]['is_required'])
	    span.className = 'essence';
	span.append(par+":");
	com_node.append(span);

	span = document.createElement('span');
	span.className = 'tiny';
	span.style.position = "relative";
	span.style.left = "50px";
	span.append(araxi_commands[command].parameters[par].description);
	com_node.append(span);

	com_node.append(document.createElement('br'));

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
	    for (const p of all_predicates.sort()) {
		araxi_commands[command].parameters[par]['enum'].push(p);
	    }
	}

	if (araxi_commands[command].parameters[par]['enum']) {
	    var span = document.createElement('span');
	    span.className = 'qgselect';

	    var sel = document.createElement('select');
	    sel.id = "__param__"+par;

	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.innerHTML = "Select&nbsp;&nbsp;&nbsp;&#8675;";
	    sel.append(opt);

	    for (var val of araxi_commands[command].parameters[par]['enum']) {
		opt = document.createElement('option');
		opt.value = val;
		opt.innerHTML = val;
		sel.append(opt);
	    }

	    span.append(sel);
	    com_node.append(span);

	    if (araxi_commands[command].parameters[par]['default'])
		sel.value = araxi_commands[command].parameters[par]['default'];

	}
	else {
	    var i = document.createElement('input');
	    i.id = "__param__"+par;
	    i.className = 'questionBox';
	    i.size = 60;
	    com_node.append(i);

	    if (araxi_commands[command].parameters[par]['default'])
		i.value = araxi_commands[command].parameters[par]['default'];
	}
    }

    com_node.append(document.createElement('br'));

    if (skipped) {
	com_node.append(document.createElement('br'));
	com_node.append('The following advanced parameters are also available: '+skipped+'. Please consult the full documentation for more information.');
	com_node.append(document.createElement('br'));
	com_node.append(document.createElement('br'));
    }

    var button = document.createElement("input");
    button.className = 'questionBox button';
    button.type = 'button';
    button.name = 'action';
    button.title = 'Append new DSL command to list above';
    button.value = 'Add';
    button.setAttribute('onclick', 'add_dsl_command("'+command+'");');
    com_node.append(button);

    var link = document.createElement("a");
    link.style.marginLeft = "20px";
    link.href = 'javascript:abort_dsl();';
    link.append(" Cancel ");
    com_node.append(link);

    com_node.append(document.createElement('hr'));
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


// WORKFLOW-RELATED FUNCTIONS
function clearWF() {
    workflow = { 'workflow' : [], 'message' : {} };
    populate_wfjson();
    populate_wflist();
    abort_wf();
    document.getElementById("statusdiv").innerHTML = '<br>A blank workflow has been created<br><br>';
    add_user_msg("A blank workflow has been created", "INFO");
}

function update_wfjson() {
    var wfj;
    try {
	wfj = JSON.parse(document.getElementById("wfJSON").value);
    }
    catch(e) {
	var statusdiv = document.getElementById("statusdiv");
	statusdiv.append(document.createElement("br"));
	if (e.name == "SyntaxError")
	    statusdiv.innerHTML += "<b>Error</b> parsing JSON input. Please correct errors and resubmit: ";
	else
	    statusdiv.innerHTML += "<b>Error</b> processing input. Please correct errors and resubmit: ";
	statusdiv.append(document.createElement("br"));
	statusdiv.innerHTML += "<span class='error'>"+e+"</span>";
	add_user_msg("Error processing JSON input","ERROR",false);
	return;
    }

    workflow = wfj;
    populate_wfjson();
    populate_wflist();
    abort_wf();
}

function populate_wfjson() {
    document.getElementById("wfJSON").value = JSON.stringify(workflow,null,2);
}

function populate_wflist() {
    var list_node = document.getElementById("wflist");
    list_node.innerHTML = '';
    var count = 0;
    for (var com of workflow['workflow']) {
	var item = document.createElement('li');
	item.className = 'wflistitem';
	item.draggable = true;
	item.title = "CLICK to view/edit operation details; DRAG to reorder list";
	item.dataset.sequence = count;
	item.innerHTML = com.id;
	list_node.append(item);

	var items = list_node.getElementsByTagName("li"), current = null;

	item.addEventListener("click", function (ev) {
	    var operation = workflow['workflow'][this.dataset.sequence]["id"];
	    show_wf_operation_options(operation, this.dataset.sequence);
            for (var it of items)
		it.className = 'wflistitem';
	    this.className = 'wflistitemselected';
	});

	item.addEventListener("dragstart", function (ev) {
	    document.getElementById("wf_operation_form").innerHTML = '';
	    current = this;
	    this.className = "wflistitemselected";
	});
	item.addEventListener("dragend", function (ev) {
            populate_wflist();
	});

	item.addEventListener("dragenter", function (ev) {
	    if (this != current) { this.style.borderLeft = "15px solid #c40"; }
	});
	item.addEventListener("dragleave", function () {
	    this.style.border = "";
	    //this.style.border = "1px solid #666";
	});

	item.addEventListener("dragover", function (evt) {
	    evt.preventDefault();
	});

	item.addEventListener("drop", function (evt) {
	    evt.preventDefault();
	    current.className = "wflistitem";
	    if (this != current) {
		let currentpos = 0, droppedpos = 0;
		for (let it=0; it<items.length; it++) {
		    if (current == items[it])
			currentpos = it;
		    if (this == items[it])
			droppedpos = it;
		}
		if (currentpos < droppedpos)
		    this.parentNode.insertBefore(current, this.nextSibling);
		else
		    this.parentNode.insertBefore(current, this);

		var tmpwf = [];
		for (let it=0; it<items.length; it++)
		    tmpwf.push(workflow['workflow'][items[it].dataset.sequence]);
		workflow['workflow'] = tmpwf;

		populate_wfjson();
		populate_wflist();
	    }
	});

	count++;
    }

    if (count == 0) {
        list_node.append(document.createElement('br'));
        list_node.append("Add workflow operations using the menu on the right, and/or via the JSON import box below.");
    }
}

function populate_wf_operations() {
    var wf_node = document.getElementById("wf_operation");
    wf_node.innerHTML = '';

    var arax = document.getElementById("arax_only").checked;

    var opt = document.createElement('option');
    opt.value = '';
    opt.innerHTML = "Workflow Operation&nbsp;&nbsp;&nbsp;&#8675;";
    wf_node.append(opt);

    for (var com in wf_operations) {
	opt = document.createElement('option');
	opt.value = com;
	opt.innerHTML = com;
	if (arax && !wf_operations[com]['in_arax'])
	    opt.disabled = true;
	wf_node.append(opt);
    }
}

function show_wf_operation_options(operation, index) {
    document.getElementById("wf_operation").value = '';
    document.getElementById("wf_operation").blur();
    if (index == null)
	populate_wflist();

    var com_node = document.getElementById("wf_operation_form");
    com_node.innerHTML = '';
    com_node.append(document.createElement('hr'));

    var h2 = document.createElement('h2');
    h2.style.marginBottom = 0;
    h2.innerHTML = operation;
    com_node.append(h2);

    if (!wf_operations[operation]) {
        var span = document.createElement('span');
	span.className = 'error';
	span.append(document.createElement('br'));
        span.append("Operation '"+operation+"' not found in workflow operations list!");
	com_node.append(span);
	span.append(document.createElement('br'));
        com_node.append(get_remove_wf_operation_button(index));

	var link = document.createElement("a");
	link.style.marginLeft = "20px";
	link.href = 'javascript:abort_wf();';
	link.append("Cancel");
	com_node.append(link);
	return;
    }

    if (!wf_operations[operation]['in_arax']) {
        h2.innerHTML += " *";
	com_node.append('* Please note that this workflow operation is not supported in ARAX, though it may be in other actors');
        com_node.append(document.createElement('br'));
    }
    if (wf_operations[operation].description) {
	com_node.append(wf_operations[operation].description);
	com_node.append(document.createElement('br'));
    }

    for (var par in wf_operations[operation].parameters) {
	com_node.append(document.createElement('br'));

	var span = document.createElement('span');
	if (wf_operations[operation].parameters[par]['is_required'])
	    span.className = 'essence';
	span.append(par+":");
	com_node.append(span);

	span = document.createElement('span');
	span.className = 'tiny';
	span.style.position = "relative";
	span.style.left = "50px";
	span.append(wf_operations[operation].parameters[par].description);
	com_node.append(span);

	com_node.append(document.createElement('br'));

	if (wf_operations[operation].parameters[par]['type'] == 'boolean') {
	    wf_operations[operation].parameters[par]['enum'] = ['true','false'];
	}
	else if (wf_operations[operation].parameters[par]['type'] == 'ARAXnode') {
	    wf_operations[operation].parameters[par]['enum'] = [];
	    for (const p in predicates) {
		wf_operations[operation].parameters[par]['enum'].push(p);
	    }
	}
	else if (wf_operations[operation].parameters[par]['type'] == 'ARAXedge') {
	    wf_operations[operation].parameters[par]['enum'] = [];
	    for (const p of all_predicates.sort()) {
		wf_operations[operation].parameters[par]['enum'].push(p);
	    }
	}

	var val = '';
	if (index != null && workflow['workflow'][index]["parameters"]) {
	    if (workflow['workflow'][index]["parameters"][par])
		val = workflow['workflow'][index]["parameters"][par];
	}

	if (wf_operations[operation].parameters[par]['enum']) {
	    var span = document.createElement('span');
	    span.className = 'qgselect';

	    var sel = document.createElement('select');
	    sel.id = "__param__"+par;

	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.innerHTML = "Select&nbsp;&nbsp;&nbsp;&#8675;";
	    sel.append(opt);

	    for (var vv of wf_operations[operation].parameters[par]['enum']) {
		opt = document.createElement('option');
		opt.value = vv;
		opt.innerHTML = vv;
		sel.append(opt);
	    }

	    span.append(sel);
	    com_node.append(span);

            if (val)
		sel.value = val;
	    else if (wf_operations[operation].parameters[par]['default'])
		sel.value = wf_operations[operation].parameters[par]['default'];
	}
	else {
	    var i = document.createElement('input');
	    i.id = "__param__"+par;
	    i.className = 'questionBox';
	    i.size = 60;
	    com_node.append(i);

	    if (val)
		i.value = val;
	    else if (wf_operations[operation].parameters[par]['default'])
		i.value = wf_operations[operation].parameters[par]['default'];
	}
    }

    if (wf_operations[operation].warning) {
	com_node.append(document.createElement('br'));
        var span = document.createElement('span');
	span.className = 'essence';
	span.append(wf_operations[operation].warning);
	com_node.append(span);
    }
    com_node.append(document.createElement('br'));

    var button = document.createElement("input");
    button.className = 'questionBox button';
    button.type = 'button';
    button.name = 'action';
    if (index == null) {
	button.title = 'Add Operation to Workflow';
	button.value = 'Add';
    }
    else {
        button.title = 'Save edited Workflow operation';
	button.value = 'Update';
    }
    button.setAttribute('onclick', 'add_wf_operation("'+operation+'",'+index+');');
    com_node.append(button);

    if (index != null)
        com_node.append(get_remove_wf_operation_button(index));

    var link = document.createElement("a");
    link.style.marginLeft = "20px";
    link.href = 'javascript:abort_wf();';
    link.append("Cancel");
    com_node.append(link);
}

function get_remove_wf_operation_button(idx) {
    var button = document.createElement("input");
    button.className = 'questionBox button';
    button.type = 'button';
    button.name = 'action';
    button.title = 'Remove operation from Workflow';
    button.value = 'Remove';
    button.setAttribute('onclick', 'remove_wf_operation('+idx+');');
    return button;
}

function remove_wf_operation(idx) {
    workflow['workflow'].splice(idx, 1);
    populate_wfjson();
    populate_wflist();
    abort_wf();
}

function add_wf_operation(operation,idx) {
    var params = document.querySelectorAll('[id^=__param__]');

    var mywf = { "id" : operation };

    var wfparams = {};
    var has_params = false;
    for (var p of params) {
	var val = p.value.trim();
	if (val.length == 0) continue;

	var pname = p.id.split("__param__")[1];
	var ptype = wf_operations[operation].parameters[pname]['type'];

	if (ptype == 'array')
	    val = val.match(/\w+|"[^"]+"/g);
	else if (ptype == 'number')
	    val = Number(val);
	else if (ptype == 'integer')
	    val = parseInt(val);

	wfparams[pname] = val;
	has_params = true;
    }

    if (has_params)
	mywf['parameters'] = wfparams;

    if (idx == null)
	workflow['workflow'].push(mywf);
    else
	workflow['workflow'][idx] = mywf;

    populate_wfjson();
    populate_wflist();
    abort_wf();
}

function abort_wf() {
    document.getElementById("wf_operation_form").innerHTML = '';
    populate_wflist();
}

async function import_intowf(what,fromqg) {
    if (!(what == 'query_graph' || what == 'message'))
	return;

    var statusdiv = document.getElementById("statusdiv");
    statusdiv.innerHTML = '';
    statusdiv.append(document.createElement("br"));

    if (fromqg) {
	if (what == 'message')
	    return;  // No

	var tmpqg = JSON.stringify(input_qg); // preserve helper attributes
	qg_clean_up(false);
	workflow['message']['query_graph'] = input_qg;
        statusdiv.append("Imported query_graph into Workflow.");
        add_user_msg("Imported query_graph into Workflow","INFO");
	input_qg = JSON.parse(tmpqg);
	selectInput('qwf');
    }
    else {
	var resp_id = document.getElementById("respId").value.trim();
	document.getElementById("respId").value = resp_id;
	if (!resp_id) return;

	statusdiv.append("Importing "+what+" from response_id = " + resp_id + " ...");
	statusdiv.append(document.createElement("br"));

	var button = document.getElementById((what=='message'?"ImportMSGbutton":"ImportQGbutton"));
	var wait = getAnimatedWaitBar(button.offsetWidth+"px");
	button.parentNode.replaceChild(wait, button);

	var response;
	if (resp_id.startsWith("http"))
	    response = await fetch(resp_id);
	else {
	    var meh_id = isNaN(resp_id) ? "X"+resp_id : resp_id;
	    response = await fetch(providers["ARAX"].url + "/response/" + meh_id);
	}
	var respjson = await response.json();

	if (respjson && respjson.message) {
	    if (what == 'message')
		workflow['message'] = respjson.message;
	    else if (respjson.message["query_graph"])
		workflow['message']['query_graph'] = respjson.message["query_graph"];
	    else {
		statusdiv.append("No query_graph found in response_id = " + resp_id + "!!");
		add_user_msg("No query_graph found in response_id = " + resp_id);
	    }
	}
	else {
	    statusdiv.append("No message found in response_id = " + resp_id + "!!");
            add_user_msg("No message found in response_id = " + resp_id);
	}

        wait.parentNode.replaceChild(button, wait);
    }

    statusdiv.append(document.createElement("br"));
    statusdiv.append(document.createElement("br"));
    populate_wfjson();
}


function load_meta_knowledge_graph() {
    var allnodes_node = document.getElementById("allnodetypes");
    var pf_inter_node = document.getElementById("pf_inter");

    fetch(providers["ARAX"].url + "/meta_knowledge_graph?format=simple")
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong with /meta_knowledge_graph');
	})
        .then(data => {
	    predicates = data.predicates_by_categories;
	    all_predicates = data.supported_predicates;

	    allnodes_node.innerHTML = '';
	    pf_inter_node.innerHTML = '';
	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.append("Add Category to Node\u00A0\u00A0\u00A0\u00A0\u21E3");
	    allnodes_node.append(opt);
	    opt = document.createElement('option');
            opt.value = '';
            opt.append("[Optional] Intermediate Node Category\u00A0\u00A0\u00A0\u00A0\u21E3");
	    pf_inter_node.append(opt);

            for (const n in data.predicates_by_categories) {
		opt = document.createElement('option');
		opt.value = n;
		opt.append(n);
		allnodes_node.append(opt);
		pf_inter_node.append(opt.cloneNode(true));
	    }
            opt = document.createElement('option');
	    opt.value = 'NONSPECIFIC';
	    opt.append("Unspecified/Non-specific");
	    allnodes_node.append(opt);

	    qg_display_edge_predicates(true);

	    var all_preds_node = document.getElementById("fullpredicatelist");
	    all_preds_node.innerHTML = '';
	    opt = document.createElement('option');
	    opt.value = '';
	    opt.append("Full List of Predicates ("+all_predicates.length+")\u00A0\u00A0\u00A0\u21E3");
	    all_preds_node.append(opt);
	    for (const p of all_predicates.sort()) {
		opt = document.createElement('option');
		opt.value = p;
		opt.append(p);
		all_preds_node.append(opt);
	    }
	})
        .catch(error => {
	    allnodes_node.innerHTML = '';
            pf_inter_node.innerHTML = '';
	    var opt = document.createElement('option');
	    opt.value = '';
	    opt.append("-- Error Loading Node Categories --");
	    allnodes_node.append(opt);
            pf_inter_node.append(opt.cloneNode(true));
	    console.error(error);
	});

}

function retrieveRecentResps() {
    var recentresps_node = document.getElementById("recent_responses_container");
    recentresps_node.innerHTML = '';
    recentresps_node.className = '';

    var wait = getAnimatedWaitBar("100px");
    wait.style.marginRight = "10px";
    recentresps_node.append(wait);
    recentresps_node.append('Loading...');

    var numpks = parseInt(document.getElementById("howmanylatest").value.match(/[\d]+/));
    if (isNaN(numpks) || numpks < 1 || numpks > 40)
	numpks = 10;
    document.getElementById("howmanylatest").value = numpks;

    var srcpks = document.getElementById("wherefromlatest").value;

    var apiurl = providers["ARAX"].url + "/status?mode=recent_pks&last_n_hours="+numpks+"&authorization="+srcpks;

    fetch(apiurl)
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Unable to fetch recent PKs from '+srcpks);
	})
        .then(data => {
            document.title = "ARAX-UI [List of "+numpks+" most recent ARS queries]";
	    recentresps_node.innerHTML = '';

            var div = document.createElement("div");
	    div.className = "statushead";
	    div.append("Viewing "+numpks+" Most Recent ARS Queries from "+srcpks);

            var link = document.createElement("a");
	    link.style.float = 'right';
	    link.target = '_blank';
	    link.title = 'link to this view';
	    link.href = "http://"+ window.location.hostname + window.location.pathname + "?latest=" + numpks + "&from=" + srcpks;
	    link.innerHTML = "[ Direct link to this view ]";
	    div.append(link);

	    recentresps_node.append(div);

	    div = document.createElement("div");
	    div.className = "status";
	    recentresps_node.append(div);

	    var table = document.createElement("table");
	    table.className = 'sumtab';

            var tr = document.createElement("tr");
            var td = document.createElement("th");
            tr.append(td);

            for (var head of ["PK","Query","Status"] ) {
		td = document.createElement("th");
		td.append(head);
		tr.append(td);
	    }

            for (var agent of data["agents_list"]) {
		td = document.createElement("th");
		td.colSpan = '2';
		td.style.minWidth = '80px';
	        td.append(agent);
	        tr.append(td);
	    }

	    table.append(tr);

	    var num = 0;
            for (var pk of data["sorted_pk_list"].reverse()) {
		num++;
		tr = document.createElement("tr");
		tr.className = 'hoverable';

		td = document.createElement("td");
		td.append(num+'.');
		tr.append(td);

		td = document.createElement("td");
		var link = document.createElement("a");
		link.title = 'view response: '+pk;
		link.style.cursor = "pointer";
		link.style.fontFamily = "monospace";
		link.setAttribute('onclick', 'pasteId("'+pk+'");sendId(false);selectInput("qid");');

                if (data["pks"][pk]["timestamp"])
		    link.append(convertUTCToLocal(data["pks"][pk]["timestamp"]));
		else
		    link.append(pk);

		td.append(link);
		tr.append(td);

                td = document.createElement("td");
		if ("query" in data["pks"][pk])
		    td.append(data["pks"][pk]["query"]);
		else
		    td.append("--- n/a ---");
		tr.append(td);

                td = document.createElement("td");
                td.style.fontWeight = 'bold';
		td.append(data["pks"][pk]["status"]);
		tr.append(td);

		for (var agent of data["agents_list"]) {
		    td = document.createElement("td");
		    td.style.borderLeft = "1px solid black";
		    td.style.textAlign = 'right';
                    var span = document.createElement("span");
		    if (data["pks"][pk]["agents"][agent]) {
                        if (data["pks"][pk]["agents"][agent]["status"] == "Done") {
			    span.innerHTML = '&check;';
			    span.className = 'explevel p9';
			}
			else if (data["pks"][pk]["agents"][agent]["status"].startsWith("Running")) {
                            span.innerHTML = '&#10140;';
			    span.className = 'explevel p3';
			}
                        else if (data["pks"][pk]["agents"][agent]["status"].startsWith("Error")) {
			    span.innerHTML = '&cross;';
			    span.className = 'explevel p1';
			}
                        else if (data["pks"][pk]["agents"][agent]["status"].startsWith("Unknown")) {
			    span.innerHTML = '?';
			    span.className = 'explevel p0';
			}
			else {
			    span.append(data["pks"][pk]["agents"][agent]["status"]);
			}
			td.append(span);
			td.title = data["pks"][pk]["agents"][agent]["status"];
		    }
		    else
			td.append('n/a');
		    tr.append(td);

                    td = document.createElement("td");
		    td.style.textAlign = 'right';
                    if (data["pks"][pk]["agents"][agent])
			td.append(data["pks"][pk]["agents"][agent]["n_results"]);
		    else
			td.append('n/a');
                    td.title = td.innerText + " results";
		    tr.append(td);
		}

		table.append(tr);
	    }

	    div.append(table);
            div.append(document.createElement("br"));
	})
        .catch(error => {
	    recentresps_node.className = "error";
	    recentresps_node.innerHTML = "<br>" + error + "<br><br>";
	});
}


function retrieveRecentQs(active) {
    document.getElementById("recentqsLink").innerHTML = '';

    var recents_node = document.getElementById("recent_queries_container");
    recents_node.innerHTML = '';
    recents_node.className = '';

    var qfspan = document.getElementById("qfilter");
    qfspan.innerHTML = '';
    var wait = getAnimatedWaitBar("100px");
    wait.style.marginRight = "10px";
    qfspan.append(wait);
    qfspan.append('Loading...');

    document.getElementById("recent_queries_timeline_container").innerHTML = '';

    var apicall = "/status?";
    var hours = 0;
    if (active) {
	apicall += "mode=active";
    }
    else {
	hours = parseInt(document.getElementById("qftime").value.match(/[\d]+/));
	if (isNaN(hours) || hours < 1 || hours > 200)
	    hours = 24;
	document.getElementById("qftime").value = hours;
        apicall += "last_n_hours="+hours;
    }

    fetch(providers["ARAX"].url + apicall)
	.then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong with '+apicall);
	})
        .then(data => {
	    var stats = {};
	    stats.elapsed   = 0;
	    stats.state     = {};
	    stats.status    = {};
	    stats.submitter = {};
	    stats.domain    = {};
	    stats.hostname  = {};
	    stats.instance_name  = {};
	    stats.remote_address = {};

	    if (hours > 0) {
		var link = document.createElement("a");
		link.target = '_blank';
		link.title = 'link to this view';
		link.href = "http://"+ window.location.hostname + window.location.pathname + "?recent=" + hours;
		link.innerHTML = "[ Direct link to this view ]";
		document.getElementById("recentqsLink").append(link);
	    }

	    var timeline = {};
            timeline["ISB_watchdog"] = { "data": [ { "label": 0 , "data": [] , "_qstart": new Date() } ] };

            var table = document.createElement("table");
	    table.className = 'sumtab';
	    table.id = "recentqs_summary";
            recents_node.append(table);
            recents_node.append(document.createElement("br"));

	    table = document.createElement("table");
	    table.id = "recentqs_table";
	    table.className = 'sumtab';

	    var tr = document.createElement("tr");
            tr.dataset.qstatus = "COLUMNHEADER";
	    var td;
	    for (var head of ["Qid","Start (UTC)","Elapsed","Submitter","Remote IP","Domain","Hostname","Instance","pid","Response","State","Status","Description"] ) {
		td = document.createElement("th")
                if (head == "Description")
		    td.style.textAlign = "left";
		else
		    td.id = 'filter_'+head.toLowerCase();
                if (head == "Instance")
		    td.id += '_name';
                else if (head == "Remote IP")
		    td.id = 'filter_remote_address';
		td.dataset.filterstring = '';
		td.append(head);
		tr.append(td);
	    }
	    table.append(tr);

	    for (var query of data.recent_queries) {
		tr = document.createElement("tr");
		tr.className = 'hoverable';
		tr.dataset.qstatus = query.state + " " + query.status;

		var qstart = null;
		var qend = null;
		var qdur = null;
		var qid = null;
		for (var field of ["query_id","start_datetime","elapsed","submitter","remote_address","domain","hostname","instance_name","pid","response_id","state","status","description"] ) {
                    td = document.createElement("td");
		    td.dataset.value = query[field];
                    if (field == "start_datetime") {
			td.style.whiteSpace = "nowrap";
			qstart = query[field];
		    }
                    else if (field == "elapsed") {
			td.style.textAlign = "right";
			if (query[field] > 60) {
			    td.className = "error";
			    td.title = "Long query response/processing time";
			}
			stats.elapsed += query[field];
			qend = query[field] * 1000; //ms

			qdur = new Date(qend);
			var days = qdur.getUTCDate()-1;
			var months = qdur.getUTCMonth();
			qdur = (months>0?months+" months! ":"") + (days>0?days+"d ":"") + qdur.getUTCHours()+"h " + qdur.getMinutes()+"m " + qdur.getSeconds()+"s";
		    }
                    else if (field == "state") {
                        td.style.whiteSpace = "nowrap";
			var span = document.createElement("span");
			if (query[field] == "Completed") {
			    span.innerHTML = '&check;';
			    span.className = 'explevel p9';
			}
			else if (query[field] == "Reset") {
			    span.innerHTML = '&cross;';
			    span.className = 'explevel p5';
			}
			else if (query[field] == "Terminated") {
			    span.innerHTML = '&cross;';
			    span.className = 'explevel p3';
			}
			else if (query[field] == "Denied") {
			    span.innerHTML = '&cross;';
			    span.className = 'explevel p1';
			}
			else if (query[field] == "Died") {
			    span.innerHTML = '&cross;';
			    span.className = 'explevel p0';
			}
			else {
			    span.innerHTML = '&#10140;';
			    span.className = 'explevel p7';
			}
			td.append(span);
			td.innerHTML += '&nbsp;';
			if (stats.state[query[field]])
			    stats.state[query[field]]++;
			else
			    stats.state[query[field]] = 1;
		    }
                    else if (field == "instance_name" || field == "submitter" || field == "remote_address" || field == "domain" || field == "hostname") {
			td.style.whiteSpace = "nowrap";
                        if (stats[field][query[field]])
			    stats[field][query[field]]++;
			else
			    stats[field][query[field]] = 1;
		    }

                    if (query[field] == null)
			td.append(' -- ');
		    else if (field == "query_id") {
                        var link = document.createElement("a");
			link.target = '_blank';
			link.title = 'view the posted query (JSON)';
			link.style.cursor = "pointer";
			link.href = providers["ARAX"].url + '/status?id=' + query[field];
			link.append(query[field]);
			td.append(link);
                        qid = query[field];
		    }
		    else if (field == "response_id") {
			var link = document.createElement("a");
                        link.target = '_blank';
			link.title = 'view this response';
			link.style.cursor = "pointer";
                        link.href = '//' + window.location.hostname + window.location.pathname + '?r=' + query[field];
			link.append(query[field]);
			td.append(link);
		    }
		    else if (field == "status") {
			td.style.textAlign = "center";
			var span = document.createElement("span");
                        span.style.padding = "2px 6px";
			if (query[field] == "OK")
			    span.className = "explevel p9";
			else if (query[field] == "Running")
			    span.className = "explevel p7";
			else if (query[field] == "Reset")
			    span.className = "explevel p5";
			else if (query[field] == "Terminated")
			    span.className = "explevel p3";
			else
			    span.className = "explevel p1";
                        span.append(query[field]);
			td.append(span);

		        if (stats.status[query[field]])
			    stats.status[query[field]]++;
		        else
			    stats.status[query[field]] = 1;
		    }
		    else
			td.append(query[field]);
		    tr.append(td);
		}
		if (qstart && qend) {
		    qstart.replace(" ","T");
		    qstart += "Z";
		    qstart = new Date(qstart);
		    qend = new Date(qstart.getTime() + qend);
		    if (qend >= new Date())
			qend = new Date(new Date() - 2000);

		    if (!timeline[query["submitter"]]) {
			timeline[query["submitter"]] = {};
			timeline[query["submitter"]]["data"] = [];
		    }

		    // below assumes data is reverse-sorted by start datetime
		    var index = 0;
		    for (var index in [...Array(200).keys()]) {
			if (!timeline[query["submitter"]]["data"][index])
			    timeline[query["submitter"]]["data"][index] = { "label": index , "data": [] , "_qstart": new Date()};

			if (qend.getTime() < timeline[query["submitter"]]["data"][index]["_qstart"].getTime())
			    break;
		    }

		    timeline[query["submitter"]]["data"][index]["data"].push(
			{
			    "timeRange": [qstart, qend],
			    "val": query["instance_name"],
			    "_qid": qid,
			    "_qdur": qdur
			}
		    );
		    timeline[query["submitter"]]["data"][index]["_qstart"] = qstart;

		}
		table.append(tr);
	    }
	    // add dummy data points to scale timeline to match requested timespan
	    timeline["ISB_watchdog"]["data"][0]["data"].push(
		{
		    "timeRange": [Date.now(), Date.now()],
		    "val": "ARAX",
		    "_qid": null,
		    "_qdur": null
		}
	    );
	    var xhoursago = new Date();
	    xhoursago.setHours(xhoursago.getHours() - hours);
	    timeline["ISB_watchdog"]["data"][0]["data"].push(
		{
		    "timeRange": [xhoursago, xhoursago],
		    "val": "ARAX",
		    "_qid": null,
		    "_qdur": null
		}
	    );

	    displayQTimeline(timeline);
	    recents_node.append(table);
            recents_node.append(document.createElement("br"));
	    recents_node.append(document.createElement("br"));

	    for (var filterfield of ["submitter","remote_address","domain","hostname","instance_name","state","status"] ) {
		if (Object.keys(stats[filterfield]).length > 1) {
		    add_filtermenu('recentqs_table',filterfield, stats[filterfield]);
		}
	    }

	    qfspan.innerHTML = '';
	    qfspan.append("Show:");

	    for (var status of ["Completed","OK","Summary","Timeline"]) {
		span = document.createElement("span");
		span.style.marginLeft = "20px";
		span.style.cursor = "pointer";
		span.className = 'qprob p9';
		var tab = "recentqs_table";
		if (status == "Summary") {
		    span.className = 'qprob p9 hide';
		    tab = "recentqs_summary";
		}
		if (status == "Timeline")
		    span.setAttribute('onclick', 'show_hide(\"recent_queries_timeline_container\", this);');
		else
		    span.setAttribute('onclick', 'filter_queries(\"'+tab+'\", this,\"'+status+'\");');
		span.append(status);
		qfspan.append(span);
	    }

            table = document.getElementById("recentqs_summary");
            tr = document.createElement("tr");
            tr.style.display = "none";
            tr.dataset.qstatus = "Summary";
	    td = document.createElement("th");
	    td.colSpan = "3";
            td.append("Query Stats");
	    tr.append(td);
            table.append(tr);

            tr = document.createElement("tr");
            tr.style.display = "none";
            tr.dataset.qstatus = "Summary";
	    td = document.createElement("td");
	    td.append("Last updated");
            tr.append(td);
	    td = document.createElement("td");
	    tr.append(td);
            td = document.createElement("td");
	    td.append(data.current_datetime);
            tr.append(td);
            table.append(tr);

	    for (var stat in stats) {
		tr = document.createElement("tr");
		tr.style.display = "none";
		tr.dataset.qstatus = "Summary";
		td = document.createElement("td");
                td.append(stat);
		tr.append(td);
                if (stat == "elapsed") {
		    td = document.createElement("td");
                    td.append(stats[stat] + " sec");
		    tr.append(td);
		    td = document.createElement("td");
                    td.append((Number(stats[stat])/3600).toPrecision(3) + " hours");
		    tr.append(td);
		}
		else {
		    td = document.createElement("td");
		    for (var val in stats[stat]) {
			td.append(val);
			td.append(document.createElement("br"));
		    }
		    tr.append(td);
		    td = document.createElement("td");
		    for (var val in stats[stat]) {
			td.append(stats[stat][val]);
			td.append(document.createElement("br"));
		    }
		    tr.append(td);
		}
                table.append(tr);
	    }
	})
        .catch(error => {
	    qfspan.innerHTML = '';
            recents_node.className = "error";
	    recents_node.innerHTML = "<br>" + error + "<br><br>";
        });
}

function displayQTimeline(tdata) {
    var timeline_node = document.getElementById("recent_queries_timeline_container");
    timeline_node.innerHTML = '';

    var data = [];
    for (var group in tdata)
	data.push( { "group": group, "data": tdata[group].data } );

    const Timeline = TimelinesChart();
    Timeline
        .data(data)
	.width(1200)
	.maxHeight(1500)
	.leftMargin(120)
	.zQualitative(true)
	.segmentTooltipContent(function(d) { return "Query ID: <strong>"+d.data["_qid"].toString()+"</strong><br>"+d.data["_qdur"]; } )
    (timeline_node);

    timeline_node.append("Your computer's local time");
}

function add_filtermenu(tid, field, values) {
    var node = document.getElementById('filter_'+field);
    //node.title = "Click to filter based on this column's values";
    node.append("\u25BC");
    node.className = 'filterhead';

    var fmenu = document.createElement('span');
    fmenu.className = 'filtermenu';

    var vals = Object.keys(values);
    vals.unshift('[ Show all ]');
    for (var val of vals) {
	var item = document.createElement('a');
	item.append(val);
	if (val != '[ Show all ]')
	    item.append(" ["+values[val]+"]");
	item.setAttribute('onclick', 'filter_table("'+tid+'","'+field+'","'+val+'");');

	var item2 = document.createElement('span');
	item2.id = 'filter_'+field+"_"+val;
	item2.style.marginLeft = "10px";
	item.append(item2);
	fmenu.append(item);
    }
    node.append(fmenu);
}

function filter_table(tableid, field, value) {
    for (var item of document.querySelectorAll('[id^="filter_'+field+'_"]')) {
	item.className = '';
	item.innerHTML = '';
    }
    document.getElementById('filter_'+field+"_"+value).className = 'explevel p9';
    document.getElementById('filter_'+field+"_"+value).innerHTML = '&check;';

    if (value == '[ Show all ]') {
	document.getElementById('filter_'+field).style.color = 'initial';
	document.getElementById('filter_'+field).dataset.filterstring = '';
    }
    else {
	document.getElementById('filter_'+field).style.color = '#291';
	document.getElementById('filter_'+field).dataset.filterstring = value;
    }

    var trs = document.getElementById(tableid).children;
    var head = true;
    for (var tr of trs) {
	if (head) {
	    head = false;
	    continue;
	}
	var showrow = true;
	for (var tdidx in tr.children) {
	    if (!trs[0].children.hasOwnProperty(tdidx) ||
		trs[0].children[tdidx].dataset.filterstring == '')
		continue;
	    if (trs[0].children[tdidx].dataset.filterstring != tr.children[tdidx].dataset.value) {
		showrow = false;
		break;
	    }
	}
	if (showrow)
	    tr.style.display = 'table-row';
	else
	    tr.style.display = 'none';
    }
}

function filter_queries(tab, span, type) {
    var disp = 'none';
    if (span.classList.contains('hide')) {
	disp = 'table-row';
	span.classList.remove('hide');
    }
    else {
	span.classList.add('hide');
    }

    for (var tr of document.getElementById(tab).children) {
	if (tr.dataset["qstatus"].includes(type)) {
	    tr.style.display = disp;
	}
    }
}


function retrieveKPInfo() {
    var kpinfo_node = document.getElementById("kpinfo_container");
    kpinfo_node.innerHTML = '';
    kpinfo_node.className = '';

    var wspan = document.getElementById("kpinfo_wait");
    wspan.innerHTML = '';
    var wait = getAnimatedWaitBar("100px");
    wait.style.marginRight = "10px";
    wspan.append(wait);
    wspan.append('Loading...');

    fetch(providers["ARAX"].url + "/status?authorization=smartapi")
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Something went wrong with /status?authorization=smartapi');
	})
        .then(data => {
	    wspan.innerHTML = '';
	    var components = {};
	    for (let item of data) {
		if (!item['component']) {
		    console.log("Found empty component: "+item['component']);
		    item['component'] = 'MISSING';
		}
		components[item['component']] = true;
	    }

	    if (Object.keys(components).length < 1) {
		kpinfo_node.className = "error";
		kpinfo_node.innerHTML =  "<br>No <b>components</b> found in API response!<br><br>";
		return;
	    }

	    var table = document.createElement("table");
	    table.className = 'sumtab';

            for (let component of Object.keys(components)) {
		var tr = document.createElement("tr");
		var td = document.createElement("td");

		td.colSpan = "5";
		td.style.background = '#fff';
		td.style.border = '0';
		td.append(document.createElement("br"));
		td.append(document.createElement("br"));
		tr.append(td);
		table.append(tr);

		tr = document.createElement("tr");
                td = document.createElement("th")
		td.style.background = '#fff';
		td.style.fontSize = 'x-large';
		td.append(component+" Info");
		tr.append(td);
		for (var head of ["Status","Maturity","Description","URL"] ) {
		    td = document.createElement("th")
                    td.style.background = '#fff';
		    td.append(head);
		    tr.append(td);
		}
		table.append(tr);

		var was_seen = [];
		for (let item of data.sort(function(a, b) { return a.title.toUpperCase() > b.title.toUpperCase() ? 1 : -1; })) {
		    //console.log("item.comp:"+item['component']);
		    if (item['component'] == component) {
			tr = document.createElement("tr");
			td = document.createElement("td");
			td.rowSpan = item["servers"].length;
			td.style.backgroundColor = "white";
			td.style.borderRight = "1px solid #aaa";
			td.style.padding = "0px 20px";

			var text = document.createElement("h3");
			text.style.float = "right";
			text.style.marginLeft = "10px";
			if (!item["version"]) {
			    item["version"] = '--NULL--';
			    text.className = "qprob p0";
			}
			else if (item["version"] == "1.5.0")
			    text.className = "qprob p9";
			//else if (item["version"] == "1.5.0")
			//text.className = "qprob schp";
			else
			    text.className = "qprob p1";
                        text.append(item["version"]);
			text.title = "TRAPI version";
			td.append(text);

	                text = document.createElement("a");
			text.style.display = "inline-block";
			text.style.color = "#000";
			text.style.fontWeight = 'bold';
			text.style.fontSize = 'initial';
			text.style.padding = '15px 0px';
			text.href = item["smartapi_url"];
			text.target = 'smartapi_reg';
			text.title = 'View SmartAPI registration for this '+component;
			text.innerHTML = item["title"];
			td.append(text);
			td.append(document.createElement("br"));

                        if (was_seen.includes(item["infores_name"]+item["version"])) {
                            td.className = "error";
                            td.append('\u274C\u00A0');
			    td.title = "This is a DUPLICATE infores entry";
			}
			else
			    was_seen.push(item["infores_name"]+item["version"]);
			td.append(item["infores_name"]);

			tr.append(td);

			var main_td = td;
			var is_first = true;
			for (var mature of ["production","testing","staging","development"] ) {
			    var status_nodes = [];
			    var had_transltr_io = false; //(item["infores_name"].startsWith("infores:automat") || component == "Utility");
			    var was_mature = false;
			    for (var server of item["servers"]) {
				if (server["maturity"] == mature) {
				    was_mature = true;
				    if (!is_first)
					tr = document.createElement("tr");
				    td = document.createElement("td");
                                    var span = document.createElement("span");

				    var stritem = item["infores_name"]+server["maturity"]+server["url"];
				    if (was_seen.includes(stritem)) {
                                        //tr.className = "error";
                                        span.className = "explevel p0";
					span.innerHTML = '&cross;';
					span.title = "This is a DUPLICATE entry";
				    }
                                    else if (was_seen.includes(server["url"])) {
					span.className = "explevel p0";
                                        span.append('\u00A0\u00A0');
					span.title = "This is a duplicate URL entry";
				    }
				    else if (server["url"].includes("transltr.io")) {
					had_transltr_io = true;
					span.className = "explevel p9";
					span.innerHTML = '&check;';
					span.title = "This entry is hosted at transltr.io";
					was_seen.push(stritem);
					was_seen.push(server["url"]);
				    }
				    else {
					status_nodes.push(span);
					span.append('\u00A0\u00A0');
					was_seen.push(stritem);
					was_seen.push(server["url"]);
				    }
				    td.append(span);
				    tr.append(td);
				    for (var what of ["maturity","description","url"] ) {
					td = document.createElement("td");
					if (server[what])
					    td.append(server[what]);
					else {
					    td.className = "error";
					    td.title = "No data!";
					    td.append("-- null --");
					}
					tr.append(td);
				    }
				    table.append(tr);
				    is_first = false;
				    server["__done"] = true;
				}
				for (var sn of status_nodes) {
				    if (had_transltr_io || mature == "development")
					sn.className = "explevel p7";
				    else
					sn.className = "explevel p5";
				}
			    }

			    if (!was_mature && !had_transltr_io) {
				main_td.rowSpan++;
				if (!is_first)
				    tr = document.createElement("tr");
				td = document.createElement("td");
				var span = document.createElement("span");
				span.className = "explevel p3";
				span.title = "No servers found at this maturity level";
				span.append('\u00A0\u00A0');
				td.append(span);
				tr.append(td);

				td = document.createElement("td");
				td.className = "error";
				td.append(mature);
				tr.append(td);

                                td = document.createElement("td");
				td.className = "error";
				td.append("-- missing maturity --");
                                tr.append(td);

                                td = document.createElement("td");
				tr.append(td);

				table.append(tr);
				is_first = false;

			    }
			}
			for (var server of item["servers"]) {
			    if (!server["__done"]) {
                                if (!is_first)
				    tr = document.createElement("tr");
				td = document.createElement("td");
				var span = document.createElement("span");
				span.className = "explevel p1";
				span.title = "Maturity does not match expected list [production, testing, staging, development]";
				span.append('\u00A0\u00A0');
				td.append(span);
				tr.append(td);
				for (var what of ["maturity","description","url"] ) {
				    td = document.createElement("td");
				    td.className = "error";
				    if (server[what])
					td.append(server[what]);
				    else {
					td.title = "No data!";
					td.append("-- null --");
				    }
				    tr.append(td);
				}
				table.append(tr);
				is_first = false;
			    }
			}
		    }
		}
	    }

	    kpinfo_node.append(table);
            kpinfo_node.append(document.createElement("br"));
            kpinfo_node.append(document.createElement("br"));

	})
        .catch(error => {
	    wspan.innerHTML = '';
	    kpinfo_node.className = "error";
	    kpinfo_node.innerHTML =  "<br>" + error + "<br><br>";
	    console.error(error);
	});

}


function retrieveTestRunnerResultsList(thisone=null) {
    var url = 'https://arax.ncats.io/devLM/ARS-testing/testRunnerResults.json';

    fetch(url, {
	headers: {'pragma': 'no-cache', 'cache-control': 'no-cache'}
    })
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Unable to fetch ARS Translator TestRunner results list from '+url);
	})
        .then(data => {
	    var menu = document.getElementById("whichsystest");
	    for (let i=0; i<menu.length; i++) {
		if (menu.options[i].value.startsWith('ARSARS_')) {
		    menu.remove(i);
		    i--;
		}
	    }

	    for (var test of data['results']) {
		var opt = document.createElement('option');
		opt.value = "ARSARS_"+test['run_no'];
		opt.innerHTML = test['title'];
		if (test['run_no'] == thisone ||
		    opt.value== thisone)
		    opt.selected = true;
		menu.prepend(opt);
	    }
	})
        .catch(error => {
	    div.append("ERROR: "+error);
	    console.error(error);
	});

}


function retrieveSysTestResultsList(num) {
    var apiurl = 'https://utility.ci.transltr.io/arstest/api/latest_pk/'+num;
    fetch(apiurl)
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Unable to fetch ARS Translator system test results list from '+apiurl);
	})
        .then(data => {
	    var menu = document.getElementById("whichsystest");
	    for (let i=0; i<menu.length; i++) {
		if (menu.options[i].value != 'LATEST' &&
		    !menu.options[i].value.startsWith('ARSARS_')) {
		    menu.remove(i);
		    i--;
		}
	    }

	    for (var test of data['latest_pks']) {
		var opt = document.createElement('option');
		opt.value = test['pk'];
                opt.innerHTML = test['time'] +" -- "+test['test_type'] +" ("+test['env']+")";
		menu.append(opt);
	    }
	})
        .catch(error => {
	    div.append("ERROR: "+error);
	    console.error(error);
	});

}

function retrieveSysTestResults(testid=null) {
    var test_pk = testid ? testid : document.getElementById("whichsystest").value;

    var systest_node = document.getElementById("systest_container");
    systest_node.innerHTML = '';
    systest_node.className = '';

    var wspan = document.getElementById("systest_wait");
    wspan.innerHTML = '';
    var wait = getAnimatedWaitBar("100px");
    wait.style.marginRight = "10px";
    wspan.append(wait);
    wspan.append('Loading...');

    var apiurl = 'https://utility.ci.transltr.io/arstest/api/';
    if (test_pk.startsWith("ARSARS_"))
	apiurl = 'https://arax.ncats.io/devLM/ARS-testing/artifacts/results/test_run_'+test_pk.split("_")[1]+'_results.json';
    else if (test_pk == "LATEST")
	apiurl += 'latest_report';
    else
	apiurl += 'report/'+test_pk;


    fetch(apiurl)
        .then(response => {
	    if (response.ok) return response.json();
	    else throw new Error('Unable to fetch ARS Translator system test results from '+apiurl);
	})
        .then(data => {
            wspan.innerHTML = '<b>Report source:</b> '+apiurl;
	    systest_node.innerHTML = '';

	    if (test_pk.startsWith("ARSARS_")) {
		displayARSResults(systest_node,data);
		systest_node.append(document.createElement("br"));
		retrieveTestRunnerResultsList(test_pk);
		return;
	    }


	    var tests = {};
	    if ('fields' in data)
		tests[data['fields']['test_type']+"_["+data['fields']['timestamp']+"]"] = data;
	    else
		tests = data;

	    for (var test in tests) {
		var div = document.createElement("div");
		div.className = "statushead";
		div.append("Viewing: "+ test);

		systest_node.append(div);

		div = document.createElement("div");
		div.className = "status";
		systest_node.append(div);

		if (test.startsWith("Load"))
		    div.append(generateLoadTimeTestResults(tests[test]['fields']));
		else
		    div.append(generateSmokeTestResults(tests[test]['fields']));

		div.append(document.createElement("br"));
	    }

	    systest_node.append(document.createElement("br"));
	    systest_node.append(document.createElement("br"));

        })
        .catch(error => {
            wspan.innerHTML = '';
	    systest_node.className = "error";
	    systest_node.innerHTML = "<br>" + error + "<br><br>";
            console.error(error);
	});

    if (test_pk == "LATEST")
	retrieveSysTestResultsList(20);
}


function generateSmokeTestResults(smoketestfields) {
    if (smoketestfields['data'] == null) {
	var h2 = document.createElement("h2");
        h2.append("-- No Data --");
	return h2;
    }

    var tdiv = document.createElement("div");

    var checknames = false;
    if (smoketestfields['parameters']) {
	smoketestfields['parameters']['Environment'] = smoketestfields['environment'];
	tdiv.append("Parameters::");
	for (var param in smoketestfields['parameters']) {
	    var span = document.createElement("span");
	    span.style.fontWeight = "bold";
	    span.style.marginLeft = '10px';
	    span.append(param+": ");
	    tdiv.append(span);
	    if (param.includes("curie")) {
		if (!Array.isArray(smoketestfields['parameters'][param]))
		    smoketestfields['parameters'][param] = [ smoketestfields['parameters'][param] ];

		var comma = '';
		for (var mol of smoketestfields['parameters'][param]) {
		    tdiv.append(comma+mol+" (");
		    span = document.createElement("span");
		    span.id = smoketestfields['pk']+"_entityname_"+mol;
		    span.title = mol;
		    if (entities[mol])
			span.append(entities[mol].name);
		    else {
			checknames = true;
			entities[mol] = {};
			entities[mol].checkHTML = '--';
			span.append(' --- ');
		    }
		    tdiv.append(span);
		    tdiv.append(") ");
		    comma = ', ';
		}
	    }
	    else
		tdiv.append(smoketestfields['parameters'][param]);

	}
	tdiv.append(document.createElement("br"));
	tdiv.append(document.createElement("br"));
    }


    if (smoketestfields['data']['analysis']) {
	for (var querytest in smoketestfields['data']['analysis']) {
            var table = renderSmokeTestTable(smoketestfields['data']['analysis'][querytest],'Test: '+querytest);
	    tdiv.append(table);
	    tdiv.append(document.createElement("br"));
	    tdiv.append(document.createElement("br"));
	}
    }
    else {
	var table = renderSmokeTestTable(smoketestfields['data'],'QUERY');
	tdiv.append(table);
	tdiv.append(document.createElement("br"));
	tdiv.append(document.createElement("br"));
    }

    if (checknames)
	check_entities_batch(99);

    tdiv.append("Legend:");
    var span = document.createElement("span");
    span.className = 'p9 qprob cytograph_controls';
    span.style.marginLeft = '10px';
    span.append("Pass");
    tdiv.append(span);
    span = document.createElement("span");
    span.className = 'p1 qprob cytograph_controls';
    span.style.marginLeft = '10px';
    span.style.marginRight = '10px';
    span.append("Fail");
    tdiv.append(span);
    tdiv.append("Number within bubble is ARS-normalized Score");

    return tdiv;
}


function renderSmokeTestTable(smoketestdata,qtest) {
    var all_agents = {};
    for (var queryname in smoketestdata) {
	for (var actor in smoketestdata[queryname]['actors'])
	    all_agents[actor] = 1;
    }

    var table = document.createElement("table");
    table.className = 'sumtab';

    var tr = document.createElement("tr");
    var td = document.createElement("th");
    td.style.textTransform = 'initial';
    td.append(qtest);
    tr.append(td);
    for (var agent of Object.keys(all_agents).sort()) {
	td = document.createElement("th");
	td.style.minWidth = '80px';
        td.append(agent.replace(/ars-|ara-|kp-/,""));
	tr.append(td);
    }
    table.append(tr);

    for (var queryname in smoketestdata) {
	tr = document.createElement("tr");
	td = document.createElement("td");

	if (smoketestdata[queryname]['parent_pk']) {
	    var link = document.createElement("a");
	    link.title = 'view this response';
            link.style.fontFamily = "monospace";
	    link.style.textTransform = 'initial';
	    link.style.cursor = "pointer";
	    link.setAttribute('onclick', 'pasteId("'+smoketestdata[queryname]['parent_pk']+'");sendId(false);selectInput("qid");');
	    link.append(queryname);
	    td.append(link);
	}
	else
	    td.append(queryname);
	tr.append(td);

	for (var agent of Object.keys(all_agents).sort()) {
	    td = document.createElement("td");
	    td.style.borderLeft = "1px solid black";
	    td.style.textAlign = 'right';

	    for (var ara in smoketestdata[queryname]['actors']) {
		if (ara == agent) {
		    var obj = smoketestdata[queryname]['actors'][ara];
		    var pcl = obj['drug_report'] == "pass" ? "p9" : "p1";

		    var span = document.createElement("span");
		    span.className = pcl+' qprob cytograph_controls';
		    span.append(Number(obj['score']).toFixed(2));
		    td.append(span);
		    td.title = obj['drug_report'];
		}
	    }
	    tr.append(td);
	}
	table.append(tr);
    }

    return table;
}


function generateLoadTimeTestResults(loadtestdata) {
    if (loadtestdata['data'] == null) {
	var h2 = document.createElement("h2");
	h2.append("-- No Data --");
	return h2;
    }

    var tdiv = document.createElement("div");

    var all_agents = {};
    for (var q in loadtestdata['data']) {
	var obj = loadtestdata['data'][q];
	if (obj['stragglers'])
	    for (var actor of obj['stragglers'])
		all_agents[actor] = 1;

	for (var actor in obj['actors'])
            all_agents[actor] = 1;
    }

    if (loadtestdata['parameters']) {
	loadtestdata['parameters']['Environment'] = loadtestdata['environment'];
	tdiv.append("Parameters::");
	for (var param in loadtestdata['parameters']) {
	    var span = document.createElement("span");
	    span.style.fontWeight = "bold";
	    span.style.marginLeft = '10px';
	    span.append(param+": ");
            tdiv.append(span);
            tdiv.append(loadtestdata['parameters'][param]);
	}
	tdiv.append(document.createElement("br"));
	tdiv.append(document.createElement("br"));
    }

    var table = document.createElement("table");
    table.className = 'sumtab';

    var tr = document.createElement("tr");
    var td = document.createElement("th");
    tr.append(td);
    //td = document.createElement("th");
    //td.innerText = 'PK';
    //tr.appendChild(td);
    td = document.createElement("th");
    td.append('Query');
    tr.append(td);
    td = document.createElement("th");
    td.append('Time');
    tr.append(td);

    for (var agent of Object.keys(all_agents).sort()) {
	td = document.createElement("th");
	td.colSpan = '2';
	td.style.minWidth = '80px';
	td.append(agent.replace(/ars-|ara-|kp-/,""));
	tr.append(td);
    }
    table.append(tr);

    var num = 0;
    for (var q in loadtestdata['data']) {
        var obj = loadtestdata['data'][q];
        num++;
	tr = document.createElement("tr");
        tr.className = 'hoverable';

	td = document.createElement("td");
	td.rowSpan = '2';
        td.append(num+'.');
	tr.append(td);

        td = document.createElement("td");
	td.rowSpan = '2';
	var link = document.createElement("a");
	link.title = 'view this response';
	link.style.cursor = "pointer";
	link.style.fontFamily = "monospace";
	link.setAttribute('onclick', 'pasteId("'+obj['parent_pk']+'");sendId(false);selectInput("qid");');
	link.append(q);
	td.append(link);
	tr.append(td);

        td = document.createElement("td");
	td.style.fontWeight = 'bold';
        td.style.textAlign = 'right';
	td.append(Number(obj["completion_time"]).toFixed(1));
	td.title = obj["completion_time"] + " seconds";
	tr.append(td);

	for (var agent of Object.keys(all_agents).sort()) {
	    td = document.createElement("td");
            td.style.borderLeft = "1px solid black";
	    td.style.textAlign = 'right';
	    var span = document.createElement("span");

            if (obj['actors'][agent]) {
		if (obj['stragglers'] && obj['stragglers'].includes(agent))
		    td.append("\u{1F422}");
		if (obj['actors'][agent]['status'] == "Done") {
		    span.innerHTML = '&check;';
		    if (obj['actors'][agent]['n_results'] > 0)
			span.className = 'explevel p9';
		    else
			span.className = 'explevel p0';
		}
                else if (obj['actors'][agent]['status'] == "Error") {
                    span.innerHTML = '&cross;';
		    span.className = 'explevel p1';
		}
                else {
		    span.append(obj['actors'][agent]['status']);
		}
                td.append(span);
		td.title = obj['actors'][agent]['status'];
                if (obj['stragglers'] && obj['stragglers'].includes(agent))
		    td.title += " (straggler)";

	    }
            else
		td.append('n/a');
	    tr.append(td);

            td = document.createElement("td");
	    td.style.textAlign = 'right';
            if (obj['actors'][agent] && obj['actors'][agent]['completion_time']) {
		td.append(Number(obj['actors'][agent]['completion_time']).toFixed(3));
		if (obj['actors'][agent]['completion_time'] == obj["completion_time"])
		    td.className = 'essence';
	    }
            else if (obj['actors'][agent] && obj['actors'][agent]['status'] == "Error")
		td.append('E');
	    else
		td.append('n/a');

	    if (obj['actors'][agent])
		td.title = (obj['actors'][agent]['n_results'] ? obj['actors'][agent]['n_results'] : "No") + " results";
	    else
		td.title = "no actor: "+agent;

	    tr.append(td);
	}

	table.append(tr);

	if (obj['merge_report']) {
            tr = document.createElement("tr");
	    tr.style.backgroundColor = 'initial';
            tr.className = 'hoverable';

	    td = document.createElement("td");
	    td.append("Merge:");
	    tr.append(td);

            for (var agent of Object.keys(all_agents).sort()) {
		td = document.createElement("td");
		td.style.borderLeft = "1px solid black";
		td.style.textAlign = 'left';
		if (obj['merge_report'][agent])
		    td.append(obj['merge_report'][agent]['status']);
		else
		    td.append('NA');
		tr.append(td);

		td = document.createElement("td");
		td.style.textAlign = 'right';
                if (obj['merge_report'][agent])
		    td.append(obj['merge_report'][agent]['completion_time'].toFixed(2));
		else
		    td.append('');
		tr.append(td);
	    }

	    table.append(tr);
	}
    }

    tdiv.append(table);
    tdiv.append(document.createElement("br"));
    tdiv.append(document.createElement("br"));
    tdiv.append("Legend:");
    var span = document.createElement("span");
    span.className = 'explevel p9';
    span.style.marginLeft = '10px';
    span.innerHTML = '&check;';
    tdiv.append(span);
    tdiv.append(" Done (mouse-over to see number of results)");
    span = document.createElement("span");
    span.className = 'explevel p0';
    span.style.marginLeft = '10px';
    span.innerHTML = '&check;';
    tdiv.append(span);
    tdiv.append(" Done, with ZERO results");
    span = document.createElement("span");
    span.className = 'explevel p1';
    span.style.marginLeft = '10px';
    span.innerHTML = '&cross;';
    tdiv.append(span);
    tdiv.append(" Error");
    tdiv.append("\u00A0\u00A0\u00A0\u{1F422} Straggler");
    tdiv.append("\u00A0\u00A0\u00A0Number is completion time (sec)");

    return tdiv;
}



function displayARSResults(parentnode,arsdata) {
    var test2css = {};
    test2css['TopAnswer'] = 'p9';
    test2css['Acceptable'] = 'p7';
    test2css['BadButForgivable'] = 'p3';
    test2css['NeverShow'] = 'p1';
    test2css['OverlyGeneric'] = 'p0';

    var hint = {};
    hint['TopAnswer'] = 'Result must be in the top 30 or top 10% of answers, whichever is greater';
    hint['Acceptable'] = 'Result must be in the top 50% of answers';
    hint['BadButForgivable'] = 'Result must NOT be in the top 50%';
    hint['NeverShow'] = 'Result must NOT appear anywhere in the answers';
    hint['OverlyGeneric'] = 'Overly. Generic.';

    var stats = {};
    stats.test_type = {};
    stats.test_case = {};
    stats.status_list = {};
    stats.status_list['PASSED'] = 1;
    stats.status_list['FAILED'] = 1;
    stats.status_list['No results'] = 1;
    for (var agent of arsdata['ara_list']) {
	stats[agent] = {};
	stats[agent]['PASSED'] = 0;
	stats[agent]['TOTAL'] = 0;
    }

    var tdiv = document.createElement("div");
    var sumtable = document.createElement("table");
    sumtable.id = 'arssummary_table'
    sumtable.className = 'sumtab';
    tdiv.append(sumtable);
    tdiv.append(document.createElement("br"));

    var table = document.createElement("table");
    table.id = 'arsresults_table'
    table.className = 'sumtab';

    var tr = document.createElement("tr");
    tr.dataset.qstatus = "COLUMNHEADER";
    var td;

    for (var head of ["","Name","Test Type","Test Case","Test Asset"]) {
	td = document.createElement("th");
	td.append(head);

        if (head == "Test Type") {
	    td.id = 'filter_test_type';
	    td.dataset.filterstring = '';
	}
        else if (head == "Test Case") {
	    td.id = 'filter_test_case';
	    td.dataset.filterstring = '';
	}
	tr.append(td);
    }

    for (var agent of arsdata['ara_list']) {
	td = document.createElement("th");
        td.id = 'filter_'+agent.toLowerCase();
	td.style.minWidth = '80px';
        td.dataset.filterstring = '';
	td.append(agent);
	tr.append(td);
    }
    table.append(tr);

    var num = 0;
    for (var row of arsdata['row_data']) {
	num++;
	tr = document.createElement("tr");
	tr.className = 'hoverable';

	td = document.createElement("td");
	td.append(num+'.');
	tr.append(td);

	td = document.createElement("td");
	td.style.textAlign = "right";
	var link = document.createElement("a");
        link.style.cursor = "pointer";
	link.target = "_radiator";
	if (row.pk) {
            link.title = 'view results in ARAX GUI';
	    link.href = row.pk;
	}
	else {
            link.title = 'view in information radiator';
	    link.href = row.url;
	}
	link.append(row.name.split(":")[1]);
	td.append(link);
	tr.append(td);

	var ttype = row.name.split(":")[0];
        td = document.createElement("td");
	td.title = hint[ttype];
        td.dataset.value = ttype;
        if (stats['test_type'][ttype])
	    stats['test_type'][ttype]++;
	else
	    stats['test_type'][ttype] = 1;

	var span = document.createElement("span");
	span.className = test2css[ttype] + " explevel";
	span.append(ttype);
        td.append(span);
        tr.append(td);

        td = document.createElement("td");
        td.dataset.value = row.TestCase;
	if (stats['test_case'][row.TestCase])
	    stats['test_case'][row.TestCase]++;
	else
	    stats['test_case'][row.TestCase] = 1;

	if (row.TestCase) {
	    link = document.createElement("a");
            link.target = "_radiator";
            link.title = 'view test JSON';
	    link.href = 'https://github.com/NCATSTranslator/Tests/blob/main/test_cases/'+row.TestCase+'.json';
	    link.append(row.TestCase);
	    td.append(link);
	}
	else {
	    td.className = 'msgWARNING';
	    td.append("--- empty ---");
	}
	tr.append(td);

        td = document.createElement("td");
        if (row.TestAsset) {
            link = document.createElement("a");
	    link.target = "_radiator";
	    link.title = 'view asset JSON';
	    link.href = 'https://github.com/NCATSTranslator/Tests/blob/main/test_assets/'+row.TestAsset+'.json';
            link.append(row.TestAsset);
	    td.append(link);
	}
	else {
            td.className = 'msgWARNING';
	    td.append("--- empty ---");
	}
	tr.append(td);


	for (var agent of arsdata['ara_list']) {
            td = document.createElement("td");
	    td.style.borderLeft = "1px solid black";
	    td.style.textAlign = 'center';
            td.dataset.value = row[agent];

	    stats.status_list[row[agent]] = 1;
            if (stats[agent][row[agent]])
		stats[agent][row[agent]]++;
	    else
		stats[agent][row[agent]] = 1;

	    var span = document.createElement("span");

	    if (row[agent] && row[agent] != '') {
		if (row[agent] == 'FAILED') {
                    span.innerHTML = '&cross;';
		    span.className = 'explevel p1';
		}
                else if (row[agent] == 'PASSED') {
                    span.innerHTML = '&check;';
		    span.className = 'explevel p9';
		}
		else if (row[agent] == 'No results') {
		    span.innerHTML = '0';
		    span.className = 'explevel p0';
		}
                else if (row[agent] == 'Timed out') {
                    span.innerHTML = 'T';
		    span.className = 'explevel p3';
		}
                else if (row[agent].startsWith('Status code:')) {
		    span.innerHTML = row[agent].split(":")[1];
                    span.className = 'explevel p3';
		}
		else {
		    span.innerHTML = row[agent];
		}

                td.append(span);
		td.title = agent+" :: "+row[agent];
	    }
	    else {
		td.append('[[ n/a ]]');
	    }

	    tr.append(td);
	}

	table.append(tr);
    }

    tdiv.append(table);
    tdiv.append(document.createElement("br"));


    tr = document.createElement("tr");
    for (var agent of ['Status Summary'].concat(arsdata['ara_list'])) {
	td = document.createElement("th");
	td.colSpan = '2';
	td.style.minWidth = '80px';
	td.append(agent);
	tr.append(td);
    }
    sumtable.append(tr);

    stats.status_list['TOTAL'] = 1;
    for (var status in stats.status_list) {
	tr = document.createElement("tr");
        tr.className = 'hoverable';

        td = document.createElement("td");
	span = document.createElement("span");
	if (status == 'FAILED') {
	    span.innerHTML = '&cross;';
	    span.className = 'explevel p1';
	}
	else if (status == 'PASSED') {
	    span.innerHTML = '&check;';
	    span.className = 'explevel p9';
	}
	else if (status == 'No results') {
	    span.innerHTML = '0';
	    span.className = 'explevel p0';
	}
	else if (status == 'Timed out') {
	    span.innerHTML = 'T';
	    span.className = 'explevel p3';
	}
	else if (status.startsWith('Status code:')) {
	    span.innerHTML = status.split(":")[1];
	    span.className = 'explevel p3';
	}
	else if (status == 'TOTAL') {
	    tr.style.borderTop = "2px solid black";
	}
        td.append(span);
	tr.append(td);

	td = document.createElement("td");
	td.className = 'fieldname';
	td.append(status);
	tr.append(td);

	for (var agent of arsdata['ara_list']) {
	    td = document.createElement("td");
            td.style.borderLeft = "1px solid black";
            td.style.textAlign = "right";
            td.append((stats[agent][status]!=null) ? stats[agent][status] : '.');
	    tr.append(td);

	    td = document.createElement("td");
	    if (status == 'PASSED') {
		var cnf = (100*Number(stats[agent][status])/num).toFixed(1);
		var passing = document.getElementById("whichsystest").options[document.getElementById("whichsystest").selectedIndex].text.includes("Sprint 4") ? 40 : 350;
		var pcl = Number(stats[agent][status])>=passing ? "p9" : Number(stats[agent][status])>=(passing/2) ? "p3" : "p1";

		td.title = 'Current Translator goal of '+passing+' passing tests :: ';
		td.title += (pcl == 'p9') ? 'YES':'NO';
		span = document.createElement("span");
		span.className = 'explevel '+pcl;
		span.append(cnf+"%");
		td.append(span);
	    }
	    tr.append(td);

	    if (status != 'TOTAL' && stats[agent][status]!=null)
		stats[agent]['TOTAL'] += stats[agent][status];
	}
	sumtable.append(tr);
    }

    parentnode.append(tdiv);

    for (var filterfield of arsdata['ara_list'].concat(['test_type','test_case']) ) {
	if (Object.keys(stats[filterfield]).length > 1) {
	    add_filtermenu('arsresults_table',filterfield, stats[filterfield]);
	}
    }
}


function show_hide(ele, span) {
    var disp = 'none';
    if (span.classList.contains('hide')) {
	disp = '';
	span.classList.remove('hide');
    }
    else {
	span.classList.add('hide');
    }

    document.getElementById(ele).style.display = disp;
}


function add_user_msg(what,code="WARNING",remove=true) {
    var div = document.createElement("div");
    div.className = 'msg'+code;
    div.style.color = "#eee";
    div.innerHTML = what;

    var span = document.createElement("span");
    span.className = 'bigx';
    span.title = "dismiss this message";
    span.innerHTML = "&times;"
    span.onclick= function(){div.remove();};
    div.append(span);

    document.getElementById("useralerts").append(div);

    if (remove) {
        setTimeout(function() { div.style.opacity = "0"; }, 3000 );
        setTimeout(function() { div.remove(); }, 3500 );
    }
    return null;
}


function add_to_dev_info(title,jobj) {
    var dev = document.getElementById("devdiv");
    dev.append(document.createElement("br"));
    dev.append('='.repeat(80)+" "+title+"::");
    var pre = document.createElement("pre");
    //pre.id = "responseJSON";
    pre.append(JSON.stringify(jobj,null,2));
    dev.append(pre);
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
	listhtml = "<table class='sumtab'><tr><th></th><th></th><th>Name</th><th></th><th>Item</th><th>Category</th><th>Action</th></tr>" + listhtml + "</table><br><br>";
	document.getElementById("menunumlistitems"+listId).classList.add("numnew");
	document.getElementById("menunumlistitems"+listId).classList.remove("numold");
    }
    else {
	document.getElementById("menunumlistitems"+listId).classList.remove("numnew");
	document.getElementById("menunumlistitems"+listId).classList.add("numold");
    }

    listhtml = "Items in this List can be compared to those in the other List, or added to a node in the query_graph via the bulk import functionality.<br><br>" + listhtml + "<hr>Enter new list item or items (space and/or comma-separated; use &quot;double quotes&quot; for multi-word items):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' onkeydown='enter_item(this, \""+listId+"\");' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>";

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
	comparediv.append(document.createElement("br"));
	comparediv.append("Items in lists A and B will be automatically displayed side-by-side for ease of comparison.");
        comparediv.append(document.createElement("br"));
	comparediv.append(document.createElement("br"));
	comparediv.append("At least one item is required in each list.");
        comparediv.append(document.createElement("br"));
	comparediv.append(document.createElement("br"));
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
    comparediv.append(button);

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
    sel.append(opt);
    opt = document.createElement('option');
    opt.style.borderBottom = "1px solid black";
    opt.value = "true";
    if (uniqueonly) opt.selected = true;
    opt.innerHTML = "Show only unique items";
    sel.append(opt);
    span.append(sel);
    comparediv.append(span);

    comparediv.append(document.createElement("br"));
    comparediv.append(document.createElement("br"));

    var comptable = document.createElement("table");
    comptable.className = 'sumtab';
    var tr = document.createElement("tr");
    var td = document.createElement("th");
    tr.append(td);
    td = document.createElement("th");
    td.append("List A");
    tr.append(td);
    td = document.createElement("th");
    tr.append(td);
    td = document.createElement("th");
    td.append("List B");
    tr.append(td);
    comptable.append(tr);

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
        td.append(span);
        tr.append(td);
        td = document.createElement("td");
	td.innerHTML = keysA[idx]?keysA[idx]:'--n/a--';
	tr.append(td);

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
	td.append(span);
	tr.append(td);
	td = document.createElement("td");
	td.innerHTML = keysB[idx]?keysB[idx]:'--n/a--';
	tr.append(td);

	comptable.append(tr);
	compare_tsv.push(keysA[idx]+"\t"+keysB[idx]);
    }

    comparediv.append(comptable);
    comparediv.append(document.createElement("br"));
    comparediv.append(document.createElement("br"));
}


// unused at the moment
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
// unused at the moment
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
            nitem = nitem.replace(/['"]+/g,''); // remove quotes
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
    var itemarr = document.getElementById("newlistitem"+listId).value.match(/\w+:?\w+|"[^"]+"/g);

    document.getElementById("newlistitem"+listId).value = '';
    for (var item in itemarr) {
	itemarr[item] = itemarr[item].replace(/['"]+/g,''); // remove quotes
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
    var thisbatch = [];
    for (var entity in entities) {
	if (entities[entity].checkHTML != '--') continue;
	if (thisbatch.length == batchsize) {
	    batches.push(thisbatch);
	    thisbatch = [];
	}
	thisbatch.push(entity);
    }
    // last one
    if (thisbatch) batches.push(thisbatch);

    for (let batch of batches) {
	if (batch.length < 1)
	    continue;
	fetch(providers["ARAX"].url + "/entity", {
	    method: 'post',
	    body: JSON.stringify({"format":"minimal","terms":batch}),
	    headers: { 'Content-type': 'application/json' }
	})
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
			document.getElementById("devdiv").innerHTML += data[entity].id.category+"<br>";
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

	fetch(providers["ARAX"].url + "/entity?q=" + entity)
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
		    document.getElementById("devdiv").innerHTML += data[entity].id.category+"<br>";
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


async function check_entity(term,wantall,maxsyn=0,getgraph=false) {
    var data = {};
    var ent  = {};
    ent.found = false;

    if (!wantall && entities[term]) {
        if (!entities[term].isvalid)
            return ent; // contains found=false

	data = entities[term];
    }
    else {
	var queryObj = {};
	queryObj['terms'] = [term];
	if(maxsyn > 0)
	    queryObj['max_synonyms'] = maxsyn;
	if(!getgraph)
	    queryObj['format'] = 'slim';

	var response = await fetch(providers["ARAX"].url + "/entity", {
	    method: 'post',
	    body: JSON.stringify(queryObj),
	    headers: { 'Content-type': 'application/json' }
	});
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
            listhtml += "<tr><td>"+li+".</td><td>";
            listhtml += "<a target='_blank' title='view this response in a new window' href='//"+ window.location.hostname + window.location.pathname + "?r="+listItems[listId][li] + "'>" + listItems['SESSION']["qtext_"+li] + "</a>";
	    listhtml += "</td><td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/>Remove</a></td></tr>";
        }
    }
    if (numitems > 0) {
        listhtml += "<tr style='background-color:unset;'><td style='border-bottom:0;'></td><td style='border-bottom:0;'></td><td style='border-bottom:0;'><a href='javascript:delete_list(\""+listId+"\");'/> Delete Session History </a></td></tr>";
    }

    if (numitems == 0)
        listhtml = "<br>Your query history will be displayed here. It can be edited or re-set.<br><br>";
    else
        listhtml = "<table class='sumtab'><tr><th></th><th>Query</th><th>Action</th></tr>" + listhtml + "</table><br><br>";

    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("menunumlistitems"+listId).innerHTML = numitems;
    document.getElementById("listdiv"+listId).innerHTML = listhtml;
}


function display_cache() {
    var listId = 'CACHE';
    var listhtml = '';
    var numitems = 0;
    var totbytes = 0;

    for (var pid in response_cache) {
        numitems++;
	var size = new TextEncoder().encode(JSON.stringify(response_cache[pid])).length;
	totbytes += size;
	size = human_readable_size(size);
        listhtml += "<tr><td>"+numitems+".</td><td style='font-family:monospace;'>"+pid+"</td><td>"+size+"</td><td><a href='javascript:remove_from_cache(\"" + pid +"\");'/>Remove</a></td></tr>";
	if (document.getElementById("cachelink_"+pid))
	    document.getElementById("cachelink_"+pid).innerHTML = "<a href='javascript:remove_from_cache(\"" + pid +"\");'/>Clear</a>";
    }

    if (numitems == 0) {
        listhtml = "<br>A list of cached responses will be displayed here. It can be edited or re-set.<br><br>";
    }
    else {
        listhtml = "<table class='sumtab'><tr><th></th><th>Response Id</th><th>Size</th><th>Action</th></tr>" + listhtml;
        listhtml += "<tr style='background-color:unset;'><td style='border-bottom:0;'></td><td style='border-bottom:0;'></td><td style='border-bottom:0;'>"+human_readable_size(totbytes)+"</td><td style='border-bottom:0;'><a href='javascript:delete_cache();'/> Delete All Cached Responses </a></td></tr>";
        listhtml += "</table><br><br>";
    }

    document.getElementById("numlistitems"+listId).innerHTML = numitems;
    document.getElementById("listdiv"+listId).innerHTML = listhtml;
}

function human_readable_size(what) {
    var units = " bytes";
    if (what > 512) {
	what /= 1024;
	units = " kB";
	if (what > 512) {
	    what /= 1024;
	    units = " MB";
	}
	what = Number(what).toFixed(2);
    }
    return what+units;
}


function remove_from_cache(item) {
    delete response_cache[item];
    if (document.getElementById("cachelink_"+item))
	document.getElementById("cachelink_"+item).innerHTML = '';
    display_cache();
}
function delete_cache(item) {
    response_cache = {};
    display_cache();
}

function enter_url(ele, urlkey) {
    if (event.key === 'Enter')
	update_url(urlkey,null);
    else
	update_submit_button(urlkey);
}
function update_url(urlkey,value) {
    if (value)
	document.getElementById(urlkey+"_url").value = value;

    if (urlkey == 'timeout') {
	var to = parseInt(document.getElementById(urlkey+"_url").value.trim());
	if (isNaN(to))
	    to = '30';
	UIstate[urlkey] = to;
	document.getElementById(urlkey+"_url").value = UIstate[urlkey];
    }
    else if (urlkey == 'pruning') {
	var to = parseInt(document.getElementById(urlkey+"_url").value.trim());
	if (isNaN(to))
	    to = '50';
	UIstate[urlkey] = to;
	document.getElementById(urlkey+"_url").value = UIstate[urlkey];
    }
    else if (urlkey == 'maxresults') {
        var mx = parseInt(document.getElementById(urlkey+"_url").value.trim());
	if (isNaN(mx))
	    mx = 1000;
	UIstate[urlkey] = mx;
	document.getElementById(urlkey+"_url").value = UIstate[urlkey];
    }
    else if (urlkey == 'maxsyns') {
        var sy = parseInt(document.getElementById(urlkey+"_url").value.trim());
        if (isNaN(sy))
	    sy = 1000;
        UIstate[urlkey] = sy;
        document.getElementById(urlkey+"_url").value = UIstate[urlkey];
    }
    else if (urlkey == 'submitter') {
	UIstate[urlkey] = document.getElementById(urlkey+"_url").value.trim();
        document.getElementById(urlkey+"_url").value = UIstate[urlkey];
    }
    else {
	providers[urlkey].url = document.getElementById(urlkey+"_url").value.trim();
	document.getElementById(urlkey+"_url").value = providers[urlkey].url;
    }
    addCheckBox(document.getElementById(urlkey+"_url_button"),true);
    var timeout = setTimeout(function() { document.getElementById(urlkey+"_url_button").disabled = true; } , 1500 );
}
function update_submit_button(urlkey) {
    var currval = (urlkey == 'submitter' || urlkey == 'timeout' || urlkey == 'pruning' || urlkey == 'maxresults' || urlkey == 'maxsyns') ? UIstate[urlkey] : providers[urlkey].url;

    if (currval == document.getElementById(urlkey+"_url").value)
	document.getElementById(urlkey+"_url_button").disabled = true;
    else
	document.getElementById(urlkey+"_url_button").disabled = false;
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
    document.body.append(dummy);
    dummy.setAttribute("id", "dummy_id");
    for (var line of tsv)
	document.getElementById("dummy_id").value+=line+"\n";
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);

    addCheckBox(ele,true);
}


function downloadCyto(gid,format='json') {
    if (!cyobj[gid])
        return add_user_msg("Unable to download.  Data not found.","ERROR",true);

    try {
	var filename = "ARAX_"+gid+'_network';

	var downloadLink = document.createElement('a');
	downloadLink.target = '_blank';
	downloadLink.download = filename + '.' + format;

        var URL = window.URL || window.webkitURL;

	if (format == 'png') {
	    var blob = cyobj[gid].png({output:"blob"});
            var downloadUrl = URL.createObjectURL(blob);
            downloadLink.href = downloadUrl;
	}
	else {
	    downloadLink.href = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(cyobj[gid].json()));
	}

        downloadLink.click();
        downloadLink.remove();
    }
    catch(e) {
        add_user_msg("Unable to download: "+e,"ERROR",false);
    }

}


function addCheckBox(ele,remove) {
    var check = document.createElement("span");
    check.className = 'explevel p9';
    check.innerHTML = '&check;';
    ele.parentNode.insertBefore(check, ele.nextSibling);

    if (remove)
	var timeout = setTimeout(function() { check.remove(); }, 1500 );
}

function getAnimatedWaitBar(width) {
    var wait = document.createElement("span");
    wait.className = 'loading_cell';
    if (width)
	wait.style.width = width;
    var waitbar = document.createElement("span");
    waitbar.className = 'loading_bar';
    wait.append(waitbar);
    return wait;
}

function submit_on_enter(ele) {
    if (event.key === 'Enter') {
	if (ele.id == 'newsynonym')
	    sendSyn();
	else if (ele.id == 'newquerynode')
            qg_add_curie_to_qnode();
        else if (ele.id == 'qedgepredicatebox')
            qg_add_predicate_to_qedge(ele.value);
        else if (ele.id == 'qftime')
	    retrieveRecentQs(false);
        else if (ele.id == 'howmanylatest')
	    retrieveRecentResps();
	else
	    console.log("element id not recognized...");
    }
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
    div.append("Version Alert");
    popup.append(div);

    div = document.createElement("div");
    div.className = 'status error';
    div.append(document.createElement("br"));
    div.append("You are using an out-of-date version of this interface ("+UIstate["version"]+")");
    div.append(document.createElement("br"));
    div.append(document.createElement("br"));
    div.append("Please use the Reload button below to load the latest version ("+version+")");
    div.append(document.createElement("br"));
    div.append(document.createElement("br"));
    div.append(document.createElement("br"));
    popup.append(div);

    var button = document.createElement("input");
    button = document.createElement("input");
    button.className = "questionBox button";
    button.type = "button";
    button.title = 'Reload to update';
    button.value = 'Reload';
    button.setAttribute('onclick', 'window.location.reload();');
    popup.append(button);

    button = document.createElement("input");
    button.className = "questionBox button";
    button.style.float = "right";
    button.type = "button";
    button.title = 'Dismiss alert';
    button.value = 'Dismiss';
    button.setAttribute('onclick', 'document.body.removeChild(document.getElementById("valert"))');
    popup.append(button);

    dragElement(popup);
    document.body.append(popup);
}


function allowDrop(event) {
    event.preventDefault();
    event.target.classList.add("drophere");
}
function stopDrop(event) {
    event.preventDefault();
    event.target.classList.remove("drophere");
}
function dropFile(where,event) {
    stopDrop(event);

    if (!event.dataTransfer.files)
        return false;

    var file = event.dataTransfer.files[0];
    reader = new FileReader();

    if (where == 'response' || where == 'jsoninput') {
	reader.onload = function(ev) {
            event.target.value = ev.target.result;
            const lineCount = ev.target.result.split('\n').length;
            document.getElementById("statusdiv").append(document.createElement("br"));
            document.getElementById("statusdiv").append("Read in "+lineCount+" lines from dropped file.");
            document.getElementById("statusdiv").append(document.createElement("br"));
            add_user_msg("Read in "+lineCount+" lines from dropped file", "INFO");
	};
    }
    else if (where == 'araxtest') {
        reader.onload = function(ev) {
	    var systest_node = document.getElementById("systest_container");
	    systest_node.innerHTML = '';
	    systest_node.className = '';
	    document.getElementById("systest_wait").innerHTML = '<strong>Dropped file:</strong> <i>'+event.dataTransfer.files[0].name+'</i>';
	    try {
		displayARSResults(systest_node,JSON.parse(ev.target.result));
	    }
	    catch(e) {
		systest_node.append(document.createElement("br"));
		systest_node.append(document.createElement("br"));
		var span = document.createElement("span");
		span.className = 'error';
		span.append("Error parsing results JSON : ");
                systest_node.append(document.createElement("br"));
		systest_node.append(document.createElement("br"));
		systest_node.append(span);
		span = document.createElement("span");
                span.className = 'error';
		span.append(e);
		systest_node.append(span);
	    }
	    systest_node.append(document.createElement("br"));
	};
    }

    reader.readAsText(file);
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

// from stackoverflow.com/questions/65824393/make-short-hash-from-long-string
//  and gist.github.com/jlevy/c246006675becc446360a798e2b2d781
function hashCode(s) {
    for (var h = 0, i = 0; i < s.length; h &= h)
	h = 31 * h + s.charCodeAt(i++);
    //return h;
    return new Uint32Array([h])[0].toString(36);
}


// from https://askjavascript.com/how-to-convert-gmt-to-local-time-in-javascript/
function convertUTCToLocal(date) {
    var gmtDate = new Date(date);
    return gmtDate.toLocaleString("en-US",{dateStyle:"medium",timeStyle:"long"});
}
