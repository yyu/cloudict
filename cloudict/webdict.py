r"""Mapping Key to Web Resource"""


import json
import csv
from functools import lru_cache
from functools import reduce

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
    (b'<Response xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="h'
     b'ttp://www.w3.org/2001/XMLSchema"><Count>1</Count><Message>Results returned s'
     b'uccessfully</Message><SearchCriteria>Manufacturer:tesla</SearchCriteria><Res'
     b'ults><MakesForMfg><Mfr_Name>TESLA, INC.</Mfr_Name><Make_ID>441</Make_ID><Mak'
     b'e_Name>Tesla</Make_Name></MakesForMfg></Results></Response>')

    >>> from pprint import pprint
    >>> ok_dict = WebDict(lambda s: 'https://vpic.nhtsa.dot.gov/api/vehicles/getmakeformanufacturer/' + s) # will get xml
    >>> pprint(ok_dict['tesla'])
    (b'<Response xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="h'
     b'ttp://www.w3.org/2001/XMLSchema"><Count>1</Count><Message>Results returned s'
     b'uccessfully</Message><SearchCriteria>Manufacturer:tesla</SearchCriteria><Res'
     b'ults><MakesForMfg><Mfr_Name>TESLA, INC.</Mfr_Name><Make_ID>441</Make_ID><Mak'
     b'e_Name>Tesla</Make_Name></MakesForMfg></Results></Response>')
    """
    pass


@lru_cache(maxsize=65536)
def _cached_retrieve(url):
    return _retrieve(url)


def _retrieve(url):
    try:
        return urllib.request.urlopen(url).read()
    except urllib.error.URLError as e:
        raise UnavailableWebResourceError('failed to get {}: {}'.format(url, e.reason))


class ResponseProcessors:
    @classmethod
    def json_loads(cls):
        return json.loads

    @classmethod
    def json_loads_path(cls, path):
        """returns a function that extracts part of a json string
        example::

            >>> f = ResponseProcessors.json_loads_path(['Results', 'Numbers'])
            >>> f('''{"Message": "success", "Results": {"Numbers": {"one": 1, "two": 2}}}''')
            {'one': 1, 'two': 2}
            >>> f('''{"Message": "success", "Results": {"Numbers": {"three": 3}}}''')
            {'three': 3}

            >>> f = ResponseProcessors.json_loads_path(['Results', 'Strings', 1])
            >>> f('''{"Message": "success", "Results": {"Strings": ["foo", "bar", "baz"]}}''')
            'bar'
        """
        def loads_with_path(s):
            return reduce(lambda x, y: x[y], path, json.loads(s))

        return loads_with_path


class WebDict(collections.UserDict):
    """Workflow: key ---➀--> url ---➁--> response ---➂--> value ---➃--> done

        :param url_maker: ➀
        :param response_processor: ➂
        :param post_processor: ➃
        :param cache: retrieve with or without caching (➁)

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

    post_processor(➃) can do some magic like this::

        >>> url = 'https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformake/tesla?format=json'
        >>> def propagate(d, _, v):
        ...     for r in v['Results']:
        ...         model = r['Model_Name']
        ...         d[model] = r
        >>> tesla = WebDict(url_maker=lambda _: url, response_processor=json.loads, post_processor=propagate)
        >>> tesla['Model S']
        {'Make_ID': 441, 'Make_Name': 'Tesla', 'Model_ID': 1685, 'Model_Name': 'Model S'}
        >>> tesla['Roadster']
        {'Make_ID': 441, 'Make_Name': 'Tesla', 'Model_ID': 2071, 'Model_Name': 'Roadster'}
        >>> list(tesla.keys())
        ['Model S', 'Roadster', 'Model X', 'Model 3']
        >>> tesla['F150']
        Traceback (most recent call last):
            ...
        KeyError: 'F150'

    as you have seen above, all models have been propagated although only 'Model S' was queried.
    """
    def __init__(self,
                 url_maker=lambda key: None,
                 response_processor=lambda s: s,
                 post_processor=lambda d, key, value: collections.UserDict.__setitem__(d, key, value),
                 cache=True):
        super().__init__()

        if url_maker is None:
            raise RuntimeError("you need a url_maker")

        self.make_url = url_maker
        self.parse_response = response_processor
        self.post_process = post_processor
        self.cache_enabled = cache

    def __missing__(self, key):
        url = self.make_url(key)

        data = _cached_retrieve(url) if self.cache_enabled else _retrieve(url)

        try:
            value = self.parse_response(data)
        except Exception as e:
            raise InvalidWebResourceError('failed to parse response from {}: {}\n{}'.format(url, e, pformat(data)))

        self.post_process(self, key, value)

        # post-process should have set (key, value), but if for any reason it didn't, raise KeyError
        if key not in self:
            raise KeyError(key)

        return self[key]


class WebCSV(WebDict):
    def __init__(self, csv_url, delimiter=',', key_pos=0):
        def load_lines(d, _, s):
            csv_as_list_of_dict = csv.DictReader(s.splitlines(), delimiter=delimiter)

            key_field = csv_as_list_of_dict.fieldnames[key_pos]

            for record in csv_as_list_of_dict:
                key = record[key_field]
                d[key] = record

        super().__init__(lambda _: csv_url, bytes.decode, load_lines, False)


class WebTSV(WebCSV):
    """example::

        >>> gazetteer = WebTSV('https://raw.githubusercontent.com/yyu/GeoJSON-US/master/ZIPCodesGazetteer.tsv')
        >>> place = gazetteer['98109']
        >>> (place['INTPTLAT'], place['INTPTLONG'])
        ('47.631863', '-122.344267')
        >>> len(gazetteer)  # all lines have been propagated, 33144 in total
        33144
    """
    def __init__(self, tsv_url, key_pos=0):
        super().__init__(tsv_url, delimiter='\t', key_pos=key_pos)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
