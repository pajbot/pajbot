class MenuItem:
    def __init__(self, href, id, caption, level=100):
        self.href = href
        self.id = id
        self.caption = caption
        self.level = level


def init(app):
    nav_bar_header = []
    nav_bar_header.append(MenuItem('/', 'home', 'Home'))
    nav_bar_header.append(MenuItem('/commands/', 'commands', 'Commands'))
    if 'deck' in app.module_manager:
        nav_bar_header.append(MenuItem('/decks/', 'decks', 'Decks'))
    if app.bot_config['main']['nickname'] not in ['scamazbot', 'exdeebot']:
        nav_bar_header.append(MenuItem('/points/', 'points', 'Points'))
    nav_bar_header.append(MenuItem('/stats/', 'stats', 'Stats'))
    nav_bar_header.append(MenuItem('/highlights/', 'highlights', 'Highlights'))
    if 'pleblist' in app.bot_modules:
        nav_bar_header.append(MenuItem('/pleblist/history/', 'pleblist', 'Pleblist'))

    nav_bar_admin_header = []
    nav_bar_admin_header.append(MenuItem('/', 'home', 'Home'))
    nav_bar_admin_header.append(MenuItem('/admin/', 'admin_home', 'Admin Home'))
    nav_bar_admin_header.append(MenuItem([
        MenuItem('/admin/banphrases/', 'admin_banphrases', 'Banphrases'),
        MenuItem('/admin/links/blacklist/', 'admin_links_blacklist', 'Blacklisted links'),
        MenuItem('/admin/links/whitelist/', 'admin_links_whitelist', 'Whitelisted links'),
        ], None, 'Filters'))
    nav_bar_admin_header.append(MenuItem('/admin/commands/', 'admin_commands', 'Commands'))
    nav_bar_admin_header.append(MenuItem('/admin/timers/', 'admin_timers', 'Timers'))
    nav_bar_admin_header.append(MenuItem('/admin/moderators/', 'admin_moderators', 'Moderators'))
    nav_bar_admin_header.append(MenuItem('/admin/modules/', 'admin_modules', 'Modules'))
    if 'predict' in app.module_manager:
        nav_bar_admin_header.append(MenuItem('/admin/predictions/', 'admin_predictions', 'Predictions'))
    nav_bar_admin_header.append(MenuItem('/admin/streamer/', 'admin_streamer', 'Streamer Info'))
    nav_bar_admin_header.append(MenuItem('/admin/clr/', 'admin_clr', 'CLR', level=1500))

    @app.context_processor
    def menu():
        data = {
                'nav_bar_header': nav_bar_header,
                'nav_bar_admin_header': nav_bar_admin_header,
                }
        return data
