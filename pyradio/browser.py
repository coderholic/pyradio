# -*- coding: utf-8 -*-
# http://www.radio-browser.info/webservice#Advanced_station_search
import json
import requests
import threading
import logging
from .widechar import cjklen, PY3
#from os import get_terminal_size

logger = logging.getLogger(__name__)


class PyRadioStationsBrowser(object):
    """A base class to get results from online radio directory services.

    Actual implementations should be subclasses of this one.
    """

    def __init__(self, search=None):
        """Initialize the station's browser.

        It should return a valid search result (for example,
        www.radio-browser.info implementation, returns 100 stations
        sorted by number of votes).

        Parameters
        ----------
        search
            Search parameters to be used instead of the default.
        """

        self._raw_stations = []
        self._last_search = None
        self._have_to_retrieve_url = False
        self._uses_internal_header = False
        self._url_timeout = 3
        self._search_timeout = 3

    @property
    def uses_internal_header(self):
        return self._uses_internal_header

    @uses_internal_header.setter
    def uses_internal_header(self, value):
        raise ValueError('property is read only')

    @property
    def have_to_retrieve_url(self):
        return self._have_to_retrieve_url

    @have_to_retrieve_url.setter
    def have_to_retrieve_url(self, value):
        raise ValueError('property is read only')

    def stations(self, playlist_format=1):
        return []

    def url(self, id_in_list):
        """Return a station's real/playable url

        It has to be implemented only in case have_to_retrieve_url is True

        Parameters
        ----------
        id_in_list
            id in list of stations (0..len-1)

        Returns
        -------
            Real/playable url or '' if failed (string)
        """

        return ''

    def real_url(self, stationid):
        """Return a station's real/playable url

        It has to be implemented only in case have_to_retrieve_url is True

        Parameters
        ----------
        stationid
            Station id of a browser.info station

        Returns
        -------
            Real/playable url (string)
        """

        return ''

    def set_played(self, id_in_list, played):
        """Note that a player has been played.

        Parameters
        ----------
        id_in_list
            id in list of stations (0..len-1)
        played
            True or False

        """
        pass

    def search(self, data=None):
        return []

    def set_encoding(self, id_in_list, new_encoding):
        return

    def format_station_line(self, id_in_list, pad, width):
        return ''


class PyRadioBrowserInfoBrowser(PyRadioStationsBrowser):
    BASE_URL = 'www.radio-browser.info'
    _open_url = \
        'http://www.radio-browser.info/webservice/json/stations/topvote/100'
    _open_headers = {'user-agent': 'PyRadio/dev'}

    _raw_stations = []

    # the output format to use based on window width
    # Default value: -1
    # Possible values: 0..4
    # Look at format_station_line() for info
    _output_format = -1
    _info_len = []
    _info_name_len = 0

    _have_to_retrieve_url = True
    _uses_internal_header = True

    _url_timeout = 3
    _search_timeout = 3

    def __init__(self, search=None):
        self._raw_stations = []
        if search:
            self.search(search)
        else:
            self.search({'order': 'votes', 'reverse': 'true'})

    def stations(self, playlist_format=1):
        """ Return stations' list (in PyRadio playlist format)

        Parameters
        ----------
        playlist_format
            0: station name, url
            1: station name, url, encoding
            2: station name, url, encoding, browser flag (default)
        """

        ret = []
        for n in self._raw_stations:
            if playlist_format == 0:
                ret.append([n['name'], n['url']])
            elif playlist_format == 1:
                enc = '' if n['encoding'] == 'utf-8' else n['encoding']
                ret.append([n['name'], n['url'], enc])
            else:
                enc = '' if n['encoding'] == 'utf-8' else n['encoding']
                ret.append([n['name'], n['url'], enc, ''])
        return ret

    def url(self, id_in_list):
        """ Get a station's url using real_url()

        Parameters
        ----------
        id_in_list
            id in list of stations (0..len-1)

        Returns
        -------
            url or '' if failed
        """

        if self._raw_stations:
            if id_in_list < len(self._raw_stations):
                if self._raw_stations[id_in_list]['real_url']:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Using existing url: "{}"'.format(self._raw_stations[id_in_list]['url']))
                    return self._raw_stations[id_in_list]['url']
                else:
                    stationid = self._raw_stations[id_in_list]['id']
                    url = self.real_url(stationid)
                    if url:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('URL retrieved: "{0}" <- "{1}'.format(url, self._raw_stations[id_in_list]['url']))
                        self._raw_stations[id_in_list]['url'] = url
                        self._raw_stations[id_in_list]['real_url'] = True
                        self._raw_stations[id_in_list]['played'] = True
                    else:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('Failed to retrieve URL for station "{0}", using "{1}"'.format(self._raw_stations[id_in_list]['name'], self._raw_stations[id_in_list]['url']))
                        url = self._raw_stations[id_in_list]['url']
                    return url
        return ''

    def real_url(self, stationid):
        """ Get real url from returned url

        Parameters
        ----------
        stationid
            Station id of a browser.info station

        Returns
        -------
            url or '' if failed
        """

        url = \
            'http://www.radio-browser.info/webservice/v2/json/url/' + \
            str(stationid)
        try:
            r = requests.get(url=url, headers=self._open_headers, timeout=self._url_timeout)
            r.raise_for_status()
            rep = json.loads(r.text)
            if rep['ok'] == 'true':
                return rep['url']
            else:
                return ''
        except requests.exceptions.RequestException as e:
            if logger.isEnabledFor(logger.ERROR):
                logger.error(e)
            return ''

    def search(self, data):
        """ Search for stations with parameters.
        Result is limited to 100 stations by default (use the
        'limit' parameter to change it).

        Parameters
        ----------
        data
            A dictionary containing the fields described at
            http://www.radio-browser.info/webservice/#Advanced_station_search

        Returns
        -------
        self._raw_stations
            A dictionary with a subset of returned station data.
            Its format is:
                name        : station name
                id          : station id
                url         : station url
                real_url    : True if url is "Playable URL"
                bitrate     : station bitrate
                hls         : HLS status
                votes       : station votes
                clickcount  : station clicks
                country     : station country
                language    : station language
                encoding    : station encoding ('' means utf-8)
        """

        self._output_format = -1
        valid_params = (
            'name', 'nameExact',
            'country', 'countryExact',
            'state', 'stateExact',
            'language', 'languageExact',
            'tag', 'tagExact',
            'tagList',
            'bitrateMin', 'bitrateMax',
            'order',
            'reverse',
            'offset',
            'limit'
        )
        post_data = {}
        for n in valid_params:
            if n in data.keys():
                post_data[n] = data[n]
        if 'limit' not in post_data.keys():
            post_data['limit'] = 100
        if not 'hidebroken' not in post_data.keys():
            post_data['hidebroken'] = 'true'
        self._last_search = post_data
        url = 'http://www.radio-browser.info/webservice/json/stations/search'
        try:
            r = requests.get(url=url, headers=self._open_headers, json=post_data, timeout=self._search_timeout)
            r.raise_for_status()
            self._raw_stations = self._extract_data(json.loads(r.text))
        except requests.exceptions.RequestException as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(e)
            self._raw_stations = []

    def format_station_line(self, id_in_list, pad, width):
        """ Create a formated line for a station

        Parameters
        ----------
        id_in_list
            id in list of stations (0..len-1)
        pad
            length of NUMBER
        width
            final length of created string

        Returns
        -------
        A string of the following format:
            NUMBER. STATION NAME [INFO]
        where:
            NUMBER
                Right padded counter (id_in_list + 1)
            STATION NAME
                Left padded station name
            INFO
                Station info. Depending on window width, it can be:
                    [Votes: XX, Clicks: XX, Bitrate: XXXkb, Country: XXXX],
                    [Votes: XX, Clicks: XX, Bitrate: XXXkb],
                    [XXXX v, XXXX, cl, XXXkb],
                    [Bitrate: XXXkb], or
                    empty string
        """

        if PY3:
            info = ('',
                    ' {0} {1}kb',
                    ' {0}{1} v│{2} cl│{3}kb',
                    ' {0} {1}│ {2}│ {3}kb',
                    ' {0} {1}│ {2}│ {3}kb│{4}',
                    ' {0} {1}│ {2}│ {3}kb│{4}│{5}',
            )
        else:
            info = ('',
                    ' {0} {1}kb',
                    ' {0}{1} v|{2} cl|{3}kb',
                    ' {0} {1}| {2}| {3}kb',
                    ' {0} {1}| {2}| {3}kb|{4}',
                    ' {0} {1}| {2}| {3}kb|{4}|{5}',
            )
        # now_width = get_terminal_size().columns - 2
        now_width = width
        if now_width <= 45:
            self._output_format = 0
        elif now_width <= 55:
            self._output_format = 1
        elif now_width <= 78:
            self._output_format = 2
        elif now_width <= 100:
            self._output_format = 3
        elif now_width <= 125:
            self._output_format = 4
        else:
            self._output_format = 5

        out = ['{0}. '.format(str(id_in_list + 1).rjust(pad)), '', '']

        # format info field
        if PY3:
            pl = u'┼' if self._raw_stations[id_in_list]['played'] else u'│'
        else:
            pl = '+' if self._raw_stations[id_in_list]['played'] else '|'
        if self._output_format == 5:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._max_len[0]),
                self._raw_stations[id_in_list]['clickcount'].rjust(self._max_len[1]),
                self._raw_stations[id_in_list]['bitrate'].rjust(7)[:7],
                self._raw_stations[id_in_list]['country'].ljust(14)[:14],
                self._raw_stations[id_in_list]['language'].ljust(15)[:15]
            )
        if self._output_format == 4:
            # full or condensed info
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._max_len[0]),
                self._raw_stations[id_in_list]['clickcount'].rjust(self._max_len[1]),
                self._raw_stations[id_in_list]['bitrate'].rjust(7)[:7],
                self._raw_stations[id_in_list]['country'].ljust(14)[:14]
            )
        elif self._output_format in (2, 3):
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._max_len[0]),
                self._raw_stations[id_in_list]['clickcount'].rjust(self._max_len[1]),
                self._raw_stations[id_in_list]['bitrate'].rjust(7)[:7]
            )
        elif self._output_format == 1:
            # Bitrate only
            out[2] = info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['bitrate'].rjust(7)[:7]
            )

        name_width = width-len(out[0])-len(out[2])
        out[1] = self._fix_cjk_string_width(self._raw_stations[id_in_list]['name'].ljust(name_width)[:name_width], name_width)
        if PY3:
            return '{0}{1}{2}'.format(*out)
        else:
            # on python 2, strings are already in utf-8
            return '{0}{1}{2}'.format(
                    out[0].encode('utf-8', 'replace'),
                    out[1].encode('utf-8', 'replace'),
                    out[2].encode('utf-8', 'replace'))

    def set_encoding(self, id_in_list, new_encoding):
        if id_in_list < len(self._raw_stations):
            self._raw_stations[id_in_list]['encoding'] = new_encoding
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('New encoding set to "{0}" for station "{1}"'.format(new_encoding, self._raw_stations[id_in_list]['name']))

    def _fix_cjk_string_width(self, a_string, width):
        while cjklen(a_string) > width:
            a_string = a_string[:-1]
        return a_string

    def _extract_data(self, a_search_result):
        ret = []
        self._max_len = [0, 0]
        if a_search_result:
            for n in a_search_result:
                ret.append({'name': n['name'].replace(',', ' ')})
                ret[-1]['bitrate'] = n['bitrate']
                ret[-1]['votes'] = n['votes']
                ret[-1]['url'] = n['url']
                ret[-1]['real_url'] = False
                ret[-1]['played'] = False
                ret[-1]['hls'] = n['hls']
                ret[-1]['id'] = n['id']
                ret[-1]['country'] = n['country']
                ret[-1]['language'] = n['language']
                ret[-1]['clickcount'] = n['clickcount']
                ret[-1]['encoding'] = ''
                self._get_max_len(ret[-1]['votes'],
                                  ret[-1]['clickcount'])
        return ret

    def _get_max_len(self, votes, clicks):
        """ Calculate the maximum length of numeric_data / country

        Parameters
        ----------
        string_data
            A tuple (name, country) - (uses cjklen)
        country
            A string (uses cjklen)
        numeric_data
            A tuple (bitrate, votes, clickcount)

        Returns
        -------
        self._max_len
            A list [max name length (max is 50),
                    max country length (max is 14),
                    max bitrate length,
                    max votes length,
                    max clickcount length]
        """

        numeric_data = (votes, clicks)
        min_data = (6, 7)
        for i, n in enumerate(numeric_data):
            if len(n) > self._max_len[i]:
                self._max_len[i] = len(n) if len(n) > min_data[i] else min_data[i]


class PyRadioBrowserInfoData(object):
    """ Read search parameters for radio.browser.info service

    parameters are:
        tags, countries(and states), codecs, languages """

    _data = {}
    _connection_error = False
    _lock = threading.Lock()
    _stop_thread = False
    _timeout = 3
    data_thread = None

    def __init__(self, timeout=3):
        self._timeout = timeout

    def start(self, force_update=False):
        """ Start data acquisition thread """
        self.data_thread = threading.Thread(
            target=self._get_all_data_thread,
            args=(
                self._lock, force_update, lambda: self._stop_thread,
                self._update_data
            )
        )
        self.data_thread.start()

    def stop(self):
        """ Stop (cancel) data acquisition thread """
        self._stop_thread = True

    @property
    def lock(self):
        """ Return thread lock (read only)"""
        return self._lock

    @lock.setter
    def lock(self, val):
        raise ValueError('property is read only')

    @property
    def terminated(self):
        """ Return True if thread is not alive (read only)
        which means that data has been retrieved"""
        if self.data_thread.is_alive():
            return False
        return True

    @terminated.setter
    def terminated(self, val):
        raise ValueError('property is read only')

    @property
    def connection_error(self):
        self._lock.acquire()
        ret = self._connection_error
        self._lock.release()
        return ret

    @connection_error.setter
    def connection_error(self, val):
        raise ValueError('property is read only')

    @property
    def tags(self):
        self._lock.acquire()
        ret = self._data['tags']
        self._lock.release()
        return ret

    @tags.setter
    def tags(self, val):
        raise ValueError('property is read only')

    @property
    def codecs(self):
        self._lock.acquire()
        if 'codecs' in self._data:
            ret = self._data['codecs']
        else:
            ret = {}
        self._lock.release()
        return ret

    @codecs.setter
    def codecs(self, val):
        raise ValueError('property is read only')

    @property
    def countries(self):
        self._lock.acquire()
        ret = self._data['countries']
        self._lock.release()
        return ret

    @countries.setter
    def countries(self, val):
        raise ValueError('property is read only')

    @property
    def languages(self):
        self._lock.acquire()
        ret = self._data['languages']
        self._lock.release()
        return ret

    @languages.setter
    def languages(self, val):
        raise ValueError('property is read only')

    def reset_all_data(self):
        self._data = {}
        self.start()

    def _update_data(self, data, connection_error):
        self._connection_error = connection_error
        self._data = data

    def _get_all_data_thread(self, lock, force_update, stop, callback): # noqa

        def get_data(data):
            ret = {}
            json_data = []
            connection_error, json_data = get_data_dict(data)
            if connection_error:
                return True, {}
            if json_data:
                for a_tag in json_data:
                    ret[a_tag['name']] = a_tag['stationcount']
                return False, ret

        def get_countries(stop):
            ret = {}
            connection_error, json_countrycodes = get_data_dict('countrycodes')
            if connection_error:
                return True, {}
            from countries import countries
            st = 'stationcount'
            for n in json_countrycodes:
                if n['name'] in countries.keys():
                    ret[countries[n['name']]] = {}
                    ret[countries[n['name']]]['code'] = n['name']
                    ret[countries[n['name']]]['stationcount'] = n[st]
                    ret[countries[n['name']]]['states'] = {}
            connection_error, json_states = get_data_dict('states')
            if connection_error:
                return True, {}
            for n in json_states:
                if n['country'] in ret.keys():
                    ret[n['country']]['states'][n['name']] = n['stationcount']
            return False, ret

        def get_data_dict(data):
            url = 'http://www.radio-browser.info/webservice/json/' + data
            jdata = {'hidebroken': 'true'}
            headers = {'user-agent': 'PyRadio/dev',
                       'encoding': 'application/json'}
            try:
                r = requests.get(url, headers=headers, json=jdata, timeout=self._timeout)
                r.raise_for_status()
                return False, json.loads(r.text)
                # if r.status_code == 200:
                #     return False, json.loads(r.text)
                # else:
                #     return True, []
            except requests.exceptions.RequestException as e:
                if logger.isEnabledFor(logger.ERROR):
                    logger.error(e)
                return True, []

        my_data = {}
        data_items = ['tags', 'countries', 'codecs', 'languages']
        for an_item in data_items:
            if an_item == 'countries':
                ret, my_data['countries'] = get_countries(stop)
            else:
                ret, my_data[an_item] = get_data(an_item)
            if stop():
                if logger.isEnabledFor(logger.DEBUG):
                    logger.info('Asked to stop after working on "{}"...'.format(an_item))
                self._terminated = True
                return
        # print('I am here')
        lock.acquire()
        # print('I am here too')
        callback(my_data, ret)
        lock.release()


def probeBrowsers(a_browser_url):
    base_url = a_browser_url.split('/')[2]
    if not base_url:
        base_url = a_browser_url
    implementedBrowsers = PyRadioStationsBrowser.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info('Implemented browsers: {}'.format(implementedBrowsers))

    for a_browser in implementedBrowsers:
        if a_browser.BASE_URL == base_url:
            if logger.isEnabledFor(logging.INFO):
                logger.info('Supported browser: {}'.format(a_browser))
            return a_browser
    if logger.isEnabledFor(logging.INFO):
        logger.info('No supported browser found for: ' + a_browser_url)
    return None
