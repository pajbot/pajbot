import logging

from pajbot.models.command import Command
from pajbot.models.command import CommandExample
from pajbot.modules import BaseModule

log = logging.getLogger("pajbot")


class DeckModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Decks (Hearthstone)"
    DESCRIPTION = "Handles displaying/updating decks through commands and the website."
    CATEGORY = "Feature"

    def load_commands(self, **options):
        self.commands["setdeck"] = Command.raw_command(
            self.set_deck,
            level=420,
            delay_all=0,
            delay_user=0,
            description="Sets the deck that is currently playing.",
            examples=[
                CommandExample(
                    None,
                    "Add a new deck",
                    chat="user:!set deck http://i.imgur.com/rInqJv0.png\n"
                    "bot>user:This deck is a new deck. Its ID is 32",
                    description="This is the output if you set a deck which hasn't been set before.",
                ).parse(),
                CommandExample(
                    None,
                    "Set a pre-existing deck",
                    chat="user:!set deck http://i.imgur.com/rInqJv0.png\n"
                    "bot>user:Updated an already-existing deck. Its ID is 32",
                    description="This is the output if you set a deck which was added previously.",
                ).parse(),
            ],
        )
        self.commands["set"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="set",
            commands={"deck": self.commands["setdeck"]},
        )

        self.commands["update"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="update",
            commands={
                "deck": Command.raw_command(
                    self.update_deck,
                    level=420,
                    description="Updates an already-existing deck.",
                    examples=[
                        CommandExample(
                            None,
                            "Set the name and class of the current deck",
                            chat="user:!update deck --name Midrange Secret --class paladin\n"
                            "bot>user:Updated deck with ID 32. Updated name, class",
                        ).parse(),
                        CommandExample(
                            None,
                            "Updates the link of the current deck",
                            chat="user:!update deck --link http://i.imgur.com/QEVwrVV.png\n"
                            "bot>user:Updated deck with ID 32. Updated link",
                            description="Changes the link of the current deck. This could be used if you want to reupload the screenshot to imgur or something.",
                        ).parse(),
                        CommandExample(
                            None,
                            "Set the name and class of an old deck",
                            chat="user:!update deck --id 12 --name Aggro --class hunter\n"
                            "bot>user:Updated deck with ID 12. Updated name, class",
                            description="Updates the name and class of an old deck. Useful for whenever you need to clean up old decks.",
                        ).parse(),
                    ],
                )
            },
        )

        self.commands["remove"] = Command.multiaction_command(
            level=100,
            delay_all=0,
            delay_user=0,
            default=None,
            command="remove",
            commands={
                "deck": Command.raw_command(
                    self.remove_deck,
                    level=420,
                    description="Removes a deck with the given ID.",
                    examples=[
                        CommandExample(
                            None,
                            "Remove a deck by ID",
                            chat="user:!remove deck 123\n" "bot>user:Successfully removed the deck.",
                            description="The ID in this case is 123",
                        ).parse(),
                        CommandExample(
                            None,
                            "Remove a deck by URL",
                            chat="user:!remove deck http://i.imgur.com/rInqJv0.png\n"
                            "bot>user:Successfully removed the deck.",
                            description="The URL in this case is http://i.imgur.com/rInqJv0.png",
                        ).parse(),
                    ],
                )
            },
        )

    @staticmethod
    def set_deck(**options):
        """Dispatch method for setting the current deck.
        The command takes a link as its argument.
        If the link is an already-added deck, the deck should be set as the current deck
        and its last use date should be set to now.
        Usage: !setdeck imgur.com/abcdefgh"""

        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            deck, new_deck = bot.decks.set_current_deck(message)
            if new_deck is True:
                bot.whisper(source.username, "This deck is a new deck. Its ID is {deck.id}".format(deck=deck))
            else:
                bot.whisper(source.username, "Updated an already-existing deck. Its ID is {deck.id}".format(deck=deck))

            bot.say("Successfully updated the latest deck.")
            return True

        return False

    @staticmethod
    def update_deck(**options):
        """Dispatch method for updating a deck.
        By default this will update things for the current deck, but you can update
        any deck assuming you know its ID.
        Usage: !updatedeck --name Midrange Secret --class paladin
        """

        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            options, response = bot.decks.parse_update_arguments(message)
            if options is False:
                bot.whisper(source.username, "Invalid update deck command")
                return False

            if "id" in options:
                deck = bot.decks.find(id=options["id"])
                # We remove id from options here so we can tell the user what
                # they have updated.
                del options["id"]
            else:
                deck = bot.decks.current_deck

            if deck is None:
                bot.whisper(source.username, "No valid deck to update.")
                return False

            if len(options) == 0:
                bot.whisper(source.username, "You have given me nothing to update with the deck!")
                return False

            bot.decks.update_deck(deck, **options)
            bot.whisper(
                source.username,
                "Updated deck with ID {deck.id}. Updated {list}".format(
                    deck=deck, list=", ".join([key for key in options])
                ),
            )

            return True
        else:
            bot.whisper(source.username, "Usage example: !updatedeck --name Midrange Secret --class paladin")
            return False

    @staticmethod
    def remove_deck(**options):
        """Dispatch method for removing a deck.
        Usage: !removedeck imgur.com/abcdef
        OR
        !removedeck 123
        """

        message = options["message"]
        bot = options["bot"]
        source = options["source"]

        if message:
            id = None
            try:
                id = int(message)
            except Exception:
                pass

            deck = bot.decks.find(id=id, link=message)

            if deck is None:
                bot.whisper(source.username, "No deck matching your parameters found.")
                return False

            try:
                bot.decks.remove_deck(deck)
                bot.whisper(source.username, "Successfully removed the deck.")
            except:
                log.exception("An exception occured while attempting to remove the deck")
                bot.whisper(source.username, "An error occured while removing your deck.")
                return False
            return True
        else:
            bot.whisper(source.username, "Usage example: !removedeck http://imgur.com/abc")
            return False
