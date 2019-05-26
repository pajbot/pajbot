import json
import logging

from pajbot.managers.db import DBManager
from pajbot.models.module import Module
from pajbot.modules import PlaysoundModule

log = logging.getLogger(__name__)


class MenuItem:
    def __init__(self, href, id, caption, level=100):
        self.href = href
        self.id = id
        self.caption = caption
        self.level = level
        self.active = True


def init(app):
    playsound_menu_item = MenuItem('/playsounds', 'user_playsounds', 'Playsounds')
    admin_playsound_menu_item = MenuItem('/admin/playsounds', 'admin_playsounds', 'Playsounds')

    def my_handler(module_update):
        if 'id' not in module_update or 'new_state' not in module_update:
            return
        if module_update['id'] == 'playsound':
            playsound_menu_item.active = module_update['new_state']
            admin_playsound_menu_item.active = module_update['new_state']

    with DBManager.create_session_scope() as session:
        playsound_module = session.query(Module).filter(Module.id == PlaysoundModule.ID).one_or_none()

        if playsound_module is not None:
            playsound_menu_item.active = playsound_module.enabled
            admin_playsound_menu_item.active = playsound_module.enabled

    app.socket_manager.add_handler('module.update', my_handler)

    nav_bar_header = []
    nav_bar_header.append(MenuItem('/', 'home', 'Home'))
    nav_bar_header.append(MenuItem('/commands', 'commands', 'Commands'))
    if 'deck' in app.module_manager:
        nav_bar_header.append(MenuItem('/decks', 'decks', 'Decks'))
    if app.bot_config['main']['nickname'] not in ['scamazbot', 'exdeebot']:
        nav_bar_header.append(MenuItem('/points', 'points', 'Points'))
    nav_bar_header.append(MenuItem('/stats', 'stats', 'Stats'))
    nav_bar_header.append(playsound_menu_item)
    nav_bar_header.append(MenuItem('/highlights', 'highlights', 'Highlights'))
    if 'pleblist' in app.bot_modules:
        nav_bar_header.append(MenuItem('/pleblist/history', 'pleblist', 'Pleblist'))

    nav_bar_admin_header = []
    nav_bar_admin_header.append(MenuItem('/', 'home', 'Home'))
    nav_bar_admin_header.append(MenuItem('/admin', 'admin_home', 'Admin Home'))
    nav_bar_admin_header.append(MenuItem([
        MenuItem('/admin/banphrases', 'admin_banphrases', 'Banphrases'),
        MenuItem('/admin/links/blacklist', 'admin_links_blacklist', 'Blacklisted links'),
        MenuItem('/admin/links/whitelist', 'admin_links_whitelist', 'Whitelisted links'),
        ], None, 'Filters'))
    nav_bar_admin_header.append(MenuItem('/admin/commands', 'admin_commands', 'Commands'))
    nav_bar_admin_header.append(MenuItem('/admin/timers', 'admin_timers', 'Timers'))
    nav_bar_admin_header.append(MenuItem('/admin/moderators', 'admin_moderators', 'Moderators'))
    nav_bar_admin_header.append(MenuItem('/admin/modules', 'admin_modules', 'Modules'))
    nav_bar_admin_header.append(admin_playsound_menu_item)
    if 'predict' in app.module_manager:
        nav_bar_admin_header.append(MenuItem('/admin/predictions', 'admin_predictions', 'Predictions'))
    nav_bar_admin_header.append(MenuItem('/admin/streamer', 'admin_streamer', 'Streamer Info'))
    nav_bar_admin_header.append(MenuItem('/admin/clr', 'admin_clr', 'CLR', level=1500))

    @app.context_processor
    def menu():
        data = {
                'nav_bar_header': nav_bar_header,
                'nav_bar_admin_header': nav_bar_admin_header,
                }
        return data
