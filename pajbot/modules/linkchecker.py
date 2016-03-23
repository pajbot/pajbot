import logging
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.mysql import TEXT

from pajbot.actions import Action
from pajbot.actions import ActionQueue
from pajbot.apiwrappers import SafeBrowsingAPI
from pajbot.managers import Base
from pajbot.managers import DBManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.models.handler import HandlerManager
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


def is_subdomain(x, y):
    """ Returns True if x is a subdomain of y, otherwise return False.

    Example:
    is_subdomain('pajlada.se', 'pajlada.se') = True
    is_subdomain('test.pajlada.se', 'pajlada.se') = True
    is_subdomain('test.pajlada.se', 'pajlada.com') = False
    """
    if y.startswith('www.'):
        y = y[4:]
    return x.endswith('.' + y) or x == y


def is_subpath(x, y):
    """ Returns True if x is a subpath of y, otherwise return False.

    Example:
    is_subpath('/a/', '/b/') = False
    is_subpath('/a/', '/a/') = True
    is_subpath('/a/abc', '/a/') = True
    is_subpath('/a/', '/a/abc') = False
    """
    if y.endswith('/'):
        return x.startswith(y) or x == y[:-1]
    else:
        return x.startswith(y + '/') or x == y


def is_same_url(x, y):
    """ Returns True if x and y should be parsed as the same URLs, otherwise return False.  """
    parsed_x = x.parsed
    parsed_y = y.parsed
    return parsed_x.netloc == parsed_y.netloc and parsed_x.path.strip('/') == parsed_y.path.strip('/') and parsed_x.query == parsed_y.query


def find_unique_urls(regex, message):
    _urls = regex.finditer(message)
    urls = []
    for i in _urls:
        url = i.group(0)
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        if not(url[-1].isalpha() or url[-1].isnumeric() or url[-1] == '/'):
            url = url[:-1]
        urls.append(url)

    return set(urls)


class Url:
    def __init__(self, url):
        self.url = url
        self.parsed = urllib.parse.urlparse(url)


class LinkCheckerCache:
    def __init__(self):
        self.cache = {}
        return

    def __getitem__(self, url):
        return self.cache[url.strip('/').lower()]

    def __setitem__(self, url, safe):
        self.cache[url.strip('/').lower()] = safe

    def __contains__(self, url):
        return url.strip('/').lower() in self.cache

    def __delitem__(self, url):
        del self.cache[url.strip('/').lower()]


class LinkCheckerLink:
    def is_subdomain(self, x):
        """ Returns True if x is a subdomain of this link, otherwise return False.  """
        y = self.domain
        if y.startswith('www.'):
            y = y[4:]
        return x.endswith('.' + y) or x == y

    def is_subpath(self, x):
        """ Returns True if x is a subpath of y, otherwise return False.  """
        y = self.path
        if y.endswith('/'):
            return x.startswith(y) or x == y[:-1]
        else:
            return x.startswith(y + '/') or x == y


class BlacklistedLink(Base, LinkCheckerLink):
    __tablename__ = 'tb_link_blacklist'

    id = Column(Integer, primary_key=True)
    domain = Column(String(256))
    path = Column(TEXT)
    level = Column(Integer)

    def __init__(self, domain, path, level):
        self.id = None
        self.domain = domain
        self.path = path
        self.level = level


class WhitelistedLink(LinkCheckerLink, Base):
    __tablename__ = 'tb_link_whitelist'

    id = Column(Integer, primary_key=True)
    domain = Column(String(256))
    path = Column(TEXT)

    def __init__(self, domain, path):
        self.id = None
        self.domain = domain
        self.path = path


class LinkCheckerModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Link Checker'
    DESCRIPTION = 'Checks links if they\'re bad'
    ENABLED_DEFAULT = True
    CATEGORY = 'Filter'
    SETTINGS = [
            ModuleSetting(
                key='ban_pleb_links',
                label='Disallow links from non-subscribers',
                type='boolean',
                required=True,
                default=False)
            ]

    def __init__(self):
        super().__init__()
        self.db_session = None
        self.links = {}

        self.blacklisted_links = []
        self.whitelisted_links = []

        self.cache = LinkCheckerCache()  # cache[url] = True means url is safe, False means the link is bad

        self.action_queue = ActionQueue()
        self.action_queue.start()

    def enable(self, bot):
        self.bot = bot
        HandlerManager.add_handler('on_message', self.on_message, priority=100)
        HandlerManager.add_handler('on_commit', self.on_commit)
        if bot:
            self.run_later = bot.execute_delayed

            if 'safebrowsingapi' in bot.config['main']:
                # XXX: This should be loaded as a setting instead.
                # There needs to be a setting for settings to have them as "passwords"
                # so they're not displayed openly
                self.safeBrowsingAPI = SafeBrowsingAPI(bot.config['main']['safebrowsingapi'], bot.nickname, bot.version)
            else:
                self.safeBrowsingAPI = None

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
        self.db_session = DBManager.create_session()
        self.blacklisted_links = []
        for link in self.db_session.query(BlacklistedLink):
            self.blacklisted_links.append(link)

        self.whitelisted_links = []
        for link in self.db_session.query(WhitelistedLink):
            self.whitelisted_links.append(link)

    def disable(self, bot):
        HandlerManager.remove_handler('on_message', self.on_message)
        HandlerManager.remove_handler('on_commit', self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.blacklisted_links = []
            self.whitelisted_links = []

    def reload(self):

        log.info('Loaded {0} bad links and {1} good links'.format(len(self.blacklisted_links), len(self.whitelisted_links)))
        return self

    super_whitelist = ['pajlada.se', 'pajlada.com', 'forsen.tv', 'pajbot.com']

    def on_message(self, source, message, emotes, whisper, urls, event):
        if not whisper and source.level < 500 and source.moderator is False:
            if self.settings['ban_pleb_links'] is True and source.subscriber is False and len(urls) > 0:
                # Check if the links are in our super-whitelist. i.e. on the pajlada.se domain o forsen.tv
                for url in urls:
                    parsed_url = Url(url)
                    if len(parsed_url.parsed.netloc.split('.')) < 2:
                        continue
                    whitelisted = False
                    for whitelist in self.super_whitelist:
                        if is_subdomain(parsed_url.parsed.netloc, whitelist):
                            whitelisted = True
                            break
                    if whitelisted is False:
                        self.bot.timeout(source.username, 30)
                        if source.minutes_in_chat_online > 60:
                            self.bot.whisper(source.username, 'You cannot post non-verified links in chat if you\'re not a subscriber.')
                        return False

            for url in urls:
                # Action which will be taken when a bad link is found
                action = Action(self.bot.timeout, args=[source.username, 20])
                # First we perform a basic check
                if self.simple_check(url, action) == self.RET_FURTHER_ANALYSIS:
                    # If the basic check returns no relevant data, we queue up a proper check on the URL
                    self.action_queue.add(self.check_url, args=[url, action])

    def on_commit(self):
        if self.db_session is not None:
            self.db_session.commit()

    def delete_from_cache(self, url):
        if url in self.cache:
            log.debug('LinkChecker: Removing url {0} from cache'.format(url))
            del self.cache[url]

    def cache_url(self, url, safe):
        if url in self.cache and self.cache[url] == safe:
            return

        log.debug('LinkChecker: Caching url {0} as {1}'.format(url, 'SAFE' if safe is True else 'UNSAFE'))
        self.cache[url] = safe
        self.run_later(20, self.delete_from_cache, (url, ))

    def counteract_bad_url(self, url, action=None, want_to_cache=True, want_to_blacklist=True):
        log.debug('LinkChecker: BAD URL FOUND {0}'.format(url.url))
        if action:
            action.run()
        if want_to_cache:
            self.cache_url(url.url, False)
        if want_to_blacklist:
            self.blacklist_url(url.url, url.parsed)

    def unlist_url(self, url, list_type, parsed_url=None):
        """ list_type is either 'blacklist' or 'whitelist' """
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url

        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)

        domain = parsed_url.netloc
        path = parsed_url.path

        if domain.startswith('www.'):
            domain = domain[4:]
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '/'

        if list_type == 'blacklist':
            link = self.db_session.query(BlacklistedLink).filter_by(domain=domain, path=path).one_or_none()
            if link:
                self.blacklisted_links.remove(link)
                self.db_session.delete(link)
            else:
                log.warning('Unable to unlist {0}{1}'.format(domain, path))
        elif list_type == 'whitelist':
            link = self.db_session.query(WhitelistedLink).filter_by(domain=domain, path=path).one_or_none()
            if link:
                self.whitelisted_links.remove(link)
                self.db_session.delete(link)
            else:
                log.warning('Unable to unlist {0}{1}'.format(domain, path))

    def blacklist_url(self, url, parsed_url=None, level=1):
        if not (url.lower().startswith('http://') or url.lower().startswith('https://')):
            url = 'http://' + url

        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)

        if self.is_blacklisted(url, parsed_url):
            return False

        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()

        if domain.startswith('www.'):
            domain = domain[4:]
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '/'

        link = BlacklistedLink(domain, path, level)
        self.db_session.add(link)
        self.blacklisted_links.append(link)
        return True

    def whitelist_url(self, url, parsed_url=None):
        if not (url.lower().startswith('http://') or url.lower().startswith('https://')):
            url = 'http://' + url
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        if self.is_whitelisted(url, parsed_url):
            return

        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()

        if domain.startswith('www.'):
            domain = domain[4:]
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '/'

        link = WhitelistedLink(domain, path)
        self.db_session.add(link)
        self.whitelisted_links.append(link)

    def is_blacklisted(self, url, parsed_url=None, sublink=False):
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        if path == '':
            path = '/'

        domain_split = domain.split('.')
        if len(domain_split) < 2:
            return False

        for link in self.blacklisted_links:
            if link.is_subdomain(domain):
                if link.is_subpath(path):
                    if not sublink:
                        return True
                    elif link.level >= 1:  # if it's a sublink, but the blacklisting level is 0, we don't consider it blacklisted
                        return True

        return False

    def is_whitelisted(self, url, parsed_url=None):
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        if path == '':
            path = '/'

        domain_split = domain.split('.')
        if len(domain_split) < 2:
            return False

        for link in self.whitelisted_links:
            if link.is_subdomain(domain):
                if link.is_subpath(path):
                    return True

        return False

    RET_BAD_LINK = -1
    RET_FURTHER_ANALYSIS = 0
    RET_GOOD_LINK = 1

    def basic_check(self, url, action, sublink=False):
        """
        Check if the url is in the cache, or if it's
        Return values:
        1 = Link is OK
        -1 = Link is bad
        0 = Link needs further analysis
        """
        if url.url in self.cache:
            log.debug('LinkChecker: Url {0} found in cache'.format(url.url))
            if not self.cache[url.url]:  # link is bad
                self.counteract_bad_url(url, action, False, False)
                return self.RET_BAD_LINK
            return self.RET_GOOD_LINK

        log.info('Checking if link is blacklisted...')
        if self.is_blacklisted(url.url, url.parsed, sublink):
            log.debug('LinkChecker: Url {0} is blacklisted'.format(url.url))
            self.counteract_bad_url(url, action, want_to_blacklist=False)
            return self.RET_BAD_LINK

        log.info('Checking if link is whitelisted...')
        if self.is_whitelisted(url.url, url.parsed):
            log.debug('LinkChecker: Url {0} allowed by the whitelist'.format(url.url))
            self.cache_url(url.url, True)
            return self.RET_GOOD_LINK

        return self.RET_FURTHER_ANALYSIS

    def simple_check(self, url, action):
        url = Url(url)
        if len(url.parsed.netloc.split('.')) < 2:
            # The URL is broken, ignore it
            return self.RET_FURTHER_ANALYSIS

        return self.basic_check(url, action)

    def check_url(self, url, action):
        url = Url(url)
        if len(url.parsed.netloc.split('.')) < 2:
            # The URL is broken, ignore it
            return

        try:
            self._check_url(url, action)
        except:
            log.exception('LinkChecker unhanled exception while _check_url')

    def _check_url(self, url, action):
        log.debug('LinkChecker: Checking url {0}'.format(url.url))

        # XXX: The basic check is currently performed twice on links found in messages. Solve
        res = self.basic_check(url, action)
        if res == self.RET_GOOD_LINK:
            return
        elif res == self.RET_BAD_LINK:
            return

        connection_timeout = 2
        read_timeout = 1
        try:
            r = requests.head(url.url, allow_redirects=True, timeout=connection_timeout)
        except:
            self.cache_url(url.url, True)
            return

        checkcontenttype = ('content-type' in r.headers and r.headers['content-type'] == 'application/octet-stream')
        checkdispotype = ('disposition-type' in r.headers and r.headers['disposition-type'] == 'attachment')

        if checkcontenttype or checkdispotype:  # triggering a download not allowed
            self.counteract_bad_url(url, action)
            return

        redirected_url = Url(r.url)
        if is_same_url(url, redirected_url) is False:
            res = self.basic_check(redirected_url, action)
            if res == self.RET_GOOD_LINK:
                return
            elif res == self.RET_BAD_LINK:
                return

        if self.safeBrowsingAPI:
            if self.safeBrowsingAPI.check_url(redirected_url.url):  # harmful url detected
                log.debug('Bad url because google api')
                self.counteract_bad_url(url, action, want_to_blacklist=False)
                self.counteract_bad_url(redirected_url, want_to_blacklist=False)
                return

        if 'content-type' not in r.headers or not r.headers['content-type'].startswith('text/html'):
            return  # can't analyze non-html content
        maximum_size = 1024 * 1024 * 10  # 10 MB
        receive_timeout = 3

        html = ''
        try:
            response = requests.get(url=url.url, stream=True, timeout=(connection_timeout, read_timeout))

            content_length = response.headers.get('Content-Length')
            if content_length and int(response.headers.get('Content-Length')) > maximum_size:
                log.error('This file is too big!')
                return

            size = 0
            start = time.time()

            for chunk in response.iter_content(1024):
                if time.time() - start > receive_timeout:
                    log.error('The site took too long to load')
                    return

                size += len(chunk)
                if size > maximum_size:
                    log.error('This file is too big! (fake header)')
                    return
                html += str(chunk)

        except requests.exceptions.ConnectTimeout:
            log.warning('Connection timed out while checking {0}'.format(url.url))
            self.cache_url(url.url, True)
            return
        except requests.exceptions.ReadTimeout:
            log.warning('Reading timed out while checking {0}'.format(url.url))
            self.cache_url(url.url, True)
            return
        except:
            log.exception('Unhandled exception')
            return

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except:
            return

        original_url = url
        original_redirected_url = redirected_url
        urls = []
        for link in soup.find_all('a'):  # get a list of links to external sites
            url = link.get('href')
            if url is None:
                continue
            if url.startswith('//'):
                urls.append('http:' + url)
            elif url.startswith('http://') or url.startswith('https://'):
                urls.append(url)

        for url in urls:  # check if the site links to anything dangerous
            url = Url(url)

            if is_subdomain(url.parsed.netloc, original_url.parsed.netloc):
                # log.debug('Skipping because internal link')
                continue

            log.debug('Checking sublink {0}'.format(url.url))
            res = self.basic_check(url, action, sublink=True)
            if res == self.RET_BAD_LINK:
                self.counteract_bad_url(url)
                self.counteract_bad_url(original_url, want_to_blacklist=False)
                self.counteract_bad_url(original_redirected_url, want_to_blacklist=False)
                return
            elif res == self.RET_GOOD_LINK:
                continue

            try:
                r = requests.head(url.url, allow_redirects=True, timeout=connection_timeout)
            except:
                continue

            redirected_url = Url(r.url)
            if not is_same_url(url, redirected_url):
                res = self.basic_check(redirected_url, action, sublink=True)
                if res == self.RET_BAD_LINK:
                    self.counteract_bad_url(url)
                    self.counteract_bad_url(original_url, want_to_blacklist=False)
                    self.counteract_bad_url(original_redirected_url, want_to_blacklist=False)
                    return
                elif res == self.RET_GOOD_LINK:
                    continue

            if self.safeBrowsingAPI:
                if self.safeBrowsingAPI.check_url(redirected_url.url):  # harmful url detected
                    log.debug('Evil sublink {0} by google API'.format(url))
                    self.counteract_bad_url(original_url, action)
                    self.counteract_bad_url(original_redirected_url)
                    self.counteract_bad_url(url)
                    self.counteract_bad_url(redirected_url)
                    return

        # if we got here, the site is clean for our standards
        self.cache_url(original_url.url, True)
        self.cache_url(original_redirected_url.url, True)
        return

    def load_commands(self, **options):
        self.commands['add'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='add',
                commands={
                    'link': Command.multiaction_command(
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        default=None,
                        commands={
                            'blacklist': Command.raw_command(self.add_link_blacklist,
                                level=500,
                                description='Blacklist a link',
                                examples=[
                                    CommandExample(None, 'Add a link to the blacklist for shallow search',
                                        chat='user:!add link blacklist 0 scamlink.lonk/\n'
                                        'bot>user:Successfully added your links',
                                        description='Added the link scamlink.lonk/ to the blacklist for a shallow search').parse(),
                                    CommandExample(None, 'Add a link to the blacklist for deep search',
                                        chat='user:!add link blacklist 1 scamlink.lonk/\n'
                                        'bot>user:Successfully added your links',
                                        description='Added the link scamlink.lonk/ to the blacklist for a deep search').parse(),
                                    ]),
                            'whitelist': Command.raw_command(self.add_link_whitelist,
                                level=500,
                                description='Whitelist a link',
                                examples=[
                                    CommandExample(None, 'Add a link to the whitelist',
                                        chat='user:!add link whitelink safelink.lonk/\n'
                                        'bot>user:Successfully added your links',
                                        description='Added the link safelink.lonk/ to the whitelist').parse(),
                                    ]),
                            }
                        )
                    }
                )

        self.commands['remove'] = Command.multiaction_command(
                level=100,
                delay_all=0,
                delay_user=0,
                default=None,
                command='remove',
                commands={
                    'link': Command.multiaction_command(
                        level=500,
                        delay_all=0,
                        delay_user=0,
                        default=None,
                        commands={
                            'blacklist': Command.raw_command(self.remove_link_blacklist,
                                level=500,
                                description='Unblacklist a link',
                                examples=[
                                    CommandExample(None, 'Remove a blacklist link',
                                        chat='user:!remove link blacklist scamtwitch.scam\n'
                                        'bot>user:Successfully removed your links',
                                        description='Removes scamtwitch.scam as a blacklisted link').parse(),
                                    ]),
                            'whitelist': Command.raw_command(self.remove_link_whitelist,
                                level=500,
                                description='Unwhitelist a link',
                                examples=[
                                    CommandExample(None, 'Remove a whitelist link',
                                        chat='user:!remove link whitelist twitch.safe\n'
                                        'bot>user:Successfully removed your links',
                                        description='Removes twitch.safe as a whitelisted link').parse(),
                                    ]),
                            }
                        ),
                    }
                )

    def add_link_blacklist(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        parts = message.split(' ')
        try:
            if not parts[0].isnumeric():
                for link in parts:
                    self.blacklist_url(link)
            else:
                for link in parts[1:]:
                    self.blacklist_url(link, level=int(parts[0]))
        except:
            log.exception('Unhandled exception in add_link')
            bot.whisper(source.username, 'Some error occurred white adding your links')
            return False

        bot.whisper(source.username, 'Successfully added your links')

    def add_link_whitelist(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        parts = message.split(' ')
        try:
            for link in parts:
                self.whitelist_url(link)
        except:
            log.exception('Unhandled exception in add_link')
            bot.whisper(source.username, 'Some error occurred white adding your links')
            return False

        bot.whisper(source.username, 'Successfully added your links')

    def remove_link_blacklist(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        parts = message.split(' ')
        try:
            for link in parts:
                self.unlist_url(link, 'blacklist')
        except:
            log.exception('Unhandled exception in add_link')
            bot.whisper(source.username, 'Some error occurred white adding your links')
            return False

        bot.whisper(source.username, 'Successfully removed your links')

    def remove_link_whitelist(self, **options):
        bot = options['bot']
        message = options['message']
        source = options['source']

        parts = message.split(' ')
        try:
            for link in parts:
                self.unlist_url(link, 'whitelist')
        except:
            log.exception('Unhandled exception in add_link')
            bot.whisper(source.username, 'Some error occurred white adding your links')
            return False

        bot.whisper(source.username, 'Successfully removed your links')
