def init(app):
    nav_bar_header = []
    nav_bar_header.append(('/', 'home', 'Home'))
    nav_bar_header.append(('/commands/', 'commands', 'Commands'))
    if 'deck' in app.module_manager:
        nav_bar_header.append(('/decks/', 'decks', 'Decks'))
    if app.bot_config['main']['nickname'] not in ['scamazbot', 'exdeebot']:
        nav_bar_header.append(('/points/', 'points', 'Points'))
    nav_bar_header.append(('/stats/', 'stats', 'Stats'))
    nav_bar_header.append(('/highlights/', 'highlights', 'Highlights'))
    if 'pleblist' in app.bot_modules:
        nav_bar_header.append(('/pleblist/history/', 'pleblist', 'Pleblist'))

    nav_bar_admin_header = []
    nav_bar_admin_header.append(('/', 'home', 'Home'))
    nav_bar_admin_header.append(('/admin/', 'admin_home', 'Admin Home'))
    nav_bar_admin_header.append(([
        ('/admin/banphrases/', 'admin_banphrases', 'Banphrases'),
        ('/admin/links/blacklist/', 'admin_links_blacklist', 'Blacklisted links'),
        ('/admin/links/whitelist/', 'admin_links_whitelist', 'Whitelisted links'),
        ], None, 'Filters'))
    nav_bar_admin_header.append(('/admin/commands/', 'admin_commands', 'Commands'))
    nav_bar_admin_header.append(('/admin/timers/', 'admin_timers', 'Timers'))
    nav_bar_admin_header.append(('/admin/moderators/', 'admin_moderators', 'Moderators'))
    nav_bar_admin_header.append(('/admin/modules/', 'admin_modules', 'Modules'))
    if 'predict' in app.module_manager:
        nav_bar_admin_header.append(('/admin/predictions/', 'admin_predictions', 'Predictions'))
    nav_bar_admin_header.append(('/admin/streamer/', 'admin_streamer', 'Streamer Info'))
    nav_bar_admin_header.append(('/admin/clr/', 'admin_clr', 'CLR'))

    @app.context_processor
    def menu():
        data = {
                'nav_bar_header': nav_bar_header,
                'nav_bar_admin_header': nav_bar_admin_header,
                }
        return data
