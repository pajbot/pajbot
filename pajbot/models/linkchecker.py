from bs4 import BeautifulSoup
from pajbot.apiwrappers import SafeBrowsingAPI

from pajbot.models.db import DBManager, Base

import re
import requests
import logging
import time
import urllib.parse
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import TEXT

log = logging.getLogger('pajbot')


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


class LinkChecker:
    regex_str = r'((http:\/\/)|\b)([\w-]|\.)*\.(((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2})\/\S*)|((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2}))\b)'

    def reload(self):
        self.blacklisted_links = []
        for link in self.db_session.query(BlacklistedLink):
            self.blacklisted_links.append(link)

        self.whitelisted_links = []
        for link in self.db_session.query(WhitelistedLink):
            self.whitelisted_links.append(link)

        log.info('Loaded {0} bad links and {1} good links'.format(len(self.blacklisted_links), len(self.whitelisted_links)))
        return self

    def commit(self):
        self.db_session.commit()

    def __init__(self, bot, run_later):
        self.db_session = DBManager.create_session()

        self.blacklisted_links = []
        self.whitelisted_links = []

        if 'safebrowsingapi' in bot.config['main']:
            self.safeBrowsingAPI = SafeBrowsingAPI(bot.config['main']['safebrowsingapi'], bot.nickname, bot.version)
        else:
            self.safeBrowsingAPI = None

        self.regex = re.compile(LinkChecker.regex_str, re.IGNORECASE)
        self.run_later = run_later
        self.cache = LinkCheckerCache()  # cache[url] = True means url is safe, False means the link is bad

    def delete_from_cache(self, url):
        if url in self.cache:
            log.debug("LinkChecker: Removing url {0} from cache".format(url))
            del self.cache[url]

    def cache_url(self, url, safe):
        if url in self.cache and self.cache[url] == safe:
            return

        log.debug("LinkChecker: Caching url {0} as {1}".format(url, 'SAFE' if safe is True else 'UNSAFE'))
        self.cache[url] = safe
        self.run_later(20, self.delete_from_cache, (url, ))

    def counteract_bad_url(self, url, action=None, want_to_cache=True, want_to_blacklist=True):
        log.debug("LinkChecker: BAD URL FOUND {0}".format(url.url))
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
            log.debug("LinkChecker: Url {0} found in cache".format(url.url))
            if not self.cache[url.url]:  # link is bad
                self.counteract_bad_url(url, action, False, False)
                return self.RET_BAD_LINK
            return self.RET_GOOD_LINK

        if self.is_whitelisted(url.url, url.parsed):
            log.debug("LinkChecker: Url {0} allowed by the whitelist".format(url.url))
            self.cache_url(url.url, True)
            return self.RET_GOOD_LINK

        if self.is_blacklisted(url.url, url.parsed, sublink):
            log.debug("LinkChecker: Url {0} is blacklisted".format(url.url))
            self.counteract_bad_url(url, action, want_to_blacklist=False)
            return self.RET_BAD_LINK

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
            log.exception("LinkChecker unhanled exception while _check_url")

    def _check_url(self, url, action):
        log.debug("LinkChecker: Checking url {0}".format(url.url))

        # XXX: The basic check is currently performed twice on links found in messages. Solve
        res = self.basic_check(url, action)
        if res == LinkChecker.RET_GOOD_LINK:
            return
        elif res == LinkChecker.RET_BAD_LINK:
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
            if res == LinkChecker.RET_GOOD_LINK:
                return
            elif res == LinkChecker.RET_BAD_LINK:
                return

        if self.safeBrowsingAPI:
            if self.safeBrowsingAPI.check_url(redirected_url.url):  # harmful url detected
                log.debug("Bad url because google api")
                self.counteract_bad_url(url, action)
                self.counteract_bad_url(redirected_url)
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
                # log.debug("Skipping because internal link")
                continue

            log.debug("Checking sublink {0}".format(url.url))
            res = self.basic_check(url, action, sublink=True)
            if res == LinkChecker.RET_BAD_LINK:
                self.counteract_bad_url(url)
                self.counteract_bad_url(original_url, want_to_blacklist=False)
                self.counteract_bad_url(original_redirected_url, want_to_blacklist=False)
                return
            elif res == LinkChecker.RET_GOOD_LINK:
                continue

            try:
                r = requests.head(url.url, allow_redirects=True, timeout=connection_timeout)
            except:
                continue

            redirected_url = Url(r.url)
            if not is_same_url(url, redirected_url):
                res = self.basic_check(redirected_url, action, sublink=True)
                if res == LinkChecker.RET_BAD_LINK:
                    self.counteract_bad_url(url)
                    self.counteract_bad_url(original_url, want_to_blacklist=False)
                    self.counteract_bad_url(original_redirected_url, want_to_blacklist=False)
                    return
                elif res == LinkChecker.RET_GOOD_LINK:
                    continue

            if self.safeBrowsingAPI:
                if self.safeBrowsingAPI.check_url(redirected_url.url):  # harmful url detected
                    log.debug("Evil sublink {0} by google API".format(url))
                    self.counteract_bad_url(original_url, action)
                    self.counteract_bad_url(original_redirected_url)
                    self.counteract_bad_url(url)
                    self.counteract_bad_url(redirected_url)
                    return

        # if we got here, the site is clean for our standards
        self.cache_url(original_url.url, True)
        self.cache_url(original_redirected_url.url, True)
        return

    def find_urls_in_message(self, msg_raw):
        return find_unique_urls(self.regex, msg_raw)
