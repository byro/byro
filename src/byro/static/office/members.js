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
      return '<div class="tt-suggestion tt-selectable">' + data.value + ' (' + data.name + ')' + '</div>'
    }
  }
});
$(".member-typeahead").bind("typeahead:select", function(ev, suggestion) {
  $(".member-typeahead").text(suggestion.value);
});
