import collections
import logging

from pajbot.managers.redis import RedisManager
from pajbot.streamhelper import StreamHelper
from pajbot.web.utils import requires_level

from flask import render_template

log = logging.getLogger(__name__)


def init(page):
    @page.route('/clr/')
    @requires_level(500)
    def clr_home(**options):
        return render_template('admin/clr_home.html')
