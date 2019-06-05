import os
import sys

import unittest

sys.path.append(os.path.abspath("."))


class TestURLMethods(unittest.TestCase):
    def test_is_subdomain(self):
        from pajbot.modules.linkchecker import is_subdomain

        self.assertTrue(is_subdomain("pajlada.se", "pajlada.se"))
        self.assertTrue(is_subdomain("test.pajlada.se", "pajlada.se"))

        self.assertFalse(is_subdomain("test.pajlada.se", "pajlada.com"))
        self.assertFalse(is_subdomain("kastaren.com", "roleplayer.se"))
        self.assertFalse(is_subdomain("foo.bar.com", "foobar.com"))

    def test_is_subpath(self):
        from pajbot.modules.linkchecker import is_subpath

        self.assertTrue(is_subpath("/foo/", "/foo/"))
        self.assertTrue(is_subpath("/foo/bar", "/foo/"))

        self.assertFalse(is_subpath("/foo/", "/bar/"))
        self.assertFalse(is_subpath("/foo/", "/foo/bar"))

    def test_is_same_url(self):
        from pajbot.modules.linkchecker import is_same_url, Url

        self.assertTrue(is_same_url(Url("pajlada.se"), Url("pajlada.se/")))

        self.assertFalse(is_same_url(Url("pajlada.com"), Url("pajlada.se")))
        self.assertFalse(is_same_url(Url("pajlada.com"), Url("pajlada.com/abc")))

    def test_find_unique_urls(self):
        from pajbot.modules.linkchecker import find_unique_urls
        from pajbot.bot import Bot
        import re

        regex = re.compile(Bot.url_regex_str, re.IGNORECASE)

        self.assertEqual(find_unique_urls(regex, "pajlada.se test http://pajlada.se"), {"http://pajlada.se"})
        self.assertEqual(
            find_unique_urls(regex, "pajlada.se pajlada.com foobar.se"),
            {"http://pajlada.se", "http://pajlada.com", "http://foobar.se"},
        )
        self.assertEqual(find_unique_urls(regex, "foobar.com foobar.com"), {"http://foobar.com"})
        self.assertEqual(find_unique_urls(regex, "foobar.com foobar.se"), {"http://foobar.com", "http://foobar.se"})
        self.assertEqual(
            find_unique_urls(regex, "www.foobar.com foobar.se"), {"http://www.foobar.com", "http://foobar.se"}
        )

        # TODO: Edge case, this behaviour should probably be changed. These URLs should be considered the same.
        # Use is_same_url method?
        self.assertEqual(find_unique_urls(regex, "pajlada.se/ pajlada.se"), {"http://pajlada.se/", "http://pajlada.se"})

        # TODO: The protocol of a URL is entirely thrown away, this behaviour should probably be changed.
        self.assertEqual(
            find_unique_urls(regex, "https://pajlada.se/ https://pajlada.se"),
            {"https://pajlada.se/", "https://pajlada.se"},
        )


class TestCleanUpMessage(unittest.TestCase):
    def test_clean_up(self):
        from pajbot.utils import clean_up_message

        self.assertEqual("󠀀", "\U000e0000")

        self.assertEqual("", clean_up_message(""))
        self.assertEqual("", clean_up_message("  "))
        self.assertEqual("", clean_up_message(" 1"))

        self.assertEqual(". .timeout pajlada 5", clean_up_message(".timeout pajlada 5"))
        self.assertEqual(". /timeout pajlada 5", clean_up_message("/timeout pajlada 5"))
        self.assertEqual(". .timeout pajlada 5", clean_up_message("   .timeout pajlada 5"))
        self.assertEqual(". /timeout pajlada 5", clean_up_message(" /timeout pajlada 5"))
        self.assertEqual(".me xD", clean_up_message(".me xD"))
        self.assertEqual("/me xD", clean_up_message("/me xD"))
        self.assertEqual("/me xD", clean_up_message("   /me xD"))
        self.assertEqual(".me xD", clean_up_message("   .me xD"))
        self.assertEqual("asd", clean_up_message("asd"))
        self.assertEqual("asd", clean_up_message("    asd"))
        for prefix in ["!", "$", "-", "<"]:
            self.assertEqual("\U000e0000{}ping".format(prefix), clean_up_message("{}ping".format(prefix)))
            self.assertEqual("/me \U000e0000{}ping".format(prefix), clean_up_message("/me {}ping".format(prefix)))
            self.assertEqual(".me \U000e0000{}ping".format(prefix), clean_up_message(".me {}ping".format(prefix)))
            self.assertEqual("\U000e0000{}ping".format(prefix), clean_up_message("    {}ping".format(prefix)))
            self.assertEqual(".me \U000e0000{}ping".format(prefix), clean_up_message(".me    {}ping".format(prefix)))
            self.assertEqual(".me \U000e0000{}ping".format(prefix), clean_up_message(" .me    {}ping".format(prefix)))
            self.assertEqual("/me \U000e0000{}ping".format(prefix), clean_up_message("/me    {}ping".format(prefix)))
            self.assertEqual("/me \U000e0000{}ping".format(prefix), clean_up_message(" /me    {}ping".format(prefix)))

            self.assertEqual("\U000e0000{}".format(prefix), clean_up_message("{}".format(prefix)))
            self.assertEqual("/me \U000e0000{}".format(prefix), clean_up_message("/me {}".format(prefix)))
            self.assertEqual(".me \U000e0000{}".format(prefix), clean_up_message(".me {}".format(prefix)))
            self.assertEqual("\U000e0000{}".format(prefix), clean_up_message("    {}".format(prefix)))
            self.assertEqual(".me \U000e0000{}".format(prefix), clean_up_message(".me    {}".format(prefix)))
            self.assertEqual(".me \U000e0000{}".format(prefix), clean_up_message(" .me    {}".format(prefix)))
            self.assertEqual("/me \U000e0000{}".format(prefix), clean_up_message("/me    {}".format(prefix)))
            self.assertEqual("/me \U000e0000{}".format(prefix), clean_up_message(" /me    {}".format(prefix)))


if __name__ == "__main__":
    unittest.main()
