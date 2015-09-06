from bs4 import BeautifulSoup
from apiwrappers import SafeBrowsingAPI

import re
import requests
import logging
import time

log = logging.getLogger('tyggbot')


class LinkChecker:
    def __init__(self, bot, run_later):
        if 'safebrowsingapi' in bot.config['main']:
            self.safeBrowsingAPI = SafeBrowsingAPI(bot.config['main']['safebrowsingapi'], bot.nickname, bot.version)
        else:
            self.safeBrowsingAPI = None

        self.regex = re.compile(r'((http:\/\/)|\b)(\w|\.)*\.(((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2})\/\S*)|(aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2}))')
        self.run_later = run_later
        self.cache = {}  # cache[url] = True means url is safe, False means the link is bad
        return

    def delete_from_cache(self, url):
        log.debug("LinkChecker: Removing url {0} from cache".format(url))
        del self.cache[url]

    def cache_url(self, url, safe):
        log.debug("LinkChecker: Caching url {0}".format(url))
        self.cache[url] = safe
        self.run_later(20, self.delete_from_cache, (url, ))

    def counteract_bad_url(self, url, action=None, want_to_cache=True):
        log.debug("LinkChecker: BAD URL FOUND {0}".format(url))
        if action:
            action.run()
        if want_to_cache:
            self.cache_url(url, False)

    def check_url(self, url, action):
        log.debug("LinkChecker: Checking url {0}".format(url))
        if url in self.cache:
            log.debug("LinkChecker: Url {0} found in cache".format(url))
            if not self.cache[url]:  # link is bad
                self.counteract_bad_url(url, action, False)
            return

        if self.safeBrowsingAPI:
            if self.safeBrowsingAPI.check_url(url):  # harmful url detected
                self.counteract_bad_url(url, action)
                return

        connection_timeout = 2
        read_timeout = 1

        try:
            r = requests.head(url, allow_redirects=True, timeout=connection_timeout)
        except:
            return

        checkcontenttype = ('content-type' in r.headers and r.headers['content-type'] == 'application/octet-stream')
        checkdispotype = ('disposition-type' in r.headers and r.headers['disposition-type'] == 'attachment')

        if checkcontenttype or checkdispotype:  # triggering a download not allowed
            self.counteract_bad_url(url, action)
            return

        if 'content-type' not in r.headers or not r.headers['content-type'].startswith('text/html'):
            return  # can't analyze non-html content

        maximum_size = 1024 * 1024 * 10  # 10 MB
        receive_timeout = 3

        html = ''
        try:
            response = requests.get(url=url, stream=True, timeout=(connection_timeout, read_timeout))

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
            log.error('Connection timed out while checking {0}'.format(url))
            self.cache_url(url, True)
            return
        except requests.exceptions.ReadTimeout:
            log.error('Reading timed out while checking {0}'.format(url))
            self.cache_url(url, True)
            return
        except:
            log.exception('Unhandled exception')
            return

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except:
            return

        original_url = url
        urls = []
        for link in soup.find_all('a'):  # get a list of links to external sites
            url = link.get('href')
            if url is None:
                continue
            if url.startswith('http://') or url.startswith('https://'):
                urls.append(url)

        for url in urls:  # check if the site links to anything dangerous
            if self.safeBrowsingAPI:
                if self.safeBrowsingAPI.check_url(url):  # harmful url detected
                    self.counteract_bad_url(original_url, action)
                    self.counteract_bad_url(url)
                    return

        # if we got here, the site is clean for our standards
        self.cache_url(original_url, True)
        return

    def findUrlsInMessage(self, msg_raw):

        _urls = self.regex.finditer(msg_raw)
        urls = []
        for i in _urls:
            url = i.group(0)
            if not (url.startswith('http://') or url.startswith('https://')):
                url = 'https://' + url
            urls.append(url)

        return urls
