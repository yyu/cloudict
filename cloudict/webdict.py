r"""Mapping Key to WebResource.

Example::

    >>> from pprint import pprint
    >>> def make_url(make):
    ...     return 'https://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/%s?format=json' % make
    ...
    >>> manufacturer_dict = WebDict(make_url, json.loads)
    >>> pprint(manufacturer_dict['tesla'])
    {'Count': 1,
     'Message': 'Results returned successfully',
     'Results': [{'Make_ID': 441, 'Make_Name': 'Tesla', 'Mfr_Name': 'TESLA, INC.'}],
     'SearchCriteria': 'Manufacturer:tesla'}
    >>> manufacturer_dict['unknown-car']
    {'Count': 0, 'Message': 'Results returned successfully', 'SearchCriteria': 'Manufacturer:unknown-car', 'Results': []}
"""


import json
import collections
import urllib.request
import urllib.error


class WebDictError(Exception):
    pass


class UnavailableWebResourceError(WebDictError):
    pass


class InvalidWebResourceError(WebDictError):
    pass


class WebDict(collections.UserDict):
    def __init__(self, key_processor=lambda key: None, value_processor=lambda s: s):
        super().__init__()
        self.make_url = key_processor
        self.parse_response = value_processor

    def __missing__(self, key):
        url = self.make_url(key)

        try:
            s = urllib.request.urlopen(url).read()
        except urllib.error.URLError as e:
            raise UnavailableWebResourceError(str.format('failed to get {}: {}', url, e.reason))

        try:
            self[key] = json.loads(s)
        except Exception as e:
            raise UnavailableWebResourceError(str.format('failed to parse response from {}: {}', url, e))

        return self[key]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
