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
	    var html = '<strong><font color="blue">' + parts[0] + '</font></strong>' + parts[1];
	    return html;
	},
	updater: function (item) {
	    var parts = item.split('#');
	    var text = parts[0] + parts[1];
	    return text;
	},
	name: 'stuff',
	display: 'value',
	source: function(query, callback) {
	    var results = []
	    $.get("auto?word="+query+"&limit=10", function(data) {
		data = JSON.parse(data);
		$.each(data, function(i, item){
		    var tmp = item.substring(0,query.length);
		    tmp += "#";
		    tmp += item.substring(query.length);
		    results.push(tmp);
		});
		if(callback)
		    callback(results);
	    });
	}
    });
});
