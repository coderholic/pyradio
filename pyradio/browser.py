# -*- coding: utf-8 -*-
# http://www.radio-browser.info/webservice#Advanced_station_search
import json
try:
    import requests
except ImportError:
    pass
import threading
import logging
from .cjkwrap import cjklen, PY3
# from os import get_terminal_size

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)


class PyRadioStationsBrowser(object):
    """ A base class to get results from online radio directory services.

        Actual implementations should be subclasses of this one.
    """

    BASE_URL = ''
    TITLE = ''
    _raw_stations = []
    _last_search = None
    _have_to_retrieve_url = False
    _internal_header_height = 0
    _url_timeout = 3
    _search_timeout = 3

    # Normally outer boddy (holding box, header, internal header) is
    # 2 chars wider that the internal body (holding the stations)
    # This property value is half the difference (normally 2 / 2 = 1)
    # Used to chgat the columns' separators in internal body
    # Check if the cursor is divided as required and adjust
    _outer_internal_body_diff = 2
    _outer_internal_body_half_diff = 1

    def __init__(self, search=None):
        """ Initialize the station's browser.

            It should return a valid search result (for example,
            www.radio-browser.info implementation, returns 100 stations
            sorted by number of votes).

            Parameters
            ----------
            search
            Search parameters to be used instead of the default.
        """

        pass

    @property
    def outer_internal_body_half_diff(self):
        return self._outer_internal_body_half_diff

    @outer_internal_body_half_diff.setter
    def outer_internal_body_half_diff(self, value):
        raise ValueError('property is read only')

    @property
    def internal_header_height(self):
        return self._internal_header_height

    @internal_header_height.setter
    def internal_header_height(self, value):
        raise ValueError('property is read only')

    @property
    def have_to_retrieve_url(self):
        return self._have_to_retrieve_url

    @have_to_retrieve_url.setter
    def have_to_retrieve_url(self, value):
        raise ValueError('property is read only')

    @property
    def title(self):
        return self.TITLE

    @title.setter
    def title(self, value):
        self.TITLE = value

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

    BASE_URL = 'api.radio-browser.info'
    TITLE = 'Radio Browser'

    _open_url = 'https://de1.api.radio-browser.info/json/stations/topvote/100'
    _open_headers = {'user-agent': 'PyRadio/dev'}

    _raw_stations = []

    # the output format to use based on window width
    # Default value: -1
    # Possible values: 0..5
    # Look at format_station_line() for info
    _output_format = -1
    _info_len = []
    _info_name_len = 0

    _raw_stations = []
    _have_to_retrieve_url = True
    _internal_header_height = 1

    _columns_width = {
            'votes': 7,
            'clickcount': 7,
            'bitrate': 7,
            'country': 14,
            'language': 15
            }

    def __init__(self, config_encoding, search=None):
        self._config_encoding = config_encoding
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
                enc = '' if n['encoding'] == self._config_encoding else n['encoding']
                ret.append([n['name'], n['url'], enc])
            else:
                enc = '' if n['encoding'] == self._config_encoding else n['encoding']
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
                        logger.debug('Using existing url: "{}"'.format(self._raw_stations[id_in_list]['url_resolved']))
                    return self._raw_stations[id_in_list]['url_resolved']
                else:
                    stationid = self._raw_stations[id_in_list]['stationuuid']
                    url = self.real_url(stationid)
                    if url:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('URL retrieved: "{0}" <- "{1}'.format(url, self._raw_stations[id_in_list]['url']))
                        self._raw_stations[id_in_list]['url_resolved'] = url
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
            if logger.isEnabledFor(logging.ERROR):
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
        url = self._open_url
        try:
            # r = requests.get(url=url)
            r = requests.get(url=url, headers=self._open_headers, json=post_data, timeout=self._search_timeout)
            r.raise_for_status()
            logger.error(r.text)
            self._raw_stations = self._extract_data(json.loads(r.text))
            # logger.error('DE {}'.format(self._raw_stations))
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

        info = (u'',
                u' {0}{1}kb',
                u' {0}{1}│{2}kb',
                u' {0}{1}│{2}│{3}kb',
                u' {0}{1}│{2}│{3}kb│{4}',
                u' {0}{1}│{2}│{3}kb│{4}│{5}',
                )
        self._get_output_format(width)
        # logger.error('DE self._output_format = {}'.format(self._output_format))
        out = ['{0}. '.format(str(id_in_list + 1).rjust(pad)), '', '']

        # format info field
        pl = u'├' if self._raw_stations[id_in_list]['played'] else u'│'
        if self._output_format == 5:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(7)[:7],
                self._raw_stations[id_in_list]['clickcount'].rjust(7)[:7],
                self._raw_stations[id_in_list]['bitrate'].rjust(5)[:5],
                self._raw_stations[id_in_list]['country'].ljust(14)[:14],
                self._raw_stations[id_in_list]['language'].ljust(15)[:15]
            )
        if self._output_format == 4:
            # full or condensed info
            aa = self._raw_stations[id_in_list]['bitrate'].rjust(7)[:7]
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(7)[:7],
                self._raw_stations[id_in_list]['clickcount'].rjust(7)[:7],
                self._raw_stations[id_in_list]['bitrate'].rjust(5)[:5],
                self._raw_stations[id_in_list]['country'].ljust(14)[:14]
            )
        elif self._output_format == 2:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(7)[:7],
                self._raw_stations[id_in_list]['bitrate'].rjust(5)[:5]
            )
        elif self._output_format == 3:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(7)[:7],
                self._raw_stations[id_in_list]['clickcount'].rjust(7)[:7],
                self._raw_stations[id_in_list]['bitrate'].rjust(5)[:5]
            )
        elif self._output_format == 1:
            # Bitrate only
            out[2] = info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['bitrate'].rjust(5)[:5]
            )

        name_width = width-len(out[0])-len(out[2])
        out[1] = self._fix_cjk_string_width(self._raw_stations[id_in_list]['name'].ljust(name_width)[:name_width], name_width)
        if PY3:
            # if pl == '╞':
            #    out[2] += '╡'
            return (self._raw_stations[id_in_list]['played'],
                    '{0}{1}{2}'.format(*out))
        else:
            # on python 2, strings are already in utf-8
            return (self._raw_stations[id_in_list]['played'],
                    '{0}{1}{2}'.format(
                    out[0].encode('utf-8', 'replace'),
                    out[1].encode('utf-8', 'replace'),
                    out[2].encode('utf-8', 'replace')))

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
                ret[-1]['url'] = n['url']
                ret[-1]['url_resolved'] = n['url_resolved']
                ret[-1]['real_url'] = True if n['url_resolved'] else False
                ret[-1]['played'] = False
                ret[-1]['hls'] = n['hls']
                ret[-1]['stationuuid'] = n['stationuuid']
                ret[-1]['countrycode'] = n['countrycode']
                ret[-1]['country'] = n['country']
                if isinstance(n['clickcount'], int):
                    # old API
                    ret[-1]['votes'] = str(n['votes'])
                    ret[-1]['clickcount'] = str(n['clickcount'])
                    ret[-1]['bitrate'] = str(n['bitrate'])
                else:
                    # new API
                    ret[-1]['votes'] = n['votes']
                    ret[-1]['clickcount'] = n['clickcount']
                    ret[-1]['bitrate'] = n['bitrate']
                ret[-1]['language'] = n['language']
                ret[-1]['encoding'] = ''
                self._get_max_len(ret[-1]['votes'],
                                  ret[-1]['clickcount'])
        return ret

    def _get_max_len(self, votes, clicks):
        """ Calculate the maximum length of numeric_data / country

        Parameters
        ----------
        votes
            Number of station's vote (string)
        clicks
            Number of station's clicks (string)
        numeric_data

        Returns
        -------
        self._max_len
            A list [max votes length,
                    max clickcount length]
        """

        numeric_data = (votes, clicks)
        logger.error('DE numeric_data = {}'.format(numeric_data))
        min_data = (6, 7)
        for i, n in enumerate(numeric_data):
            if len(n) > self._max_len[i]:
                self._max_len[i] = len(n) if len(n) > min_data[i] else min_data[i]

    def _get_output_format(self, width):
        """ Return output format based on window width

        Paramaters
        ----------
        width
            Window width

        Returns
        -------
        self._output_format
            A number 0..5
        """

        # now_width = get_terminal_size().columns - 2
        if width <= 50:
            self._output_format = 0
        elif width < 57:
            self._output_format = 1
        elif width < 65:
            self._output_format = 2
        elif width < 80:
            self._output_format = 3
        elif width < 95:
            self._output_format = 4
        else:
            self._output_format = 5

    def _populate_columns_separators(self, a_tuple, width):
        ret = []
        for i, n in enumerate(a_tuple):
            if i == 0:
                ret.append(width - self._columns_width[n])
            else:
                ret.append(ret[-1] - 1 - self._columns_width[n])
        ret.reverse()
        return ret

    def get_columns_separators(self,
                               width,
                               use_old_output_format=False,
                               adjust=0,
                               adjust_for_body=False,
                               adjust_for_header=False,
                               ):
        """Calculates columns separators for a given width
        based on self._output_format.

        Parameters
        ----------
        width
            Window width to use for the calculation.
        use_old_output_format
            If True, do not calculate self._output_format
            (use what's already calculated).
        adjust
            Delete adjust from the output
            Example:
                if the output was [55, 67]
                and adjust was 2
                the output would become [53, 65]
        adjust_for_header
            Delete self._outer_internal_body_diff from output
            This is to be used for displaying the internal header
        adjust_for_body
            Delete self._outer_internal_body_half_diff from output
            This is to be used for changing columns' separators
            color, when displaying body lines (stations' lines).

        IMPORTANT
        ---------
        The adjust* parameters are mutually exclusive, which means
        that ONLY ONE of them can be used at any given call to the
        function. If you fail to comply, the result will be wrong.

        Returns
        -------
        A list containing columns_separotors (e.g. [55, 65]).
        """

        columns_separotors = []
        if not use_old_output_format:
            self._get_output_format(width)
        if self._output_format == 0:
            columns_separotors = []
        elif self._output_format == 1:
            columns_separotors = [width - col_width['bitrate']]
        elif self._output_format == 2:
            columns_separotors = self._populate_columns_separators(('bitrate', 'votes'), width)

        elif self._output_format == 3:
            columns_separotors = self._populate_columns_separators(('bitrate', 'clickcount', 'votes'), width)

        elif self._output_format == 4:
            columns_separotors = self._populate_columns_separators(('country', 'bitrate', 'clickcount', 'votes'), width)

        elif self._output_format == 5:
            columns_separotors = self._populate_columns_separators(('language', 'country', 'bitrate', 'clickcount', 'votes'), width)

        if adjust_for_header:
            for n in range(0, len(columns_separotors)):
                columns_separotors[n] -= self._outer_internal_body_diff

        if adjust_for_body:
            for n in range(0, len(columns_separotors)):
                columns_separotors[n] -= self._outer_internal_body_half_diff

        if adjust > 0:
            for n in range(0, len(columns_separotors)):
                columns_separotors[n] -= adjust
        return columns_separotors

    def get_internal_header(self, pad, width):
        columns = ((),
                   ('Bitrate', ),
                   ('  Votes', 'Bitrate'),
                   ('  Votes', ' Clicks', 'Bitrate'),
                   ('  Votes', ' Clicks', 'Bitrate', 'Country'),
                   ('  Votes', ' Clicks', 'Bitrate', 'Country', 'Language')
                   )
        columns_separotors = self.get_columns_separators(width, use_old_output_format=True)
        for i in range(0, len(columns_separotors)):
            columns_separotors[i] -= 2
        title = '#'.rjust(pad) + '  Name'
        return ((title, columns_separotors, columns[self._output_format]), )


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
        lock.acquire()
        callback(my_data, ret)
        lock.release()

def probeBrowsers(a_browser_url):
    base_url = a_browser_url.split('/')[2]
    logger.error('DE base_url = ' + base_url)
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
