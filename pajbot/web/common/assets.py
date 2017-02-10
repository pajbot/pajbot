import logging

from flask_assets import Bundle
from flask_assets import Environment

log = logging.getLogger(__name__)


def init(app):
    assets = Environment(app)

    # Basic CSS and Javascript:
    # Available under: base_css, semantic_css, base_js
    base_css = Bundle('css/base.min.css',
            output='css/base.gen.%(version)s.css')
    semantic_css = Bundle('semantic/semantic.min.css',
            output='semantic/semantic.gen.%(version)s.css')
    base_js = Bundle('scripts/base.js', filters='jsmin',
            output='scripts/base.gen.%(version)s.js')
    semantic_js = Bundle('semantic/semantic.min.js',
            output='semantic/semantic.gen.%(version)s.js')
    assets.register('base_css', base_css)
    assets.register('base_js', base_js)
    assets.register('semantic_css', semantic_css)
    assets.register('semantic_js', semantic_js)

    # Pleblist-related javascript
    # Available undeer the following assets: pleblist_shared, pleblist_host, pleblist_client
    pleblist_client = Bundle('scripts/pleblist.js', filters='jsmin',
            output='scripts/pleblist.gen.%(version)s.js')
    pleblist_shared = Bundle('scripts/pleblist.shared.js', filters='jsmin',
            output='scripts/pleblist.gen.shared.%(version)s.js')
    pleblist_host = Bundle('scripts/pleblist.host.js', filters='jsmin',
            output='scripts/pleblist.gen.host.%(version)s.js')
    assets.register('pleblist_shared', pleblist_shared)
    assets.register('pleblist_client', pleblist_client)
    assets.register('pleblist_host', pleblist_host)

    # CLR Overlay
    # Availabe under: clr_overlay, clr_donations, clr_shared
    clr_overlay_js = Bundle('scripts/clr.overlay.js', filters='jsmin',
            output='scripts/clr.gen.overlay.%(version)s.js')
    clr_overlay_css = Bundle('css/clr.overlay.css',
            output='css/gen.clr.overlay.%(version)s.css')
    clr_donations = Bundle('scripts/clr.donations.js', filters='jsmin',
            output='scripts/clr.gen.donations.%(version)s.js')
    clr_shared = Bundle('scripts/clr.shared.js', filters='jsmin',
            output='scripts/clr.gen.shared.%(version)s.js')
    assets.register('clr_overlay_js', clr_overlay_js)
    assets.register('clr_overlay_css', clr_overlay_css)
    assets.register('clr_donations', clr_donations)
    assets.register('clr_shared', clr_shared)

    # Admin site
    # Availabe under: admin_create_banphrase, admin_create_command,
    #                 admin_create_row, admin_edit_command
    admin_create_banphrase = Bundle('scripts/admin/create_banphrase.js', filters='jsmin',
            output='scripts/admin/create_banphrase.gen.%(version)s.js')
    admin_create_command = Bundle('scripts/admin/create_command.js', filters='jsmin',
            output='scripts/admin/create_command.gen.%(version)s.js')
    admin_create_row = Bundle('scripts/admin/create_row.js', filters='jsmin',
            output='scripts/admin/create_row.gen.%(version)s.js')
    admin_edit_command = Bundle('scripts/admin/edit_command.js', filters='jsmin',
            output='scripts/admin/edit_command.gen.%(version)s.js')
    assets.register('admin_create_banphrase', admin_create_banphrase)
    assets.register('admin_create_command', admin_create_command)
    assets.register('admin_create_row', admin_create_row)
    assets.register('admin_edit_command', admin_edit_command)

    # Admin CLR
    admin_clr_donations_edit_js = Bundle('scripts/admin/clr/donations/edit.js',
            output='scripts/admin/clr/donations/gen.edit.%(version)s.js')
    assets.register('admin_clr_donations_edit_js', admin_clr_donations_edit_js)

    notifications_base = Bundle('scripts/notifications/base.js', filters='jsmin',
            output='scripts/notifications/base.gen.%(version)s.js')
    assets.register('notifications_base', notifications_base)

    notifications_subscribers = Bundle('scripts/notifications/subscribers.js', filters='jsmin',
            output='scripts/notifications/subscribers.gen.%(version)s.js')
    assets.register('notifications_subscribers', notifications_subscribers)

    # Third party libraries
    # Available under: autolinker
    autolinker = Bundle('scripts/autolinker.js', filters='jsmin',
            output='scripts/autolinker.gen.%(version)s.js')
    assets.register('autolinker', autolinker)

    # Commands
    # Available under: commands_js
    commands_js = Bundle('scripts/commands.js', filters='jsmin',
            output='scripts/gen.commands.%(version)s.js')
    assets.register('commands_js', commands_js)

    # Pagination script
    # Available under: paginate_js
    paginate_js = Bundle('scripts/paginate.js', filters='jsmin',
            output='scripts/gen.paginate.%(version)s.js')
    assets.register('paginate_js', paginate_js)

    assets.init_app(app)
