from pajbot.web.utils import requires_level

from flask import render_template


def init(page):
    @page.route('/')
    @requires_level(500)
    def home(**options):
        return render_template('admin/home.html')
