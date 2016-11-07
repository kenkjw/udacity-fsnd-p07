from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
import json


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    class GameState(messages.Enum):
        WAITING_FOR_OPPONENT = 0
        PREPARING_BOARD = 1
        PLAYER_1_TURN = 2
        PLAYER_2_TURN = 3
        GAME_COMPLETE = 4

    class BoardRules(messages.Message):
        width = messages.IntegerField(1, default=10)
        height = messages.IntegerField(2, default=10)
        ship_2 = messages.IntegerField(3, default=1)
        ship_3 = messages.IntegerField(4, default=2)
        ship_4 = messages.IntegerField(5, default=1)
        ship_5 = messages.IntegerField(6, default=1)

    player_one = ndb.KeyProperty(required=True, kind='User')
    player_two = ndb.KeyProperty(kind='User')
    game_state = msgprop.EnumProperty(GameState, required=True)
    game_settings = msgprop.MessageProperty(BoardRules, required=True)
    game_board = ndb.JsonProperty()
    game_history = ndb.JsonProperty()

    @classmethod
    def create_game(cls, user, form):
        settings = form.get_assigned_value('rules') or Game.BoardRules()

        # Fix an issue with default values not saving until assigned.
        settings.width = settings.width
        settings.height = settings.height
        settings.ship_2 = settings.ship_2
        settings.ship_3 = settings.ship_3
        settings.ship_4 = settings.ship_4
        settings.ship_5 = settings.ship_5

        game = Game(
                player_one=user.key,
                game_state=Game.GameState.WAITING_FOR_OPPONENT,
                game_settings=settings
            )
        game.put()
        return game

    def to_form(self):
        """Returns a GameForm representation of the Game"""
        form = GameInfoForm()
        form.urlsafe_key = self.key.urlsafe()
        form.player_one = self.player_one.get().name
        form.player_two = self.player_two and self.player_two.get().name
        form.game_state = self.game_state
        form.rules = self.game_settings
        return form


class RegisterUserForm(messages.Message):
    user_name = messages.StringField(1, required=True)


class NewGameForm(messages.Message):
    rules = messages.MessageField(Game.BoardRules, 1)


class GameInfoForm(messages.Message):
    urlsafe_key = messages.StringField(1)
    player_one = messages.StringField(2)
    player_two = messages.StringField(3)
    game_state = messages.EnumField(Game.GameState, 4,
                                    default='WAITING_FOR_OPPONENT')
    rules = messages.MessageField(Game.BoardRules, 5)


class GameListForm(messages.Message):
    games = messages.MessageField(GameInfoForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
