#!/usr/bin/env python3

import unittest


class TestURLMethods(unittest.TestCase):
    def test_is_subdomain(self):
        from models.linkchecker import is_subdomain

        self.assertTrue(is_subdomain('pajlada.se', 'pajlada.se'))
        self.assertTrue(is_subdomain('test.pajlada.se', 'pajlada.se'))

        self.assertFalse(is_subdomain('test.pajlada.se', 'pajlada.com'))
        self.assertFalse(is_subdomain('kastaren.com', 'roleplayer.se'))
        self.assertFalse(is_subdomain('foo.bar.com', 'foobar.com'))

    def test_is_subpath(self):
        from models.linkchecker import is_subpath

        self.assertTrue(is_subpath('/foo/', '/foo/'))
        self.assertTrue(is_subpath('/foo/bar', '/foo/'))

        self.assertFalse(is_subpath('/foo/', '/bar/'))
        self.assertFalse(is_subpath('/foo/', '/foo/bar'))

    def test_is_same_url(self):
        from models.linkchecker import is_same_url, Url

        self.assertEqual(is_same_url(Url('pajlada.se'), Url('pajlada.se/')), True)

        self.assertEqual(is_same_url(Url('pajlada.com'), Url('pajlada.se')), False)
        self.assertEqual(is_same_url(Url('pajlada.com'), Url('pajlada.com/abc')), False)

    def test_find_unique_urls(self):
        from models.linkchecker import LinkChecker, find_unique_urls
        import re

        regex = re.compile(LinkChecker.regex_str, re.IGNORECASE)

        self.assertEqual(find_unique_urls(regex, 'pajlada.se test http://pajlada.se'), {'http://pajlada.se'})
        self.assertEqual(find_unique_urls(regex, 'pajlada.se pajlada.com foobar.se'), {'http://pajlada.se', 'http://pajlada.com', 'http://foobar.se'})
        self.assertEqual(find_unique_urls(regex, 'foobar.com foobar.com'), {'http://foobar.com'})
        self.assertEqual(find_unique_urls(regex, 'foobar.com foobar.se'), {'http://foobar.com', 'http://foobar.se'})
        self.assertEqual(find_unique_urls(regex, 'www.foobar.com foobar.se'), {'http://www.foobar.com', 'http://foobar.se'})

        # TODO: Edge case, this behaviour should probably be changed. These URLs should be considered the same.
        # Use is_same_url method?
        self.assertEqual(find_unique_urls(regex, 'pajlada.se/ pajlada.se'), {'http://pajlada.se/', 'http://pajlada.se'})

        # TODO: The protocol of a URL is entirely thrown away, this behaviour should probably be changed.
        self.assertEqual(find_unique_urls(regex, 'https://pajlada.se/ https://pajlada.se'), {'http://pajlada.se/', 'http://pajlada.se'})

if __name__ == '__main__':
    unittest.main()
