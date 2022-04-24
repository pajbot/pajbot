from __future__ import annotations

from typing import Any, Dict, List, Union

import logging

from pajbot.web.utils import get_cached_enabled_modules

log = logging.getLogger(__name__)


class MenuItem:
    def __init__(
        self,
        href: Union[str, List[MenuItem]],
        menu_id: str,
        caption: str,
        enabled: bool = True,
        level: int = 100,
    ) -> None:
        self.href = href
        self.id = menu_id
        self.caption = caption
        self.enabled = enabled
        self.level = level
        self.type = "single"

        if isinstance(self.href, list):
            self.type = "multi"


def init(app):
    @app.context_processor
    def menu() -> Dict[str, Any]:
        enabled_modules = get_cached_enabled_modules()

        # Menu items that are shown for normal users
        menu_items: List[MenuItem] = [
            MenuItem("/", "home", "Home"),
            MenuItem("/commands", "commands", "Commands"),
            MenuItem("/points", "points", "Points", "chatters_refresh" in enabled_modules),
            MenuItem("/stats", "stats", "Stats"),
            MenuItem("/decks", "decks", "Decks", "deck" in enabled_modules),
            MenuItem("/playsounds", "user_playsounds", "Playsounds", "playsound" in enabled_modules),
        ]

        # Menu items that are shown to admin when in an /admin page
        admin_menu_items: List[MenuItem] = [
            MenuItem("/", "home", "Home"),
            MenuItem("/admin", "admin_home", "Admin Home"),
            MenuItem(
                [
                    MenuItem("/admin/banphrases", "admin_banphrases", "Banphrases"),
                    MenuItem("/admin/links/blacklist", "admin_links_blacklist", "Blacklisted links"),
                    MenuItem("/admin/links/whitelist", "admin_links_whitelist", "Whitelisted links"),
                ],
                "filters",
                "Filters",
            ),
            MenuItem("/admin/commands", "admin_commands", "Commands"),
            MenuItem("/admin/timers", "admin_timers", "Timers"),
            MenuItem("/admin/moderators", "admin_moderators", "Moderators"),
            MenuItem("/admin/modules", "admin_modules", "Modules"),
            MenuItem("/admin/playsounds", "admin_playsounds", "Playsounds", "playsound" in enabled_modules),
            MenuItem("/admin/streamer", "admin_streamer", "Streamer Info"),
        ]

        data = {
            "enabled_modules": enabled_modules,
            "nav_bar_header": menu_items,
            "nav_bar_admin_header": admin_menu_items,
        }
        return data
