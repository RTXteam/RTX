//var max_suggs;
//var fetchResults;
//var fetchQuery;
//var fetchResultsCallback;

/*window.onerror = function(msg, url, lineNo, columnNo, error){
    alert("onerror fired");
}*/

$( document ).ready( function(){
    $('.typeInput').typeahead({
	highlighter: function (item) {
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
	    var parts = item.split('#');
	    var text = parts.join("");
	    return text;
	},
	matcher: function (item){
	    return true;
	},
	name: 'stuff',
	display: 'value',
	source: function(query, callback) {
	    $.ajax({
		url: "http://rtxcomplete.ixlab.org/auto?word="+query+"&limit=10",
		cache: false,
		dataType:"jsonp",
		success: function (response) {
		    var results = [];
		    $.each(response, function(i, item){
			var lowerItem = item.toLowerCase();
			var lowerQuery = query.trim().toLowerCase();
			if (lowerQuery[lowerQuery.length-1] == '?'){
			    lowerQuery = lowerQuery.substring(0,lowerQuery.length-1);
			}
			var idx = lowerItem.indexOf(lowerQuery);
			var tmp = "";
			var lastIdx = 0;
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
    
