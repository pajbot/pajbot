from actions import Action, ActionQueue
from bs4 import BeautifulSoup
from apiwrappers import SafeBrowsingAPI
from tbutil import time_limit

import re
import requests
import logging
import os
import time

log = logging.getLogger('tyggbot') 

class LinkChecker:
    def __init__(self, bot):
        if 'safebrowsingapi' in bot.config['main']:
            self.safeBrowsingAPI = SafeBrowsingAPI(bot.config['main']['safebrowsingapi'], bot.nickname, bot.version)
        else:
            self.safeBrowsingAPI = None

        self.regex = re.compile(r'((http:\/\/)|\b)(\w|\.)*\.(((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2})\/\S*)|(aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2}))')
        return

    def check_url(self, url, action):
        if self.safeBrowsingAPI:
            if self.safeBrowsingAPI.check_url(url): # harmful url detected
                action.func(*action.args, **action.kwargs) # execute the specified action
                return

        connection_timeout = 2
        read_timeout = 1

        try: r = requests.head(url, allow_redirects=True, timeout=connection_timeout)
        except: return

        checkcontenttype = ('content-type' in r.headers and r.headers['content-type'] == 'application/octet-stream')
        checkdispotype = ('disposition-type' in r.headers and r.headers['disposition-type'] == 'attachment')

        if checkcontenttype or checkdispotype: # triggering a download not allowed
            action.func(*action.args, **action.kwargs)

        if 'content-type' not in r.headers or not r.headers['content-type'].startswith('text/html'):
            return # can't analyze non-html content

        maximum_size = 1024*1024*10 #10 MB
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
     
        except requests.exceptions.ConnectTimeout as e:
            log.error('Connection timed out while checking {0}'.format(url))
            return
        except requests.exceptions.ReadTimeout as e:
            log.error('Reading timed out while checking {0}'.format(url))
        except:
            log.exception('Unhandled exception')
            return

        try: soup = BeautifulSoup(html, 'html.parser')
        except: return

        urls = []
        for link in soup.find_all('a'): # get a list of links to external sites
            url = link.get('href')
            if url is None:
                continue
            if url.startswith('http://') or url.startswith('https://'):
                urls.append(url)

        for url in urls: # check if the site links to anything dangerous
            if self.safeBrowsingAPI:
                if self.safeBrowsingAPI.check_url(url): # harmful url detected
                    action.func(*action.args, **action.kwargs) # execute the specified action
                    return           

        #if we got here, the site is clean for our standards            

        return

    def findUrlsInMessage(self, msg_raw):

        _urls = self.regex.finditer(msg_raw)
        urls = []
        for i in _urls:
            url = i.group(0)
            if not (url.startswith('http://') or url.startswith('https://')): url = 'https://' + url             
            urls.append(url)

        return urls
