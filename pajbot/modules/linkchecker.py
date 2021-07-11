import argparse
import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import Column, INT, TEXT
from urlextract import URLExtract

import pajbot.managers
import pajbot.models
import pajbot.utils
from pajbot.apiwrappers.safebrowsing import SafeBrowsingAPI
from pajbot.managers.adminlog import AdminLogManager
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.managers.handler import HandlerManager
from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule
from pajbot.modules import ModuleSetting

log = logging.getLogger(__name__)


extractor = URLExtract()
extractor.update_when_older(14)


def is_subdomain(x, y):
    """Returns True if x is a subdomain of y, otherwise return False.

    Example:
    is_subdomain('pajlada.se', 'pajlada.se') = True
    is_subdomain('test.pajlada.se', 'pajlada.se') = True
    is_subdomain('test.pajlada.se', 'pajlada.com') = False
    """
    if y.startswith("www."):
        y = y[4:]
    return x.endswith("." + y) or x == y


def is_subpath(x, y):
    """Returns True if x is a subpath of y, otherwise return False.

    Example:
    is_subpath('/a/', '/b/') = False
    is_subpath('/a/', '/a/') = True
    is_subpath('/a/abc', '/a/') = True
    is_subpath('/a/', '/a/abc') = False
    """
    if y.endswith("/"):
        return x.startswith(y) or x == y[:-1]

    return x.startswith(y + "/") or x == y


def is_same_url(x, y):
    """Returns True if x and y should be parsed as the same URLs, otherwise return False."""
    parsed_x = x.parsed
    parsed_y = y.parsed
    return (
        parsed_x.netloc == parsed_y.netloc
        and parsed_x.path.strip("/") == parsed_y.path.strip("/")
        and parsed_x.query == parsed_y.query
    )


def find_unique_urls(message):
    urls = []
    for url in extractor.gen_urls(message):
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url
        if not (url[-1].isalpha() or url[-1].isnumeric() or url[-1] == "/"):
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
        return self.cache[url.strip("/").lower()]

    def __setitem__(self, url, safe):
        self.cache[url.strip("/").lower()] = safe

    def __contains__(self, url):
        return url.strip("/").lower() in self.cache

    def __delitem__(self, url):
        del self.cache[url.strip("/").lower()]


class LinkCheckerLink:
    def is_subdomain(self, x):
        """Returns True if x is a subdomain of this link, otherwise return False."""
        y = self.domain
        if y.startswith("www."):
            y = y[4:]
        return x.endswith("." + y) or x == y

    def is_subpath(self, x):
        """Returns True if x is a subpath of y, otherwise return False."""
        y = self.path
        if y.endswith("/"):
            return x.startswith(y) or x == y[:-1]

        return x.startswith(y + "/") or x == y


class BlacklistedLink(Base, LinkCheckerLink):
    __tablename__ = "link_blacklist"

    id = Column(INT, primary_key=True)
    domain = Column(TEXT)
    path = Column(TEXT)
    level = Column(INT)

    def __init__(self, domain, path, level):
        self.id = None
        self.domain = domain
        self.path = path
        self.level = level


class WhitelistedLink(LinkCheckerLink, Base):
    __tablename__ = "link_whitelist"

    id = Column(INT, primary_key=True)
    domain = Column(TEXT)
    path = Column(TEXT)

    def __init__(self, domain, path):
        self.id = None
        self.domain = domain
        self.path = path


class LinkCheckerModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Link Checker"
    DESCRIPTION = "Checks links if they're bad"
    ENABLED_DEFAULT = True
    CATEGORY = "Moderation"
    SETTINGS = [
        ModuleSetting(
            key="ban_pleb_links",
            label="Disallow links from non-subscribers",
            type="boolean",
            required=True,
            default=False,
        ),
        ModuleSetting(
            key="ban_sub_links", label="Disallow links from subscribers", type="boolean", required=True, default=False
        ),
        ModuleSetting(key="vip_exemption", label="Allow links from VIPs", type="boolean", required=True, default=False),
        ModuleSetting(
            key="timeout_length",
            label="Timeout length",
            type="number",
            required=True,
            placeholder="Timeout length in seconds",
            default=60,
            constraints={"min_value": 1, "max_value": 1209600},
        ),
        ModuleSetting(
            key="bypass_level",
            label="Level to bypass module",
            type="number",
            required=True,
            placeholder="",
            default=500,
            constraints={"min_value": 100, "max_value": 1000},
        ),
        ModuleSetting(
            key="banned_link_timeout_reason",
            label="Banned Link Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="You have been timed out for posting a banned link in chat",
            constraints={},
        ),
        ModuleSetting(
            key="pleb_timeout_reason",
            label="Pleb Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="You cannot post non-verified links in chat if you're a pleb",
            constraints={},
        ),
        ModuleSetting(
            key="sub_timeout_reason",
            label="Subscriber Timeout Reason",
            type="text",
            required=False,
            placeholder="",
            default="You cannot post non-verified links in chat if you're a subscriber",
            constraints={},
        ),
    ]

    def __init__(self, bot):
        super().__init__(bot)
        self.db_session = None
        self.links = {}

        self.blacklisted_links = []
        self.whitelisted_links = []

        self.cache = LinkCheckerCache()  # cache[url] = True means url is safe, False means the link is bad

        if bot and "safebrowsingapi" in bot.config["main"]:
            # XXX: This should be loaded as a setting instead.
            # There needs to be a setting for settings to have them as "passwords"
            # so they're not displayed openly
            self.safe_browsing_api = SafeBrowsingAPI(bot.config["main"]["safebrowsingapi"])
        else:
            self.safe_browsing_api = None

    def enable(self, bot):
        if not bot:
            return

        HandlerManager.add_handler("on_message", self.on_message, priority=150, run_if_propagation_stopped=True)
        HandlerManager.add_handler("on_commit", self.on_commit)

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
        if not bot:
            return

        pajbot.managers.handler.HandlerManager.remove_handler("on_message", self.on_message)
        pajbot.managers.handler.HandlerManager.remove_handler("on_commit", self.on_commit)

        if self.db_session is not None:
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
            self.blacklisted_links = []
            self.whitelisted_links = []

    def reload(self):

        log.info(f"Loaded {len(self.blacklisted_links)} bad links and {len(self.whitelisted_links)} good links")
        return self

    super_whitelist = ["pajlada.se", "pajlada.com", "forsen.tv", "pajbot.com"]

    def on_message(self, source, whisper, urls, **rest):
        if whisper:
            return

        if source.level >= self.settings["bypass_level"] or source.moderator is True:
            return

        if self.settings["vip_exemption"] and source.vip is True:
            return

        if len(urls) > 0:
            do_timeout = False
            ban_reason = "You are not allowed to post links in chat"

            if self.settings["ban_pleb_links"] is True and source.subscriber is False:
                do_timeout = True
                ban_reason = self.settings["pleb_timeout_reason"]
            elif self.settings["ban_sub_links"] is True and source.subscriber is True:
                do_timeout = True
                ban_reason = self.settings["sub_timeout_reason"]

            if do_timeout is True:
                # Check if the links are in our super-whitelist. i.e. on the pajlada.se domain o forsen.tv
                for url in urls:
                    parsed_url = Url(url)
                    if len(parsed_url.parsed.netloc.split(".")) < 2:
                        continue
                    whitelisted = False
                    for whitelist in self.super_whitelist:
                        if is_subdomain(parsed_url.parsed.netloc, whitelist):
                            whitelisted = True
                            break

                    if whitelisted is False and self.is_whitelisted(url):
                        whitelisted = True

                    if whitelisted is False:
                        self.bot.timeout(source, self.settings["timeout_length"], reason=ban_reason)
                        return False

        for url in urls:
            # Action which will be taken when a bad link is found
            def action():
                self.bot.timeout(
                    source, self.settings["timeout_length"], reason=self.settings["banned_link_timeout_reason"]
                )

            # First we perform a basic check
            if self.simple_check(url, action) == self.RET_FURTHER_ANALYSIS:
                # If the basic check returns no relevant data, we queue up a proper check on the URL
                self.bot.action_queue.submit(self.check_url, url, action)

    def on_commit(self, **rest):
        if self.db_session is not None:
            self.db_session.commit()

    def delete_from_cache(self, url):
        if url in self.cache:
            del self.cache[url]

    def cache_url(self, url, safe):
        if url in self.cache and self.cache[url] == safe:
            return

        self.cache[url] = safe
        self.bot.execute_delayed(20, self.delete_from_cache, url)

    def counteract_bad_url(self, url, action=None, want_to_cache=True, want_to_blacklist=False):
        log.debug(f"LinkChecker: BAD URL FOUND {url.url}")
        if action:
            action()
        if want_to_cache:
            self.cache_url(url.url, False)
        if want_to_blacklist:
            self.blacklist_url(url.url, url.parsed)
            return True

    def blacklist_url(self, url, parsed_url=None, level=0):
        if not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            url = "http://" + url

        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)

        if self.is_blacklisted(url, parsed_url):
            return False

        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()

        if domain.startswith("www."):
            domain = domain[4:]
        if path.endswith("/"):
            path = path[:-1]
        if path == "":
            path = "/"

        link = BlacklistedLink(domain, path, level)
        self.db_session.add(link)
        self.blacklisted_links.append(link)
        self.db_session.commit()

    def whitelist_url(self, url, parsed_url=None):
        if not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            url = "http://" + url
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        if self.is_whitelisted(url, parsed_url):
            return

        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()

        if domain.startswith("www."):
            domain = domain[4:]
        if path.endswith("/"):
            path = path[:-1]
        if path == "":
            path = "/"

        link = WhitelistedLink(domain, path)
        self.db_session.add(link)
        self.whitelisted_links.append(link)
        self.db_session.commit()

    def is_blacklisted(self, url, parsed_url=None, sublink=False):
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        if path == "":
            path = "/"

        domain_split = domain.split(".")
        if len(domain_split) < 2:
            return False

        for link in self.blacklisted_links:
            if link.is_subdomain(domain):
                if link.is_subpath(path):
                    if not sublink:
                        return True

                    # if it's a sublink, but the blacklisting level is 0, we don't consider it blacklisted
                    if link.level >= 1:
                        return True

        return False

    def is_whitelisted(self, url, parsed_url=None):
        if parsed_url is None:
            parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        if path == "":
            path = "/"

        domain_split = domain.split(".")
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
            if not self.cache[url.url]:  # link is bad
                self.counteract_bad_url(url, action, False, False)
                return self.RET_BAD_LINK

            return self.RET_GOOD_LINK

        if self.is_blacklisted(url.url, url.parsed, sublink):
            self.counteract_bad_url(url, action, want_to_blacklist=False)
            return self.RET_BAD_LINK

        if self.is_whitelisted(url.url, url.parsed):
            self.cache_url(url.url, True)
            return self.RET_GOOD_LINK

        return self.RET_FURTHER_ANALYSIS

    def simple_check(self, url, action):
        url = Url(url)
        if len(url.parsed.netloc.split(".")) < 2:
            # The URL is broken, ignore it
            return self.RET_FURTHER_ANALYSIS

        return self.basic_check(url, action)

    def check_url(self, url, action):
        url = Url(url)
        if len(url.parsed.netloc.split(".")) < 2:
            # The URL is broken, ignore it
            return

        try:
            self._check_url(url, action)
        except:
            log.exception("LinkChecker unhandled exception while _check_url")

    def _check_url(self, url, action):
        # XXX: The basic check is currently performed twice on links found in messages. Solve
        res = self.basic_check(url, action)
        if res == self.RET_GOOD_LINK:
            return
        elif res == self.RET_BAD_LINK:
            return

        connection_timeout = 2
        read_timeout = 1
        try:
            r = requests.head(
                url.url, allow_redirects=True, timeout=connection_timeout, headers={"User-Agent": self.bot.user_agent}
            )
        except:
            self.cache_url(url.url, True)
            return

        checkcontenttype = "content-type" in r.headers and r.headers["content-type"] == "application/octet-stream"
        checkdispotype = "disposition-type" in r.headers and r.headers["disposition-type"] == "attachment"

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

        if self.safe_browsing_api and self.safe_browsing_api.is_url_bad(redirected_url.url):  # harmful url detected
            log.debug("Google Safe Browsing API lists URL")
            self.counteract_bad_url(url, action, want_to_blacklist=False)
            self.counteract_bad_url(redirected_url, want_to_blacklist=False)
            return

        if "content-type" not in r.headers or not r.headers["content-type"].startswith("text/html"):
            return  # can't analyze non-html content
        maximum_size = 1024 * 1024 * 10  # 10 MB
        receive_timeout = 3

        html = ""
        try:
            response = requests.get(
                url=url.url,
                stream=True,
                timeout=(connection_timeout, read_timeout),
                headers={"User-Agent": self.bot.user_agent},
            )

            content_length = response.headers.get("Content-Length")
            if content_length and int(response.headers.get("Content-Length")) > maximum_size:
                log.error("This file is too big!")
                return

            size = 0
            start = pajbot.utils.now().timestamp()

            for chunk in response.iter_content(1024):
                if pajbot.utils.now().timestamp() - start > receive_timeout:
                    log.error("The site took too long to load")
                    return

                size += len(chunk)
                if size > maximum_size:
                    log.error("This file is too big! (fake header)")
                    return
                html += str(chunk)

        except requests.exceptions.ConnectTimeout:
            log.warning(f"Connection timed out while checking {url.url}")
            self.cache_url(url.url, True)
            return
        except requests.exceptions.ReadTimeout:
            log.warning(f"Reading timed out while checking {url.url}")
            self.cache_url(url.url, True)
            return
        except:
            log.exception("Unhandled exception")
            return

        try:
            soup = BeautifulSoup(html, "html.parser")
        except:
            return

        original_url = url
        original_redirected_url = redirected_url
        urls = []
        for link in soup.find_all("a"):  # get a list of links to external sites
            url = link.get("href")
            if url is None:
                continue
            if url.startswith("//"):
                urls.append("http:" + url)
            elif url.startswith("http://") or url.startswith("https://"):
                urls.append(url)

        for url in urls:  # check if the site links to anything dangerous
            url = Url(url)

            if is_subdomain(url.parsed.netloc, original_url.parsed.netloc):
                # log.debug('Skipping because internal link')
                continue

            res = self.basic_check(url, action, sublink=True)
            if res == self.RET_BAD_LINK:
                self.counteract_bad_url(url)
                self.counteract_bad_url(original_url, want_to_blacklist=False)
                self.counteract_bad_url(original_redirected_url, want_to_blacklist=False)
                return
            elif res == self.RET_GOOD_LINK:
                continue

            try:
                r = requests.head(
                    url.url,
                    allow_redirects=True,
                    timeout=connection_timeout,
                    headers={"User-Agent": self.bot.user_agent},
                )
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

            if self.safe_browsing_api and self.safe_browsing_api.is_url_bad(redirected_url.url):  # harmful url detected
                log.debug(f"Evil sublink {url} by google API")
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
        self.commands["add"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="add",
            commands={
                "link": Command.multiaction_command(
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    default=None,
                    commands={
                        "blacklist": Command.raw_command(
                            self.add_link_blacklist,
                            level=500,
                            delay_all=0,
                            delay_user=0,
                            description="Blacklist a link",
                            examples=[
                                CommandExample(
                                    None,
                                    "Add a link to the blacklist for a shallow search",
                                    chat="user:!add link blacklist --shallow scamlink.lonk/\n"
                                    "bot>user:Successfully added your links",
                                    description="Added the link scamlink.lonk/ to the blacklist for a shallow search",
                                ).parse(),
                                CommandExample(
                                    None,
                                    "Add a link to the blacklist for a deep search",
                                    chat="user:!add link blacklist --deep scamlink.lonk/\n"
                                    "bot>user:Successfully added your links",
                                    description="Added the link scamlink.lonk/ to the blacklist for a deep search",
                                ).parse(),
                            ],
                        ),
                        "whitelist": Command.raw_command(
                            self.add_link_whitelist,
                            level=500,
                            delay_all=0,
                            delay_user=0,
                            description="Whitelist a link",
                            examples=[
                                CommandExample(
                                    None,
                                    "Add a link to the whitelist",
                                    chat="user:!add link whitelink safelink.lonk/\n"
                                    "bot>user:Successfully added your links",
                                    description="Added the link safelink.lonk/ to the whitelist",
                                ).parse()
                            ],
                        ),
                    },
                )
            },
        )

        self.commands["remove"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="remove",
            commands={
                "link": Command.multiaction_command(
                    level=500,
                    delay_all=0,
                    delay_user=0,
                    default=None,
                    commands={
                        "blacklist": Command.raw_command(
                            self.remove_link_blacklist,
                            level=500,
                            delay_all=0,
                            delay_user=0,
                            description="Remove a link from the blacklist.",
                            examples=[
                                CommandExample(
                                    None,
                                    "Remove a link from the blacklist.",
                                    chat="user:!remove link blacklist 20\n"
                                    "bot>user:Successfully removed blacklisted link with id 20",
                                    description="Remove a link from the blacklist with an ID",
                                ).parse()
                            ],
                        ),
                        "whitelist": Command.raw_command(
                            self.remove_link_whitelist,
                            level=500,
                            delay_all=0,
                            delay_user=0,
                            description="Remove a link from the whitelist.",
                            examples=[
                                CommandExample(
                                    None,
                                    "Remove a link from the whitelist.",
                                    chat="user:!remove link whitelist 12\n"
                                    "bot>user:Successfully removed blacklisted link with id 12",
                                    description="Remove a link from the whitelist with an ID",
                                ).parse()
                            ],
                        ),
                    },
                )
            },
        )

    def add_link_blacklist(self, bot, source, message, **rest):
        options, new_links = self.parse_link_blacklist_arguments(message)

        if new_links:
            parts = new_links.split(" ")
            try:
                for link in parts:
                    if len(link) > 1:
                        self.blacklist_url(link, **options)
                        AdminLogManager.post("Blacklist link added", source, link)
                bot.whisper(source, "Successfully added your links")
                return True
            except:
                log.exception("Unhandled exception in add_link_blacklist")
                bot.whisper(source, "Some error occurred while adding your links")
                return False
        else:
            bot.whisper(source, "Usage: !add link blacklist LINK")
            return False

    def add_link_whitelist(self, bot, source, message, **rest):
        parts = message.split(" ")
        try:
            for link in parts:
                self.whitelist_url(link)
                AdminLogManager.post("Whitelist link added", source, link)
        except:
            log.exception("Unhandled exception in add_link")
            bot.whisper(source, "Some error occurred white adding your links")
            return False

        bot.whisper(source, "Successfully added your links")

    def remove_link_blacklist(self, bot, source, message, **rest):
        if not message:
            bot.whisper(source, "Usage: !remove link blacklist ID")
            return False

        id = None
        try:
            id = int(message)
        except ValueError:
            pass

        link = self.db_session.query(BlacklistedLink).filter_by(id=id).one_or_none()

        if link:
            self.blacklisted_links.remove(link)
            self.db_session.delete(link)
            self.db_session.commit()
        else:
            bot.whisper(source, "No link with the given id found")
            return False

        AdminLogManager.post("Blacklist link removed", source, link.domain)
        bot.whisper(source, f"Successfully removed blacklisted link with id {link.id}")

    def remove_link_whitelist(self, bot, source, message, **rest):
        if not message:
            bot.whisper(source, "Usage: !remove link whitelist ID")
            return False

        id = None
        try:
            id = int(message)
        except ValueError:
            pass

        link = self.db_session.query(WhitelistedLink).filter_by(id=id).one_or_none()

        if link:
            self.whitelisted_links.remove(link)
            self.db_session.delete(link)
            self.db_session.commit()
        else:
            bot.whisper(source, "No link with the given id found")
            return False

        AdminLogManager.post("Whitelist link removed", source, link.domain)
        bot.whisper(source, f"Successfully removed whitelisted link with id {link.id}")

    @staticmethod
    def parse_link_blacklist_arguments(message):
        parser = argparse.ArgumentParser()
        parser.add_argument("--deep", dest="level", action="store_true")
        parser.add_argument("--shallow", dest="level", action="store_false")
        parser.set_defaults(level=False)

        try:
            args, unknown = parser.parse_known_args(message.split())
        except SystemExit:
            return False, False
        except:
            log.exception("Unhandled exception in add_link_blacklist")
            return False, False

        # Strip options of any values that are set as None
        options = {k: v for k, v in vars(args).items() if v is not None}
        response = " ".join(unknown)

        if "level" in options:
            options["level"] = int(options["level"])

        return options, response
