import logging
from pajbot.managers.handler import HandlerManager

log = logging.getLogger("pajbot")


class SpotifyStreamLabsManager:
    def __init__(self, bot):
        self.bot = bot
        self.currentSong = {"title": None, "requestor": None}
        # Handlers
        HandlerManager.add_handler("resume_spotify", self.play_spotify)
        HandlerManager.add_handler("pause_spotify", self.pause_spotify)
        HandlerManager.add_handler("change_state", self.change_state)
        self.isPaused = False
        self.spotifyPreviouslyPlaying = False

    def change_state(self, state):
        self.isPaused = state

    def play_spotify(self):
        if self.spotifyPreviouslyPlaying:
            self.currentSong["title"] = None
            self.currentSong["requestedBy"] = None
            self.bot.spotify_player_api.play(self.bot.spotify_token_manager)

    def pause_spotify(self, requestor, title):
        isPlaying = self.bot.spotify_player_api.state(self.bot.spotify_token_manager)[0]
        self.spotifyPreviouslyPlaying = isPlaying or self.spotifyPreviouslyPlaying
        self.currentSong["title"] = title
        self.currentSong["requestor"] = requestor
        self.bot.spotify_player_api.pause(self.bot.spotify_token_manager)

    def getCurrentSong(self):
        return_song_data = {"playing": False, "spotify": False, "title": "", "artists": []}
        if self.currentSong["title"] is None:
            isPlaying, name, artists = self.bot.spotify_player_api.state(self.bot.spotify_token_manager)
            if not isPlaying:
                return return_song_data

            return_song_data["playing"] = True
            return_song_data["spotify"] = True
            return_song_data["title"] = name
            return_song_data["artists"] = artists
            return return_song_data

        return_song_data["playing"] = True
        return_song_data["title"] = self.currentSong["title"]
        return_song_data["requestor"] = self.currentSong["requestor"]
        return return_song_data
