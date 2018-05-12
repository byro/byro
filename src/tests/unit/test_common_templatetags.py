import pytest
from django.http.request import QueryDict

from byro.common.templatetags.url_replace import url_replace


class request:
    def __init__(self, get):
        self.GET = QueryDict(get)


@pytest.mark.parametrize('GET,key,value,expected', (
    ('foo=bar', 'foo', 'baz', ['foo=baz']),
    ('foo=bar', 'fork', 'baz', ['foo=bar', 'fork=baz']),
))
def test_templatetag_url_replace(GET, key, value, expected):
    result = url_replace(request(GET), key, value)
    assert all(e in result for e in expected)
