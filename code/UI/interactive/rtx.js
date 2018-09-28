var cyobj = [];
var cytodata = [];
var fb_explvls = [];
var fb_ratings = [];
var response_id = null;
var summary_table_html = '';
var columnlist = [];

function sesame(head,content) {
    if (head == "openmax") {
	content.style.maxHeight = content.scrollHeight + "px";
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


function pasteQuestion(question) {
    document.getElementById("questionForm").elements["questionText"].value = question;
    document.getElementById("qqq").value = '';
    document.getElementById("qqq").blur();
}

function sendQuestion(e) {
    add_status_divs();
    document.getElementById("result_container").innerHTML = "";
    document.getElementById("summary_container").innerHTML = "";
    summary_table_html = '';
    cyobj = [];
    cytodata = [];

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

    // construct an HTTP request
    var xhr = new XMLHttpRequest();
    xhr.open("post", "api/rtx/v1/translate", true);
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');

    // send the collected data as JSON
    xhr.send(JSON.stringify(data));

    xhr.onloadend = function() {
	if ( xhr.status == 200 ) {
	    var jsonObj = JSON.parse(xhr.responseText);
	    document.getElementById("devdiv").innerHTML += "<PRE>\n" + JSON.stringify(jsonObj,null,2) + "</PRE>";

	    if ( jsonObj.query_type_id && jsonObj.terms ) {
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


			if ( jsonObj2["table_column_names"] ) {
			    add_to_summary(jsonObj2["table_column_names"],0);
			}
			if ( jsonObj2["result_list"] ) {
			    add_result(jsonObj2["result_list"]);
			    add_feedback();
			    //sesame(h1_div,a1_div);
			}
			else {
			    document.getElementById("result_container").innerHTML += "<H2>No results...</H2>";
			}

			if ( jsonObj2["table_column_names"] ) {
			    document.getElementById("summary_container").innerHTML = "<div onclick='sesame(null,summarydiv);' title='click to expand / collapse summary' class='statushead'>Summary</div><div class='status' id='summarydiv'><br><table class='sumtab'>" + summary_table_html + "</table><br></div>";

			}

		    }
		    else if ( jsonObj.message ) {
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


function add_status_divs() {
    document.getElementById("status_container").innerHTML = "<div onclick='sesame(null,statusdiv);' title='click to expand / collapse status' class='statushead'>Status</div><div class='status' id='statusdiv'></div>";

    document.getElementById("dev_result_json_container").innerHTML = "<div onclick='sesame(null,devdiv);' title='click to expand / collapse dev info' class='statushead'>Dev Info <i style='float:right; font-weight:normal;'>( json responses )</i></div><div class='status' id='devdiv'></div>";
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
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><br>"+reslist[i].text+"<br><br><span id='"+fid+"'><i>User Feedback</i></span></div>";

	}
	else {
	    document.getElementById("result_container").innerHTML += "<div id='a"+num+"_div' class='panel'><table class='t100'><tr><td class='textanswer'>"+reslist[i].text+"</td><td class='cytograph_controls'><a title='reset zoom and center' onclick='cyobj["+i+"].reset();'>&#8635;</a><br><a title='breadthfirst layout' onclick='cylayout("+i+",\"breadthfirst\");'>B</a><br><a title='force-directed layout' onclick='cylayout("+i+",\"cose\");'>F</a><br><a title='circle layout' onclick='cylayout("+i+",\"circle\");'>C</a><br><a title='random layout' onclick='cylayout("+i+",\"random\");'>R</a>	</td><td class='cytograph'><div style='height: 100%; width: 100%' id='cy"+num+"'></div></td></tr><tr><td><span id='"+fid+"'><i>User Feedback</i><hr><span id='"+fff+"'><a href='javascript:add_fefo(\""+rid+"\",\"a"+num+"_div\");'>Add Feedback</a></span><hr></span></td><td></td><td><div id='d"+num+"_div'><i>Click on a node or edge to get details</i></div></td></tr></table></div>";


	    if ( reslist[i].row_data ) {
		add_to_summary(reslist[i].row_data, num);
	    }

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
				    type   : gd.edge_list[g].type,
				    provided_by   : gd.edge_list[g].provided_by
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
		    'shape': function(ele) { return mapNodeShape(ele); } ,
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

	    document.getElementById(dnum).innerHTML = "<b>Name:</b> " + this.data('name') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>ID:</b> " + this.data('id') + "<br>";
	    document.getElementById(dnum).innerHTML+= "<b>URI:</b> <a target='_blank' href='" + this.data('uri') + "'>" + this.data('uri') + "</a><br>";
	    document.getElementById(dnum).innerHTML+= "<b>Type:</b> " + this.data('type') + "<br>";

	    if (this.data('description') !== 'UNKNOWN' && this.data('description') !== 'None') {
		document.getElementById(dnum).innerHTML+= "<b>Description:</b> " + this.data('description') + "<br>";
	    }

	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

	cyobj[i].on('tap','edge', function() {
	    var dnum = 'd'+this.data('parentdivnum')+'_div';

	    document.getElementById(dnum).innerHTML = this.data('source');
	    document.getElementById(dnum).innerHTML+= " <b>" + this.data('type') + "</b> ";
	    document.getElementById(dnum).innerHTML+= this.data('target') + "<br>";
            document.getElementById(dnum).innerHTML+= "<b>Provenance:</b> <a target='_blank' href='" + this.data('provided_by') + "'>" + this.data('provided_by') + "</a><br>";


	    sesame('openmax',document.getElementById('a'+this.data('parentdivnum')+'_div'));
	});

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
    if (ntype == "protein") { return "octagon";}
    if (ntype == "disease") { return "triangle";}
    if (ntype == "chemical_substance" ) { return "diamond";}
    if (ntype == "anatomical_entity") { return "ellipse";}
    if (ntype == "phenotypic_feature") { return "star";}
    return "rectangle";
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
    xhr6.open("post", "api/rtx/v1/result/" + res_id + "/feedback", true);
    xhr6.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr6.send(JSON.stringify(feedback));

    xhr6.onloadend = function() {
	var jsonObj6 = JSON.parse(xhr6.responseText);
	document.getElementById("devdiv").innerHTML += "================================================================= FEEDBACK-POST::<PRE>\nPOST to api/rtx/v1/result/" + res_id + "/feedback ::<br>" + JSON.stringify(feedback,null,2) + "<br>------<br>" + JSON.stringify(jsonObj6,null,2) + "</PRE>";

	if ( xhr6.status == 200 ) {
	    document.getElementById(fff+"_msgs").innerHTML = "Your feedback has been recorded...";
	    setRTXUserCookie(nom);

	    var xhr7 = new XMLHttpRequest();
	    xhr7.open("get", "api/rtx/v1/result/" + res_id + "/feedback", true);
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
		    insert_feedback_item(fid, jsonObj3[i]);
		}
		else {
		    document.getElementById("devdiv").innerHTML += "[warn] Feedback " + fid + " does not exist in response!<br>";
		}
	    }

	}
	sesame(h1_div,a1_div);
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


function get_example_questions() {
    var xhr8 = new XMLHttpRequest();
    xhr8.open("get", "api/rtx/v1/exampleQuestions", true);
    xhr8.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr8.send(null);

    xhr8.onloadend = function() {
	if ( xhr8.status == 200 ) {
	    var ex_qs = JSON.parse(xhr8.responseText);

	    document.getElementById("qqq").innerHTML = "<option style='border-bottom:1px solid black;' value=''>Example Questions&nbsp;&nbsp;&nbsp;&#8675;</option>";

	    for (var i in ex_qs) {
		var opt = document.createElement('option');
		opt.value = ex_qs[i].question_text;
		opt.innerHTML = ex_qs[i].query_type_id+": "+ex_qs[i].question_text;
		document.getElementById("qqq").appendChild(opt);
	    }

	}

    };

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

// LIST FUNCTIONS
var listItems = {};
listItems['A'] = {};
listItems['B'] = {};

function display_list(listId) {
    var listhtml = '';
    var numitems = 0;

    for (var li in listItems[listId]) {
	if (listItems[listId].hasOwnProperty(li) && listItems[listId][li] == 1) {
	    numitems++;
	    listhtml += "<tr class='hoverable'><td>" + li + "</td><td><a href='javascript:remove_item(\"" + listId + "\",\""+ li +"\");'/> Remove </a></td></tr>";
	}
    }


    if (numitems == 0) {
	listhtml = "Items in this list can be passed as input to queries that support list input, by specifying <b>["+listId+"]</b> as a parameter.<br>";
    }
    else {
	listhtml = "<table class='sumtab'><tr><th>Item</th><th>Action</th></tr>" + listhtml + "</table>";
    }

    document.getElementById("numlistitems"+listId).innerHTML = numitems;

    listhtml += "<hr>Enter new list item or items (space and/or comma-separated):<br><input type='text' class='questionBox' id='newlistitem"+listId+"' value='' size='60'><input type='button' class='questionBox button' name='action' value='Add' onClick='javascript:add_new_to_list(\""+listId+"\");'/>&nbsp;&nbsp;&nbsp;&nbsp;<a href='javascript:delete_list(\""+listId+"\");'/> Delete List </a><br><br>";


    document.getElementById("listdiv"+listId).innerHTML = listhtml;
    sesame('openmax',document.getElementById("listdiv"+listId));
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


function add_new_to_list(listId) {
    var itemarr = document.getElementById("newlistitem"+listId).value.split(/[ ,]/);
    document.getElementById("newlistitem"+listId).value = '';
    for (var item in itemarr) {
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

