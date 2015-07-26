import logging

from apiwrappers import APIBase

log = logging.getLogger('tyggbot')

def get_chatters(channel):
    url = 'http://tmi.twitch.tv/group/user/{0}/chatters'.format(channel)

    try:
        chatters_data = APIBase._get_json(url)
        chatters = chatters_data['chatters']

        return chatters['moderators'] + chatters['staff'] + chatters['admins'] + chatters['global_mods'] + chatters['viewers']
    except KeyError:
        log.exception('Caught exception while trying to get chatters for channel {0}'.format(channel))
    except Exception:
        log.exception('Uncaught exception in get_chatters')

    return []
