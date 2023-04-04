# -*- coding: utf-8 -*-
import curses
try:
    from dns import resolver
except:
    pass
from copy import deepcopy
import random
import json
from os import path
import collections
from operator import itemgetter
try:
    import requests
except:
    pass
import threading
import logging
from .player import info_dict_to_list
from .cjkwrap import cjklen, PY3
from .countries import countries
from .simple_curses_widgets import SimpleCursesLineEdit, SimpleCursesHorizontalPushButtons, SimpleCursesWidgetColumns, SimpleCursesCheckBox, SimpleCursesCounter, SimpleCursesBoolean, DisabledWidget, SimpleCursesString, SimpleCursesWidget
from .ping import ping

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

RADIO_BROWSER_DISPLAY_TERMS = {
    'topvote': 0,
    'topclick': 1,
    'lastclick': 2,
    'lastchange': 3,
    'changed': -1,
    'improvable': -1,
    'broken': -1,
}

RADIO_BROWSER_SEARCH_BY_TERMS = {
    'byuuid': -1,
    'byname': 6,
    'bynameexact': 6,
    'bycodec': 16,
    'bycodecexact': 16,
    'bycountry': 8,
    'bycountryexact': 8,
    'bycountrycodeexact': -1,
    'bystate': 14,
    'bystateexact': 14,
    'bylanguage': 10,
    'bylanguageexact': 10,
    'bytag': 12,
    'bytagexact': 12,
}

RADIO_BROWSER_SEARCH_SORT_TERMS = {
    'random': 1,
    'name': 2,
    'tags': 3,
    'country': 4,
    'state': 5,
    'language': 6,
    'votes': 7,
    'clickcount': 8,
    'bitrate': 9,
    'codec': 10,
}

RADIO_BROWSER_SEARCH_TERMS = {
    'name': 6,
    'nameExact': 5,
    'country': 8,
    'countryExact': 7,
    'countrycode': -1,
    'state': 13,
    'stateExact': 14,
    'language': 10,
    'languageExact': 9,
    'tag': 12,
    'tagList': 12,
    'tagExact': 11,
    'codec': 16,
    'bitrateMin': -1,
    'bitrateMax': -1,
    'has_geo_info': -1,
    'offset': -1,
}

RADIO_BROWSER_EXACT_SEARCH_TERM = {
    'name': 'nameExact',
    'country': 'countryExact',
    'state': 'stateExact',
    'language': 'languageExact',
    'tag': 'tagExact'
}

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

    BROWSER_NAME = 'PyRadioStationsBrowser'
    BASE_URL = ''
    AUTO_SAVE_CONFIG = False
    TITLE = ''
    _parent = _outer_parent = None
    _raw_stations = []
    _last_search = None
    _internal_header_height = 0
    _url_timeout = 3
    _search_timeout = 3
    _vote_callback = None
    _sort = _search_win = None

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
                 message_function=None,
                 cannot_delete_function=None):
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

    def __del__(self):
        self._sort = None
        self._search_win = None

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
        if self._search_win:
            self._search_win._parent = val

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

    def stations(self, playlist_format=2):
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
        return True

    def save_config(self):
        ''' setting AUTO_SAVE_CONFIG to True here, so that any
            calling functions will call save_config (which does
            nothing) directly (without displaying a confirm
            window).

            Subclasses should set it to False (if a confirmation
            window is needed)
        '''
        self.AUTO_SAVE_CONFIG = True
        return True

    def is_config_dirty(self):
        return False


class RadioBrowser(PyRadioStationsBrowser):

    BROWSER_NAME = 'RadioBrowser'
    BASE_URL = 'api.radio-browser.info'
    TITLE = 'RadioBrowser '

    browser_config = _config_win = None

    _headers = {
        'User-Agent': 'PyRadio/dev',
        'Content-Type': 'application/json'
    }

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

    _default_max_number_of_results = 100
    _default_server = ''
    _default_ping_count = 1
    _default_ping_timeout = 1
    _do_ping = False

    keyboard_handler = None

    ''' _search_history_index            - current item in this browser  -  corresponds to search window _history_id
        _default_search_history_index    - autoload item in this browser  -  corresponds to search window _default_history_id
    '''
    _search_history_index = 1
    _default_search_history_index = 1

    def __init__(self,
                 config,
                 config_encoding,
                 session=None,
                 search=None,
                 pyradio_info=None,
                 search_return_function=None,
                 message_function=None,
                 cannot_delete_function=None):
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
        self.browser_config = RadioBrowserConfig(self._cnf.stations_dir)

        # logger.error('DE AUTO_SAVE_CONFIG = {}'.format(self.AUTO_SAVE_CONFIG))

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
        self._cannot_delete_function = cannot_delete_function

    def reset_dirty_config(self):
        self.browser_config.dirty = False

    def is_config_dirty(self):
        return self.browser_config.dirty if self.browser_config else False

    def initialize(self):
        self._dns_info = RadioBrowserDns()

        return self.read_config()

    @property
    def server(self):
        return self._server

    @property
    def add_to_title(self):
        return self._server.split('.')[0]

    def _get_title(self):
        self.TITLE = 'RadioBrowser ({})'.format(country_from_server(self._server))

    def set_station_history(self,
                            execute_funct,
                            pass_first_item_funct,
                            pass_last_item_funct,
                            no_items_funct):
        self.stations_history = RadioBrowserStationsStack(
            execute_function=execute_funct,
            pass_first_item_function=pass_first_item_funct,
            pass_last_item_function=pass_last_item_funct,
            no_items_function=no_items_funct
        )
        return self.stations_history

    def set_global_functions(self, global_functions):
        self._global_functions = {}
        if global_functions is not None:
            self._global_functions = dict(global_functions)
            if ord('t') in self._global_functions.keys():
                del self._global_functions[ord('t')]
            # if 'T' in self._global_functions.keys():
            #     del self._global_functions['T']

    def stations(self, playlist_format=2):
        ''' Return stations' list (in PyRadio playlist format)

            Parameters
            ----------
            playlist_format
                0: station name, url
                1: station name, url, encoding
                2: station name, url, encoding, {icon}
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
                fav = ''
                chk_fav = n['favicon'].split('?')
                use_fav = chk_fav[0]
                if use_fav.endswith('.jpg') or \
                        use_fav.endswith('.png'):
                    fav = use_fav
                # ret.append([n['name'], n['url'], enc, ''])
                ret.append([n['name'], n['url'], enc, {'image': fav}])
        return ret

    def save_config(self):
        ''' just an interface to config class save_config
        '''
        if self._config_win:
            return self._config_win.save_config()
        else:
            return self.browser_config.save_config(
                self.AUTO_SAVE_CONFIG,
                self._search_history,
                self._default_search_history_index,
                self._default_server if 'Random' not in self._default_server else '',
                self._default_ping_count,
                self._default_ping_timeout,
                self._default_max_number_of_results)

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
        def do_click(a_station, a_station_uuid):
            url = 'http://' + self._server + '/json/url/' + a_station_uuid
            try:
                r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Station click result: "{}"'.format(r.text))
                # if '"ok":true' in r.text:
                #     self._raw_stations[a_station]['clickcount'] += 1
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Station click failed...')
        threading.Thread(target=do_click, args=(a_station, self._raw_stations[a_station]['stationuuid'], )).start()

    def vote(self, a_station):
        url = 'http://' + self._server + '/json/vote/' + self._raw_stations[a_station]['stationuuid']
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Voting for: {}'.format(self._raw_stations[a_station]))
            logger.debug('Voting url: ' + url)
        try:
            r = self._session.get(url=url, headers=self._headers, timeout=(self._search_timeout, 2 * self._search_timeout))
            message = json.loads(r.text)
            self.vote_result = self._raw_stations[a_station]['name'], message['message'][0].upper() + message['message'][1:]
            # logger.error('DE voting result = {}'.format(self.vote_result))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Voting result: "{}"'.format(message))
            ret = message['ok']
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station voting failed...')
            self.vote_result = self._raw_stations[a_station]['name'], 'Voting for station failed'
            ret = False

        if ret:
            self._raw_stations[a_station]['votes'] += 1

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
            try:
                info[n[0]] = str(self._raw_stations[a_station][n[1]])
            except:
                ''' do this here for python 2
                    TODO: make the previous statement work on py2
                '''
                info[n[0]] = self._raw_stations[a_station][n[1]].encode('utf-8', 'replace')
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
                        state          : station state
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
            if 'limit' not in post_data.keys() and self._default_max_number_of_results > 0:
                post_data['limit'] = self._default_max_number_of_results
            else:
                if post_data['limit'] == '0':
                    post_data.pop('limit')

        if 'hidebroken' not in post_data.keys():
            post_data['hidebroken'] = 'true'

        self._log_query(url, post_data)

        ''' keep server results here '''
        new_raw_stations = []

        try:
            r = self._session.get(url=url, headers=self._headers, params=post_data, timeout=(self._search_timeout, 2 * self._search_timeout))
            self._log_response(r)
            r.raise_for_status()

            new_raw_stations = self._extract_data(json.loads(r.text))
            # logger.error('DE \n\n{}'.format(new_raw_stations))
            ret = True, len(new_raw_stations), go_back_in_history
        except requests.exceptions.RequestException as e:
            if logger.isEnabledFor(logging.INFO):
                logger.info(e)
            # self._raw_stations = []
            ret = False, 0, go_back_in_history

        ''' use server result '''
        if len(new_raw_stations) > 0:
            self._raw_stations = new_raw_stations[:]

        if self._search_return_function:
            self._search_return_function(ret)


    def _log_query(self, url, post_data):
        if logger.isEnabledFor(logging.INFO):
            try:
                logger.info('>>> RadioBrowser Query:')
                logger.info('  search term = {}'.format(self._search_history[self._search_history_index]))
                logger.info('  url = "{}"'.format(url))
                logger.info('  headers = "{}"'.format(self._headers))
                logger.info('  post_data = "{}"'.format(post_data))
            except:
                pass

    def _log_response(self, r):
        if logger.isEnabledFor(logging.INFO):
            try:
                logger.info('>>> RadioBrowser Response Query:')
                logger.info('  url = "{}"'.format(r.request.url))
                logger.info('  body = "{}"'.format(r.request.body))
                logger.info('  headers = "{}"'.format(r.request.headers))
            except:
                pass

    def _get_search_elements(self, a_search):
        '''
            get "by search" and "reverse"
            values from a search dict.
            To be used with the sort function
        '''
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('_get_search_elements() :search term is\n\t"{}"'.format(a_search))
        a_term = a_search['term']
        p_data = a_search['post_data']
        self.search_by = None
        self.reverse = False
        if a_search['post_data']:
            if 'order' in a_search['post_data'].keys():
                self.search_by = a_search['post_data']['order']
            if 'reverse' in a_search['post_data']:
                self.reverse = True if a_search['post_data']['reverse'] == 'true' else False

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('searching by was: "{}"'.format(self.search_by))
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
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.error('p_data searching by: "name" (default)')

        if self.search_by is None:
            self.search_by = 'name'
            if logger.isEnabledFor(logging.DEBUG):
                logger.error('forced searching by: "name" (default)')

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('searching by: "{}"'.format(self.search_by))

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
        ''' work on a copy, this way we can change it and not
            break "term to widgets" assignment
        '''
        a_search_copy = deepcopy(a_search)
        logger.error('_format_url(): a_search_copy = {}'.format(a_search_copy))
        if a_search_copy['type'] in RADIO_BROWSER_DISPLAY_TERMS.keys():
            url = 'http://{0}{1}'.format(
                self._server,
                '/json/stations/{}'.format(a_search_copy['type'])
            )
            if a_search_copy['term'] not in ('', '0'):
                url += '/{}'.format(a_search_copy['term'])
            self._search_type = 0

        elif a_search_copy['type'] in RADIO_BROWSER_SEARCH_BY_TERMS.keys():
            if a_search_copy['type'].startswith('bycountry') and \
                    len(a_search_copy['term']) == 2:
                a_search_copy['type'] = 'bycountrycodeexact'
                a_search_copy['term'] = a_search_copy['term'].upper()
            url = 'http://{0}{1}/{2}'.format(
                self._server,
                '/json/stations/{}'.format(a_search_copy['type']),
                a_search_copy['term']
            )
            self._search_type = 1

        elif a_search_copy['type'] == 'search':
            url = 'http://{0}{1}'.format(
                self._server,
                '/json/stations/search'
            )
            if a_search_copy['post_data']:
                if 'country' in a_search_copy['post_data']:
                    ''' look for country code '''
                    if len(a_search_copy['post_data']['country']) == 2:
                        ''' revert to countrcode '''
                        a_search_copy['post_data']['countrycode'] = a_search_copy['post_data']['country'].upper()
                        try:
                            a_search_copy['post_data'].pop('country', None)
                            # a_search_copy['post_data'].pop('countryExact', None)
                        except KeyError:
                            pass
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
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country']), self._columns_width['country']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['state'].ljust(self._columns_width['state']), self._columns_width['state']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language']), self._columns_width['language']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['tags'].ljust(self._columns_width['tags']), self._columns_width['tags'])
            )
        if self._output_format == 6:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country']), self._columns_width['country']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['state'].ljust(self._columns_width['state']), self._columns_width['state']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language']), self._columns_width['language']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['tags'].ljust(self._columns_width['tags']), self._columns_width['tags'])
            )
        if self._output_format == 5:
            # full with state
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country']), self._columns_width['country']),
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['language'].ljust(self._columns_width['language']), self._columns_width['language']),
            )
        if self._output_format == 4:
            # full or condensed info
            out[2] = ' ' + info[self._output_format].format(
                pl,
                str(self._raw_stations[id_in_list]['votes']).rjust(self._columns_width['votes'])[:self._columns_width['votes']],
                str(self._raw_stations[id_in_list]['clickcount']).rjust(self._columns_width['clickcount'])[:self._columns_width['clickcount']],
                str(self._raw_stations[id_in_list]['bitrate']).rjust(self._columns_width['bitrate']-2)[:self._columns_width['bitrate']-2],
                self._fix_cjk_string_width(self._raw_stations[id_in_list]['country'].ljust(self._columns_width['country']), self._columns_width['country']),
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

        if PY3:
            return out[0] + self._raw_stations[id_in_list]['name'], ' ' + out[2]
        else:
            return out[0] + self._raw_stations[id_in_list]['name'].encode('utf-8', 'replace'), ' ' + out[2].encode('utf-8', 'replace')

    def set_encoding(self, id_in_list, new_encoding):
        if id_in_list < len(self._raw_stations):
            self._raw_stations[id_in_list]['encoding'] = new_encoding
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('New encoding set to "{0}" for station "{1}"'.format(new_encoding, self._raw_stations[id_in_list]['name']))

    def _fix_cjk_string_width(self, a_string, width):
        while cjklen(a_string) > width:
            a_string = a_string[:-1]
        while cjklen(a_string) < width:
            a_string += ' '
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
                ret[-1]['favicon'] = n['favicon']
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

    def get_history_from_search(self):
        if self._search_win:
            self._search_history_index, self._default_search_history_index, history = self._search_win.get_history()
            logger.error('DE search_history_index = {}'.format(self._search_history_index))
            logger.error('DE search_default_history_index = {}'.format(self._default_search_history_index))
            logger.error('DE history = {}'.format(history))
            self._search_history = deepcopy(history)

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
        title = '#  '.rjust(pad), ' Name '
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

    def select_servers(self, with_config=False, return_function=None, init=False, global_functions=None):
        ''' RadioBrowser select servers '''
        if init:
            self._server_selection_window = None
        if self._server_selection_window is None:
            self._old_server = self._server
            if with_config:
                self._server_selection_window = RadioBrowserServersSelect(
                    self._config_win._win,
                    self._dns_info.server_urls,
                    self._config_win._params[0]['server'],
                    self._config_win._params[0]['ping_count'],
                    self._config_win._params[0]['ping_timeout'],
                    Y=12, X=self._config_win._left+7,
                    show_random=True,
                    return_function=return_function,
                    global_functions=global_functions
                )
            else:
                self._server_selection_window = RadioBrowserServersSelect(
                    self.parent,
                    self._dns_info.server_urls,
                    self._server,
                    self._default_ping_count,
                    self._default_ping_timeout,
                    return_function=return_function,
                    global_functions=global_functions
                )
        else:
            self._server_selection_window.set_parent(self.parent)
            if with_config:
                self._server_selection_window.move(12, self._left + 7)
            else:
                self._server_selection_window.move(12, self._config_win._left + 7)
        self.keyboard_handler = self._server_selection_window
        self.server_window_from_config = with_config
        self._server_selection_window.show()
        return self._server_selection_window

    def sort(self):
        '''
            Create and show the Sort window
        '''
        if self._sort is None:
            self._get_search_elements(
                self._search_history[self._search_history_index]
            )
            self._sort = RadioBrowserSort(
                parent=self.parent,
                search_by=self.search_by
            )
        self.keyboard_handler = self._sort
        self._sort.show()

    def _calculate_do_ping(self):
        if self._default_ping_count == 0 or self._default_ping_timeout == 0:
            self._do_ping = False
        else:
            self._do_ping = True
        return self._do_ping

    def read_config(self):
        ''' RadioBrowser read config '''
        self.browser_config.read_config()
        self.AUTO_SAVE_CONFIG = self.browser_config.auto_save
        self._default_max_number_of_results = int(self.browser_config.limit)
        self._default_search_history_index = self._search_history_index = self.browser_config.default
        self._search_history = self.browser_config.terms
        self._default_server = self.browser_config.server
        self._default_ping_count = self.browser_config.ping_count
        self._default_ping_timeout = self.browser_config.ping_timeout
        self._calculate_do_ping()
        self._server = None
        if self._default_server:
            if logger.isEnabledFor(logging.INFO):
                logger.info('RadioBrowser: pinging user default server: ' + self._default_server)
            if self._do_ping:
                if ping(self._default_server,
                        count=self._default_ping_count,
                        timeout_in_seconds=self._default_ping_timeout) == 1:
                    self._server = self._default_server
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('ping was successful!')
                        logger.info('RadioBrowser: server is set by user: ' + self._server)
            else:
                self._server = self._default_server

        if not self._server:
            random_server = self._dns_info.give_me_a_server_url()
            # logger.error('DE random_server = {}'.format(random_server))
            if random_server is None:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('RadioBrowser: No server is reachable!')
                return False

            self._server = random_server
            if logger.isEnabledFor(logging.INFO):
                logger.info('RadioBrowser: using random server: ' + self._server)

        if logger.isEnabledFor(logging.INFO):
            logger.info('RadioBrowser: result limit = {}'.format(self._default_max_number_of_results))
            logger.info('RadioBrowser: default search term = {}'.format(self._default_search_history_index))
            logger.info('RadioBrowser: search history')
            for i, n in enumerate(self._search_history):
                logger.info('  {0}: {1}'.format(i, n))
        self._get_title()
        return True

    def keypress(self, char):
        ''' RadioBrowser keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''
        # logger.error('DE keyboard handler = {}'.format(self.keyboard_handler))
        ret = self.keyboard_handler.keypress(char)
        # logger.error('DE online_browser ret = {}'.format(ret))

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
                        logger.info('RadioBrowser: user selected server is ' + self._server)
                    self._get_title()

        return ret

    def line_editor_has_focus(self):
        if self._search_win:
            return self._search_win.line_editor_has_focus()
        return False

    def do_search(self, parent=None, init=False):
        if init:
            self._search_win = RadioBrowserSearchWindow(
                parent=parent,
                config=self.browser_config,
                limit=self._default_max_number_of_results,
                init=init,
                global_functions=self._global_functions
            )
        self._search_win.set_search_history(
            self._default_search_history_index,
            self._search_history_index,
            self._search_history, init)
        self.keyboard_handler = self._search_win
        self._search_win.show()

    def show_config(self, parent=None, init=False, cannot_delete_function=None):
        if init:
            self._config_win = RadioBrowserConfigWindow(
                parent=parent,
                config=self.browser_config,
                dns_info=self._dns_info,
                current_auto_save=self.AUTO_SAVE_CONFIG,
                current_server=self._default_server,
                current_history=self._search_history,
                current_history_id=self._default_search_history_index,
                current_limit=self._default_max_number_of_results,
                current_ping_count=self._default_ping_count,
                current_ping_timeout=self._default_ping_timeout,
                init=init,
                with_browser=True,
                global_functions=self._global_functions,
                cannot_delete_function=cannot_delete_function
            )
        self.keyboard_handler = self._config_win
        self._config_win.show(parent=parent)

class RadioBrowserConfig(object):
    ''' RadioBrowser config calss

        Parameters:
            auto_save    : Boolean
            server       : string
            default      : int (id on terms)
            ping_timeout : int (ping timeout is seconds)
            ping_count   : int (number of ping packages)
            terms        : list of dicts (the actual search paremeters)
    '''
    auto_save = False
    server = ''
    default = 1
    limit = '100'
    terms = []
    dirty = False
    ping_count = 1
    ping_timeout = 1

    def __init__(self, stations_dir):
        self.config_file = path.join(stations_dir, 'radio-browser-config')

    def read_config(self):
        ''' RadioBrowserConfig read config '''
        self.terms = [{ 'type': '',
                  'term': '100',
                  'post_data': {}
                  }]
        self.default = 1
        self.auto_save = False
        self.limit = 100
        self.ping_count = 1
        self.ping_timeout = 1
        lines = []
        term_str = []
        try:
            with open(self.config_file, 'r', encoding='utf-8') as cfgfile:
                lines = [line.strip() for line in cfgfile if line.strip() and not line.startswith('#') ]

        except:
            self.terms.append({
                    'type': 'topvote',
                    'term': '100',
                    'post_data': {'reverse': 'true'}
                })
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('RadioBrowser: error reading config, reverting to defaults')
            return False

        for line in lines:
            if '=' in line:
                # logger.error('DE line = "' + line + '"')
                sp = line.split('=')
                for n in range(0, len(sp)):
                    sp[n] = sp[n].strip()
                # logger.error('DE   sp = {}'.format(sp))
                if sp[1]:
                    if sp[0] == 'AUTO_SAVE_CONFIG':
                        self.auto_save = True if sp[1].lower() == 'true' else False
                    elif sp[0] == 'DEFAULT_SERVER':
                        self.server = sp[1]
                    elif sp[0] == 'DEFAULT_LIMIT':
                        try:
                            self.limit = int(sp[1])
                        except:
                            self.limit = '100'
                    elif sp[0] == 'SEARCH_TERM':
                        term_str.append(sp[1])
                    elif sp[0] == 'PING_COUNT':
                        try:
                            self.ping_count = int(sp[1])
                        except:
                            self.ping_count = 1
                    elif sp[0] == 'PING_TIMEOUT':
                        try:
                            self.ping_timeout = int(sp[1])
                        except:
                            self.ping_timeout = 1

        if term_str:
            for n in range(0, len(term_str)):
                if term_str[n].startswith('*'):
                    term_str[n] = term_str[n][1:]
                    self.default = n + 1

                term_str[n] = term_str[n].replace("'", '"')
                # logger.error('term {0} = "{1}"'.format(n, term_str[n]))
                try:
                    self.terms.append(json.loads(term_str[n]))
                except:
                    try:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('RadioBrowser: error inserting search term {}'.format(n))
                    except:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('RadioBrowser: error inserting serch item id {}'.format(n))
                if 'limit' in self.terms[-1]['post_data'].keys():
                    if self.terms[-1]['post_data']['limit'] == str(self.limit):
                        self.terms[-1]['post_data'].pop('limit')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('RadioBrowser: no search terms found, reverting to defaults')
            self.terms.append({
                    'type': 'topvote',
                    'term': '100',
                    'post_data': {'reverse': 'true'}
                })
            return False


        self.terms[0]['term'] = self.limit
        # logger.error('DE limit = {}'.format(self.limit))
        # logger.error('DE server = ' + self.server)
        # logger.error('DE default = {}'.format(self.default))
        # logger.error('DE terms = {}'.format(self.terms))
        return True

    def save_config(self,
                    auto_save,
                    search_history,
                    search_default_history_index,
                    default_server,
                    default_ping_count,
                    default_ping_timeout,
                    default_max_number_of_results):
        self.auto_save = auto_save
        self.server = default_server if 'Random' not in default_server else ''
        self.default = default_max_number_of_results
        self.terms = deepcopy(search_history)
        txt = '''##############################################################################
#                    RadioBrowser config file for PyRadio                    #
##############################################################################
#
# Auto save config
# If True, the config will be automatically saved upon
# closing RadioBrowser. Otherwise, confirmation will be asked
# Possible values: True, False (default)
AUTO_SAVE_CONFIG = '''

        txt += str(auto_save)

        txt += '''

# Default server
# The server that RadioBrowser will use by default
# Default: empty string (use random server)
DEFAULT_SERVER = '''

        txt += default_server

        txt += '''

# Default maximum number of returned results
# for any query to a RadioBrowser saerver
# Default value: 100
DEFAULT_LIMIT = '''

        txt += str(default_max_number_of_results)

        txt += '''

# server pinging parameters
# set any parameter to 0 to disable pinging
# number of packages to send
PING_COUNT = '''

        txt += str(default_ping_count)

        txt += '''
# timeout in seconds
PING_TIMEOUT = '''

        txt += str(default_ping_timeout)

        txt += '''

# List of "search terms" (queries)
# An asterisk specifies the default search term (the
# one activated when RadioBrowser opens up)
# Default = {'type': 'topvote',
#            'term': '100',
#            'post_data': {'reverse': 'true'}
#           }
#
'''
        for n in range(1, len(search_history)):
            asterisk = '*' if n == search_default_history_index else ''
            if PY3:
                txt += 'SEARCH_TERM = ' + asterisk + str(search_history[n]) + '\n'
            else:
                txt += 'SEARCH_TERM = ' + asterisk + str(search_history[n]).replace('{u\'', '{\'').replace('u\'', '\'') + '\n'

        try:
            with open(self.config_file, 'w', encoding='utf-8') as cfgfile:
                cfgfile.write(txt)
        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Saving Online Browser config file failed')
            return False
        self.dirty = False
        if logger.isEnabledFor(logging.INFO):
            logger.info('Saved Online Browser config file')
        return True

class RadioBrowserConfigWindow(object):

    BROWSER_NAME = 'RadioBrowser'
    TITLE = ' RadioBrowser Config '
    _win = _widgets = _config = _history = _dns = None
    _server_selection_window = None
    _default_history_id = _focus = 0
    _auto_save =_showed = False
    invalid = False
    _widgets = None
    _params = []
    _focused = 0
    _token = ''
    server_window_from_config = False

    keyboard_handler = None

    enable_servers = True

    _wleft = (2, 5, 7, 8, 10, 14)

    def __init__(
            self,
            parent,
            config=None,
            dns_info=None,
            current_auto_save=False,
            current_server='',
            current_ping_count=1,
            current_ping_timeout=1,
            current_history=None,
            current_history_id=-1,
            current_limit=100,
            init=False,
            stations_dir=None,
            distro=None,
            global_functions=None,
            with_browser=False,
            cannot_delete_function=None
    ):
        ''' Parameters
                0: working
                1: current in browser window
                2: from config
        '''
        self._cannot_delete_function = cannot_delete_function
        if len(self._params) == 0:
            for i in range(0, 3):
                self._params.append(
                    {'auto_save': False,
                     'server': '',
                     'default': 1,
                     'limit': 100,
                     'ping_count': 1,
                     'ping_timeout': 1,
                     'terms': [{
                         'type': '',
                         'term': current_limit,
                         'post_data': {}
                     },
                     {
                         'type': 'topvote',
                         'term': '100',
                         'post_data': {'reverse': 'true'}
                     }]},
                )
        self._win = self._parent = parent
        self.maxY, self.maxX = self._parent.getmaxyx()

        '''
        static messages
            Y, X, message, color_pair
        '''
        self._static_msg = [
            [1, 0, 'General Options', 4],
            [3, 4, 'If True, no confirmation will be asked before saving', 5],
            [4, 4, 'the configuration when leaving the search window', 5],
            [6, 4, 'A value of -1 will disable return items limiting', 5],
            [9, 4, 'Set any ping parameter to 0 to disable server pinging', 5],
            [11, 4, 'Set to "Random" if you cannot connet to service', 5],
            [12, 0, 'Search Terms', 4],
        ]
        self._with_browser = with_browser
        self._calculate_left_margin()
        if config:
            self._config = config
        else:
            self._config = RadioBrowserConfig(stations_dir)
            self._config.read_config()
        if dns_info:
            self._dns_info = dns_info
        else:
            self._dns_info = RadioBrowserDns()
        self._distro = distro
        self._init_set_working_params(current_auto_save,
                                      current_server,
                                      current_ping_count,
                                      current_ping_timeout,
                                      current_limit,
                                      current_history_id,
                                      current_history
                                      )
        self._global_functions = {}
        if global_functions is not None:
            self._global_functions = global_functions.copy()
            if ord('d') in self._global_functions.keys():
                del self._global_functions[ord('d')]
            if ord('t') in self._global_functions.keys():
                del self._global_functions[ord('t')]
        # self._print_params()

    @property
    def urls(self):
        return self._dns_info.server_urls

    @urls.setter
    def urls(self, val):
        return

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
        if self._showed:
            self.show()

    def _fix_server(self, server):
        if server == '':
            return 'Random'
        return server

    def _focus_next(self):
        if self._focused == len(self._widgets) - 1:
            self._focused = 0
        else:
            self._focused += 1
        while not self._widgets[self._focused].enabled:
            self._focus_next()
            return
        self._refresh()

    def _focus_previous(self):
        if self._focused == 0:
            self._focused = len(self._widgets) - 1
        else:
            self._focused -= 1
        while not self._widgets[self._focused].enabled:
            self._focus_previous()
            return
        self._refresh()

    def _refresh(self):
        self._fix_focus()
        self._win.refresh()

    def _fix_focus(self, show=True):
        for i, widg in enumerate(self._widgets):
            widg.focused = True if self._focused == i else False
        if show:
            for n in self._widgets:
                n.show(self._win)

    def _calculate_left_margin(self):
        self._width = max([len(x[2]) for x in self._static_msg])
        self._left = self.maxX - self._width
        self._left = int(self._left / 2) - 2

    def _init_set_working_params(self,
                                 auto_save,
                                 server,
                                 ping_count,
                                 ping_timeout,
                                 limit,
                                 default,
                                 terms
     ):
        if terms is None:
            self._revert_to_default_params()
            self._params[0]['auto_save'] = self._config.auto_save
            self._params[0]['server'] = self._fix_server(self._config.server)
            self._params[0]['ping_count'] = self._config.ping_count
            self._params[0]['ping_timeout'] = self._config.ping_timeout
            self._params[0]['limit'] = self._config.limit
            self._params[0]['default'] = self._config.default
            self._params[0]['terms'] = deepcopy(self._config.terms)
        else:
            self._params[0]['auto_save'] = auto_save
            self._params[0]['server'] = self._fix_server(server)
            self._params[0]['ping_count'] = ping_count
            self._params[0]['ping_timeout'] = ping_timeout
            self._params[0]['limit'] = limit
            self._params[0]['default'] = default
            self._params[0]['terms'] = deepcopy(terms)
        self._params[1]['auto_save'] = self._params[0]['auto_save']
        self._params[1]['server'] = self._params[0]['server']
        self._params[1]['ping_count'] = self._params[0]['ping_count']
        self._params[1]['ping_timeout'] = self._params[0]['ping_timeout']
        self._params[1]['default'] = self._params[0]['default']
        self._params[1]['limit'] = self._params[0]['limit']
        self._params[1]['terms'] = deepcopy(self._params[0]['terms'])

    def _revert_to_saved_params(self):
        self._revert_params(1)

    def _revert_to_default_params(self):
        self._revert_params(2)

    def is_config_dirty(self):
        return self._config.dirty

    def reset_dirty_config(self):
        self._config.dirty = False

    def _revert_params(self, index):
        self._params[0]['auto_save'] = self._params[index]['auto_save']
        self._params[0]['server'] = self._fix_server(self._params[index]['server'])
        self._params[0]['server'] = self._fix_server(self._params[index]['server'])
        self._params[0]['ping_count'] = self._params[index]['ping_count']
        self._params[0]['ping_timeout'] = self._params[index]['ping_timeout']
        self._params[0]['limit'] = self._params[index]['limit']
        self._params[0]['default'] = self._params[index]['default']
        self._params[0]['terms'] = deepcopy(self._params[index]['terms'])
        ''' set to widgets '''
        if self._widgets:
            self._widgets[0].value = self._params[0]['auto_save']
            self._widgets[1].value = int(self._params[0]['limit'])
            self._widgets[2].value = int(self._params[0]['ping_count'])
            self._widgets[3].value = int(self._params[0]['ping_timeout'])
            self._widgets[4].string = self._params[0]['server'] if self._params[0]['server'] else 'Random'
            # TODO: set of ping count and timeout
            self._fix_ping_enable()
            self._widgets[-1].set_data(self._params[0]['default'], self._params[0]['limit'], self._params[0]['terms'])
            for n in self._widgets:
               n.show(self._win)
            self._win.refresh()
            # self._widgets[-1].refresh()
        # self._print_params()

    def _fix_ping_enable(self):
        self._widgets[2].enabled = True
        self._widgets[3].enabled = True
        if self._widgets[2].value == 0:
            self._widgets[3].enabled = False
        elif self._widgets[3].value == 0:
            self._widgets[2].enabled = False

    def calculate_dirty(self):
        self._config.dirty = False
        if self._widgets[-1].dirty:
            self._config.dirty = True
        else:
            for n in (
                'auto_save', 'server',
                'ping_count', 'ping_timeout',
                'limit','default', 'terms'
            ):
                if self._params[0][n] != self._params[1][n]:
                    self._config.dirty = True
                    break
        self.print_title()

    def print_title(self):
        self._win.box()
        token = ' *' if self._config.dirty else ''
        if token:
            title = self.TITLE[1:]
            self._win.addstr(
                0,
                int((self.maxX - len(title)) / 2) - 2,
                token,
                curses.color_pair(3))
            self._win.addstr(
                title,
                curses.color_pair(4))
        else:
            self._win.addstr(
                0,
                int((self.maxX - len(self.TITLE)) / 2),
                self.TITLE,
                curses.color_pair(4))
        self._win.refresh()
        if self._widgets:
            self._widgets[-1].refresh()

    def show(self, parent, init=False):
        self._parent = parent
        pY, pX = self._parent.getmaxyx()
        # logger.error('DE pY = {}, pX = {}'.format(pY, pX))
        self.Y, self.X = self._parent.getbegyx()

        if self.maxY != pY or self.maxX != pX:
            pY, pX = self._parent.getmaxyx()
            # logger.error('DE pY = {}, pX = {}'.format(pY, pX))
            self.maxY = pY
            self.maxX = pX
            self._win = self._parent

        if self.maxX < 80 or self.maxY < 22:
            self._too_small = True
        else:
            self._too_small = False

        if self._with_browser:
            self._win.bkgdset(' ', curses.color_pair(13))
        else:
            self._win.bkgdset(' ', curses.color_pair(12))
        self._win.erase()
        self.print_title()

        if self._too_small:
            # TODO Print messge
            msg = 'Window too small'
            self._win.addstr(
                int(self.maxY/2), int((self.maxX - len(msg))/2),
                msg, curses.color_pair(5)
            )
            self._win.refresh()
            return

        self._calculate_left_margin()
        if self._widgets is None:
            self._widgets = []

            self._widgets.append(
                SimpleCursesBoolean(
                    Y=2, X=2+self._left,
                    window=self._win,
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(6),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    value=self._params[0]['auto_save'],
                    string='Auto save config: {0}',
                    full_selection=(2,59)
                )
            )
            self._widgets[-1].token = 'auto_save'
            self._widgets[-1].id = 0

            self._widgets.append(
                SimpleCursesCounter(
                    Y=5, X=2+self._left,
                    window=self._win,
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(6),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    minimum=0, maximum=1000,
                    step=1, big_step=10,
                    value=self._params[0]['limit'],
                    string='Maximum number of results: {0}',
                    full_selection=(2,59)
                )
            )
            self._widgets[-1].token = 'limit'
            self._widgets[-1].id = 1

            self._widgets.append(
                SimpleCursesCounter(
                    Y=7, X=2+self._left,
                    window=self._win,
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(6),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    minimum=0, maximum=9,
                    step=1, big_step=5,
                    number_length=1,
                    value=self._params[0]['ping_count'],
                    string='Number of ping packages: {0}',
                    full_selection=(2,59)
                )
            )
            self._widgets[-1].token = 'ping_count'
            self._widgets[-1].id = 2

            self._widgets.append(
                SimpleCursesCounter(
                    Y=8, X=2+self._left,
                    window=self._win,
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(6),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    minimum=0, maximum=9,
                    step=1, big_step=5,
                    number_length=1,
                    value=self._params[0]['ping_timeout'],
                    string='Ping timeout (seconds): {0}',
                    full_selection=(2,59)
                )
            )
            self._widgets[-1].token = 'ping_timeout'
            self._widgets[-1].id = 3

            self._widgets.append(
                SimpleCursesString(
                    Y=10, X=2+self._left,
                    parent=self._win,
                    caption='Default Server: ',
                    string=self._params[0]['server'],
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(6),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    full_selection=(2,59)
                )
            )
            self._widgets[-1].token = 'server'
            self._widgets[-1].id = 4
            self._widgets[-1].enabled = self.enable_servers

            self._widgets.append(
                RadioBrowserTermNavigator(
                    parent=self._win,
                    items=self._params[0]['terms'],
                    default=self._params[0]['default'],
                    limit=self._params[0]['limit'],
                    X=self._left, Y=14,
                    width=self._width+6,
                    color=curses.color_pair(5),
                    header_color=curses.color_pair(4),
                    highlight_color=curses.color_pair(6),
                    cannot_delete_function=self._cannot_delete_function
                )
            )
            self._widgets[-1].token = 'terms'
            self._widgets[-1].id = 5
            self._widgets[-1].enabled = True
            self._fix_focus(show=False)
        else:
            for i in range(0, len(self._widgets)):
                self._widgets[i].move(self._wleft[i], 2+self._left)
        for n in self._widgets:
            n.show(self._win)

        for i in self._static_msg:
            self._win.addstr(i[0], i[1] + self._left, i[2], curses.color_pair(i[-1]))

        if self._distro != 'None':
            try:
                X = int((self.maxX - 20 - len(self._distro) - 1) / 2)
                self._win.addstr(self.maxY - 1, X, ' Package provided by ', curses.color_pair(5))
                self._win.addstr(self._distro + ' ', curses.color_pair(4))
            except:
                pass

        self._fix_ping_enable()
        self._win.refresh()
        self._widgets[-1].refresh()

        self._showed = True

    def save_config(self):
        ''' RadioBrowserConfigWindow save config

            Returns:
                -2: config saved
                -3: error saving config
                -4: config not modified
        '''
        if self._config.dirty:
            self._params[0]['default'], self._params[0]['terms'] = self._widgets[-1].get_result()
            ret = self._config.save_config(
                auto_save=self._params[0]['auto_save'],
                search_history=self._params[0]['terms'],
                search_default_history_index=self._params[0]['default'],
                default_server=self._params[0]['server'] if 'Random' not in self._params[0]['server'] else '',
                default_ping_count=self._params[0]['ping_count'],
                default_ping_timeout=self._params[0]['ping_timeout'],
                default_max_number_of_results=self._params[0]['limit']
            )
            if ret:
                self._config.dirty = False
                ''' config saved '''
                return -2
            else:
                ''' error saving config '''
                return -3
        ''' config not modified '''
        return -4

    def select_servers(self, with_config=False, return_function=None, init=False, global_functions=None):
        ''' RadioBrowserConfigWindow select servers '''
        if init:
            self._server_selection_window = None
        if self._server_selection_window is None:
            self._server_selection_window = RadioBrowserServersSelect(
                self._win,
                self._dns_info.server_urls,
                self._params[0]['server'],
                self._params[0]['ping_count'],
                self._params[0]['ping_timeout'],
                Y=12, X=self._left+7,
                show_random=True,
                return_function=return_function,
                global_functions=global_functions
            )
        else:
            self._server_selection_window.move(12, self._left+7, self._win)
            # self._server_selection_window.X = self._left + 18
            # self._server_selection_window.set_parent(self._win)
        # self.keyboard_handler = self._server_selection_window
        self._server_selection_window.show()
        return self._server_selection_window

    def get_server_value(self, a_server=None):
        if a_server is not None:
            act_server = a_server if not 'Random' in a_server else ''
            self._params[0]['server'] = act_server
            self._widgets[4].string = act_server if act_server != '' else 'Random'
        else:

            try:
                self._params[0]['server'] = self._server_selection_window.servers.server
                logger.error('---=== 1. Server Selection is None ===---')
                self._server_selection_window = None
                self._widgets[4].string = self._params[0]['server'] if self._params[0]['server'] else 'Random'
            except AttributeError:
                pass
        self._widgets[4].show(parent=self._win)
        self._win.refresh()

    def _print_params(self):
        logger.error('\n\n')
        for i, n in enumerate(self._params):
            logger.error('-- id: {}'.format(i))
            logger.error(n['auto_save'])
            logger.error(n['server'])
            logger.error(n['ping_count'])
            logger.error(n['ping_timeout'])
            logger.error(n['limit'])
            logger.error(n['default'])
            logger.error(n['terms'])

    def keypress(self, char):
        ''' RadioBrowserConfigWindow keypress

            Returns:
              -4: config not modified
              -3: error saving config
              -2: config saved successfully
              -1: Cancel
               0: Save Config
               1: Continue
               2: Display help
               3: Display server selection window
               4: Return from server selection window
        '''
        if self._server_selection_window:
            # ret = self._server_selection_window.keypress(char)
            if self._server_selection_window.return_value < 1:
                if self._server_selection_window.return_value == 0:
                    # logger.error('DE SSW {}'.format(self._params[0]))
                    self._params[0]['server'] = self._server_selection_window.servers.server
                    # logger.error('DE SSW {}'.format(self._params[0]))
                logger.error('---=== Server Selection is None ===---')
                self._server_selection_window = None

        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 1
        if char in (
            curses.KEY_EXIT, 27, ord('q')
        ):
            return -1

        elif char in (ord(' '), curses.KEY_ENTER, ord('\n'),
                      ord('\r')) and self._focus == len(self._widgets) - 2:
            ''' enter on ok button  '''
            ret = self._handle_new_or_existing_search_term()
            # self._print_params()
            return 0 if ret == 1 else ret

        elif char == ord('?'):
            return 2

        elif char in (ord('\t'), 9):
            self._focus_next()
            self.calculate_dirty()

        elif char in (curses.KEY_BTAB, ):
            self._focus_previous()
            self.calculate_dirty()

        elif char == ord('s'):
            return self.save_config()

        elif char == ord('r'):
            self._revert_to_saved_params()
            self.calculate_dirty()

        elif char == ord('d'):
            self._revert_to_default_params()
            self.calculate_dirty()

        elif char in (curses.KEY_UP, ord('j')):
            self._focus_previous()
            self.calculate_dirty()

        elif char in (curses.KEY_DOWN, ord('k')):
            self._focus_next()
            self.calculate_dirty()

        else:
            if self._focused < 4:
                ret = self._widgets[self._focused].keypress(char)
                if ret == 0:

                    if self._focused == 0:
                        ''' auto save  '''
                        self._widgets[0].show(self._win)
                        self._params[0]['auto_save'] = self._widgets[0].value
                        self.calculate_dirty()

                    else:
                        ''' limit  '''
                        self._widgets[self._focused].show(self._win)
                        self._params[0][self._widgets[self._focused].token] = self._widgets[self._focused].value
                        if self._focused == 2 or self._focused == 3:
                            self._fix_ping_enable()
                    self._win.refresh()
                    #self._print_params()
                    self.calculate_dirty()

            elif self._focused == 4:
                ''' server '''
                if char in (ord(' '), curses.KEY_ENTER, ord('\n'),
                            ord('\r'), ord('l'), curses.KEY_RIGHT):
                    ''' open server selection window '''
                    return 3
            elif self._focused == 5:
                ''' terms '''
                ret = self._widgets[-1].keypress(char)
                self.calculate_dirty()
                return ret
        return 1

class RadioBrowserSearchWindow(object):

    NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION = 3

    _cnf = None

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

    yx = [
        [0, 0],     # (0) search check box
        [0, 0],     # (1) caption 0
        [0, 0],     # (2) caption 1
        [0, 0],     # (3) caption 2
        [0, 0],     # (4) caption 3
        [0, 0],     # (5) caption 4
        [0, 0],     # (6) caption 5
        [0, 0],     # (7) limit
        [0, 0],     # (8) buttons
    ]

    captions = (
        '',
        'Name',
        'Country',
        'Language',
        'Tag',
        'State',
        'Codec')

    ''' vertical placement of widgets
        used for navigation
    '''
    _left_column = (0, 1, 4, 5, 6, 11, 12, 17, 18)
    _middle_column = (7, 8, 13, 14, 18)
    _right_column = (2, 3, 9, 10, 16, 19)

    ''' line editors ids '''
    _line_editor_id = []

    ''' columns widget ids '''
    _columns_id = []

    ''' checkboxes ids to enable/disable columns widgets '''
    _checkbox_to_enable_widgets = (0, 4)

    _default_limit = 100

    ''' _selected_history_id  : current id in search window
        _history_id           : current id (active in browser)    - corresponds in browser to _search_history_index
        _default_history_id   : default id (autoload for service) - corresponds in browser to _default_search_history_index
    '''
    _history_id = _selected_history_id = _default_history_id = 1
    _history = []

    _global_functions = {}

    def __init__(self,
                 parent,
                 config,
                 limit=100,
                 init=False,
                 global_functions=None
                 ):
        self._parent = parent
        self._cnf = config
        self._default_limit = limit
        self._init = init
        self._too_small = False
        self._focus = 0
        self._win = None
        self.maxY = self.maxX = 0
        self.TITLE = ' RadioBrowser Search '

        ''' we have two columns;
            this is the width of each of them
        '''
        self._half_width = 0
        self._widgets = [ None ]

        if global_functions is not None:
            self._global_functions = dict(global_functions)
            if ord('t') in self._global_functions.keys():
                del self._global_functions[ord('t')]

    def __del__(self):
        for a_widget in self._widgets:
            # logger.error('DE deleting: {}'.format(a_widget))
            a_widget = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, val):
        self._parent = val

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

    def _search_term_to_widgets(self, a_search):
        # logger.error('DE =========================')
        # logger.error('DE term = {}'.format(a_search))
        # logger.error('DE type = {}'.format(a_search['type']))
        self._widgets[1].selection = self._widgets[1].active = 0
        self._widgets[2].selection = self._widgets[2].active = 0
        self._widgets[3].checked = False
        self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value = self._default_limit
        self._widgets[-2].enabled = True
        self._widgets[-1].enabled = True
        for i in range(5, len(self._widgets) - self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION):
            if type(self._widgets[i]).__name__ == 'SimpleCursesLineEdit':
                self._widgets[i].string = ''
            else:
                self._widgets[i].checked = False

        if a_search['type'] == '':
            ''' for empty type '''
            self._widgets[0].checked = False
            self._widgets[4].checked = True
            self._focus = 4

        elif a_search['type'] in RADIO_BROWSER_DISPLAY_TERMS.keys():
            ''' populate the "Display by" part '''
            self._widgets[0].checked = True
            self._widgets[4].checked = False
            self._widgets[1].selection = self._widgets[1].active = RADIO_BROWSER_DISPLAY_TERMS[a_search['type']]

            self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value = int(a_search['term'])
            for i in range(5, len(self._widgets) - self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION):
                try:
                    self._widgets[i].string = ''
                except:
                    self._widgets[i].checked = False
                self._widgets[i].enabled = False

            self._focus = 0
            # logger.error('DE RADIO_BROWSER_DISPLAY_TERMS[a_search["type"]] = {}'.format(RADIO_BROWSER_DISPLAY_TERMS[a_search['type']]))

        else:
            ''' populate the "Search" part '''
            self._widgets[0].checked = False
            self._widgets[4].checked = True
            self._widgets[1].selection = self._widgets[1].active = 0
            self._widgets[2].selection = self._widgets[2].active = 0
            self._widgets[3].checked = False
            for i in range(5, len(self._widgets) - self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION):
                self._widgets[i].enabled = True

            if a_search['type'] in RADIO_BROWSER_SEARCH_BY_TERMS.keys():
                line_edit = RADIO_BROWSER_SEARCH_BY_TERMS[a_search['type']]

                if a_search['type'].endswith('exact'):
                    # logger.error('DE Exact checked!!!')
                    self._widgets[line_edit-1].checked = True
                self._widgets[line_edit].string = a_search['term']
                self._focus = 4
                # logger.error('DE RADIO_BROWSER_SEARCH_BY_TERMS[a_search["type"]] = {}'.format(RADIO_BROWSER_SEARCH_BY_TERMS[a_search['type']]))

            elif a_search['type'] == 'search':
                ''' populate the "Search" part '''
                s_id_list = []
                for n in a_search['post_data'].items():
                    # logger.error('DE s_id = {}'.format(s_id))
                    if n[0] in RADIO_BROWSER_SEARCH_TERMS.keys():
                        if n[1] != -1:
                            s_id = RADIO_BROWSER_SEARCH_TERMS[n[0]]
                            # logger.error('DE s_id = {}'.format(s_id))
                            if type(self._widgets[s_id]).__name__ == 'SimpleCursesLineEdit':
                                self._widgets[s_id].string = n[1]
                                # logger.error('DE n[0] = {0}, string = "{1}"'.format(n[0], n[1]))
                            else:
                                self._widgets[s_id].checked = bool(n[1])
                                # logger.error('DE n[0] = {0}, n[1] = {1}, bool = {2}'.format(n[0], n[1], bool(n[1])))
                            s_id_list.append(s_id)
                self._focus = 4

        if a_search['post_data']:
            for n in a_search['post_data'].keys():
                if n == 'order':
                    order = a_search['post_data']['order']
                    if order in RADIO_BROWSER_SEARCH_SORT_TERMS.keys():
                        order_id = RADIO_BROWSER_SEARCH_SORT_TERMS[order]
                        self._widgets[2].selection = self._widgets[2].active = order_id
                elif n == 'limit':
                    self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value = int(a_search['post_data']['limit'])
                elif n == 'reverse':
                    self._widgets[3].checked = bool(a_search['post_data']['reverse'])


        # logger.error('DE =========================')

    def _widgets_to_search_term(self):
        ret = {'type': '', 'term': '', 'post_data': {}}
        type_part = ''
        order_part = ''
        if self._widgets[0].checked:
            ''' type is "Display by" '''
            ''' get search type '''
            for key in RADIO_BROWSER_DISPLAY_TERMS.items():
                if key[1] == self._widgets[1].active:
                    type_part = key[0]
                    break
            # logger.error('DE type_part = "{}"'.format(type_part))
            if type_part:
                ret['type'] = type_part
            else:
                logger.error('RadioBrowser Search: Error in search parameters!')
                return None
            ''' get limit (term)'''
            ret['term'] = str(self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value)

        else:
            ''' type is search (simple or advanced) '''
            what_type = []
            for i in range(5, len(self._widgets) - self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION):
                if type(self._widgets[i]).__name__ == 'SimpleCursesLineEdit':
                    if self._widgets[i].string:
                        what_type.append(i)
            if len(what_type) == 0:
                logger.error('RadioBrowser Search: Error in search parameters!')
                return None

            if len(what_type) == 1:
                ''' simple search '''
                logger.error('DE simple search')
                for n in RADIO_BROWSER_SEARCH_BY_TERMS.items():
                    if n[1] == what_type[0]:
                        ret['type'] = n [0]
                        logger.error('DE type = {}'.format(ret['type']))
                        break
                if self._widgets[what_type[0] - 1].checked and \
                        not ret['type'].endswith('exact'):
                    ret['type'] += 'exact'
                ret['term'] = self._widgets[what_type[0]].string
            else:
                ''' advanced search '''
                # logger.error('DE advanced search')
                ret['type'] = 'search'

                # logger.error('DE what_type = {}'.format(what_type))
                for a_what_type in what_type:
                    for n in RADIO_BROWSER_SEARCH_TERMS.items():
                        if n[1] == a_what_type:
                            if n[0] == 'tagList':
                                if ',' not in self._widgets[a_what_type].string:
                                    continue
                            if n[0] == 'tag':
                                if ',' in self._widgets[a_what_type].string:
                                    continue
                            ret['post_data'][n[0]] = self._widgets[a_what_type].string
                            if self._widgets[a_what_type-1].checked:
                                if n[0] in RADIO_BROWSER_EXACT_SEARCH_TERM.keys():
                                    ret['post_data'][RADIO_BROWSER_EXACT_SEARCH_TERM[n[0]]] = 'true'

            ''' get limit (term)'''
            if self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value != self._default_limit:
                ret['post_data']['limit'] = str(self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].value)
            # else:
            #     ret['post_data']['limit'] = str(self._default_limit)

        ''' get order '''
        self._order_to_term(ret)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Search term returned: {}'.format(ret))
        return ret

    def _order_to_term(self, ret):
        if self._widgets[2].active > 0:
            for key in RADIO_BROWSER_SEARCH_SORT_TERMS.items():
                if key[1] == self._widgets[2].active:
                    order_part = key[0]
                    break
            # logger.error('DE order_part = "{}"'.format(order_part))
            if order_part:
                ret['post_data']['order'] = order_part
        ''' check for reverse order '''
        if self._widgets[3].checked:
            ret['post_data']['reverse'] = 'true'

    def get_history(self):
        return self._selected_history_id, self._default_history_id, self._history

    def set_search_history(
            self,
            main_window_default_search_history_index,
            main_window_search_history_index,
            main_window_search_history,
            init=False
    ):
        ''' get search history from main window

            Return self._search_term
        '''
        self._history_id = main_window_search_history_index
        if init:
            self._default_history_id = main_window_default_search_history_index
            self._selected_history_id = main_window_search_history_index
        logger.error('DE set_search_history - _selected_history_id={}'.format(self._selected_history_id))
        self._history = deepcopy(main_window_search_history)
        self._search_term = self._history[self._history_id]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Search history')
            logger.debug('     search history: {}'.format(self._history))
            logger.debug('     search history index: {}'.format(self._history_id))
            logger.debug('     active search term: {}'.format(self._search_term))

    def _get_a_third(self):
        ''' calculate window / 3 X
            this is the length of a line editor + 2
        '''
        X = int ((self.maxX - 6) / 3)
        return X
        return X if X % 2 == 0 else X - 1

    def _calculate_widgets_yx(self, Y, X):
        # logger.error('DE {}'.format(self.yx))
        ''' set Y and X for search check box and limit field '''
        self.yx[0] = self.yx[7] = [Y, 2]
        ''' set y for all consecutive widgets '''
        self.yx[1][0] = self.yx[2][0] = self.yx[3][0] = Y
        self.yx[4][0] = self.yx[5][0] = self.yx[6][0] = Y + 3
        self.yx[7][0] = self.yx[6][0] + 3
        self.yx[8][0] = self.yx[7][0] + 2


        self.yx[1][1] = self.yx[4][1] = 3
        self.yx[2][1] = self.yx[5][1] = 3 + X
        self.yx[3][1] = self.yx[6][1] = 3 + 2 * X
        # logger.error('DE {}'.format(self.yx))

    def show(self, parent=None):
        pY, pX = self._parent.getmaxyx()
        # logger.error('DE pY = {}, pX = {}'.format(pY, pX))
        self.Y, self.X = self._parent.getbegyx()

        if self.maxY != pY or self.maxX != pX:
            pY, pX = self._parent.getmaxyx()
            # logger.error('DE pY = {}, pX = {}'.format(pY, pX))
            self.maxY = pY
            self.maxX = pX
            self._win = self._parent
            # self._win = curses.newwin(
            #     self.maxY, self.maxX,
            #     Y, X
            # )
            self._half_width = int((self.maxX -2 ) / 2) -3
            # logger.error('>>>> hajf width = {} <<<<'.format(self._half_width))

        if self.maxX < 80 or self.maxY < 22:
            self._too_small = True
        else:
            self._too_small = False

        self._win.bkgdset(' ', curses.color_pair(13))
        self._win.erase()
        self._win.box()
        self._win.addstr(0, int((self.maxX - len(self.TITLE)) / 2),
                         self.TITLE,
                         curses.color_pair(4))

        if self._too_small:
            # TODO Print messge
            msg = 'Window too small'
            self._win.addstr(
                int(self.maxY/2), int((self.maxX - len(msg))/2),
                msg, curses.color_pair(5)
            )
            self._win.refresh()
            return

        X = self._get_a_third()

        if self._widgets[0] is None:
            ''' display by '''
            self._widgets[0] = SimpleCursesCheckBox(
                    2, 2,
                    'Display by',
                    curses.color_pair(9), curses.color_pair(4), curses.color_pair(5))

            ''' display by columns (index = 1) '''
            self._widgets.append(SimpleCursesWidgetColumns(
                Y=2, X=3, window=self._win,
                selection=0,
                active=0,
                items=self.search_by_items,
                color=curses.color_pair(5),
                color_active=curses.color_pair(4),
                color_cursor_selection=curses.color_pair(6),
                color_cursor_active=curses.color_pair(9),
                margin=1,
                max_width=self._half_width,
                on_up_callback_function=self._focus_up,
                on_down_callback_function=self._focus_down,
                on_left_callback_function=self._focus_previous,
                on_right_callback_function=self._focus_next
            ))

            ''' sort by (index = 2) '''
            self._widgets.append(SimpleCursesWidgetColumns(
                Y=2, X=self.maxX - 1 - self._half_width,
                max_width=self._half_width,
                window=self._win,
                selection=0,
                active=0,
                items=self.sort_by_items,
                color=curses.color_pair(5),
                color_active=curses.color_pair(4),
                color_cursor_selection=curses.color_pair(6),
                color_cursor_active=curses.color_pair(9),
                margin=1,
                on_up_callback_function=self._focus_up,
                on_down_callback_function=self._focus_down,
                on_left_callback_function=self._focus_previous,
                on_right_callback_function=self._focus_next
            ))

            '''' sort ascending / descending (index = 3) '''
            self._widgets.append(SimpleCursesCheckBox(
                    self._widgets[2].Y + self._widgets[2].height + 1,
                    self._widgets[2].X - 2 + self._widgets[2].margin,
                    'Reverse order',
                    curses.color_pair(9), curses.color_pair(5), curses.color_pair(5)))

            ''' Two lines under the lists '''
            Y = max(self._widgets[2].Y, self._widgets[1].Y + self._widgets[1].height, self._widgets[3].Y) + 2

            self._win.addstr(
                self._widgets[2].Y - 1,
                self._widgets[2].X - 2,
                 'Sort by', curses.color_pair(4))
            ''' search check box (index = 4) '''
            self._widgets.append(SimpleCursesCheckBox(
                    Y, 2, 'Search for',
                    curses.color_pair(9), curses.color_pair(4), curses.color_pair(5)))
            self._calculate_widgets_yx(Y, X)
            for n in range(1,7):
                if n == 6:
                    self._widgets.append(DisabledWidget())
                else:
                    self._widgets.append(SimpleCursesCheckBox(
                        self.yx[n][0] + 1,
                        self.yx[n][1] + len(self.captions[n]) + 2,
                        'Exact',
                        curses.color_pair(9), curses.color_pair(5), curses.color_pair(5)))
                self._widgets.append(SimpleCursesLineEdit(
                    parent=self._win,
                    width=X-2,
                    begin_y=self.yx[n][0]+2,
                    begin_x=self.yx[n][1],
                    boxed=False,
                    has_history=False,
                    caption='',
                    box_color=curses.color_pair(9),
                    caption_color=curses.color_pair(4),
                    edit_color=curses.color_pair(9),
                    cursor_color=curses.color_pair(8),
                    unfocused_color=curses.color_pair(5),
                    key_up_function_handler=self._focus_up,
                    key_down_function_handler=self._focus_down))
                self._widgets[-1].bracket = False
                self._widgets[-1].use_paste_mode = True
                self._widgets[-1].set_global_functions(self._global_functions)
                self._widgets[-1]._global_functions[ord('0')] = self._goto_first_history_item
                self._widgets[-1]._global_functions[ord('$')] = self._goto_last_history_item
                #self._widgets[-1].string = self.captions[n]

            ''' limit - index = -3 '''
            self._widgets.append(
                SimpleCursesCounter(
                    Y=self.yx[-2][0],
                    X=self.yx[-2][1],
                    window=self._win,
                    color=curses.color_pair(5),
                    color_focused=curses.color_pair(9),
                    color_not_focused=curses.color_pair(4),
                    color_disabled=curses.color_pair(5),
                    minimum=0, maximum=1000,
                    step=1, big_step=10,
                    value=self._default_limit,
                    string='Limit results to {0} stations'
                )
            )
            ''' buttons - index -2, -1 '''
            self._h_buttons = SimpleCursesHorizontalPushButtons(
                self.yx[-1][0],
                captions=('OK', 'Cancel'),
                color_focused=curses.color_pair(9),
                color=curses.color_pair(4),
                bracket_color=curses.color_pair(5),
                parent=self._win)
            self._widgets.append(self._h_buttons.buttons[0])
            self._widgets.append(self._h_buttons.buttons[1])
            for i, n in enumerate(self._widgets):
                self._widgets[i].id = i
                if type(self._widgets[i]).__name__ == 'SimpleCursesLineEdit':
                    self._line_editor_id.append(i)
                elif type(self._widgets[i]).__name__ == 'SimpleCursesWidgetColumns':
                    self._columns_id.append(i)
                if i < 5:
                    self._widgets[i].enabled = True
                else:
                    self._widgets[i].enabled = False

            for i in range(-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION, 0):
                self._widgets[i].enabled = True

            self._search_term_to_widgets(self._search_term)
            self._win.refresh()

            # set vertical placement variable
            for i in range(0, len(self._widgets)):
                if type(self._widgets[i]).__name__ != 'DisabledWidget':
                    if self._widgets[i].id in self._left_column:
                        self._widgets[i]._vert = self._left_column
                    elif self._widgets[i].id in self._middle_column:
                        self._widgets[i]._vert = self._middle_column
                    elif self._widgets[i].id in self._right_column:
                        self._widgets[i]._vert = self._right_column
                    self._widgets[i]._vert_id = self._widgets[i]._vert.index(self._widgets[i].id)
                    # logger.error('DE =======\ni = {0}\nw = {1}\nid = {2}\n_vert = {3}\n_vert_id = {4}'.format(i, self._widgets[i], self._widgets[i].id, self._widgets[i]._vert, self._widgets[i]._vert_id))

        else:
            ''' update up to lists '''
            self._widgets[1].window = self._widgets[2].window = self._win
            self._widgets[1].max_width = self._widgets[2].max_width = self._half_width
            self._widgets[2].X = self.maxX - 1 - self._half_width
            self._widgets[3].move(
                self._widgets[2].Y + self._widgets[2].height + 1,
                self._widgets[2].X - 2 + self._widgets[2].margin
            )
            self._widgets[1].recalculate_columns()
            self._widgets[2].recalculate_columns()
            ''' search check box (index = 4) '''
            self._win.addstr(
                self._widgets[2].Y - 1,
                self._widgets[2].X - 2,
                 'Sort by', curses.color_pair(4))

            ''' Two lines under the lists '''
            Y = max(self._widgets[2].Y, self._widgets[1].Y + self._widgets[1].height, self._widgets[3].Y) + 2
            ''' place search check box '''
            self._widgets[4].move(Y, 2)
            ''' show descending check box '''
            self._widgets[3].Y = self._widgets[2].Y + self._widgets[2].height + 1
            self._widgets[3].X = self._widgets[2].X - 2 + self._widgets[2].margin,
            self._widgets[3].show()

            ''' search check box (index = 4) '''
            self._win.addstr(
                self._widgets[2].Y - 1,
                self._widgets[2].X - 2,
                 'Sort by', curses.color_pair(4))
            ''' Search check box not moved, will be handled by show '''
            self._win.refresh()
            self._calculate_widgets_yx(Y, X)

            for n in range(0, 6):
                ''' place editors' captions '''
                # self._win.addstr(
                #     self.yx[n+1][0],
                #     self.yx[n+1][1],
                #     self.captions[n+1],
                #     curses.color_pair(5)
                # )
                ''' move exact check boxes '''
                if type(self._widgets[5+n*2]).__name__ != 'DisabledWidget':
                    self._widgets[5+n*2].move(
                        self.yx[n+1][0] + 1,
                        self.yx[n+1][1] + len(self.captions[n+1]) + 2
                    )
                ''' move line editors '''
                self._widgets[6+n*2].move(
                    self._win,
                    self.yx[n+1][0]+2,
                    self.yx[n+1][1],
                    update=False
                )
                ''' change line editors width '''
                self._widgets[6+n*2].width = X - 2

            ''' move limit field '''
            self._widgets[-self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION].move(
                self.yx[-2][0],
                self.yx[-2][1]
            )
            ''' move buttons Y '''
            self._h_buttons.move(self.yx[-1][0])
            self._win.refresh()

        self._h_buttons.calculate_buttons_position()
        self._print_history_legend()
        self._display_all_widgets()

    def _print_history_legend(self):

        self._win.addstr(self.maxY - 3, 2, 25 * ' ')
        if self._selected_history_id == 0:
                self._win.addstr(self.maxY - 3, 2, 'Empty item!!!', curses.color_pair(4))
        elif self._selected_history_id == self._history_id:
            if self._default_history_id == self._history_id:
                self._win.addstr(self.maxY - 3, 2, 'Last search, Default', curses.color_pair(4))
            else:
                self._win.addstr(self.maxY - 3, 2, 'Last search', curses.color_pair(4))
        elif self._selected_history_id == self._default_history_id:
                self._win.addstr(self.maxY - 3, 2, 'Default item', curses.color_pair(4))

        msg = 'History navigation: ^N/^P, HOME,0/END,g,$, PgUp/PgDown'
        thisX = self.maxX - 2 - len(msg)
        self._win.addstr(self.maxY - 3, thisX, msg.split(':')[0] + ':', curses.color_pair(5))
        msg = msg.split(':')[1]
        thisX = self.maxX - 3 - len(msg)
        self._win.addstr(msg, curses.color_pair(4))
        self._other_chgat(self.maxY - 3, thisX, msg)
        #self._carret_chgat(self.maxY-3, thisX, msg)
        msg = 'Add/Del: ^Y/^X, Make default: ^B, Save history: ^E'
        thisX = self.maxX - 2 - len(msg)
        self._win.addstr(self.maxY - 2, thisX, msg)
        self._carret_chgat(self.maxY-2, thisX, msg)

        self._win.addstr(self.maxY - 2, 2 , 'History item: ')
        self._win.addstr('{}'.format(self._selected_history_id), curses.color_pair(4))
        self._win.addstr('/{} '.format(len(self._history)-1))

    def _other_chgat(self, Y, X, a_string):
        indexes = [i for i, c in enumerate(a_string) if c == '/' or c == ',']
        logger.error(indexes)
        for n in indexes:
            self._win.chgat(Y, X+n+1, 1, curses.color_pair(5))

    def _carret_chgat(self, Y, X, a_string):
        indexes = [i for i, c in enumerate(a_string) if c == '^']
        for n in indexes:
            self._win.chgat(Y, X+n, 2, curses.color_pair(4))

    def _activate_search_term(self, a_search_term):
        self._search_term_to_widgets(a_search_term)
        self._win.refresh()
        self._display_all_widgets()

    def _display_all_widgets(self):
        self._update_focus()
        self._fix_widgets_enabling()
        self._fix_search_captions_color()
        for n in self._widgets:
            try:
                n.show()
            except:
                n.show(self._win, opening=False)
        self._win.refresh()

    def _fix_search_captions_color(self):
        col = 5 if self._widgets[0].checked else 4
        for n in range(1,7):
            self._win.addstr(
                self.yx[n][0],
                self.yx[n][1],
                self.captions[n],
                curses.color_pair(col))
        self._win.refresh()

    def _update_focus(self):
        # use _focused here to avoid triggering
        # widgets' refresh
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    # logger.error('_update_focus: {} - True'.format(i))
                    x._focused = True
                else:
                    # logger.error('_update_focus: {} - False'.format(i))
                    x._focused = False

    def _get_search_term_index(self, new_search_term):
        ''' search for a search term in history

            if found            return True, index
            if not found        return False, len(self._history) - 1
                                and append the search term in the history
        '''
        found = False
        for a_search_term_index, a_search_term in enumerate(self._history):
            if new_search_term == a_search_term:
                # self._history_id = self._selected_history_id
                ret_index = a_search_term_index
                found = True
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('New search term already in history, id = {}'.format(ret_index))
                break

        if not found:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Adding new search term to history, id = {}'.format(len(self._history)))
            self._history.append(new_search_term)
            # self._history_id = self._selected_history_id = len(self._history) - 1
            ret_index = len(self._history) - 1
            self._cnf.dirty = True

        return found, ret_index

    def _goto_first_history_item(self):
        self._handle_new_or_existing_search_term()
        self._selected_history_id = 0
        self._print_history_legend()
        self._activate_search_term(self._history[self._selected_history_id])

    def _goto_last_history_item(self):
        self._handle_new_or_existing_search_term()
        self._selected_history_id = len(self._history) - 1
        self._print_history_legend()
        self._activate_search_term(self._history[self._selected_history_id])

    def _jump_history_up(self):
        self._handle_new_or_existing_search_term()
        self._selected_history_id -= 5
        if self._selected_history_id < 0:
            self._selected_history_id = len(self._history) - 1
        self._print_history_legend()
        self._activate_search_term(self._history[self._selected_history_id])

    def _jump_history_down(self):
        self._handle_new_or_existing_search_term()
        self._selected_history_id += 5
        if self._selected_history_id >= len(self._history):
            self._selected_history_id = 0
        self._print_history_legend()
        self._activate_search_term(self._history[self._selected_history_id])

    def _ctrl_n(self):
        ''' ^N - Next history item '''
        cur_history_id = self._selected_history_id
        logger.error('cur_history_id = {}'.format(cur_history_id))
        self._handle_new_or_existing_search_term()
        if abs(self._selected_history_id - cur_history_id) > 1:
            self._selected_history_id = cur_history_id
        if len(self._history) > 1:
            self._selected_history_id += 1
            if self._selected_history_id >= len(self._history):
                self._selected_history_id = 0
            self._print_history_legend()
            self._activate_search_term(self._history[self._selected_history_id])

    def _ctrl_p(self):
        ''' ^P - Previous history item '''
        cur_history_id = self._selected_history_id
        self._handle_new_or_existing_search_term()
        if abs(self._selected_history_id - cur_history_id) > 1:
            self._selected_history_id = cur_history_id
        if len(self._history) > 1:
            self._selected_history_id -= 1
            if self._selected_history_id < 0:
                self._selected_history_id = len(self._history) - 1
            self._print_history_legend()
            self._activate_search_term(self._history[self._selected_history_id])

    def _ctrl_x(self):
        ''' ^X - Delete history item '''
        self._handle_new_or_existing_search_term()
        if len(self._history) > 2 and \
                self._selected_history_id > 0:
            if self._default_history_id == self._selected_history_id:
                self._default_history_id = 1
            self._history.pop(self._selected_history_id)
            if self._selected_history_id == len(self._history):
                self._selected_history_id -= 1
            self._print_history_legend()
            self._activate_search_term(self._history[self._selected_history_id])
            self._cnf.dirty = True

    def _ctrl_b(self):
        ''' ^B - Set default item '''
        ret = self._handle_new_or_existing_search_term()
        if self._selected_history_id > 0:
            if ret == 1:
                self._default_history_id = self._selected_history_id
                self._print_history_legend()
                self._win.refresh()
            self._cnf.dirty = True

    def _ctrl_f(self):
        ''' ^T - Go to template (item 0) '''
        self._selected_history_id = 0
        self._print_history_legend()
        self._activate_search_term(self._history[self._selected_history_id])

    def selected_widget_class_name(self):
        return type(self._widgets[self._focus]).__name__

    def line_editor_has_focus(self):
        if self.selected_widget_class_name() == 'SimpleCursesLineEdit':
            return True
        return False

    def keypress(self, char):
        ''' RadioBrowserSearchWindow keypress

            Returns
            -------
               -1 - Cancel
                0 - do search
                1 - Continue
                2 - Display help
                3 - Display Line Editor Help
                4 - Error in search paremeter
                5 - Save search history
        '''
        if char in (
            curses.KEY_EXIT, 27
        ):
            return -1

        class_name = type(self._widgets[self._focus]).__name__

        if char == ord('q') and \
                class_name != 'SimpleCursesLineEdit':
            return -1

        if self._too_small:
            return 1

        if char == ord('0') and \
                class_name != 'SimpleCursesLineEdit':
            self._goto_first_history_item()

        elif char == ord('$') and \
                class_name != 'SimpleCursesLineEdit':
            self._goto_last_history_item()

        elif char in (curses.KEY_PPAGE, ) and self._focus != len(self._widgets) -3:
            self._jump_history_up()

        elif char in (curses.KEY_NPAGE, ) and self._focus != len(self._widgets) -3:
            self._jump_history_down()

        elif char in (ord('\t'), 9):
            self._focus_next()

        elif char in (curses.KEY_BTAB, ):
            self._focus_previous()

        elif char in (ord(' '), curses.KEY_ENTER, ord('\n'),
                      ord('\r')) and self._focus == len(self._widgets) - 1:
            ''' enter on cancel button  '''
            return -1

        elif char in (ord(' '), curses.KEY_ENTER, ord('\n'),
                      ord('\r')) and self._focus == len(self._widgets) - 2:
            ''' enter on ok button  '''
            ret = self._handle_new_or_existing_search_term()
            return 0 if ret == 1 else ret

        elif char in (curses.ascii.SO, ):
            ''' ^N - Next history item '''
            self._ctrl_n()

        elif char in (curses.ascii.DLE, ):
            ''' ^P - Previous history item '''
            self._ctrl_p()

        # elif char in (curses.ascii.ETB, ):
        elif char in (curses.ascii.ENQ, ):
            ''' ^E - Save search history '''
            self._handle_new_or_existing_search_term()
            ''' Save search history '''
            return 5

        elif char in (curses.ascii.EM, ):
            ''' ^Y - Add history item '''
            self._handle_new_or_existing_search_term()

        elif char in (curses.ascii.CAN, ):
            ''' ^X - Delete history item '''
            self._ctrl_x()

        elif char in (curses.ascii.STX, ):
            ''' ^B - Set default item '''
            self._ctrl_b()

        elif char in (curses.ascii.ACK, ):
            ''' ^F - Go to template (item 0) '''
            self._ctrl_f()

        else:
            if class_name == 'SimpleCursesWidgetColumns':
                ret = self._widgets[self._focus].keypress(char)
                if ret == 0:
                    # item selected
                    self._win.refresh()
                elif ret == 2:
                    # cursor moved
                    self._win.refresh()

            elif self._focus in self._checkbox_to_enable_widgets:
                ret = self._widgets[self._focus].keypress(char)
                if not ret:
                    tp = list(self._checkbox_to_enable_widgets)
                    tp.remove(self._focus)
                    other = tp[0]
                    self._widgets[other].checked = not self._widgets[self._focus].checked
                    self._fix_widgets_enabling()
                    self._win.refresh()
                    return 1

            elif class_name == 'SimpleCursesCheckBox':
                ret = self._widgets[self._focus].keypress(char)
                if not ret:
                    return 1

            elif class_name == 'SimpleCursesCounter':
                ret = self._widgets[self._focus].keypress(char)
                if ret == 0:
                    self._win.refresh()
                    return 1

            elif class_name == 'SimpleCursesLineEdit':
                ret = self._widgets[self._focus].keypress(self._win, char)
                if ret == -1:
                    # Cancel
                    return -1
                elif ret == 2:
                    ''' display Line Editor Help '''
                    return 3
                elif ret < 2:
                    return 1

            if char in (ord('s'), ):
                ''' prerform search '''
                ret = self._handle_new_or_existing_search_term()
                return 0 if ret == 1 else ret

            elif char == curses.KEY_HOME:
                self._goto_first_history_item()

            elif char in (curses.KEY_END, ord('g')):
                self._goto_last_history_item()

            elif char in (ord('n'), ):
                ''' ^N - Next history item '''
                self._ctrl_n()

            elif char in (ord('p'), ):
                ''' ^P - Previous history item '''
                self._ctrl_p()

            elif char in (ord('e'), ):
                ''' ^E - Save search history '''
                self._handle_new_or_existing_search_term()
                return 5

            elif char in (ord('f'), ):
                ''' ^F - Go to template (item 0) '''
                self._ctrl_f()

            elif char in (ord('x'), ):
                ''' ^X - Delete history item '''
                self._ctrl_x()

            elif char in (ord('b'), ):
                ''' ^B - Set default item '''
                self._ctrl_b()

            elif char in (ord('y'), ):
                ''' ^Y - Add current item to history'''
                self._handle_new_or_existing_search_term()

            elif char in (ord('k'), curses.KEY_UP) and \
                    class_name != 'SimpleCursesWidgetColumns':
                self._focus_up()
            elif char in (ord('j'), curses.KEY_DOWN) and \
                    class_name != 'SimpleCursesWidgetColumns':
                self._focus_down()
            elif char in (ord('l'), curses.KEY_RIGHT) and \
                    class_name not in ('SimpleCursesWidgetColumns',
                                       'SimpleCursesLineEdit'):
                if 5 <= self._widgets[self._focus].id <= 13:
                    new_focus = self._focus + 2
                    # logger.error('DE focus = {}'.format(new_focus))
                    if new_focus == 15:
                        new_focus = 16
                    # logger.error('DE focus = {}'.format(new_focus))
                    self._apply_new_focus(new_focus)
                else:
                    self._focus_next()
            elif char in (ord('h'), curses.KEY_LEFT) and \
                    class_name not in ('SimpleCursesWidgetColumns',
                                       'SimpleCursesLineEdit'):
                if 5 <= self._widgets[self._focus].id <= 13:
                    new_focus = self._focus - 2
                    # logger.error('DE focus = {}'.format(new_focus))
                    if new_focus == 3:
                        new_focus = 4
                    # logger.error('DE focus = {}'.format(new_focus))
                    self._apply_new_focus(new_focus)
                else:
                    self._focus_previous()

        if char == ord('?'):
            ''' display help '''
            return 2

        ''' continue '''
        return 1

    def _handle_new_or_existing_search_term(self):
        ''' read all widgets and create a search term
            if it  does not exist add it to history
        '''
        test_search_term = self._widgets_to_search_term()
        if test_search_term:
            found, index = self._get_search_term_index(test_search_term)
            # TODO: check if item is altered
            self._selected_history_id = index
            self._print_history_legend()
            self._win.refresh()
        else:
            ''' parameter error'''
            return 4
        return 1

    def _fix_widgets_enabling(self):
        self._fix_search_captions_color()
        col = True if self._widgets[0].checked else False
        self._widgets[1].enabled = col
        for i in range(self._checkbox_to_enable_widgets[1] + 1, len(self._widgets) - self.NUMBER_OF_WIDGETS_AFTER_SEARCH_SECTION):
            self._widgets[i].enabled = not col
            # logger.error('DE widget {0} enabled: {1}'.format(i, not col))

    def _focus_next(self):
        # logger.error('DE focus next ==========================')
        new_focus = self._focus + 1
        if new_focus == len(self._widgets):
            new_focus = 0
        # logger.error('DE new_focus = {}'.format(new_focus))
        focus_ok = False
        for i in range(new_focus, len(self._widgets)):
            if self._widgets[i].enabled:
                new_focus = i
                focus_ok = True
                # logger.error('DE 1 new_focus = {}'.format(new_focus))
                break
        if not focus_ok:
            for i in range(0, new_focus + 1):
                if self._widgets[i].enabled:
                    new_focus = i
                    focus_ok = True
                    # logger.error('DE 2 new_focus = {}'.format(new_focus))
                    break
        # logger.error('DE new_focus = {}'.format(new_focus))
        # logger.error('DE end focus next ==========================')
        self._apply_new_focus(new_focus)

    def _focus_previous(self):
        # logger.error('DE focus previous ==========================')
        new_focus = self._focus - 1
        if new_focus == -1:
            new_focus = len(self._widgets) - 1
        # logger.error('DE new_focus = {}'.format(new_focus))
        focus_ok = False
        for i in range(new_focus, -1, -1):
            # logger.error('DE i = {}'.format(i))
            if self._widgets[i].enabled:
                new_focus = i
                focus_ok = True
                # logger.error('DE 1 new_focus = {}'.format(new_focus))
                break
        if not focus_ok:
            for i in range(len(self._widgets) - 1, new_focus, -1):
                # logger.error('DE i = {}'.format(i))
                if self._widgets[i].enabled:
                    new_focus = i
                    focus_ok = True
                    # logger.error('DE 2 new_focus = {}'.format(new_focus))
                    break
        # logger.error('DE end focus previous ==========================')
        self._apply_new_focus(new_focus)

    def _focus_up(self):
        # logger.error('DE self._focus_up()')
        new_focus, col = self._get_column_list(self._focus)
        # logger.error('DE new_focus = {0}, col = {1}'.format(new_focus, col))
        while True:
            new_focus -= 1
            # logger.error('DE new_focus = {}'.format(new_focus))
            if new_focus < 0:
                new_focus = len(col) - 1
            # logger.error('DE new_focus = {}'.format(new_focus))
            # logger.error('DE col[new_focus] = {}'.format(col[new_focus]))
            if self._widgets[col[new_focus]].enabled:
                break
        self._apply_new_focus(col[new_focus])

    def _focus_down(self):
        new_focus, col = self._get_column_list(self._focus)
        # logger.error('DE new_focus = {0}, col = {1}'.format(new_focus, col))
        while True:
            new_focus += 1
            # logger.error('DE new_focus = {}'.format(new_focus))
            if new_focus == len(col):
                new_focus = 0
            # logger.error('DE new_focus = {}'.format(new_focus))
            # logger.error('DE col[new_focus] = {}'.format(col[new_focus]))
            if self._widgets[col[new_focus]].enabled:
                break
        self._apply_new_focus(col[new_focus])

    def _apply_new_focus(self, new_focus):
        if new_focus != self._focus:
            self._widgets[self._focus].focused = False
            self._focus = new_focus
            self._widgets[self._focus].focused = True
            self._win.refresh()

    def _get_column_list(self, this_id):
        if this_id in self._left_column:
            return self._left_column.index(this_id), self._left_column
        elif this_id in self._middle_column:
            return self._middle_column.index(this_id), self._middle_column
        elif this_id in self._right_column:
            return self._right_column.index(this_id), self._right_column

class RadioBrowserData(object):
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


class RadioBrowserDns(object):
    ''' Preforms query the DNS SRV record of
        _api._tcp.radio-browser.info which
        gives the list of server names directly
        without reverse dns lookups '''

    _urls = None
    _countries = None

    def __init__(self):
        pass

    @property
    def connected(self):
        return self._urls

    @property
    def server_urls(self):
        ''' Returns server urls in a tuple '''
        if self._urls is None:
            self._get_urls()

        return tuple(self._urls) if self._urls is not None else None

    @server_urls.setter
    def server_urls(self, val):
        return

    @property
    def server_countries(self):
        ''' Returns server countries in a tuple '''
        if self._urls is None:
            self._get_urls()
        self._get_countries()
        return self._countries

    @server_countries.setter
    def server_countries(self, value):
        return

    def get_server_names_and_urls(self):
        if self._urls is None:
            self._get_urls()
        if self._countries is None:
            self._get_countries()
        zipped = list(zip(self._countries, self._urls))
        self._names_and_urls = []
        for n in zipped:
            self._names_and_urls.append(n[1] + ' (' + n[0] + ')')
        return self._names_and_urls

    def _get_urls(self):
        # self._urls = None
        # return
        self._urls = []
        result = None
        try:
            result = resolver.query('_api._tcp.radio-browser.info', 'SRV')
        except:
            self._urls = None

        if result:
            for n in result:
                self._urls.append(str(n).split(' ')[-1][:-1])
        else:
            self._urls = None

    def _get_countries(self):
        self._countries = []
        for n in self._urls:
            self._countries.append(country_from_server(n))
        logger.error('DE countries = {}'.format(self._countries))

    def give_me_a_server_url(self):
        ''' Returns a random server '''
        if self._urls is None:
            self._get_urls()

        if self._urls:
            ping_response = [-2] * len(self._urls)
            start_num = num = random.randint(0, len(self._urls) - 1)
            while ping_response[num] == -2:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('pinging random server: ' + self._urls[num])
                ping_response[num] = ping(self._urls[num], count=1, timeout_in_seconds=1)
                if ping_response[num] == 1:
                    ''' ping was ok '''
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('ping was successful!')
                    break
                if logger.isEnabledFor(logging.INFO):
                    logger.info('ping was unsuccessful!')
                num += 1
                if num == len(self._urls):
                    num = 0
                if num == start_num:
                    return None
            return self._urls[num]
        else:
            return None

    def servers(self):
        ''' server urls as generator '''
        if self._urls is None:
            self._get_urls()

        for a_url in self._urls:
            yield a_url

class RadioBrowserSort(object):

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

    def show(self, parent=None):
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
                                 curses.color_pair(10))
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
                         curses.color_pair(11))
        self._refresh()

    def _refresh(self):
        for i, n in enumerate(self.items.keys()):
            col = 10
            if i == self.active == self.selection:
                col = 9
            elif i == self.selection:
                col = 6
            elif i == self.active:
                col = 11

            self._win.addstr(i + 1, 1,
                             ' {}'.format(n.ljust(self.maxX - 3)),
                             curses.color_pair(col))
        self._win.refresh()

    def keypress(self, char):
        ''' RadioBrowserSort keypress

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


class RadioBrowserServersSelect(object):
    ''' Server selection Window
        Uses RadioBrowserServers
    '''

    TITLE = ' Server Selection '

    return_value = 1

    def __init__(self,
                 parent,
                 servers,
                 current_server,
                 ping_count,
                 ping_timeout,
                 Y=None,
                 X=None,
                 show_random=False,
                 return_function=None,
                 global_functions=None):
        ''' Server selection Window
            if Y and X are valid (not None)
              keypress just returns 0
            If Y is None
              keypress returns 0 and self.server is set
        '''
        self._parent = parent
        self.items = list(servers)
        self.server = current_server
        self.ping_count = ping_count
        self.ping_timeout = ping_timeout
        self._show_random = self.from_config = show_random
        self._return_function = return_function

        self.servers = RadioBrowserServers(
            parent, servers, current_server, show_random, global_functions
        )
        self.maxY = self.servers.maxY + 2
        self.maxX = self.servers.maxX + 2
        self._Y = Y
        self._X = X
        logger.error('DE self._Y ={0}, self._X = {1}'.format(self._Y, self._X))

    def move(self, Y, X, parent=None):
        self._Y = Y
        self._X = X
        self._win = curses.newwin(
            self.maxY, self.maxX,
            self._Y, self._X
        )
        self.show(parent)

    def show(self, parent=None):
        if parent:
            self._parent = parent
            self.servers._parent = parent
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
                                 curses.color_pair(10))
            except:
                pass
            self._win.refresh()
            return

        if self._Y is None:
            self._win = curses.newwin(
                self.maxY, self.maxX,
                Y + int((pY - self.maxY) / 2),
                int((pX - self.maxX) / 2)
            )
        else:
            self._win = curses.newwin(
                self.maxY, self.maxX,
                self._Y, self._X
            )
        self._win.bkgdset(' ', curses.color_pair(3))
        # self._win.erase()
        self._box_and_title()
        self.servers._parent = self._win
        self.servers.show()

    def _box_and_title(self):
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self.TITLE)) / 2),
            self.TITLE,
            curses.color_pair(11)
        )
        self._win.refresh()

    def set_parent(self, parent):
        self._parent = parent
        self.servers._parent = parent

    def keypress(self, char):
        ''' RadioBrowserServersSelect keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
        '''

        self.return_value = self.servers.keypress(char)

        if self.return_value == 2:
            self.return_value = 1
        if self.return_value == 0:
            if self.servers.server:
                if self.ping_count > 0 and self.ping_timeout > 0:
                    msg = ' Checking Host '
                    self._win.addstr(
                        self.maxY - 1, int((self.maxX - len(msg)) / 2),
                        msg,
                        curses.color_pair(3)
                    )
                    self._win.refresh()
                    if ping(self.servers.server,
                            count=self.ping_count,
                            timeout_in_seconds=self.ping_timeout) != 1:
                        ''' ping was not ok '''
                        msg = ' Host is unreachable '
                        self._win.addstr(
                            self.maxY - 1, int((self.maxX - len(msg)) / 2),
                            msg,
                            curses.color_pair(3)
                        )
                        self._win.refresh()
                        th = threading.Timer(1, self._box_and_title)
                        th.start()
                        th.join()
                        self.show()
                        return 1

                if self._Y is None:
                    self.server = self.servers.server
            if self._return_function:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('selected server: {}'.format(self.servers.server))
                self._return_function(self.servers.server)
                return 2

        return self.return_value


class RadioBrowserServers(object):
    ''' Display RadioBrowser server
        This is supposed to be pluged into
        another widget
    '''

    _too_small = False
    from_config = False

    def __init__(self, parent, servers, current_server, show_random=False, global_functions=None):
        self._parent = parent
        self.items = list(servers)
        self.server = current_server
        self.from_config = show_random

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
        self._global_functions = {}
        # if global_functions is not None:
        #     logger.error('\n\n{}\n\n'.format(global_functions))
        #     self._global_functions = deepcopy(global_functions)
        #     if ord('t') in self._global_functions.keys():
        #             del self._global_functions[ord('t')]

        if show_random:
            self.items.reverse()
            self.items.append(' Random' + (s_max - 7) * ' ')
            self.items.reverse()
            self.maxY = len(self.items)
            logger.error('DE items = {}'.format(self.items))
        ''' get selection and active server id '''
        if show_random and (
            self.server == '' or 'Random' in self.server
        ):
            self.active = self.selection = 0
        else:
            for i, n in enumerate(self.items):
                if self.server in n:
                    self.active = self.selection = i
                    break

    def show(self, parent=None):
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
                col = 10
                if i == self.active == self.selection:
                    col = 9
                elif i == self.selection:
                    col = 6
                elif i == self.active:
                    col = 11
                try:
                    self._win.addstr(i, 0 , n, curses.color_pair(col))
                except:
                    pass
            self._win.refresh()

    def keypress(self, char):
        ''' RadioBrowserServers keypress

            Returns:
                -1: Cancel
                 0: Done, result is in ....
                 1: Continue
                 2: Show help
        '''

        if self._too_small:
            return 1

        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 1
        elif char in (
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
                    if 'Random' in n:
                        self.server = ''
                    else:
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

class RadioBrowserStationsStack(object):
    pass_first_item_func=None
    pass_last_item_func=None
    no_items_func=None
    play_from_history = False

    ''' items: list of lists
        [
            [name, station name, station id],
            ...
        ]
    '''

    def __init__(
        self,
        execute_function,
        pass_first_item_function=None,
        pass_last_item_function=None,
        no_items_function=None
    ):
        self.items = []
        self.item = -1

        ######## DEBUG START
        #self.items = [
        #    ['reversed', 'WKHR', 1],
        #    ['reversed', 'Jazz (Sonic Universe - SomaFM)', 11],
        #    ['stations', 'Celtic (ThistleRadio - SomaFM)', 3]
        #]
        #self.item = 0
        #self.play_from_history = True
        #self.clear()
        ######## DEBUG END

        self.execute_func = execute_function
        self.pass_first_item_func = pass_first_item_function
        self.pass_last_item_func = pass_last_item_function
        self.no_items_func = no_items_function

    def _show_station_history_debug(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('>>> Online browser stations history')
            if self.items:
                for n in self.items:
                    logger.debug('   {}'.format(n))
                logger.debug('   item was = {}'.format(self.item))
            else:
                logger.debug('   No items in list')
                logger.debug('   item = {}'.format(self.item))

    def add(self, a_playlist, a_station, a_station_id):
        a_playlist = 'Online Browser'
        if self.item == -1:
            self.items.append([a_playlist, a_station, a_station_id])
            self.item = 0
            self._show_station_history_debug()
        else:
            if not a_station.startswith('register_') and \
                    (not self.play_from_history) and \
                     self.items[self.item][1] != a_station:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Adding station history item...')
                self.items.append([a_playlist, a_station, a_station_id])
                self.item = len(self.items) - 1
                self._show_station_history_debug()
            #else:
            #    if logger.isEnabledFor(logging.DEBUG):
            #        logger.debug('Not adding station history item...')
        self.play_from_history = False

    def clear(self):
        self.items = []
        self.item = -1
        self.play_from_history = False

    def remove_station(self, a_station):
        for i in range(len(self.items) - 1, -1, -1):
            if self.items[i][1] == a_station:
                self.items.pop(i)
        if self.item >= len(self.items):
            self.item = len(self.items) - 1
        self._show_station_history_debug()

    def rename_station(self, playlist, orig_station, new_station):
         # logger.error('playlist = "{}"'.format(playlist))
         # logger.error('orig_station = "{}"'.format(orig_station))
         # logger.error('new_station = "{}"'.format(new_station))
         self._show_station_history_debug()
         for i in range(len(self.items) - 1, -1, -1):
             if self.items[i][1] == orig_station:
                 logger.error('item = {}'.format(self.items[i]))
                 self.items[i][1] = new_station
                 logger.error('item = {}'.format(self.items[i]))
         self._show_station_history_debug()

    def _get(self):
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        return tuple(self.items[self.item])

    def play_previous(self):
        self._show_station_history_debug()
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        elif self.item == 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   Already on first item')
            if self.pass_first_item_func is not None:
                self.pass_first_item_func()
        else:
            self.item -= 1
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   item is  = {}'.format(self.item))
            self.execute_func(self._get(), self.play_previous)

    def play_next(self):
        self._show_station_history_debug()
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        elif self.item == len(self.items) - 1:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   Already on last item')
            if self.pass_last_item_func is not None:
                self.pass_last_item_func()
        else:
            self.item += 1
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   item is  = {}'.format(self.item))
            self.execute_func(self._get(), self.play_next)


class RadioBrowserTermNavigator(SimpleCursesWidget):
    """ A widget to show Radio Browser Search Terms
        Availabe actions:
            change default item
            delete item
    """
    parent = None
    _win = None
    _width = _height = _X = _Y = 0
    _selection = 1

    _items = []

    _page_jump = 5

    log = None
    _log_file = ''

    _showed = False

    def __init__(
        self,
        parent,
        items,
        default,
        limit,
        X, Y,
        width,
        color,
        header_color,
        highlight_color,
        cannot_delete_function,
        log_file=''
    ):
        """ A widget to show RarioBrowser Search Terms
            Available actions:
                change default term
                delete terms
        """
        self._ungetch = 0
        if log_file:
            self._log_file = log_file
            self.log = self._log

        self._default, self._default_limit = default, limit
        self._Y, self._X, self._width = Y, X, width
        self._parent = parent
        self._color = color
        self._header_color = header_color
        self._highlight_color = highlight_color
        self._height = 7
        self._get_win()
        self._orig_items = items
        self._selection = self._orig_default = default
        self._items =deepcopy(items)
        self._cannot_delete_function = cannot_delete_function

    @property
    def dirty(self):
        return self._default != self._orig_default or \
            self._items != self._orig_items

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, val):
        old_selection = self._selection
        if 0 <= val < len(self._items):
            self._selection = val
            self.show()

    def set_data(self, default, default_limit, items):
        self._selection = self._default = default
        self._default_limit = default_limit
        self._items = deepcopy(items)

    def get_result(self):
        return self._default, self._items

    def _get_win(self):
        self._parent_Y, self._parent_X = self._parent.getmaxyx()
        self._win = curses.newwin(
            self._height,
            self._width,
            self._Y,
            self._X
        )
        self._win.bkgdset(' ', self._color)
        self._win.erase()


    def refresh(self, parent=None):
        self.show(parent)

    def _print_post_data(self, token, col):
        str_out = 15 * ' '
        if 'post_data' in self._items[self._selection]:
            if token in self._items[self._selection]['post_data']:
                str_out = '{}'.format(self._items[self._selection]['post_data'][token].ljust(15))
        self._win.addstr(str_out, col)

    def show(self, parent=None):
        if self._focused:
            col = self._header_color
            fcol = self._highlight_color
        else:
            col = fcol = self._color
        if parent:
            if parent is not self._parent:
                # self._log('changing parent!\n')
                self._parent = parent
                self._get_win()

        limit = term = None
        if self._items:
            if 'type' in self._items[self._selection].keys():
                # self._log('   >>> I am here\n')
                if self._items[self._selection]['type'] in (
                        'topvote',
                        'lastchange',
                        'topclick',
                        'lastclick'
                ):
                    limit = self._items[self._selection]['term']
                    term = ''

        rpad = len(str(len(self._items)))
        self._win.addstr(0, 0, '  Item: ', self._color)
        if self._items:
            self._win.addstr(' {}'.format(str(self._selection).rjust(rpad)), col)
        else:
            self._win.addstr(' {}'.format(0), col)
            self._selection = -1
        self._win.addstr('/{}   '.format(len(self._items) - 1), self._color)

        if self._selection == 0:
            self._win.addstr('   Template Item!     ', col)
        elif self._selection == self._default:
            self._win.addstr('   Default Item!      ', col)
        else:
            self._win.addstr('                      ', col)

        self._win.addstr(1, 0, '  Type: ', self._color)
        str_out = 15 * ' '
        if self._items:
            if 'type' in self._items[self._selection].keys():
                str_out = self._items[self._selection]['type'].ljust(15)
        self._win.addstr(str_out, col)

        self._win.addstr(1, 25, ' Limit: ', self._color)
        str_out = 15 * ' '
        if limit is not None:
            str_out ='{}'.format(limit)
        else:
            if self._items:
                if 'post_data' in self._items[self._selection]:
                    if 'limit' in self._items[self._selection]['post_data']:
                        str_out = '{}'.format(self._items[self._selection]['post_data']['limit'])
                    else:
                        if limit is None:
                            str_out = '{}'.format(self._default_limit)
                        else:
                            if limit != '':
                                str_out = '{}'.format(limit)
        self._win.addstr(str_out, col)

        self._win.addstr('   Codec: ', self._color)
        self._print_post_data('codec', col)

        self._win.addstr(2, 0, '  Term: ', self._color)
        str_out = 15 * ' '
        if self._items:
            if term is not None:
                if term != '':
                    str_out = '{}'.format(term)
            else:
                if 'term' in self._items[self._selection]:
                    try:
                        x = len(self._items[self._selection]['term'])
                        x = self._items[self._selection]['term']
                    except TypeError:
                        x = str(self._items[self._selection]['term'])
                    str_out = x.ljust(15)
        self._win.addstr(str_out, col)

        self._win.addstr(2, 25, ' Language: ', self._color)
        self._print_post_data('language', col)

        self._win.addstr(3, 0, '  Name: ', self._color)
        self._print_post_data('name', col)

        self._win.addstr(3, 25, ' Tag: ', self._color)
        self._print_post_data('tag', col)

        self._win.addstr(4, 0, '  Country: ', self._color)
        self._print_post_data('country', col)

        self._win.addstr(4, 25, ' State: ', self._color)
        self._print_post_data('state', col)

        self._win.addstr(5, 0, '  Sorting: ', self._color)
        if self._items:
            if 'post_data' in self._items[self._selection]:
                if 'order' in self._items[self._selection]['post_data']:
                    self._win.addstr('{} '.format(self._items[self._selection]['post_data']['order']), col)

                    if 'reverse' in self._items[self._selection]['post_data']:
                        self._win.addstr(' (', self._color)
                        if self._items[self._selection]['post_data']['reverse'] == 'true':
                            self._win.addstr('descending', col)
                        else:
                            self._win.addstr('ascending', col)
                        self._win.addstr(')  ', self._color)
                    else:
                        self._win.addstr(' ' * (len(' (descending)   ') + 15), self._color)
                else:
                    self._win.addstr(' ' * (len(' (descending)   ') + 15), self._color)
            else:
                self._win.addstr(' ' * (len(' (descending)   ') + 15), self._color)
        else:
            self._win.addstr(' ' * (len(' (descending)   ') + 15), self._color)

        self._win.hline(6, 0, ' ', self._width, fcol)
        self._win.addstr(6, 0, '  Extra keys: x - delete item , Space - make item default', fcol)
        # do this for windows
        self._win.touchwin()
        #####################
        self._win.refresh()
        self._showed = True

    def move(self, Y, X, show=True, erase=False):
        self.mvwin(Y, X-2, show, erase=True)
        if self._ungetch == 0:
            curses.ungetch('#')
            self._ungetch += 1
        else:
            self._ungetch = 0

    def getmaxyx(self):
        return self._width, self._height

    def _remove_item(self):
        if self._items:
            self._items.pop(self._selection)
            if self._default == self._selection:
                self._default = 1
            if self._selection == len(self._items):
                self._selection -= 1
            self.show()

    def _go_up(self):
        self._selection -= 1
        if self._selection < 1:
            self._selection = len(self._items) - 1
        self.show()

    def _go_down(self):
        self._selection += 1
        if self._selection == len(self._items):
            self._selection = 1
        self.show()

    def _go_home(self):
        self._selection = 1
        self.show()

    def _go_end(self):
        self.selection = len(self._items) - 1
        self.show()

    def _jump_up(self):
        if self._selection == 1:
            self._selection = len(self._items) - 1
        else:
            sel = self._selection - self._page_jump
            if sel < 1:
                self._selection = 1
            else:
                self._selection = sel
        self.show()

    def _jump_down(self):
        if self._selection == len(self._items) - 1:
            self._selection = 1
        else:
            sel = self._selection + self._page_jump
            if sel >= len(self._items):
                self._selection = len(self._items) - 1
            else:
                self._selection = sel
        self.show()

    def keypress(self, char):
        """ returns theme_id, save_theme
            return_id
               -1    : cancel
                1    : go on
                2    : help
        """
        if char == ord('?'):
            return 2
        elif char == ord('x'):
            if len(self._items) > 2:
                self._remove_item()
            else:
                self._cannot_delete_function()
        elif char in (ord(' '), ):
            if self._items:
                self._default = self._selection
                self.show()
        elif char in (curses.KEY_LEFT, ord('h'), ord('p')):
            self._go_up()
        elif char in (curses.KEY_RIGHT, ord('l'), ord('n')):
            self._go_down()
        elif char in (curses.KEY_HOME, ord('g'), ord('0'), ord('^')):
            self._go_home()
        elif char in (curses.KEY_END, ord('G'), ord('$')):
            self._go_end()
        elif char in (curses.KEY_NPAGE, ):
            self._jump_down()
        elif char in (curses.KEY_PPAGE, ):
            self._jump_up()
        elif char in (curses.KEY_EXIT, 27, ord('q')):
            return -1
        return 1

    def _log(self, msg):
        with open(self._log_file, 'a') as log_file:
            log_file.write(msg)

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
