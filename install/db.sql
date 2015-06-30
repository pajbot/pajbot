SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS `tb_commands` (
  `id` int(11) NOT NULL,
  `level` int(11) NOT NULL DEFAULT '100' COMMENT 'authentication level required. 100 = user, 1000 = admin',
  `action` text COLLATE utf8_unicode_ci NOT NULL COMMENT 'the action to be performed if the command is executed',
  `extra_args` text COLLATE utf8_unicode_ci,
  `command` text COLLATE utf8_unicode_ci NOT NULL COMMENT 'excluding the !',
  `description` text COLLATE utf8_unicode_ci,
  `delay_all` int(11) NOT NULL DEFAULT '5' COMMENT 'The minimum amount of time (in seconds) to wait before executing this command again.',
  `delay_user` int(11) NOT NULL DEFAULT '15' COMMENT 'The minimum amount of time (in seconds) to wait before responding to this command to the same user.',
  `enabled` tinyint(1) NOT NULL DEFAULT '1',
  `num_uses` int(11) NOT NULL DEFAULT '0',
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_updated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `tb_filters` (
  `id` int(11) NOT NULL,
  `name` varchar(128) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'Filter Name',
  `type` varchar(64) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'regex',
  `action` text COLLATE utf8_unicode_ci NOT NULL,
  `extra_args` text COLLATE utf8_unicode_ci,
  `filter` text COLLATE utf8_unicode_ci NOT NULL,
  `source` text COLLATE utf8_unicode_ci,
  `enabled` tinyint(1) NOT NULL DEFAULT '1',
  `num_uses` int(11) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `tb_idata` (
  `id` varchar(64) COLLATE utf8_unicode_ci NOT NULL,
  `value` int(11) NOT NULL,
  `type` set('value','nl','emote_stats') COLLATE utf8_unicode_ci NOT NULL DEFAULT 'value'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `tb_ignores` (
  `id` int(11) NOT NULL,
  `username` varchar(128) COLLATE utf8_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `tb_settings` (
  `id` int(11) NOT NULL,
  `setting` varchar(128) COLLATE utf8_unicode_ci NOT NULL,
  `value` text COLLATE utf8_unicode_ci NOT NULL,
  `type` set('int','string','list','bool') COLLATE utf8_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `tb_user` (
  `id` int(11) NOT NULL,
  `username` varchar(128) COLLATE utf8_unicode_ci NOT NULL,
  `username_raw` varchar(128) COLLATE utf8_unicode_ci DEFAULT NULL COMMENT 'Raw username, if they ever let us fetch the "case-specific" username from the IRC connection.',
  `level` int(11) NOT NULL DEFAULT '100' COMMENT 'Access level, this determines what commands the user can access. 100 = User. 250 = Regular, 500 = Moderator, 1000 = Admin, 2000 = Super admin',
  `num_lines` int(11) NOT NULL DEFAULT '0' COMMENT 'Number of lines the user has written in chat.'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;


ALTER TABLE `tb_commands`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `tb_filters`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `tb_idata`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `tb_ignores`
  ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `username` (`username`);

ALTER TABLE `tb_settings`
  ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `setting` (`setting`);

ALTER TABLE `tb_user`
  ADD PRIMARY KEY (`id`), ADD KEY `username` (`username`);


ALTER TABLE `tb_commands`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `tb_filters`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `tb_ignores`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `tb_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `tb_user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
