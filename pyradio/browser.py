# -*- coding: utf-8 -*-
# http://www.radio-browser.info/webservice#Advanced_station_search
from dns import resolver
from copy import deepcopy
import random
import json
import collections
from operator import itemgetter
try:
    import requests
except ImportError:
    pass
import threading
import logging
from .player import info_dict_to_list
from .cjkwrap import cjklen, PY3
from .countries import countries

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

def capitalize_comma_separated_string(a_string):
    sp = a_string.split(',')
    for i, n in enumerate(sp):
        sp[i] = n.strip().capitalize()
    return ', '.join(sp)

class PyRadioStationsBrowser(object):
    ''' A base class to get results from online radio directory services.

        Actual implementations should be subclasses of this one.
    '''

    BASE_URL = ''
    TITLE = ''
    _raw_stations = []
    _last_search = None
    _internal_header_height = 0
    _url_timeout = 3
    _search_timeout = 3
    _vote_callback = None

    # Normally outer boddy (holding box, header, internal header) is
    # 2 chars wider that the internal body (holding the stations)
    # This property value is half the difference (normally 2 / 2 = 1)
    # Used to chgat the columns' separators in internal body
    # Check if the cursor is divided as required and adjust
    _outer_internal_body_diff = 2
    _outer_internal_body_half_diff = 1

    def __init__(self,
                 config_encoding,
                 session=None,
                 search=None,
                 pyradio_info=None):
        ''' Initialize the station's browser.

            It should return a valid search result (for example,
            www.radio-browser.info implementation, returns 100 stations
            sorted by number of votes).

            Parameters
            ----------
            search
            Search parameters to be used instead of the default.
        '''

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
    def title(self):
        return self.TITLE

    @title.setter
    def title(self, value):
        self.TITLE = value

    @property
    def vote_callback(self):
        return self._vote_callback

    @vote_callback.setter
    def vote_callback(self, val):
        self._vote_callback = val

    def stations(self, playlist_format=1):
        return []

    def url(self, id_in_list):
        ''' Return a station's real/playable url

            It has to be implemented only in case have_to_retrieve_url is True

            Parameters
            ----------
            id_in_list
                id in list of stations (0..len-1)

            Returns
            -------
                Real/playable url or '' if failed (string)
        '''

        return ''

    def set_played(self, id_in_list, played):
        ''' Note that a player has been played.

            Parameters
            ----------
            id_in_list
                id in list of stations (0..len-1)
            played
                True or False

        '''
        pass

    def search(self, data=None):
        return []

    def set_encoding(self, id_in_list, new_encoding):
        return

    def format_station_line(self, id_in_list, pad, width):
        return ''

    def click(self, a_station):
        pass

    def vote(self, a_station):
        pass


class RadioBrowserInfo(PyRadioStationsBrowser):

    BASE_URL = 'api.radio-browser.info'
    TITLE = 'Radio Browser '

    _headers = {'User-Agent': 'PyRadio/dev',
                     'Content-Type': 'application/json'}

    _raw_stations = []

    # the output format to use based on window width
    # Default value: -1
    # Possible values: 0..5
    # Look at format_station_line() for info
    _output_format = -1
    _info_len = []
    _info_name_len = 0

    _raw_stations = []
    _internal_header_height = 1

    _search_history = []
    _search_history_index = -1

    _columns_width = {
            'votes': 7,
            'clickcount': 7,
            'bitrate': 7,
            'country': 18,
            'language': 15,
            'state': 18,
            'tags': 20,
            'codec': 5
            }

    _dns_info = None

    def __init__(self,
                 config_encoding,
                 session=None,
                 search=None,
                 pyradio_info=None):
        if session:
            self._session = session
        else:
            self._session = requests.Session()
        self._pyradio_info = pyradio_info.strip()
        if self._pyradio_info:
            self._headers['User-Agent'] = self._pyradio_info.replace(' ', '/')
        self._config_encoding = config_encoding
        self._dns_info = RadioBrowserInfoDns()
        self._server = self._dns_info.give_me_a_server_url()
        self._get_title()

        self._search_history.append({
            'type': 'topvote',
            'term': '100',
            'param': None,
        })

        self._search_history.append({
            'type': 'bytagexact',
            'term': 'big band',
            'param': {'order': 'votes', 'reverse': 'true'},
        })
        self._search_history_index = 0

        self.search()

    @property
    def server(self):
        return self._server

    @property
    def add_to_title(self):
        return self._server.split('.')[0]

    def _get_title(self):
        self.TITLE = 'Radio Browser ({})'.format(self._country_from_server(self._server))

    def _country_from_server(self, a_server):
        country = a_server.split('.')[0]
        up = country[:-1].upper()
        if up in countries.keys():
            return countries[up]
        else:
            return country

    def stations(self, playlist_format=1):
        ''' Return stations' list (in PyRadio playlist format)

            Parameters
            ----------
            playlist_format
                0: station name, url
                1: station name, url, encoding
                2: station name, url, encoding, browser flag (default)
        '''

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
        ''' Get a station's url using resolved_url

            Parameters
            ----------
            id_in_list
                id in list of stations (0..len-1)

            Returns
            -------
                url or '' if failed
        '''

        if self._raw_stations:
            if id_in_list < len(self._raw_stations):
                if self._raw_stations[id_in_list]['url_resolved']:
                    return self._raw_stations[id_in_list]['url_resolved']
                else:
                    return self._raw_stations[id_in_list]['url']
        return ''

    def click(self, a_station):
        url = 'http://' + self._server + '/json/url/' + self._raw_stations[a_station]['stationuuid']
        try:
            r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station click result: "{}"'.format(r.text))
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station click failed...')

    def vote(self, a_station):
        url = 'http://' + self._server + '/json/vote/' + self._raw_stations[a_station]['stationuuid']
        try:
            r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
            message = json.loads(r.text)
            self.vote_result = message['message'][0].upper() + message['message'][1:]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station vote result: "{}"'.format(self.vote_result))
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station voting failed...')
            self.vote_result = 'Voting for station failed'

        if self._vote_callback:
            self._vote_callback()

    def get_info_string(self, a_station, max_width=60):
        guide = [
            ('Name',  'name'),
            ('URL', 'url'),
            ('Resolved URL', 'url_resolved'),
            ('Website', 'homepage'),
            ('Tags', 'tags'),
            ('Votes', 'votes'),
            ('Clicks', 'clickcount'),
            ('Country', 'country'),
            ('State', 'state'),
            ('Language', 'language'),
            ('Bitrate', 'bitrate'),
            ('Codec', 'codec')
        ]
        if self._raw_stations[a_station]['url'] == self._raw_stations[a_station]['url_resolved']:
            guide.pop(2)
        info = collections.OrderedDict()
        for n in guide:
            info[n[0]] = self._raw_stations[a_station][n[1]]
            if n[1] == 'bitrate':
                info[n[0]] += ' kb/s'

        a_list = []
        fix_highlight = []
        a_list = info_dict_to_list(info, fix_highlight, max_width)
        ret = '|' + '\n|'.join(a_list)
        # logger.error('DE \n\n{}\n\n'.format(ret))
        sp = ret.split('\n')
        wrong_wrap = -1
        for i, n in enumerate(sp):
            # logger.exception('DE {0}: "{1}"'.format(i, n))
            if wrong_wrap == i:
                sp[i] = n.replace('|', '')
                sp[i-1] += sp[i].replace('_', '')
                sp[i] = '*' + sp[i]
                wrong_wrap = -1
            else:
                if ': ' not in n:
                    sp[i] = n[1:]
                if n[-1] ==  ':':
                    ''' wrong wrapping! '''
                    wrong_wrap = i + 1
                    sp[i] += '|'
                    if sp[i][-1] != ' ':
                        sp[i] += ' '
                    if sp[i][0] != '|':
                        sp[i] = '|' + sp[i]
        for i, n in enumerate(sp):
            if n[0] == '*':
                sp.pop(i)
        ret = '\n'.join(sp).replace(': |', ':| ').replace(': ', ':| ')
        # logger.error('DE \n\n{}\n\n'.format(ret))
        return ret, ''

    def search(self):
        ''' Search for stations with parameters.
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
                        name           : station name
                        id             : station id
                        url            : station url
                        resolved_url   : station resolved_url
                        tags           : starion tags
                        bitrate        : station bitrate
                        hls            : HLS status
                        votes          : station votes
                        clickcount     : station clicks
                        country        : station country
                        state          : statiob state
                        language       : station language
                        codec          : station codec
                        encoding       : station encoding ('' means utf-8)
        '''

        url = self._format_url(self._search_history[self._search_history_index])
        logger.error('DE \n\nurl = "{}"\n\n'.format(url))
        post_data = {}
        if self._search_history[self._search_history_index]['param']:
            post_data = deepcopy(self._search_history[self._search_history_index]['param'])

        self._output_format = -1
        if self._search_type > 0:
            if 'limit' not in post_data.keys():
                post_data['limit'] = 100
            if not 'hidebroken' not in post_data.keys():
                post_data['hidebroken'] = True
        # url = 'https://' + self._server + '/json/stations/search'
        logger.error('DE \n\nheaders = "{}"'.format(self._headers))
        logger.error('DE \n\npost_data = "{}"'.format(post_data))
        try:
            # r = requests.get(url=url)
            r = self._session.get(url=url, headers=self._headers, params=post_data, timeout=(self._search_timeout, 2 * self._search_timeout))
            r.raise_for_status()
            self._raw_stations = self._extract_data(json.loads(r.text))
            for n in self._raw_stations:
                logger.error('{}'.format(n))
            # logger.error('DE \n\n{}'.format(self._raw_stations))
        except requests.exceptions.RequestException as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(e)
            self._raw_stations = []

    def get_next(self, search_term, start=0, stop=None):
        if search_term:
            pass
            for n in range(start, len(self._raw_stations)):
                if self._search_in_station(search_term, n):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(search_term, n))
                    return n

            """ if not found start from list top """
            for n in range(0, start):
                if self._search_in_station(search_term, n):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(search_term, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('forward search term "{}" not found'.format(search_term))
            return None
        else:
            return None

    def get_previous(self, search_term, start=0, stop=None):
        if search_term:
            for n in range(start, -1, -1):
                if self._search_in_station(search_term, n):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(search_term, n))
                    return n
            """ if not found start from list end """
            for n in range(len(self._raw_stations) - 1, start, -1):
                if self._search_in_station(search_term, n):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(search_term, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('backward search term "{}" not found'.format(search_term))
            return None
        else:
            return None

    def _search_in_station(self, a_search_term, a_station):
        guide = (
            'name',
            'country',
            'codec',
            'tags',
            'bitrate',
            'language'
        )
        for n in guide:
            if a_search_term.lower() in self._raw_stations[a_station][n].lower():
                return True
        return False

    def _format_url(self, a_search):
        if a_search['type'] in ('topvote',
                                'topclick',
                                'lastclick',
                                'lastchange',
                                'changed',
                                'improvable',
                                'broken',
                                ):
            url = 'http://{0}{1}'.format(
                self._server,
                '/json/stations/{}'.format(a_search['type'])
            )
            if a_search['term'] not in ('', '0'):
                url += '/{}'.format(a_search['term'])
            self._search_type = 0

        elif a_search['type'] in ('byuuid',
                                  'byname',
                                  'bynameexact',
                                  'bycodec',
                                  'bycodecexact',
                                  'bycountry',
                                  'bycountryexact',
                                  'bycountrycodeexact',
                                  'bystate',
                                  'bystateexact',
                                  'bylanguage',
                                  'bylanguageexact',
                                  'bytag',
                                  'bytagexact',
                                  ):
            url = 'http://{0}{1}/{2}'.format(
                self._server,
                '/json/stations/{}'.format(a_search['type']),
                a_search['term']
            )
            self._search_type = 1

        return url

    def format_empty_line(self, width):
        if self._output_format == 0:
            return  -1, ' '
        info = (
            (),
            ('bitrate', ),
            ('votes', 'bitrate'),
            ('votes', 'clickcount', 'bitrate'),
            ('votes', 'clickcount', 'bitrate', 'country'),
            ('votes', 'clickcount', 'bitrate', 'country', 'language'),
            ('votes', 'clickcount', 'bitrate', 'country', 'state', 'language'),
            ('votes', 'clickcount', 'bitrate', 'codec', 'country', 'state', 'language', 'tags')
        )

        out = ['', '']
        i_out = []
        for i, n in enumerate(info[self._output_format]):
            i_out.append(u'│' + ' ' * self._columns_width[n])
        out[1] = ''.join(i_out)

        name_width = width-len(out[1])
        out[0] = ' ' * name_width

        if PY3:
            return -1, '{0}{1}'.format(*out)
        else:
            return -1 , '{0}{1}'.format(
                out[0],
                out[1].encode('utf-8', 'replace')
            )


    def format_station_line(self, id_in_list, pad, width):
        ''' Create a formated line for a station

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
        '''

        info = (u'',
                u' {0}{1}kb',
                u' {0}{1}│{2}kb',
                u' {0}{1}│{2}│{3}kb',
                u' {0}{1}│{2}│{3}kb│{4}',
                u' {0}{1}│{2}│{3}kb│{4}│{5}',
                u' {0}{1}│{2}│{3}kb│{4}│{5}│{6}',
                u' {0}{1}│{2}│{3}kb│{4}│{5}│{6}│{7}│{8}',
                )
        self._get_output_format(width)
        # logger.error('DE self._output_format = {}'.format(self._output_format))
        out = ['{0}. '.format(str(id_in_list + 1).rjust(pad)), '', '']

        # format info field
        pl = u'├' if self._raw_stations[id_in_list]['played'] else u'│'
        if self._output_format == 7:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['clickcount'].rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['codec'].rjust(self._columns_width['codec'])[:self._columns_width['codec']],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']],
                self._raw_stations[id_in_list]['state'].ljust(self._columns_width['state'])[:self._columns_width['state']],
                self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language'])[:self._columns_width['language']],
                self._raw_stations[id_in_list]['tags'].ljust(self._columns_width['tags'])[:self._columns_width['tags']]
            )
        if self._output_format == 6:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['clickcount'].rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']],
                self._raw_stations[id_in_list]['state'].ljust(self._columns_width['state'])[:self._columns_width['state']],
                self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language'])[:self._columns_width['language']]
            )
        if self._output_format == 5:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['clickcount'].rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']],
                self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language'])[:self._columns_width['language']]
            )
        if self._output_format == 4:
            # full or condensed info
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['clickcount'].rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']]
            )
        elif self._output_format == 2:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
            )
        elif self._output_format == 3:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['votes'].rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                self._raw_stations[id_in_list]['clickcount'].rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
            )
        elif self._output_format == 1:
            # Bitrate only
            out[2] = info[self._output_format].format(
                pl,
                self._raw_stations[id_in_list]['bitrate'].rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
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
                ret[-1]['stationuuid'] = n['stationuuid']
                ret[-1]['url'] = n['url']
                ret[-1]['url_resolved'] = n['url_resolved']
                ret[-1]['url'] = n['url']
                ret[-1]['played'] = False
                ret[-1]['hls'] = n['hls']
                ret[-1]['stationuuid'] = n['stationuuid']
                ret[-1]['countrycode'] = n['countrycode']
                ret[-1]['country'] = n['country']
                ret[-1]['codec'] = n['codec']
                ret[-1]['state'] = n['state']
                ret[-1]['tags'] = n['tags'].replace(',', ', ')
                ret[-1]['homepage'] = n['homepage']
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
                ret[-1]['language'] = capitalize_comma_separated_string(n['language'])
                ret[-1]['encoding'] = ''
                self._get_max_len(ret[-1]['votes'],
                                  ret[-1]['clickcount'])
        return ret

    def _get_max_len(self, votes, clicks):
        ''' Calculate the maximum length of numeric_data / country

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
        '''

        numeric_data = (votes, clicks)
        # logger.error('DE numeric_data = {}'.format(numeric_data))
        min_data = (6, 7)
        for i, n in enumerate(numeric_data):
            if len(n) > self._max_len[i]:
                self._max_len[i] = len(n) if len(n) > min_data[i] else min_data[i]

    def _get_output_format(self, width):
        ''' Return output format based on window width

            Paramaters
            ----------
            width
                Window width

            Returns
            -------
            self._output_format
                A number 0..5
        '''

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
        elif width < 120:
            self._output_format = 5
        elif width < 145:
            self._output_format = 6
        else:
            self._output_format = 7

    def _populate_columns_separators(self, a_tuple, width):
        ret = []
        for i, n in enumerate(a_tuple):
            if i == 0:
                # logger.error('DE {0} - {1} = {2} - {3}'.format(width, self._columns_width[n], width-self._columns_width[n]-2, n))
                ret.append(width - self._columns_width[n] - 2)
            else:
                # logger.error('{0} -1 - {1} = {2} - {3}'.format(ret[-1], self._columns_width[n], ret[-1] - 1  - self._columns_width[n], n))
                ret.append(ret[-1] - 1 - self._columns_width[n])
        ret.reverse()
        # logger.error('DE \n\nret = {}\n\n'.format(ret))
        return ret

    def get_columns_separators(self,
                               width,
                               use_old_output_format=False,
                               adjust=0,
                               adjust_for_body=False,
                               adjust_for_header=False,
                               ):
        ''' Calculates columns separators for a given width
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
        '''

        columns_separotors = []
        if not use_old_output_format:
            self._get_output_format(width)
        if self._output_format == 0:
            columns_separotors = []
        elif self._output_format == 1:
            columns_separotors = [width - self._columns_width['bitrate']]
        elif self._output_format == 2:
            columns_separotors = self._populate_columns_separators(('bitrate', 'votes'), width)

        elif self._output_format == 3:
            columns_separotors = self._populate_columns_separators(('bitrate', 'clickcount', 'votes'), width)

        elif self._output_format == 4:
            columns_separotors = self._populate_columns_separators(('country', 'bitrate', 'clickcount', 'votes'), width)

        elif self._output_format == 5:
            columns_separotors = self._populate_columns_separators(('language', 'country', 'bitrate', 'clickcount', 'votes'), width)

        elif self._output_format == 6:
            columns_separotors = self._populate_columns_separators(('language', 'state', 'country', 'bitrate', 'clickcount', 'votes'), width)

        else:
            columns_separotors = self._populate_columns_separators(('tags', 'language', 'state', 'country', 'codec', 'bitrate', 'clickcount', 'votes'), width)

        if adjust_for_header and self._output_format == 1:
                columns_separotors[0] -= self._outer_internal_body_diff

        if adjust_for_body:
            if self._output_format == 1:
                columns_separotors[0] -= self._outer_internal_body_half_diff
            else:
                for n in range(0, len(columns_separotors)):
                    columns_separotors[n] += self._outer_internal_body_half_diff

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
                   ('  Votes', ' Clicks', 'Bitrate', 'Country', 'Language'),
                   ('  Votes', ' Clicks', 'Bitrate', 'Country', 'State', 'Language'),
                   ('  Votes', ' Clicks', 'Bitrate', 'Codec', 'Country', 'State', 'Language', 'Tags')
                   )
        columns_separotors = self.get_columns_separators(width, use_old_output_format=True)
        if self._output_format == 1:
            columns_separotors[0] -= 2
        title = '#'.rjust(pad) + '  Name'
        return ((title, columns_separotors, columns[self._output_format]), )

    def create_sort_window(self, parent):
        self._sort = RadioBrowserInfoSort(parent)
        self._sort.show()

    def show_sort_window(self):
        self._sort.show()

    def keypress(self, char):
        '''
            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''
        ret = self._sort.keypress(char)

        if ret == 0:
            self.active_selection = self._sort.active_selection
            self._sort = None
        return ret

class RadioBrowserInfoData(object):
    ''' Read search parameters for radio.browser.info service

        parameters are:
            tags, countries(and states), codecs, languages
    '''

    _data = {}
    _connection_error = False
    _lock = threading.Lock()
    _stop_thread = False
    _timeout = 3
    data_thread = None

    def __init__(self, url, timeout=3):
        self._url = url
        self._timeout = timeout

    def start(self, force_update=False):
        ''' Start data acquisition thread '''
        self.data_thread = threading.Thread(
            target=self._get_all_data_thread,
            args=(
                self._lock, force_update, lambda: self._stop_thread,
                self._update_data
            )
        )
        self.data_thread.start()

    def stop(self):
        ''' Stop (cancel) data acquisition thread '''
        self._stop_thread = True

    @property
    def lock(self):
        ''' Return thread lock (read only)'''
        return self._lock

    @lock.setter
    def lock(self, val):
        raise ValueError('property is read only')

    @property
    def terminated(self):
        ''' Return True if thread is not alive (read only)
        which means that data has been retrieved'''
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
            url = 'http://' + self._url + '/json/' + data
            jdata = {'hidebroken': 'true'}
            headers = {'user-agent': 'PyRadio/dev',
                       'encoding': 'application/json'}
            if self._pyradio_info:
                headers['user-agent'] = self._pyradio_info.replace(' ', '/')
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


class RadioBrowserInfoDns(object):
    ''' Preforms query the DNS SRV record of
        _api._tcp.radio-browser.info which
        gives the list of server names directly
        without reverse dns lookups '''

    _urls = None

    def __init__(self):
        pass

    @property
    def server_urls(self):
        ''' Returns server urls in a tuple '''
        if self._urls is None:
            self._get_urls()

        return tuple(self._urls) if self._urls is not None else None

    def _get_urls(self):
        self._urls = []
        result = None
        try:
            result = resolver.query('_api._tcp.radio-browser.info', 'SRV')
        except:
            self._urls = None
            return ''

        for n in result:
            self._urls.append(str(n).split(' ')[-1][:-1])

    def give_me_a_server_url(self):
        ''' Returns a random server '''
        if self._urls is None:
            self._get_urls()

        num = random.randint(0, len(self._urls) - 1)
        return self._urls[num]

    def servers(self):
        ''' server urls as generator '''
        if self._urls is None:
            self._get_urls()

        for a_url in self._urls:
            yield a_url

class RadioBrowserInfoSort(object):

    TITLE = ' Sort by  '

    items = collections.OrderedDict()
    items = {
        'Name': 'name',
        'Votes': 'votes',
        'Clicks': 'clicks',
        'Bitrate': 'bitrate',
        'Codec': 'codec',
        'Country': 'country',
        'State': 'state',
        'Language': 'language',
        'Tag': 'tags'
    }

    _too_small = False

    def __init__(self, parent, active=None):
        self.active = self.selection = 0
        self.maxY = len(self.items) + 2
        self._maxX = max(len(x) for x in self.items.keys()) + 4
        if len(self.TITLE) + 4 > self.maxX:
            self.maxX = len(self.TITLE) + 4
        self._win = None
        if active:
            self.set_active_by_value(active)

    def set_parent(self, parent):
        self._parent = parent
        self.show()

    def set_active_by_value(self, a_string, set_selection=True):
        for i, n in enumerate(self.items.values()):
            if a_string == n:
                if set_selection:
                    self.active = self.selection = i
                else:
                    self.active = i
                return

        if set_selection:
            self.active = self.selection = 0
        else:
            self.active = 0

    def show(self):
        pY, pX = self._parent.getmaxyx()
        if self.maxY > pY -2 or self.maxX > pX -2:
            self._too_small = True
            msg = 'Window too small to display content!'
            if self.maxX < len(msg) + 2:
                msg = 'Window too small!'
            self._win = curses.newwin(
                3, len(msg) + 2,
                int(pY / 2) - 1,
                int((pX - len(msg)) / 2))
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.box()
            try:
                self._win.addstr(
                    1, 1,
                    msg, curses.color_pair(5))
            except:
                pass
            self._win.refresh()
            return

        self._win = curses.newwin(
            self.maxY, self.maxX,
            int((pY - self.maxY) / 2),
            int((pX - self.maxX) / 2)
        )
        self._win.bkgdset(' ', curses.color_pair(3))
        # self._win.erase()
        self._win.box()
        self._win.addstr(0, int((self.maxX - len(self.TITLE)) / 2),
                         self.TITLE, curses.color_pair(4))
        self._refresh()

    def _refresh(self):
        for i, n in self.items.keys():
            col = 5
            if i == self.active == self.selection:
                col = 4
            elif i == self.selection:
                col = 3
            elif i == self.active:
                col = 2

            self._win.addstr(i + 1, 2, n + ' ' * (self.maxX - 2 - len(n)), curses.color_pair(col))
        self._win.refresh()

    def keypress(char):
        '''
            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''
        if not self._too_small:

            if char in (
                curses.KEY_EXIT, ord('q'), 27,
                ord('h'), curses.KEY_RIGHT
            ):
                return -1

            elif char in (
                ord('l'), ord(' '), '\n', '\r',
                curses.KEY_LEFT, curses.KEY_ENTER
            ):
                for i, n in enumerate(self.items.keys()):
                    if i == self.selection:
                        self.active_selection = self.items[n]
                        break
                return 0

            elif char in (ord('g'), curses.KEY_HOME):
                self.selection = 0
                self._refresh()

            elif char in (ord('G'), curses.KEY_END):
                self.selection = len(self.items) - 1
                self._refresh()

            elif char in (curses.KEY_PPAGE, ):
                if self.selection == 0:
                    self.selection = len(self.items) - 1
                else:
                    self.selection -= 5
                    if self.selection < 0:
                        self.selection = len(self.items) - 1
                self._refresh()

            elif char in (curses.KEY_NPAGE):
                if self.selection == len(self.items) - 1:
                    self.selection = 0
                else:
                    self.selection += 5
                    if self.selection >= len(self.items):
                        self.selection = 0
                self._refresh()

            elif char in (ord('k'), curses.KEY_UP):
                self.selection -= 1
                if self.selection <= 0:
                    self.selection = len(self.items) - 1
                self._refresh()

            elif char in (ord('j'), curses.KEY_DOWN):
                self.selection += 1
                if self.selection == len(self.items):
                    self.selection = 0
                self._refresh()

        return 1


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


