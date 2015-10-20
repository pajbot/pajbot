import logging

log = logging.getLogger('tyggbot')


def update_database(sqlconn):
    """
    This function will handle all database changes

    TODO: Also let it create all tables if none exist.
    """
    cursor = sqlconn.cursor()

    try:
        cursor.execute("SELECT `value` FROM `tb_settings` WHERE `setting`='db_version'")
    except:
        pass

    latest_db_version = 20
    version = 0

    if cursor.rowcount > 0:
        version = int(cursor.fetchone()[0])
    else:
        # No db version specified
        version = -1

    while version < latest_db_version:
        version += 1
        queries = []

        if version == 0:
            # Create `tb_commands` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_commands` ( `id` int(11) NOT NULL, `level` int(11) NOT NULL DEFAULT '100' COMMENT 'authentication level required. 100 = user, 1000 = admin', `action` text COLLATE utf8_unicode_ci NOT NULL COMMENT 'the action to be performed if the command is executed', `extra_args` text COLLATE utf8_unicode_ci, `command` text COLLATE utf8_unicode_ci NOT NULL COMMENT 'excluding the !', `description` text COLLATE utf8_unicode_ci, `delay_all` int(11) NOT NULL DEFAULT '5' COMMENT 'The minimum amount of time (in seconds) to wait before executing this command again.', `delay_user` int(11) NOT NULL DEFAULT '15' COMMENT 'The minimum amount of time (in seconds) to wait before responding to this command to the same user.', `enabled` tinyint(1) NOT NULL DEFAULT '1', `num_uses` int(11) NOT NULL DEFAULT '0', `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP, `last_updated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Create `tb_filters` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_filters` ( `id` int(11) NOT NULL, `name` varchar(128) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'Filter Name', `type` varchar(64) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'regex', `action` text COLLATE utf8_unicode_ci NOT NULL, `extra_args` text COLLATE utf8_unicode_ci, `filter` text COLLATE utf8_unicode_ci NOT NULL, `source` text COLLATE utf8_unicode_ci, `enabled` tinyint(1) NOT NULL DEFAULT '1', `num_uses` int(11) NOT NULL DEFAULT '0') ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Create `tb_idata` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_idata` ( `id` varchar(64) COLLATE utf8_unicode_ci NOT NULL, `value` int(11) NOT NULL, `type` set('value','nl','emote_stats') COLLATE utf8_unicode_ci NOT NULL DEFAULT 'value') ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Create `tb_ignored` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_ignores` ( `id` int(11) NOT NULL, `username` varchar(128) COLLATE utf8_unicode_ci NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Create `tb_settings` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_settings` ( `id` int(11) NOT NULL, `setting` varchar(128) COLLATE utf8_unicode_ci NOT NULL, `value` text COLLATE utf8_unicode_ci NOT NULL, `type` set('int','string','list','bool') COLLATE utf8_unicode_ci NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Create `tb_user` table
            queries.append("CREATE TABLE IF NOT EXISTS `tb_user` ( `id` int(11) NOT NULL, `username` varchar(128) COLLATE utf8_unicode_ci NOT NULL, `username_raw` varchar(128) COLLATE utf8_unicode_ci DEFAULT NULL COMMENT 'Raw username, if they ever let us fetch the \"case-specific\" username from the IRC connection.', `level` int(11) NOT NULL DEFAULT '100' COMMENT 'Access level, this determines what commands the user can access. 100 = User. 250 = Regular, 500 = Moderator, 1000 = Admin, 2000 = Super admin', `num_lines` int(11) NOT NULL DEFAULT '0' COMMENT 'Number of lines the user has written in chat.') ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;")

            # Add primary keys to tables
            queries.append("ALTER TABLE `tb_commands` ADD PRIMARY KEY (`id`);")
            queries.append("ALTER TABLE `tb_filters` ADD PRIMARY KEY (`id`);")
            queries.append("ALTER TABLE `tb_idata` ADD PRIMARY KEY (`id`);")
            queries.append("ALTER TABLE `tb_ignores` ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `username` (`username`);")
            queries.append("ALTER TABLE `tb_settings` ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `setting` (`setting`);")
            queries.append("ALTER TABLE `tb_user` ADD PRIMARY KEY (`id`), ADD KEY `username` (`username`);")

            # Set auto-increment values
            queries.append("ALTER TABLE `tb_commands` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;")
            queries.append("ALTER TABLE `tb_filters` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;")
            queries.append("ALTER TABLE `tb_ignores` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;")
            queries.append("ALTER TABLE `tb_settings` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;")
            queries.append("ALTER TABLE `tb_user` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;")

            # Insert db_version into tb_settings
            queries.append("INSERT INTO `tb_settings` (`setting`, `value`, `type`) VALUES ('db_version', 0, 'int')")
        elif version == 1:
            queries.append("ALTER TABLE `tb_user` ADD `subscriber` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Keeps track of whether the user is a subscriber or not. This is only updated when the user actually types in chat, so the information might be outdated if the person stops typing in chat.' ;")
        elif version == 2:
            queries.append("CREATE TABLE `tb_emote` ( `id` INT NOT NULL AUTO_INCREMENT , `code` VARCHAR(64) NOT NULL COMMENT 'All regexes for emotes are escaped. so if the emote code is (ditto) the regex will be \\(ditto\\)' , `deque` TEXT NULL DEFAULT NULL COMMENT 'Dump of the emote deque, so the state can be saved properly' , `pm_record` INT NOT NULL DEFAULT '0' , `tm_record` INT NOT NULL DEFAULT '0' , `count` INT NOT NULL DEFAULT '0', PRIMARY KEY (`id`) ) ENGINE = InnoDB;")
        elif version == 3:
            queries.append("CREATE TABLE `tb_motd` ( `id` INT NOT NULL AUTO_INCREMENT , `message` VARCHAR(400) NOT NULL , `enabled` BOOLEAN NOT NULL DEFAULT TRUE , PRIMARY KEY (`id`) ) ENGINE = InnoDB;")
        elif version == 4:
            queries.append("ALTER TABLE `tb_user` ADD `points` INT NOT NULL DEFAULT '0' AFTER `level`;")
        elif version == 5:
            queries.append("ALTER TABLE `tb_user` ADD `last_seen` DATETIME NULL DEFAULT NULL , ADD `last_active` DATETIME NULL DEFAULT NULL ;")
        elif version == 6:
            queries.append("ALTER TABLE `tb_user` ADD `minutes_in_chat_online` INT NOT NULL DEFAULT '0' , ADD `minutes_in_chat_offline` INT NOT NULL DEFAULT '0' ;")
        elif version == 7:
            queries.append("ALTER TABLE `tb_commands` ADD `cost` INT NOT NULL DEFAULT '0' AFTER `num_uses`;")
        elif version == 8:
            queries.append("ALTER TABLE `tb_commands` ADD `can_execute_with_whisper` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Decides whether the command can be used through whispers or not.' AFTER `cost`;")
        elif version == 9:
            queries.append("CREATE TABLE `tb_whisper_account` ( `username` VARCHAR(128) NOT NULL , `oauth` VARCHAR(128) NOT NULL , `enabled` BOOLEAN NOT NULL DEFAULT TRUE , PRIMARY KEY (`username`) ) ENGINE = InnoDB;")
        elif version == 10:
            queries.append("ALTER TABLE `tb_emote` ADD `emote_id` INT NULL DEFAULT NULL AFTER `id`, ADD UNIQUE (`emote_id`) ;")
        elif version == 11:
            queries.append("ALTER TABLE `tb_emote` ADD `emote_hash` VARCHAR(32) NULL DEFAULT NULL COMMENT 'Used for BTTV Emotes.' AFTER `emote_id`;")
        elif version == 12:
            queries.append("ALTER TABLE `tb_emote` DROP `deque`, DROP `pm_record`;")
        elif version == 13:
            queries.append("CREATE TABLE `tb_link_data` ( `id` INT NOT NULL AUTO_INCREMENT , `url` TEXT NOT NULL , `times_linked` INT NOT NULL DEFAULT '0' , `first_linked` DATETIME NOT NULL , `last_linked` DATETIME NOT NULL , PRIMARY KEY (`id`) ) ENGINE = InnoDB COMMENT = 'Stores statistics about links that are posted in the twitch chat.';")
        elif version == 14:
            queries.append("CREATE TABLE `tb_link_blacklist` ( `domain` VARCHAR(256) NOT NULL , `path` TEXT NOT NULL ) ENGINE = InnoDB COMMENT = 'Stores a list of blacklisted links.';")
            queries.append("CREATE TABLE `tb_link_whitelist` ( `domain` VARCHAR(256) NOT NULL , `path` TEXT NOT NULL ) ENGINE = InnoDB COMMENT = 'Stores a list of whitelisted links.';")
        elif version == 15:
            queries.append("ALTER TABLE `tb_link_blacklist` ADD COLUMN level int(11) DEFAULT 1;")
        elif version == 16:
            values = ['stream_status', 'last_online', 'last_offline']
            for value in values:
                cursor.execute("SELECT * FROM `tb_idata` WHERE `id`='" + value + "' AND `type`='value'")
                if cursor.rowcount == 0:
                    cursor.execute("INSERT INTO `tb_idata` (`id`, `type`, `value`) VALUES ('" + value + "', 'value', 0)")
                else:
                    log.info('{0} already added to the database.'.format(value))
        elif version == 17:
            queries.append("CREATE TABLE `tb_deck` ( `id` INT NOT NULL AUTO_INCREMENT , `name` VARCHAR(256) NOT NULL DEFAULT '' , `class` VARCHAR(64) NOT NULL DEFAULT 'undefined' , `link` VARCHAR(128) NOT NULL , `first_used` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP , `last_used` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP , `times_used` INT NOT NULL DEFAULT '0', PRIMARY KEY (`id`) ) ENGINE = InnoDB;")
        elif version == 18:
            queries.append("ALTER TABLE `tb_user` ADD `twitch_access_token` VARCHAR(128) NULL DEFAULT NULL , ADD `twitch_refresh_token` VARCHAR(128) NULL DEFAULT NULL , ADD `discord_user_id` VARCHAR(32) NULL DEFAULT NULL ;")
        elif version == 19:
            queries.append("ALTER TABLE `tb_commands` ADD `sub_only` BOOLEAN NOT NULL DEFAULT FALSE AFTER `can_execute_with_whisper`;")
        elif version == 20:
            queries.append("CREATE TABLE `tb_twitter_following` ( `id` INT NOT NULL AUTO_INCREMENT , `username` VARCHAR(32) NOT NULL , PRIMARY KEY (`id`) ) ENGINE = InnoDB;")

        for query in queries:
            cursor.execute(query)

        log.info('Updating db version to {0}'.format(version))
        cursor.execute("UPDATE `tb_settings` SET `value`=%s WHERE `setting`='db_version'", (version))

    log.info('db version: {0}'.format(version))
