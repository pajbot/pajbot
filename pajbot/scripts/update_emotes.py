#!/usr/bin/env python3

import json
import logging
import os

import pymysql

log = logging.getLogger('pajbot')


def update_emote(cursor, code, image_id):
    cursor.execute('INSERT INTO `tb_emote` (`code`, `emote_id`) VALUES(%s, %s) ON DUPLICATE KEY UPDATE `code`=%s',
            (code, image_id, code))
    return True


def refresh_emotes(cursor):
    log.info('Refreshing emotes...')
    base_url = 'http://twitchemotes.com/api_cache/v2/{0}.json'
    endpoints = [
            'global',
            'subscriber',
            ]

    data = {}

    for endpoint in endpoints:
        log.debug('Refreshing {0} emotes...'.format(endpoint))
        try:
            data = json.loads(APIBase._get(base_url.format(endpoint)))
        except ValueError:
            log.error('Invalid data fetched while refreshing emotes...')
            return False

        if 'channels' in data:
            for channel in data['channels']:
                chan = data['channels'][channel]
                emotes = chan['emotes']

                emote_codes = []
                pending_emotes = []

                for emote in emotes:
                    emote_codes.append(emote['code'])
                    pending_emotes.append(emote)

                prefix = os.path.commonprefix(emote_codes)
                if len(prefix) > 1 and ''.join(filter(lambda c: c.isalpha(), prefix)).islower():
                    for emote in pending_emotes:
                        update_emote(cursor, emote['code'], emote['image_id'])
        else:
            for code in data['emotes']:
                update_emote(cursor, code, data['emotes'][code]['image_id'])

    cursor.close()

    return True

if __name__ == "__main__":
    import sys
    sys.path.append('../')
    from utils import load_config, init_logging
    init_logging('pajbot')
    from apiwrappers import APIBase
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c',
                        required=True,
                        help='Specify which config file to use '
                                '(default: config.ini)')

    args = parser.parse_args()
    config = load_config(args.config)

    sqlconn = pymysql.connect(unix_socket=config['sql']['unix_socket'], user=config['sql']['user'], passwd=config['sql']['passwd'], db=config['sql']['db'], charset='utf8')

    cursor = sqlconn.cursor()

    refresh_emotes(cursor)

    sqlconn.commit()
    cursor.close()
    sqlconn.close()
