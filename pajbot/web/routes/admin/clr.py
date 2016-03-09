import logging

from flask import render_template

from pajbot.web.utils import requires_level

log = logging.getLogger(__name__)


def init(page):
    @page.route('/clr/')
    @requires_level(500)
    def clr_home(**options):
        return render_template('admin/clr/home.html')
