import logging

from flask_assets import Bundle
from flask_assets import Environment

log = logging.getLogger(__name__)


def init(app):
    assets = Environment(app)

    # Basic CSS and Javascript:
    # Available under: base_css, base_js
    base_css = Bundle("css/base.css", filters="cssmin", output="gen/css/base.%(version)s.css")
    base_js = Bundle("scripts/base.js", filters="jsmin", output="gen/scripts/base.%(version)s.js")
    assets.register("base_css", base_css)
    assets.register("base_js", base_js)

    datetime_js = Bundle("scripts/datetime.js", filters="jsmin", output="gen/scripts/datetime.%(version)s.js")
    assets.register("datetime", datetime_js)

    # Pleblist-related javascript
    # Available under the following assets: pleblist_shared, pleblist_client
    pleblist_client = Bundle("scripts/pleblist.js", filters="jsmin", output="gen/scripts/pleblist.%(version)s.js")
    pleblist_shared = Bundle(
        "scripts/pleblist.shared.js", filters="jsmin", output="gen/scripts/pleblist.shared.%(version)s.js"
    )

    assets.register("pleblist_shared", pleblist_shared)
    assets.register("pleblist_client", pleblist_client)

    # CLR Overlay
    # Availabe under: clr_overlay_js, clr_overlay_css
    # jsmin is intentionally disabled for clr.overlay.js because the output is broken (same as below for
    # playsounds)
    clr_overlay_js = Bundle("scripts/clr.overlay.js", output="gen/scripts/clr.overlay.%(version)s.js")
    clr_overlay_css = Bundle("css/clr.overlay.css", filters="cssmin", output="gen/css/clr.overlay.%(version)s.css")
    assets.register("clr_overlay_js", clr_overlay_js)
    assets.register("clr_overlay_css", clr_overlay_css)

    # Admin site
    # Availabe under: admin_create_banphrase, admin_create_command,
    #                 admin_create_row, admin_edit_command
    admin_create_banphrase = Bundle(
        "scripts/admin/create_banphrase.js", filters="jsmin", output="gen/scripts/admin/create_banphrase.%(version)s.js"
    )
    admin_create_command = Bundle(
        "scripts/admin/create_command.js", filters="jsmin", output="gen/scripts/admin/create_command.%(version)s.js"
    )
    admin_create_row = Bundle(
        "scripts/admin/create_row.js", filters="jsmin", output="gen/scripts/admin/create_row.%(version)s.js"
    )
    admin_edit_command = Bundle(
        "scripts/admin/edit_command.js", filters="jsmin", output="gen/scripts/admin/edit_command.%(version)s.js"
    )
    assets.register("admin_create_banphrase", admin_create_banphrase)
    assets.register("admin_create_command", admin_create_command)
    assets.register("admin_create_row", admin_create_row)
    assets.register("admin_edit_command", admin_edit_command)

    notifications_subscribers = Bundle(
        "scripts/notifications/subscribers.js",
        filters="jsmin",
        output="gen/scripts/notifications/subscribers.%(version)s.js",
    )
    assets.register("notifications_subscribers", notifications_subscribers)

    # Third party libraries
    # Available under: autolinker
    autolinker = Bundle("scripts/autolinker.js", filters="jsmin", output="gen/scripts/autolinker.%(version)s.js")
    assets.register("autolinker", autolinker)

    # Commands
    # Available under: commands_js
    commands_js = Bundle("scripts/commands.js", filters="jsmin", output="gen/scripts/commands.%(version)s.js")
    assets.register("commands_js", commands_js)

    # Pagination script
    # Available under: paginate_js
    paginate_js = Bundle("scripts/paginate.js", filters="jsmin", output="gen/scripts/paginate.%(version)s.js")
    assets.register("paginate_js", paginate_js)

    # range slider for semantic UI
    range_slider_js = Bundle("scripts/range.js", filters="jsmin", output="gen/scripts/range.%(version)s.js")
    assets.register("range_slider_js", range_slider_js)
    range_slider_css = Bundle("css/range.css", filters="cssmin", output="gen/css/range.%(version)s.css")
    assets.register("range_slider_css", range_slider_css)

    # common controls for the playsound pages
    playsound_common_js = Bundle(
        "scripts/playsound.common.js", filters="jsmin", output="gen/scripts/playsound.common.%(version)s.js"
    )
    assets.register("playsound_common_js", playsound_common_js)

    # DON'T enable jsmin for this resource, it breaks the output
    # probably because it uses ECMAScript features that are too new
    playsound_admin_js = Bundle(
        "scripts/admin/playsound.admin.js", output="gen/scripts/admin/playsound.admin.%(version)s.js"
    )
    assets.register("playsound_admin_js", playsound_admin_js)
    playsound_admin_css = Bundle(
        "css/admin/playsound.admin.css", filters="cssmin", output="gen/css/admin/playsound.admin.%(version)s.css"
    )
    assets.register("playsound_admin_css", playsound_admin_css)

    assets.init_app(app)
