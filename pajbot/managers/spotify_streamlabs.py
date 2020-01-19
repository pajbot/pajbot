import logging
from pajbot.managers.handler import HandlerManager
from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot import utils
import time

import sys
import json

log = logging.getLogger("pajbot")


class SpotifyStreamLabsManager:
    def __init__(self, bot):
        self.bot = bot
        self.currentSong = {"title": None}
        # Handlers
        HandlerManager.add_handler("resume_spotify", self.play_spotify)
        HandlerManager.add_handler("pause_spotify", self.pause_spotify)
        HandlerManager.add_handler("change_state", self.change_state)
        self.isPaused = False
        self.spotifyPreviouslyPlaying = False

    # BACKUP LIST FUNCTION START

    def change_state(self, state):
        self.isPaused = state

    def play_spotify(self):
        if self.spotifyPreviouslyPlaying:
            self.currentSong["title"] = None
            self.currentSong["requestedBy"] = None
            self.bot.spotify_api.play(self.bot.spotify_token_manager)

    def pause_spotify(self, title):
        isPlaying, name, artists = self.bot.spotify_api.state(self.bot.spotify_token_manager)
        self.spotifyPreviouslyPlaying = isPlaying or self.spotifyPreviouslyPlaying
        self.currentSong["title"] = title
        self.bot.spotify_api.pause(self.bot.spotify_token_manager)

    def getCurrentSong(self):
        return_song_data = {"playing": False, "spotify": False, "title": "", "artists": []}
        if self.currentSong["title"] is None:
            isPlaying, name, artists = self.bot.spotify_api.state(self.bot.spotify_token_manager)
            if not isPlaying:
                return return_song_data
            return_song_data["playing"] = True
            return_song_data["spotify"] = True
            return_song_data["title"] = name
            return_song_data["artists"] = artists
            return return_song_data
        return_song_data["playing"] = True
        return_song_data["title"] = self.currentSong["title"]
        return return_song_data
