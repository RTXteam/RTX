// which is one of: [ translator_gene , pigean ]
function postGenes(which="translator_gene") {
    document.getElementById("pigeanresultsDiv").innerHTML = '';

    var wait = getAnimatedWaitBar("200px");
    wait.style.marginTop = "20px";
    wait.style.marginBottom = "20px";
    document.getElementById("pigeanresultsDiv").append(wait);

    var dev = document.getElementById("devdiv");

    dev.innerHTML = "Posting Gene List...";
    dev.append(document.createElement("br"));

    var queryObj = {};
    queryObj["max_number_gene_sets"] = 150;
    queryObj["gene_sets"] = "default";
    queryObj["enrichment_analysis"] = "hypergeometric";
    queryObj["generate_factor_labels"] = false;
    queryObj["calculate_gene_scores"] = true;
    queryObj["exclude_controls"] = true;

    queryObj["p_value"] = document.getElementById("pigeanPvalue").value;

    queryObj["genes"] = [];
    for (var gene of document.getElementById("pigeanText").value.split("\n")) {
        gene = gene.trim();
	if (!gene) continue;
	queryObj["genes"].push(gene);
    }

    var GLurl = 'https://translator.broadinstitute.org/genetics_provider/bayes_gene/'+which;

    dev.append(" - contacting " + which + "...");
    dev.append(document.createElement("br"));

    fetch(GLurl, {
        method: 'post',
        body: JSON.stringify(queryObj),
        headers: { 'Content-type': 'application/json' }

    }).then(response => {
        wait.remove();
        if (response.ok) return response.json();
        else throw new Error('Something went wrong');

    }).then(data => {
        dev.append(document.createElement("br"));
        dev.append('='.repeat(80)+" RESPONSE MESSAGE::");
        var pre = document.createElement("pre");
        pre.id = "responseJSON";
        pre.append(JSON.stringify(data,null,2));
        dev.append(pre);

	dev.append(" - Success: JSON response received");
        dev.append(document.createElement("br"));

	add_user_msg("Call to Gene Set Enrichment successful","INFO",true);

	if (data["logs"]) {
	    var span = document.createElement("a");
	    span.style.fontWeight = "bold";
	    span.style.cursor = "pointer";
	    span.title = "view processing log";
	    span.append("[ log ]");
	    span.onclick = function () { showJSONpopup("PIGEAN Processing Log", data["logs"], false); };
	    document.getElementById("pigeanresultsDiv").append(span);
        }

        if (data["pigean-factor"]) {
	    renderPigeanSummary(data["pigean-factor"]["data"]);
            if (data["gene-factor"])
		renderPigeanResults(data["gene-factor"],data["input_genes"]);
	}
	else
	    throw new Error("No data in response!");

    }).catch(error => {
        console.error(error);
	dev.append(" - ERROR:: "+error);
        add_user_msg("Error:"+error,"ERROR",false);
    });

    return;
}


function renderPigeanResults(factorresults,input) {
    var resultsdiv = document.getElementById("pigeanresultsDiv");
    resultsdiv.append(document.createElement("hr"));

    var div = document.createElement("div");
    div.className = 'statushead';
    div.append("Gene Factor Table");
    resultsdiv.append(div);

    div = document.createElement("div");
    div.className = 'status';
    div.style.maxHeight = "50vh";
    div.style.overflow = "auto";
    resultsdiv.append(div);

    var table = document.createElement("table");
    table.className = 'sumtab';
    var tr = document.createElement("tr");
    var td = document.createElement("th")
    td.append("Gene");
    tr.append(td);

    var data = {};
    for (var factor in factorresults) {
	td = document.createElement("th")
	//td.style.writingMode = "sideways-lr";
	td.append(factor);
	tr.append(td);

	for (var fgene of factorresults[factor]) {
	    if (fgene.gene in data)
		data[fgene.gene] += "::"+factor+"::";
	    else
		data[fgene.gene] = "::"+factor+"::";
	}
    }
    table.append(tr);

    for (var gene in data) {
	tr = document.createElement("tr");
	tr.className = 'hoverable';
        td = document.createElement("td");
	if (input.includes(gene))
	    td.className = "essence";  // numnew?
        td.append(gene);
        tr.append(td);

	for (var factor in factorresults) {
            td = document.createElement("td")
            tr.append(td);
	    if (data[gene].includes(factor)) {
		var text = document.createElement("span");
                text.className = 'explevel p9';
                //text.innerHTML = '&check;';
                text.append(factor)
		td.append(text);
	    }
	}

	table.append(tr);
    }

    div.append(table);

}

function renderPigeanSummary(generesults) {
    var resultsdiv = document.getElementById("pigeanresultsDiv");
    resultsdiv.append(document.createElement("hr"));

    var span = document.createElement("h2");
    if (Object.keys(generesults).length == 0)
	span.append("No Results");
    else {
	span.append("Results (");
	span.append(Object.keys(generesults).length);
	span.append(" groups):");
    }
    resultsdiv.append(span);

    for (var result of generesults) {
	span = document.createElement("span");
        span.className = 'attbox';
        span.style.cursor = "auto";

        var head = document.createElement("div");
        head.className = 'head';
        head.append(result['label']);
        head.style.background = '#3d6d98';
        span.append(head);

        var atts_table = document.createElement("table");

        for (var field in result) {
            if (field == 'label') continue;

	    var row = document.createElement("tr");
            var cell = document.createElement("td");
            cell.className = "fieldname";
            cell.append(field+": ");
            row.append(cell);

            cell = document.createElement("td");

            if (field == 'top_genes') {
		var sep = '';
		for (var val of result[field].split(";")) {
                    var a = document.createElement("a");
                    a.title = 'view ARAX synonyms';
                    a.href = "javascript:lookup_synonym('"+val+"',true)";
                    a.innerHTML = val;
                    cell.append(sep);
                    cell.append(a);
                    sep = ', ';
		}
	    }
	    else if (field == 'top_gene_sets')
		cell.append(result[field].replaceAll(";","; "));
	    else
		cell.append(result[field]);

	    row.append(cell);
            atts_table.append(row);
        }

        span.append(atts_table);
        resultsdiv.append(span);
    }

}


function pigean_add_curielist_input(list) {
    var listId = list.split("LIST_")[1];

    var added = 0;
    for (var li in listItems[listId]) {
        if (listItems[listId].hasOwnProperty(li) && listItems[listId][li] == 1 && entities[li].isvalid) {
            document.getElementById("pigeanText").value += "\n" + entities[li].curie;
	    added++;
        }
    }
    if (added == 0)
	add_user_msg("Did not add any items from list <i>"+listId+"</i>","WARNING",true);
    else
	add_user_msg("Added <b>"+added+"</b> curies to input list of genes from list <i>"+listId+"</i>","INFO",true);
}
