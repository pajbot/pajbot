import logging

from flask_assets import Bundle
from flask_assets import Environment

log = logging.getLogger(__name__)


def init(app):
    assets = Environment(app)

    # Basic CSS and Javascript:
    # Available under: base_css, base_js
    base_css = Bundle('css/base.scss', filters='pyscss',
            output='gen/css/base.%(version)s.css')
    base_js = Bundle('scripts/base.js', filters='jsmin',
            output='gen/scripts/base.%(version)s.js')
    assets.register('base_css', base_css)
    assets.register('base_js', base_js)

    # Pleblist-related javascript
    # Available under the following assets: pleblist_shared, pleblist_host, pleblist_client
    pleblist_client = Bundle('scripts/pleblist.js', filters='jsmin',
            output='gen/scripts/pleblist.%(version)s.js')
    pleblist_shared = Bundle('scripts/pleblist.shared.js', filters='jsmin',
            output='gen/scripts/pleblist.shared.%(version)s.js')
    pleblist_host = Bundle(
            'scripts/pleblist.host.js',
            'scripts/pleblist.host.streamtip.js',
            'scripts/pleblist.host.streamelements.js',
            'scripts/pleblist.host.streamlabs.js',
            filters='jsmin',
            output='gen/scripts/pleblist.host.%(version)s.js')
    assets.register('pleblist_shared', pleblist_shared)
    assets.register('pleblist_client', pleblist_client)
    assets.register('pleblist_host', pleblist_host)

    # CLR Overlay
    # Availabe under: clr_overlay_js, clr_overlay_css, clr_donations_js, clr_donations_css, clr_shared_js
    clr_overlay_js = Bundle('scripts/clr.overlay.js', filters='jsmin',
            output='gen/scripts/clr.overlay.%(version)s.js')
    clr_overlay_css = Bundle('css/clr.overlay.scss', filters='pyscss',
            output='gen/css/clr.overlay.%(version)s.css')
    clr_donations_js = Bundle('scripts/clr.donations.js', filters='jsmin',
            output='gen/scripts/clr.donations.%(version)s.js')
    clr_donations_css = Bundle('css/clr.donations.scss', filters='pyscss',
            output='gen/css/clr.donations.%(version)s.css')
    clr_shared_js = Bundle('scripts/clr.shared.js', filters='jsmin',
            output='gen/scripts/clr.shared.%(version)s.js')
    assets.register('clr_overlay_js', clr_overlay_js)
    assets.register('clr_overlay_css', clr_overlay_css)
    assets.register('clr_donations_js', clr_donations_js)
    assets.register('clr_donations_css', clr_donations_css)
    assets.register('clr_shared_js', clr_shared_js)

    # Admin site
    # Availabe under: admin_create_banphrase, admin_create_command,
    #                 admin_create_row, admin_edit_command
    admin_create_banphrase = Bundle('scripts/admin/create_banphrase.js', filters='jsmin',
            output='gen/scripts/admin/create_banphrase.%(version)s.js')
    admin_create_command = Bundle('scripts/admin/create_command.js', filters='jsmin',
            output='gen/scripts/admin/create_command.%(version)s.js')
    admin_create_row = Bundle('scripts/admin/create_row.js', filters='jsmin',
            output='gen/scripts/admin/create_row.%(version)s.js')
    admin_edit_command = Bundle('scripts/admin/edit_command.js', filters='jsmin',
            output='gen/scripts/admin/edit_command.%(version)s.js')
    assets.register('admin_create_banphrase', admin_create_banphrase)
    assets.register('admin_create_command', admin_create_command)
    assets.register('admin_create_row', admin_create_row)
    assets.register('admin_edit_command', admin_edit_command)

    # Admin CLR
    admin_clr_donations_edit_js = Bundle('scripts/admin/clr/donations/edit.js',
            output='gen/scripts/admin/clr/donations/edit.%(version)s.js')
    assets.register('admin_clr_donations_edit_js', admin_clr_donations_edit_js)

    notifications_base = Bundle('scripts/notifications/base.js', filters='jsmin',
            output='gen/scripts/notifications/base.%(version)s.js')
    assets.register('notifications_base', notifications_base)

    notifications_subscribers = Bundle('scripts/notifications/subscribers.js', filters='jsmin',
            output='gen/scripts/notifications/subscribers.%(version)s.js')
    assets.register('notifications_subscribers', notifications_subscribers)

    # Third party libraries
    # Available under: autolinker
    autolinker = Bundle('scripts/autolinker.js', filters='jsmin',
            output='gen/scripts/autolinker.%(version)s.js')
    assets.register('autolinker', autolinker)

    # Commands
    # Available under: commands_js
    commands_js = Bundle('scripts/commands.js', filters='jsmin',
            output='gen/scripts/commands.%(version)s.js')
    assets.register('commands_js', commands_js)

    # Pagination script
    # Available under: paginate_js
    paginate_js = Bundle('scripts/paginate.js', filters='jsmin',
            output='gen/scripts/paginate.%(version)s.js')
    assets.register('paginate_js', paginate_js)

    assets.init_app(app)
