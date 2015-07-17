from actions import Action, ActionQueue
from bs4 import BeautifulSoup

class LinkChecker:
    def __init__(self):
        return

    def check_url(self, url, action):
        if self.safeBrowsingAPI:
            if self.safeBrowsingAPI.check_url(url): # harmful url detected
                action.f(*action.args, **action.kwargs) # execute the specified action
                return
                
        try: r = requests.get(url)
        except: return
        
        soup = BeautifulSoup(r.text, 'html.parser')
        urls = []
        for link in soup.find_all('a'): # get a list of links to external sites
            url = link.get('href')
            if url.startswith('http://') or url.startswith('https://')
            urls.append(url)

        for url in urls: # check if the site links to anything dangerous
            if self.safeBrowsingAPI:
                if self.safeBrowsingAPI.check_url(url): # harmful url detected
                    action.f(*action.args, **action.kwargs) # execute the specified action
                    return           

        #if we got here, the site is clean for our standards            

        return

    def findUrlsInMessage(self, msg_raw):
        regex = r'((http:\/\/)|\b)(\w|\.)*\.(((aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2})\/\S*)|(aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel|[a-zA-Z]{2}))'

        _urls = re.finditer(regex, msg_raw)
        urls = []
        for i in _urls:
            url = i.group(0)
            if not (url.startswith('http://') or url.startswith('https://')): url = 'https://' + url             
            urls.append(url)

        return urls
