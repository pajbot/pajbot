#!/usr/bin/env python3
import os
import sys

import unittest2

sys.path.append(os.path.abspath('..'))
os.chdir('..')


class TestURLMethods(unittest2.TestCase):
    def test_is_subdomain(self):
        from pajbot.modules.linkchecker import is_subdomain

        self.assertTrue(is_subdomain('pajlada.se', 'pajlada.se'))
        self.assertTrue(is_subdomain('test.pajlada.se', 'pajlada.se'))

        self.assertFalse(is_subdomain('test.pajlada.se', 'pajlada.com'))
        self.assertFalse(is_subdomain('kastaren.com', 'roleplayer.se'))
        self.assertFalse(is_subdomain('foo.bar.com', 'foobar.com'))

    def test_is_subpath(self):
        from pajbot.modules.linkchecker import is_subpath

        self.assertTrue(is_subpath('/foo/', '/foo/'))
        self.assertTrue(is_subpath('/foo/bar', '/foo/'))

        self.assertFalse(is_subpath('/foo/', '/bar/'))
        self.assertFalse(is_subpath('/foo/', '/foo/bar'))

    def test_is_same_url(self):
        from pajbot.modules.linkchecker import is_same_url, Url

        self.assertTrue(is_same_url(Url('pajlada.se'), Url('pajlada.se/')))

        self.assertFalse(is_same_url(Url('pajlada.com'), Url('pajlada.se')))
        self.assertFalse(is_same_url(Url('pajlada.com'), Url('pajlada.com/abc')))

    def test_find_unique_urls(self):
        from pajbot.modules.linkchecker import find_unique_urls
        from pajbot.bot import Bot
        import re

        regex = re.compile(Bot.url_regex_str, re.IGNORECASE)

        self.assertEqual(find_unique_urls(regex, 'pajlada.se test http://pajlada.se'), {'http://pajlada.se'})
        self.assertEqual(find_unique_urls(regex, 'pajlada.se pajlada.com foobar.se'), {'http://pajlada.se', 'http://pajlada.com', 'http://foobar.se'})
        self.assertEqual(find_unique_urls(regex, 'foobar.com foobar.com'), {'http://foobar.com'})
        self.assertEqual(find_unique_urls(regex, 'foobar.com foobar.se'), {'http://foobar.com', 'http://foobar.se'})
        self.assertEqual(find_unique_urls(regex, 'www.foobar.com foobar.se'), {'http://www.foobar.com', 'http://foobar.se'})

        # TODO: Edge case, this behaviour should probably be changed. These URLs should be considered the same.
        # Use is_same_url method?
        self.assertEqual(find_unique_urls(regex, 'pajlada.se/ pajlada.se'), {'http://pajlada.se/', 'http://pajlada.se'})

        # TODO: The protocol of a URL is entirely thrown away, this behaviour should probably be changed.
        self.assertEqual(find_unique_urls(regex, 'https://pajlada.se/ https://pajlada.se'), {'https://pajlada.se/', 'https://pajlada.se'})


class ActionsTester(unittest2.TestCase):
    def setUp(self):
        from pajbot.bot import Bot
        from pajbot.utils import load_config
        import datetime

        config = load_config('config.ini')
        args = Bot.parse_args()
        self.pajbot = Bot(config, args)
        self.source = self.pajbot.users['omgthisuserdoesnotexist123']
        self.source.username_raw = 'OmgthisuserdoesnotexiSt123'
        self.source.points = 142
        self.source.last_seen = datetime.datetime.strptime('17:01:42', '%H:%M:%S')

    def test_message_action_parse(self):
        from pajbot.models.action import SayAction  # noqa
        import pytz
        import datetime

        values = [  # noqa
                {
                    'message': 'hi',
                    'num_argument_subs': 0,
                    'num_subs': 0,
                    'arguments': '',
                    'result': 'hi',
                }, {
                    'message': 'Hello $(source:username)!',
                    'num_argument_subs': 0,
                    'num_subs': 1,
                    'arguments': '',
                    'result': 'Hello omgthisuserdoesnotexist123!',
                }, {
                    'message': 'Testing $(1)',
                    'num_argument_subs': 1,
                    'num_subs': 0,
                    'arguments': 'a b c',
                    'result': 'Testing a',
                }, {
                    'message': 'Testing $(1) $(2)',
                    'num_argument_subs': 2,
                    'num_subs': 0,
                    'arguments': '',
                    'result': 'Testing  ',
                }, {
                    'message': 'Testing $(1) $(2) $(1)',
                    'num_argument_subs': 2,
                    'num_subs': 0,
                    'arguments': '',
                    'result': 'Testing   ',
                }, {
                    'message': '$(user;1:username_raw) has $(user;1:points) points. 1',
                    'num_argument_subs': 0,
                    'num_subs': 2,
                    'arguments': 'omgthisuserdoesnotexist123',
                    'result': 'OmgthisuserdoesnotexiSt123 has 142 points. 1',
                }, {
                    'message': '$(user;1:username_raw|lower) has $(user;1:points) points. 2',
                    'num_argument_subs': 0,
                    'num_subs': 2,
                    'arguments': 'omgthisuserdoesnotexist123',
                    'result': 'omgthisuserdoesnotexist123 has 142 points. 2',
                }, {
                    'message': '$(user;1:username_raw) has $(user;1:points) points. 3',
                    'num_argument_subs': 0,
                    'num_subs': 2,
                    'arguments': 'OmgthisuserdoesnotExiSt123',
                    'result': 'OmgthisuserdoesnotexiSt123 has 142 points. 3',
                }, {
                    'message': '$(user;1:username_raw|lower) was last seen $(source:last_seen|strftime(%H:%M:%S)).',
                    'num_argument_subs': 0,
                    'num_subs': 2,
                    'arguments': 'omgthisuserdoesnotexist123',
                    'result': 'omgthisuserdoesnotexist123 was last seen 18:01:42.',
                }, {
                    'message': 'Time in Sweden: $(time:Europe/Stockholm)',
                    'num_argument_subs': 0,
                    'num_subs': 1,
                    'arguments': 'omgthisuserdoesnotexist123',
                    'result': 'Time in Sweden: {}'.format(datetime.datetime.now(pytz.timezone('Europe/Stockholm')).strftime(self.pajbot.date_fmt)),
                }, {
                    'message': 'BEFORE $(if:$(1),"YES","NO") AFTER',
                    'num_argument_subs': 1,
                    'num_subs': 1,
                    'arguments': 'omgthisuserdoesnotexist123',
                    'result': 'BEFORE YES AFTER',
                }, {
                    'message': 'BEFORE $(if:$(1),"YES","NO") AFTER',
                    'num_argument_subs': 1,
                    'num_subs': 1,
                    'arguments': '',
                    'result': 'BEFORE NO AFTER',
                }, {
                    'message': 'BEFORE $(source:username|lower|upper) AFTER',
                    'num_argument_subs': 0,
                    'num_subs': 1,
                    'arguments': '',
                    'result': 'BEFORE OMGTHISUSERDOESNOTEXIST123 AFTER',
                },
                ]

        """
        for data in values:
            action = SayAction(data['message'], self.pajbot)
            response = action.get_response(self.pajbot, {'source': self.source, 'message': data['arguments']})
            self.assertEqual(len(action.argument_subs), data['num_argument_subs'], 'Wrong amount of argument substitutions for "{0}"'.format(data['message']))
            self.assertEqual(len(action.subs), data['num_subs'], 'Wrong amount of substitutions for "{0}"'.format(data['message']))
            self.assertEqual(response, data['result'], 'Got output "{}", expected "{}"'.format(response, data['result']))
            """


if __name__ == '__main__':
    unittest2.main()
