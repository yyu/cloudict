r"""Mapping Key to WebResource.

Example::

    >>> from pprint import pprint
    >>> api_base = 'https://vpic.nhtsa.dot.gov/api/vehicles'
    >>> manufacturer_dict = WebDict(lambda s: api_base + '/getmakeformanufacturer/' + s + '?format=json', json.loads)
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

from pprint import pformat


class WebDictError(Exception):
    pass


class UnavailableWebResourceError(WebDictError):
    """
    >>> bad_dict = WebDict(lambda s: 'http://example.com/' + s)
    >>> bad_dict['foo']
    Traceback (most recent call last):
        ...
    UnavailableWebResourceError: failed to get http://example.com/foo: [Errno 8] nodename nor servname provided, or not known
    """
    pass


class InvalidWebResourceError(WebDictError):
    """
    >>> wrong_dict = WebDict(lambda s: 'https://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/' + s, json.loads) # will get xml
    >>> wrong_dict['tesla']
    Traceback (most recent call last):
        ...
    InvalidWebResourceError: failed to parse response from https://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/tesla: Expecting value: line 1 column 1 (char 0)
    ('<Response xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
     'xmlns:xsd="http://www.w3.org/2001/XMLSchema"><Count>1</Count><Message>Results '
     'returned '
     'successfully</Message><SearchCriteria>Manufacturer:tesla</SearchCriteria><Results><MakesForMfg><Mfr_Name>TESLA, '
     'INC.</Mfr_Name><Make_ID>441</Make_ID><Make_Name>Tesla</Make_Name></MakesForMfg></Results></Response>')

    >>> from pprint import pprint
    >>> ok_dict = WebDict(lambda s: 'https://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/' + s) # will get xml
    >>> pprint(ok_dict['tesla'])
    ('<Response xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
     'xmlns:xsd="http://www.w3.org/2001/XMLSchema"><Count>1</Count><Message>Results '
     'returned '
     'successfully</Message><SearchCriteria>Manufacturer:tesla</SearchCriteria><Results><MakesForMfg><Mfr_Name>TESLA, '
     'INC.</Mfr_Name><Make_ID>441</Make_ID><Make_Name>Tesla</Make_Name></MakesForMfg></Results></Response>')
    """
    pass


class WebDict(collections.UserDict):
    def __init__(self, key_processor=lambda key: None, value_processor=lambda s: s):
        super().__init__()
        self.make_url = key_processor
        self.parse_response = value_processor

    def __missing__(self, key):
        url = self.make_url(key)

        try:
            s = urllib.request.urlopen(url).read().decode('utf8')
        except urllib.error.URLError as e:
            raise UnavailableWebResourceError(str.format('failed to get {}: {}', url, e.reason))

        try:
            self[key] = self.parse_response(s)
        except Exception as e:
            raise InvalidWebResourceError(str.format('failed to parse response from {}: {}\n{}', url, e, pformat(s)))

        return self[key]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
