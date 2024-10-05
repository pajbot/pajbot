import logging

from flask_assets import Bundle, Environment

log = logging.getLogger(__name__)


def js_bundle(path: str, output: str) -> Bundle:
    return Bundle(
        path,
        filters="rjsmin",
        output=output,
    )


def init(app):
    assets = Environment(app)

    # Basic CSS and Javascript:
    # Available under: base_css, base_js
    base_css = Bundle("css/base.css", filters="cssmin", output="gen/css/base.%(version)s.css")
    base_js = js_bundle("scripts/base.js", "gen/scripts/base.%(version)s.js")
    assets.register("base_css", base_css)
    assets.register("base_js", base_js)

    datetime_js = js_bundle("scripts/datetime.js", "gen/scripts/datetime.%(version)s.js")
    assets.register("datetime", datetime_js)

    # CLR Overlay
    # Availabe under: clr_overlay_js, clr_overlay_css
    # jsmin is intentionally disabled for clr.overlay.js because the output is broken (same as below for
    # playsounds)
    clr_overlay_js = js_bundle("scripts/clr.overlay.js", "gen/scripts/clr.overlay.%(version)s.js")
    clr_overlay_css = Bundle("css/clr.overlay.css", filters="cssmin", output="gen/css/clr.overlay.%(version)s.css")
    assets.register("clr_overlay_js", clr_overlay_js)
    assets.register("clr_overlay_css", clr_overlay_css)

    # Admin site
    # Availabe under: admin_create_banphrase, admin_create_command,
    #                 admin_create_row, admin_edit_command
    admin_create_banphrase = js_bundle(
        "scripts/admin/create_banphrase.js", "gen/scripts/admin/create_banphrase.%(version)s.js"
    )
    admin_create_command = js_bundle(
        "scripts/admin/create_command.js", "gen/scripts/admin/create_command.%(version)s.js"
    )
    admin_create_row = js_bundle("scripts/admin/create_row.js", "gen/scripts/admin/create_row.%(version)s.js")
    admin_edit_command = js_bundle("scripts/admin/edit_command.js", "gen/scripts/admin/edit_command.%(version)s.js")
    assets.register("admin_create_banphrase", admin_create_banphrase)
    assets.register("admin_create_command", admin_create_command)
    assets.register("admin_create_row", admin_create_row)
    assets.register("admin_edit_command", admin_edit_command)

    notifications_subscribers = js_bundle(
        "scripts/notifications/subscribers.js",
        "gen/scripts/notifications/subscribers.%(version)s.js",
    )
    assets.register("notifications_subscribers", notifications_subscribers)

    # Third party libraries
    # Available under: autolinker
    autolinker = js_bundle("scripts/autolinker.js", "gen/scripts/autolinker.%(version)s.js")
    assets.register("autolinker", autolinker)

    # Commands
    # Available under: commands_js
    commands_js = js_bundle("scripts/commands.js", "gen/scripts/commands.%(version)s.js")
    assets.register("commands_js", commands_js)

    # Pagination script
    # Available under: paginate_js
    paginate_js = js_bundle("scripts/paginate.js", "gen/scripts/paginate.%(version)s.js")
    assets.register("paginate_js", paginate_js)

    # common controls for the playsound pages
    playsound_common_js = js_bundle("scripts/playsound.common.js", "gen/scripts/playsound.common.%(version)s.js")
    assets.register("playsound_common_js", playsound_common_js)

    playsound_admin_js = js_bundle(
        "scripts/admin/playsound.admin.js", output="gen/scripts/admin/playsound.admin.%(version)s.js"
    )
    assets.register("playsound_admin_js", playsound_admin_js)
    playsound_admin_css = Bundle(
        "css/admin/playsound.admin.css", filters="cssmin", output="gen/css/admin/playsound.admin.%(version)s.css"
    )
    assets.register("playsound_admin_css", playsound_admin_css)

    assets.init_app(app)
