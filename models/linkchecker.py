from bs4 import BeautifulSoup
from apiwrappers import SafeBrowsingAPI

import re
import requests
import logging
import pymysql
import time
import urllib.parse

log = logging.getLogger('tyggbot')

def is_subdomain(x, y): #is x a subdomain of y?
    if y.startswith('www.'):
        y = y[4:]
    return x.endswith('.' + y) or x == y

def is_subpath(x, y): #is x a subpath of y?
    if y.endswith('/'):
        return x.startswith(y) or x == y[:-1]
    else:
        return x.startswith(y + '/') or x == y

def is_same_url(x, y): # are x and y essentially the same urls
    parsed_x = x.parsed
    parsed_y = y.parsed
    return parsed_x.netloc == parsed_y.netloc and parsed_x.path.strip('/') == parsed_y.path.strip('/') and parsed_x.query == parsed_y.query

class Url:
    def __init__(self, url):
        self.url = url
        self.parsed = urllib.parse.urlparse(url)

class LinkCheckerCache:
    def __init__(self):
        self.cache = {}
        return

    def __getitem__(self, url):
        return self.cache[url.strip('/')]

    def __setitem__(self, url, safe):
        self.cache[url.strip('/')] = safe

    def __contains__(self, url):
        return url.strip('/') in self.cache

    def __delitem__(self, url):
        del self.cache[url.strip('/')]

class LinkChecker:

    def __init__(self, bot, run_later):
        if 'safebrowsingapi' in bot.config['main']:
            self.safeBrowsingAPI = SafeBrowsingAPI(bot.config['main']['safebrowsingapi'], bot.nickname, bot.version)
        else:
            self.safeBrowsingAPI = None

        self.sqlconn = bot.sqlconn

        self.regex = re.compile(r'((http:\/\/)|\b)(\w|\.)*\.(((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2})\/\S*)|((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2}))\b)')
        self.run_later = run_later
        self.cache = LinkCheckerCache()  # cache[url] = True means url is safe, False means the link is bad
        return

    def delete_from_cache(self, url):
        if url in self.cache:
            log.debug("LinkChecker: Removing url {0} from cache".format(url))
            del self.cache[url]

    def cache_url(self, url, safe):
        if url in self.cache and self.cache[url] == safe:
            return

        log.debug("LinkChecker: Caching url {0}".format(url))
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

    def blacklist_url(self, url, parsed_url = None):
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url

        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)

        if self.is_blacklisted(url, parsed_url):
            return

        self.sqlconn.ping()
        cursor = self.sqlconn.cursor()
        domain = parsed_url.netloc
        path = parsed_url.path

        if domain.startswith('www.'):
            domain = domain[4:]
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '/'

        cursor.execute("INSERT INTO `tb_link_blacklist` VALUES(%s, %s)", (domain, path))

    def whitelist_url(self, url, parsed_url = None):
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        if self.is_whitelisted(url, parsed_url):
            return

        self.sqlconn.ping()
        cursor = self.sqlconn.cursor()
        domain = parsed_url.netloc
        path = parsed_url.path

        if domain.startswith('www.'):
            domain = domain[4:]
        if path.endswith('/'):
            path = path[:-1]
        if path == '':
            path = '/'

        cursor.execute("INSERT INTO `tb_link_whitelist` VALUES(%s, %s)", (domain, path))

    def is_blacklisted(self, url, parsed_url = None):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        if path == '':
            path = '/'

        domain_split = domain.split('.')
        if len(domain_split) < 2:
            return False

        domain_tail = '.' + domain_split[-2] + '.' + domain_split[-1]
        cursor.execute("SELECT * FROM `tb_link_blacklist` WHERE `domain` LIKE %s OR `domain`=%s", ('%' + domain_tail, domain))
        for row in cursor:
            if is_subdomain(domain, row['domain']):
                if is_subpath(path, row['path']):
                    return True

        return False

    def is_whitelisted(self, url, parsed_url = None):
        cursor = self.sqlconn.cursor(pymysql.cursors.DictCursor)
        if parsed_url is None:        
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        if path == '':
            path = '/'

        domain_split = domain.split('.')
        if len(domain_split) < 2:
            return

        domain_tail = '.' + domain_split[-2] + '.' + domain_split[-1]
        cursor.execute("SELECT * FROM `tb_link_whitelist` WHERE `domain` LIKE %s OR `domain`=%s", ('%' + domain_tail, domain))
        for row in cursor:
            if is_subdomain(domain, row['domain']):
                if is_subpath(path, row['path']):
                    return True

        return False

    def basic_check(self, url, action): # 1 means link is ok, -1 means link is bad, 0 means further analysis needed
        if url.url in self.cache:
            log.debug("LinkChecker: Url {0} found in cache".format(url.url))
            if not self.cache[url]:  # link is bad
                self.counteract_bad_url(url, action, False)
                return -1
            return 1

        if self.is_whitelisted(url.url, url.parsed):
            log.debug("LinkChecker: Url {0} allowed by the whitelist".format(url.url))
            self.cache_url(url.url, True)
            return 1

        if self.is_blacklisted(url.url, url.parsed):
            log.debug("LinkChecker: Url {0} is blacklisted".format(url.url))
            self.counteract_bad_url(url, action, want_to_blacklist=False)
            return -1

        return 0

    def check_url(self, url, action):
        url = Url(url)
        if len(url.parsed.netloc.split('.')) < 2:
            return # shit url

        try:
            self._check_url(url, action)
        except:
            log.exception("LinkChecker unhanled exception while _check_url")

    def _check_url(self, url, action):
        self.sqlconn.ping()
        log.debug("LinkChecker: Checking url {0}".format(url.url))

        if self.basic_check(url, action):
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
        if not is_same_url(url, redirected_url):
            if self.basic_check(redirected_url, action):
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
            log.error('Connection timed out while checking {0}'.format(url.url))
            self.cache_url(url.url, True)
            return
        except requests.exceptions.ReadTimeout:
            log.error('Reading timed out while checking {0}'.format(url.url))
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
            log.debug("Checking sublink {0}".format(url))
            url = Url(url)

            if is_subdomain(url.parsed.netloc, original_url.parsed.netloc):
                #log.debug("Skipping because internal link")
                continue
            res = self.basic_check(url, action)
            if res == -1:
                return
            elif res == 1:
                continue

            try:
                r = requests.head(url.url, allow_redirects=True, timeout=connection_timeout)
            except:
                continue

            redirected_url = Url(r.url)
            if not is_same_url(url, redirected_url):
                res = self.basic_check(redirected_url, action)
                if res == -1:
                    self.counteract_bad_url(url, want_to_blacklist=False)
                    self.counteract_bad_url(original_url)
                    self.counteract_bad_url(original_redirected_url)
                    return
                elif res == 1:
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
        _urls = self.regex.finditer(msg_raw)
        urls = []
        for i in _urls:
            url = i.group(0)
            if not (url.startswith('http://') or url.startswith('https://')):
                url = 'http://' + url
            if not(url[-1].isalpha() or url[-1].isnumeric() or url[-1] == '/'):
                url = url[:-1]
            urls.append(url)

        return set(urls)
