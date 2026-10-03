var members = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  limit: Infinity,
  remote: {
    url: document.getElementById('vars').getAttribute('remoteUrl'),
    wildcard: '%QUERY',
    transform: function (object) {
      var results = object.results
      var suggestions = []
      for (i = 0; i < results.length; i++) {
        suggestions.push({value: results[i].id, name: results[i].name})
      }
      return suggestions
    }
  }
});

$('.member-typeahead').typeahead(null, {
  name: 'id',
  display: 'name',
  source: members,
  templates: {
    suggestion: function(data) {
      // Member data is untrusted: build the element and set it as text, never as HTML.
      return $('<div>').text(data.value + ' (' + data.name + ')')
    }
  }
});
$(".member-typeahead").bind("typeahead:select", function(ev, suggestion) {
  $(".member-typeahead").text(suggestion.value);
});
