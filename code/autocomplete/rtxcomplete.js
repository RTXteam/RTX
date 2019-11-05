//var max_suggs;
//var fetchResults;
//var fetchQuery;
//var fetchResultsCallback;

/*window.onerror = function(msg, url, lineNo, columnNo, error){
    alert("onerror fired");
}*/

$( document ).ready( function(){
    $('.typeInput').typeahead({
	fitToElement : true,
	highlighter: function (item){
	    var parts = item.split('#');
	    var html = '';
	    for (i = 0; i < parts.length; i++){
		if (i % 2 == 0){
		    html += parts[i];
		} else {
		    html += '<strong><font color="blue">' + parts[i] + '</font></strong>';
		}
	    }
	    return html;
	},
	updater: function (item) {
	    //console.log("updater: ");
	    //console.log($('.typeInput').val());
	    var tmp = $('.typeInput').val().split(",");
	    tmp = tmp.slice(0,tmp.length-1).join(", ");
	    var parts = item.split('#');
	    var text = "";
	    if (tmp.length > 0){
		text += tmp + ", ";
	    }
	    text += parts.join("");
	    return text;
	},
	matcher: function (item){
	    //console.log("matcher");
	    return true;
	},
	name: 'stuff',
	display: 'value',
	source: function(query, callback) {
	    //console.log("'"+query+"'");
	    //console.log($('.typeInput').innerWidth());
	    //console.log(query.split(","));
	    query = query.split(",");
	    //var first_part = query.slice(0,query.length-1).join(", ");
	    //console.log(first_part);
	    query = query[query.length-1].trim();
	    if (query.length == 0){
		return;
	    }
	    var hit = false;
	    var def_tmp = query.split(" ");
	    var def = null;
	    for (i = 0; i < def_tmp.length && !def; i++){
		def = quick_def[def_tmp[i].toLowerCase()];
	    }
	    $.ajax({
		url: "/rtxcomplete/auto?word="+query+"&limit=10",
		cache: false,
		dataType:"jsonp",
		success: function (response) {
		    var results = [];
		    if (def){
			var split_length = 100;
			def = def.match(/.{1,split_length}/g).join('<br>');
			results.push("<strong>Quick Def:</strong> "+def);
		    }
		    $.each(response, function(i, item){
			var lowerItem = item.toLowerCase();
			var lowerQuery = query.trim().toLowerCase();
			if (lowerQuery[lowerQuery.length-1] == '?'){
			    lowerQuery = lowerQuery.substring(0,lowerQuery.length-1);
			}
			var idx = lowerItem.indexOf(lowerQuery);
			var tmp = "";
			var lastIdx = 0;
			//can change this later to a more efficient version with split()
			while (idx > -1){
			    tmp += item.substring(lastIdx,idx);
			    tmp += "#";
			    lastIdx = idx;
			    idx += lowerQuery.length;
			    tmp += item.substring(lastIdx,idx);
			    tmp += "#";
			    lastIdx = idx;
			    idx = lowerItem.indexOf(lowerQuery,idx);
			}
			tmp += item.substring(lastIdx);
			results.push(tmp);
		    });
		    if(callback){
			callback(results);
		    }
		}
	    });	    
	}
    });
});
    
