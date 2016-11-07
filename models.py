from protorpc import messages
from google.appengine.ext import ndb
import json


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    player_one = ndb.KeyProperty(required=True, kind='User')
    player_two = ndb.KeyProperty(kind='User')
    game_state = ndb.IntegerProperty(required=True, default=0)
    game_settings = ndb.JsonProperty(required=True)
    game_board = ndb.JsonProperty()
    game_history = ndb.JsonProperty()

    @classmethod
    def create_game(cls, user, form):
        rules = form.get_assigned_value('rules') or BoardRules()
        settings = {
            'width': rules.width,
            'height': rules.height,
            'ship_2': rules.ship_2,
            'ship_3': rules.ship_3,
            'ship_4': rules.ship_4,
            'ship_5': rules.ship_5
        }
        game = Game(
                player_one=user.key,
                game_state=0,
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
        rules = BoardRules()
        rules.width = self.game_settings['width']
        rules.height = self.game_settings['height']
        rules.ship_2 = self.game_settings['ship_2']
        rules.ship_3 = self.game_settings['ship_3']
        rules.ship_4 = self.game_settings['ship_4']
        rules.ship_5 = self.game_settings['ship_5']
        form.rules = rules
        return form


class RegisterUserForm(messages.Message):
    user_name = messages.StringField(1, required=True)


class BoardRules(messages.Message):
    width = messages.IntegerField(1, default=10)
    height = messages.IntegerField(2, default=10)
    ship_2 = messages.IntegerField(3, default=1)
    ship_3 = messages.IntegerField(4, default=2)
    ship_4 = messages.IntegerField(5, default=1)
    ship_5 = messages.IntegerField(6, default=1)


class NewGameForm(messages.Message):
    rules = messages.MessageField(BoardRules, 1)


class GameInfoForm(messages.Message):
    urlsafe_key = messages.StringField(1)
    player_one = messages.StringField(2)
    player_two = messages.StringField(3)
    game_state = messages.IntegerField(4)
    rules = messages.MessageField(BoardRules, 5)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
