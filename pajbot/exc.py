class FailedCommand(Exception):
    pass


class UserNotFound(Exception):
    pass


class InvalidLogin(Exception):
    pass


class InvalidPointAmount(Exception):
    pass


class TimeoutException(Exception):
    pass


class ManagerDisabled(Exception):
    pass


class InvalidState(Exception):
    pass


class InvalidVolume(Exception):
    pass


class InvalidSong(Exception):
    pass


class InvalidPlaylist(Exception):
    pass


class SongBanned(Exception):
    pass
