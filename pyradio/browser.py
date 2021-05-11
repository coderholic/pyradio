# -*- coding: utf-8 -*-
import curses
try:
    from dns import resolver
except ImportError:
    pass
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
from .simple_curses_widgets import SimpleCursesLineEdit, SimpleCursesHorizontalPushButtons, SimpleCursesWidgetColumns, SimpleCursesCheckBox

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

def country_from_server(a_server):
    if a_server:
        country = a_server.split('.')[0]
        up = country[:-1].upper()
        if up in countries.keys():
            return countries[up]
        else:
            return country
    else:
        return None

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
    _parent = _outer_parent = None
    _raw_stations = []
    _last_search = None
    _internal_header_height = 0
    _url_timeout = 3
    _search_timeout = 3
    _vote_callback = None
    _sort = _sort_win = None

    # Normally outer boddy (holding box, header, internal header) is
    # 2 chars wider that the internal body (holding the stations)
    # This property value is half the difference (normally 2 / 2 = 1)
    # Used to chgat the columns' separators in internal body
    # Check if the cursor is divided as required and adjust
    _outer_internal_body_diff = 2
    _outer_internal_body_half_diff = 1

    def __init__(self,
                 config,
                 config_encoding,
                 session=None,
                 search=None,
                 pyradio_info=None,
                 search_return_function=None,
                 message_function=None):
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
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, val):
        self._parent = val
        if self._sort:
            self._sort._parent = val

    @property
    def outer_parent(self):
        return self._outer_parent

    @outer_parent.setter
    def outer_parent(self, val):
        self._outer_parent = val
        if self._sort_win:
            self._sort_win._parent = val

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

    def search(self, go_back_in_history=True):
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

    _server_selection_window = None
    _dns_info = None

    search_by = _old_search_by = None

    keyboard_handler = None

    def __init__(self,
                 config,
                 config_encoding,
                 session=None,
                 search=None,
                 pyradio_info=None,
                 search_return_function=None,
                 message_function=None):
        '''
            When first_search is True, it means that we are opening
            the browser. If empty result is returned by the first
            browser search, we show an empty stations' list.
            if it is False and an empty result is returned by the first
            browser search, which means we are already in the browser's
            search screen, we just display the 'no result message'.
            All of this is done at radio.py
        '''
        self.first_search = True
        self._cnf = config
        if session:
            self._session = session
        else:
            self._session = requests.Session()
        self._pyradio_info = pyradio_info.strip()
        if self._pyradio_info:
            self._headers['User-Agent'] = self._pyradio_info.replace(' ', '/')
        self._config_encoding = config_encoding
        self._message_function = message_function
        self._search_return_function = search_return_function


    def initialize(self):
        self._dns_info = RadioBrowserInfoDns()
        self._server = self._dns_info.give_me_a_server_url()
        if logger.isEnabledFor(logging.INFO):
            logger.info('random server is ' + self._server)
        if self._server:
            self._get_title()

            self._search_history.append({
                'type': 'topvote',
                'term': '100',
                'post_data': None,
            })

            self._search_history.append({
                'type': 'bytagexact',
                'term': 'big band',
                'post_data': {'order': 'votes', 'reverse': 'true'},
            })

            self._search_history.append({
                'type': 'search',
                'term': '',
                'post_data': {'name': 'jaz'},
            })
            self._search_history_index = 0
            return True
        return False

    @property
    def server(self):
        return self._server

    @property
    def add_to_title(self):
        return self._server.split('.')[0]

    def _get_title(self):
        self.TITLE = 'Radio Browser ({})'.format(country_from_server(self._server))

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
        def do_click(a_station_uuid):
            url = 'http://' + self._server + '/json/url/' + a_station_uuid
            try:
                r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Station click result: "{}"'.format(r.text))
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Station click failed...')
        threading.Thread(target=do_click, args=(self._raw_stations[a_station]['stationuuid'], )).start()

    def vote(self, a_station):
        url = 'http://' + self._server + '/json/vote/' + self._raw_stations[a_station]['stationuuid']
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Voting for: {}'.format(self._raw_stations[a_station]))
            logger.debug('Voting url: ' + url)
        try:
            r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
            message = json.loads(r.text)
            self.vote_result = self._raw_stations[a_station]['name'], message['message'][0].upper() + message['message'][1:]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Voting result: "{}"'.format(message))
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station voting failed...')
            self.vote_result = self._raw_stations[a_station]['name'], 'Voting for station failed'

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
            info[n[0]] = str(self._raw_stations[a_station][n[1]])
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

    def search(self, go_back_in_history=True):
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

        if self._message_function:
            self._message_function()
        self.search_by = self._old_search_by = None
        self._get_search_elements(
            self._search_history[self._search_history_index]
        )
        self._old_search_by = self.search_by
        self._sort = None
        url = self._format_url(self._search_history[self._search_history_index])
        post_data = {}
        if self._search_history[self._search_history_index]['post_data']:
            post_data = deepcopy(self._search_history[self._search_history_index]['post_data'])

        self._output_format = -1
        if self._search_type > 0:
            if 'limit' not in post_data.keys():
                post_data['limit'] = 100
            if not 'hidebroken' not in post_data.keys():
                post_data['hidebroken'] = True

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('  == history = {}'.format(self._search_history[self._search_history_index]))
            logger.debug('  == url = "{}"'.format(url))
            logger.debug('  == headers = "{}"'.format(self._headers))
            logger.debug('  == post_data = "{}"'.format(post_data))

        ''' keep server results here '''
        new_raw_stations = []

        try:
            r = self._session.get(url=url, headers=self._headers, params=post_data, timeout=(self._search_timeout, 2 * self._search_timeout))
            r.raise_for_status()
            new_raw_stations = self._extract_data(json.loads(r.text))
            # logger.error('DE \n\n{}'.format(new_raw_stations))
            ret = True, len(new_raw_stations), go_back_in_history
        except requests.exceptions.RequestException as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(e)
            self._raw_stations = []
            ret = False, 0, go_back_in_history

        ''' use server result '''
        if len(new_raw_stations) > 0:
            self._raw_stations = new_raw_stations[:]

        if self._search_return_function:
            self._search_return_function(ret)

    def _get_search_elements(self, a_search):
        '''
            get "by search" and "reverse"
            values from a search dict.
            To be used with the sort function
        '''
        logger.error('DE search in function is "{}"'.format(a_search))
        a_term = a_search['term']
        p_data = a_search['post_data']
        self.search_by = None
        self.reverse = False
        if a_search['post_data']:
            if 'order' in a_search['post_data'].keys():
                self.search_by = a_search['post_data']['order']
            if 'reverse' in a_search['post_data']:
                self.reverse = True if a_search['post_data']['reverse'] == 'true' else False

        logger.error('DE search by was "{}"'.format(self.search_by))
        if self.search_by is None:
            a_type = a_search['type']
            if a_type == 'byname':
                self.search_by = 'name'
            elif a_type == 'topvote':
                self.search_by = 'votes'
                logger.error('DE search by is votes')
            elif a_type == 'clickcount':
                self.search_by = 'clickcount'
            elif a_type == 'bitrate':
                self.search_by = 'bitrate'
            elif a_type == 'codec':
                self.search_by = 'codec'
            elif a_type == 'country':
                self.search_by = 'country'
            elif a_type == 'state':
                self.search_by = 'state'
            elif a_type == 'language':
                self.search_by = 'language'
            elif a_type == 'tags':
                self.search_by = 'tags'

        if self.search_by is None:
            if p_data:
                if 'name' in p_data.keys():
                    self.search_by = 'name'
                    logger.error('DE search by is name (default)')

        if self.search_by is None:
            self.search_by = 'name'
            logger.error('DE search by is name (default)')

        logger.error('DE search by is "{}"'.format(self.search_by))

    def get_next(self, search_term, start=0, stop=None):
        if search_term:
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
            source = self._raw_stations[a_station][n]
            if isinstance(source, int):
                ''' this is one of the numerical data '''
                source = str(source)
            if a_search_term.lower() in source.lower():
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

        elif a_search['type'] == 'search':
            url = 'http://{0}{1}'.format(
                self._server,
                '/json/stations/search'
            )
            self._search_type = 2

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
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
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
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']],
                self._raw_stations[id_in_list]['state'].ljust(self._columns_width['state'])[:self._columns_width['state']],
                self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language'])[:self._columns_width['language']]
            )
        if self._output_format == 5:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']],
                self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language'])[:self._columns_width['language']]
            )
        if self._output_format == 4:
            # full or condensed info
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country'])[:self._columns_width['country']]
            )
        elif self._output_format == 2:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
            )
        elif self._output_format == 3:
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
            )
        elif self._output_format == 1:
            # Bitrate only
            out[2] = info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2]
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
                    ret[-1]['votes'] = n['votes']
                    ret[-1]['clickcount'] = n['clickcount']
                    ret[-1]['bitrate'] = n['bitrate']
                else:
                    # new API
                    ret[-1]['votes'] = int(n['votes'])
                    ret[-1]['clickcount'] = int(n['clickcount'])
                    ret[-1]['bitrate'] = int(n['bitrate'])
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
        for i, x in enumerate(numeric_data):
            n = str(x)
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
        guide = {
            'name': 'Name',
            'votes': '  Votes',
            'clickcount': ' Clicks',
            'bitrate': 'Bitrate',
            'codec': 'Codec',
            'country': 'Country',
            'state': 'State',
            'language': 'Language',
            'tags': 'Tags',
        }
        # logger.error('DE search = {}'.format(self._search_history[self._search_history_index]))
        reset_search_elements = False
        if self.search_by is None:
            reset_search_elements = True
            self._get_search_elements(self._search_history[self._search_history_index])
            # logger.error('DE search by = {}'.format(self.search_by))
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
        title = '#'.rjust(pad), ' Name '
        if reset_search_elements:
            self._old_search_by = self.search_by
        # logger.error('DE search by = {}'.format(self.search_by))
        # logger.error('DE Looking for: "{}"'.format(guide[self.search_by]))
        # logger.error('DE Names = {}'.format(columns[self._output_format]))
        if guide[self.search_by] == 'Name':
            highlight = -2
        else:
            try:
                highlight = columns[self._output_format].index(guide[self.search_by])
            except:
                highlight = -1
        return highlight, ((title, columns_separotors, columns[self._output_format]), )

    def select_servers(self):
        if self._server_selection_window is None:
            self._server_selection_window = RadioBrowserInfoServersSelect(
                self.parent, self._dns_info.server_urls, self._server)
        else:
            self._server_selection_window.set_parent(self.parent)
        self.keyboard_handler = self._server_selection_window
        self._server_selection_window.show()

    def sort(self):
        '''
            Create and show the Sort window
        '''
        if self._sort is None:
            self._get_search_elements(
                self._search_history[self._search_history_index]
            )
            self._sort = RadioBrowserInfoSort(
                parent=self.parent,
                search_by=self.search_by
            )
        self.keyboard_handler = self._sort
        self._sort.show()

    def keypress(self, char):
        ''' RadioBrowserInfo keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''
        ret = self.keyboard_handler.keypress(char)

        if ret == 0:
            if self.keyboard_handler == self._sort:
                self.search_by = self._sort.search_by
                if self.search_by == self._old_search_by:
                    self.reverse = not self.reverse
                else:
                    self.reverse = False
                    if self.search_by != self._old_search_by:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('search by = "{}"'.format(self.search_by))
                        ''' set reverse to True for numerical values
                            when changing sort type
                        '''
                        if self.search_by in (
                            'votes',
                            'clickcount',
                            'bitrate'
                        ):
                            self.reverse = True
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('settng reverse to {}'.format(self.reverse))

                self._raw_stations = sorted(self._raw_stations, key=itemgetter(self.search_by), reverse=self.reverse)
                self._old_search_by = self.search_by

            elif self.keyboard_handler == self._server_selection_window:
                if ret == 0:
                    self._server = self._server_selection_window.server
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('user selected server is ' + self._server)
                    self._get_title()

        return ret

    def do_search(self, parent=None, init=False):
        if init:
            self._sort_win = RadioBrowserInfoSearchWindow(
                parent=parent,
                init=init
            )
        self.keyboard_handler = self._sort_win
        self._sort_win.show()

class RadioBrowserInfoSearchWindow(object):

    # search_by_items = (
    #     'No search term',
    #     'Name',
    #     'Tag',
    #     'Country',
    #     'State',
    #     'Codec',
    #     'Language',
    # )

    search_by_items = (
        'Votes',
        'Clicks',
        'Recent click',
        'Recently changed'
    )

    sort_by_items = (
        'No sorting',
        'Random',
        'Name',
        'Tag',
        'Country',
        'State',
        'Language',
        'Votes',
        'Clicks',
        'Bitrate',
        'Codec',
    )

    def __init__(self,
                 parent,
                 init=False
                 ):
        self._parent = parent
        self._init = init
        self._too_small = False
        self._focus = 0
        self._win = None
        self.maxY = self.maxX = 0
        self.TITLE = ' Radio Browser Search '

        ''' we have two columns;
            this is the width of each of them
        '''
        self._half_width = 0
        self._widgets = [ None, None, None, None, None, None, None, None]

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0, len(self._widgets)):
            self._focus = val
        else:
            if val < 0:
                self._focus = len(self._widgets) - 1
            else:
                self._focus = 0
        self.show()

    def show(self):
        pY, pX = self._parent.getmaxyx()
        logger.error('DE pY = {}, pX = {}'.format(pY, pX))
        self.Y, self.X = self._parent.getbegyx()

        if self.maxY != pY or self.maxX != pX:
            logger.error('DE --== SEARCH ==--')
            pY, pX = self._parent.getmaxyx()
            logger.error('DE pY = {}, pX = {}'.format(pY, pX))
            self.maxY = pY
            self.maxX = pX
            self._win = self._parent
            # self._win = curses.newwin(
            #     self.maxY, self.maxX,
            #     Y, X
            # )
            self._half_width = int((self.maxX -2 ) / 2) -3
        self._win.bkgdset(' ', curses.color_pair(5))
        # self._win.erase()
        self._win.box()
        self._win.addstr(0, int((self.maxX - len(self.TITLE)) / 2),
                         self.TITLE,
                         curses.color_pair(4))
        self._win.refresh()
        # self._erase_win(self.maxY, self.maxX, self.Y, self.X)

        ''' start displaying things '''
        self._win.addstr(1, 2, 'Search for', curses.color_pair(5))
        self._win.addstr(4, 2, 'Search by', curses.color_pair(5))

        for i, n in enumerate(self._widgets):
            if n is None:
                if i == 0:
                    #self._widgets[2] = SimpleCursesCheckBox(
                    #    1, 2, 'Display by',
                    #    curses.color_pair(9),
                    #    curses.color_pair(4),
                    #    curses.color_pair(5))
                    self._widgets[0] = SimpleCursesLineEdit(
                        parent=self._win,
                        width=-2,
                        begin_y=3,
                        begin_x=2,
                        boxed=False,
                        has_history=False,
                        caption='',
                        box_color=curses.color_pair(9),
                        caption_color=curses.color_pair(4),
                        edit_color=curses.color_pair(9),
                        cursor_color=curses.color_pair(8),
                        unfocused_color=curses.color_pair(5),
                        string_changed_handler='')
                    self._widgets[0].bracket = False
                    self._line_editor = self._widgets[0]
                elif i == 1:
                    ''' search by '''
                    self._widgets[i] = SimpleCursesWidgetColumns(
                        Y=5, X=3, window=self._win,
                        selection=0,
                        active=0,
                        items=self.search_by_items,
                        color=curses.color_pair(5),
                        color_active=curses.color_pair(4),
                        color_cursor_selection=curses.color_pair(6),
                        color_cursor_active=curses.color_pair(9),
                        margin=1,
                        max_width=self._half_width
                    )
                elif i == 2:
                    ''' search exact '''
                    self._widgets[2] = SimpleCursesCheckBox(
                            self._widgets[1].Y + self._widgets[1].height + 2, 2,
                            'Exact match',
                            curses.color_pair(9), curses.color_pair(4), curses.color_pair(5))
                elif i == 3:
                    ''' sort by '''
                    self._widgets[i] = SimpleCursesWidgetColumns(
                        Y=5, X=self.maxX - 1 - self._half_width,
                        max_width=self._half_width,
                        window=self._win,
                        selection=0,
                        active=0,
                        items=self.sort_by_items,
                        color=curses.color_pair(5),
                        color_active=curses.color_pair(4),
                        color_cursor_selection=curses.color_pair(6),
                        color_cursor_active=curses.color_pair(9),
                        margin=1
                    )
                elif i == 4:
                    '''' sort ascending / descending '''
                    self._widgets[4] = SimpleCursesCheckBox(
                            self._widgets[3].Y + self._widgets[3].height + 1, self._widgets[3].X - 2 + self._widgets[3].margin,
                            'Sort descending',
                            curses.color_pair(9), curses.color_pair(4), curses.color_pair(5))
                elif i == 5:
                    '''' limit results '''
                    self._widgets[5] = None
                elif i == 6:
                    self._widgets[i] = None
                    ''' add horizontal push buttons '''
                    self._h_buttons = SimpleCursesHorizontalPushButtons(
                            Y=5 + len(self.search_by_items) + 2,
                            captions=('OK', 'Cancel'),
                            color_focused=curses.color_pair(9),
                            color=curses.color_pair(4),
                            bracket_color=curses.color_pair(5),
                            parent=self._win)
                    #self._h_buttons.calculate_buttons_position()
                    self._widgets[6], self._widgets[7] = self._h_buttons.buttons
                    self._widgets[6]._focused = self._widgets[7].focused = False
            else:
                if i in (1, 3):
                    ''' update lists' window '''
                    if i == 3:
                        self._widgets[3].X = self.maxX - 1 - self._half_width
                    self._widgets[i].window = self._win
                    self._widgets[i].max_width = self._half_width

        self._win.addstr(
            4,
            self._widgets[3].X - 2 + self._widgets[3].margin,
            'Sort by',
            curses.color_pair(5)
        )
        self._win.refresh()
        self._update_focus()
        if not self._too_small:
            self._line_editor.show(self._win, opening=False)
            self._h_buttons.calculate_buttons_position()
            for n in range(1, len(self._widgets)):
                if self._widgets[n]:
                    if n in (2, 4):
                        if n == 2:
                            self._widgets[2].Y = self._widgets[1].Y + self._widgets[1].height + 2
                        else:
                            self._widgets[4].Y = self._widgets[3].Y + self._widgets[3].height + 1
                            self._widgets[4].X = self._widgets[3].X - 2 + self._widgets[3].margin
                        self._widgets[n].move()
                        # self._widgets[n].resize()
                    self._widgets[n].show()
        self._win.refresh()

        # self._refresh()

    def _update_focus(self):
        # use _focused here to avoid triggering
        # widgets' refresh
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False


    def keypress(self, char):
        ''' RadioBrowserInfoSearchWindow keypress

            Returns
            -------
               -1 - Cancel
                0 - do search
                1 - Continue
                2 - Display help
        '''
        if self._too_small:
            return 1

        if char == ord('?'):
            return 2

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
            ord('h'), curses.KEY_LEFT
        ):
            return -1

        elif char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            return 0

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
                if logger.isEnabledFor(logging.DEBUG):
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

    @server_urls.setter
    def server_urls(self, val):
        return

    def _get_urls(self):
        self._urls = []
        result = None
        try:
            result = resolver.query('_api._tcp.radio-browser.info', 'SRV')
        except:
            self._urls = None

        for n in result:
            self._urls.append(str(n).split(' ')[-1][:-1])

    def give_me_a_server_url(self):
        ''' Returns a random server '''
        if self._urls is None:
            self._get_urls()

        if self._urls:
            num = random.randint(0, len(self._urls) - 1)
            return self._urls[num]
        else:
            return None

    def servers(self):
        ''' server urls as generator '''
        if self._urls is None:
            self._get_urls()

        for a_url in self._urls:
            yield a_url

class RadioBrowserInfoSort(object):

    TITLE = ' Sort by '

    items = collections.OrderedDict({
        'Name': 'name',
        'Votes': 'votes',
        'Clicks': 'clickcount',
        'Bitrate': 'bitrate',
        'Codec': 'codec',
        'Country': 'country',
        'State': 'state',
        'Language': 'language',
        'Tag': 'tags'
    })

    _too_small = False

    def __init__(self, parent, search_by=None):
        self._parent = parent
        self.active = self.selection = 0
        if search_by:
            if search_by in self.items.values():
                self.active = self.selection = self._value_to_index(search_by)
        self.maxY = len(self.items) + 2
        self.maxX = max(len(x) for x in self.items.keys()) + 4
        if len(self.TITLE) + 4 > self.maxX:
            self.maxX = len(self.TITLE) + 4
        self._win = None
        if search_by:
            self.set_active_by_value(search_by)

    def _value_to_index(self, val):
        for i, n in enumerate(self.items.values()):
            if val == n:
                return i
        return -1

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
        self._too_small = False
        pY, pX = self._parent.getmaxyx()
        Y, X = self._parent.getbegyx()
        if self.maxY > pY or self.maxX > pX -2:
            self._too_small = True
            msg = 'Window too small to display content!'
            if pX < len(msg) + 2:
                msg = 'Window too small!'
            self._win = curses.newwin(
                3, len(msg) + 2,
                Y + int((pY - 3) / 2),
                int((pX - len(msg)) / 2))
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.box()
            try:
                self._win.addstr( 1, 1, msg,
                                 curses.color_pair(5))
            except:
                pass
            self._win.refresh()
            return

        self._win = curses.newwin(
            self.maxY, self.maxX,
            Y + int((pY - self.maxY) / 2),
            int((pX - self.maxX) / 2)
        )
        self._win.bkgdset(' ', curses.color_pair(3))
        # self._win.erase()
        self._win.box()
        self._win.addstr(0, 1,
                         self.TITLE,
                         curses.color_pair(4))
        self._refresh()

    def _refresh(self):
        for i, n in enumerate(self.items.keys()):
            col = 5
            if i == self.active == self.selection:
                col = 9
            elif i == self.selection:
                col = 6
            elif i == self.active:
                col = 4

            self._win.addstr(i + 1, 1,
                             ' {}'.format(n.ljust(self.maxX - 3)),
                             curses.color_pair(col))
        self._win.refresh()

    def keypress(self, char):
        ''' RadioBrowserInfoSort keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''

        if self._too_small:
            return 1

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
            ord('h'), curses.KEY_LEFT
        ):
            return -1

        elif char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            for i, n in enumerate(self.items.keys()):
                if i == self.selection:
                    self.search_by = self.items[n]
                    self.active = i
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
                    self.selection = 0
            self._refresh()

        elif char in (curses.KEY_NPAGE, ):
            if self.selection == len(self.items) - 1:
                self.selection = 0
            else:
                self.selection += 5
                if self.selection >= len(self.items):
                    self.selection = len(self.items) - 1
            self._refresh()

        elif char in (ord('k'), curses.KEY_UP):
            self.selection -= 1
            if self.selection < 0:
                self.selection = len(self.items) - 1
            self._refresh()

        elif char in (ord('j'), curses.KEY_DOWN):
            self.selection += 1
            if self.selection == len(self.items):
                self.selection = 0
            self._refresh()

        return 1


class RadioBrowserInfoServersSelect(object):

    TITLE = ' Server Selection '

    def __init__(self, parent, servers, current_server):
        self._parent = parent
        self.items = list(servers)
        self.server = current_server

        self.servers = RadioBrowserInfoServers(
            parent, servers, current_server
        )
        self.maxY = self.servers.maxY + 2
        self.maxX = self.servers.maxX + 2

    def show(self):
        self._too_small = False
        pY, pX = self._parent.getmaxyx()
        Y, X = self._parent.getbegyx()
        if self.maxY > pY or self.maxX > pX -2:
            self._too_small = True
            msg = 'Window too small to display content!'
            if pX < len(msg) + 2:
                msg = 'Window too small!'
            self._win = curses.newwin(
                3, len(msg) + 2,
                Y + int((pY - 3) / 2),
                int((pX - len(msg)) / 2))
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.box()
            try:
                self._win.addstr( 1, 1, msg,
                                 curses.color_pair(5))
            except:
                pass
            self._win.refresh()
            return

        self._win = curses.newwin(
            self.maxY, self.maxX,
            Y + int((pY - self.maxY) / 2),
            int((pX - self.maxX) / 2)
        )
        self._win.bkgdset(' ', curses.color_pair(3))
        # self._win.erase()
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self.TITLE)) / 2),
            self.TITLE,
            curses.color_pair(4)
        )
        self._win.refresh()
        self.servers._parent = self._win
        self.servers.show()

    def set_parent(self, parent):
        self._parent = parent
        self.servers._parent = parent

    def keypress(self, char):
        ''' RadioBrowserInfoServersSelect keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''

        ret = self.servers.keypress(char)

        if ret == 2:
            ret = 1
        if ret == 0:
            self.server = self.servers.server

        return ret


class RadioBrowserInfoServers(object):
    ''' Display Radio Browser server
        This is supposed to be pluged into
        another widget
    '''

    _too_small = False

    def __init__(self, parent, servers, current_server):
        self._parent = parent
        self.items = list(servers)
        self.server = current_server

        s_max = 0
        for i, n in enumerate(self.items):
            if self.server == n:
                self.selection = self.active = i
            self.items[i] = ' ' + country_from_server(n) + '  ({}) '.format(n)
            if len(self.items[i]) > s_max:
                s_max = len(self.items[i])
        self.items.sort()
        for i, n in enumerate(self.items):
            if len(self.items[i]) < s_max:
                self.items[i] = self.items[i].replace('(', ' ' * (s_max - len(self.items[i])) + '(')
        self.maxY = len(self.items)
        self.maxX = len(self.items[0])

        ''' get selection and active server id '''
        for i, n in enumerate(self.items):
            if self.server in n:
                self.active = self.selection = i
                break

    def show(self):
        self._too_small = False
        pY, pX = self._parent.getmaxyx()
        Y, X = self._parent.getbegyx()
        if self.maxY > pY or self.maxX > pX -2:
            ''' display nothing
                let the parent do whatever
            '''
            self._too_small = True
        else:
            self._win = curses.newwin(
                self.maxY, self.maxX,
                Y + 1, X + 1
            )
            for i, n in enumerate(self.items):
                col = 5
                if i == self.active == self.selection:
                    col = 9
                elif i == self.selection:
                    col = 6
                elif i == self.active:
                    col = 4
                try:
                    self._win.addstr(i, 0 , n, curses.color_pair(col))
                except:
                    pass
            self._win.refresh()

    def keypress(self, char):
        ''' RadioBrowserInfoServers keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
                 2: Show help
        '''

        if self._too_small:
            return 1

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
            ord('h'), curses.KEY_LEFT
        ):
            return -1

        elif char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            for i, n in enumerate(self.items):
                if i == self.selection:
                    self.server = n.split('(')[1].replace(') ', '')
                    self.active = i
                    break
            return 0

        elif char in (ord('?'), ):
            return 2

        elif char in (ord('g'), curses.KEY_HOME):
            self.selection = 0
            self.show()

        elif char in (ord('G'), curses.KEY_END):
            self.selection = len(self.items) - 1
            self.show()

        elif char in (curses.KEY_PPAGE, ):
            if self.selection == 0:
                self.selection = len(self.items) - 1
            else:
                self.selection -= 5
                if self.selection < 0:
                    self.selection = 0
            self.show()

        elif char in (curses.KEY_NPAGE, ):
            if self.selection == len(self.items) - 1:
                self.selection = 0
            else:
                self.selection += 5
                if self.selection >= len(self.items):
                    self.selection = len(self.items) - 1
            self.show()

        elif char in (ord('k'), curses.KEY_UP):
            self.selection -= 1
            if self.selection < 0:
                self.selection = len(self.items) - 1
            self.show()

        elif char in (ord('j'), curses.KEY_DOWN):
            self.selection += 1
            if self.selection == len(self.items):
                self.selection = 0
            self.show()

        return 1


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


