from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
import json


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()

    @classmethod
    def create_user(cls, auth_user, user_name):

        if User.query(User.email == auth_user.email()).get():
            raise endpoints.ConflictException(
                    'You have already registered!')

        if User.query(User.name == user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=user_name, email=auth_user.email())
        user.put()
        return user

    @classmethod
    def by_email(cls, email):
        user = cls.query(cls.email == email).get()
        return user


class Game(ndb.Model):
    class GameState(messages.Enum):
        WAITING_FOR_OPPONENT = 0
        PREPARING_BOARD = 1
        PLAYER_ONE_TURN = 2
        PLAYER_TWO_TURN = 3
        GAME_COMPLETE = 4
        GAME_CANCELLED = 5

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
    player_winner = ndb.KeyProperty(kind='User')
    last_update = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def create_game(cls, user, form):
        settings = form.get_assigned_value('rules') or cls.BoardRules()

        # Fix an issue with default values not saving until assigned.
        settings.width = settings.width
        settings.height = settings.height
        settings.ship_2 = settings.ship_2
        settings.ship_3 = settings.ship_3
        settings.ship_4 = settings.ship_4
        settings.ship_5 = settings.ship_5

        game = Game(
                player_one=user.key,
                game_state=cls.GameState.WAITING_FOR_OPPONENT,
                game_settings=settings
            )
        game.put()
        return game

    @classmethod
    def by_urlsafe(cls, urlsafe):
        try:
            return ndb.Key(urlsafe=urlsafe).get()
        except TypeError:
            raise endpoints.BadRequestException('Invalid Key')
        except Exception, e:
            if e.__class__.__name__ == 'ProtocolBufferDecodeError':
                raise endpoints.BadRequestException('Invalid Key')
            else:
                raise

    @classmethod
    def by_game_state(cls, game_state, limit=10):
        games = (
                cls.query()
                .filter(cls.game_state == game_state)
                .order(-cls.last_update)
                .fetch(limit)
            )
        return games

    @classmethod
    def get_active_games(cls, user, limit=10):
        games = (
            cls.query()
            .filter(ndb.OR(
                cls.player_one == user.key,
                cls.player_two == user.key
            ))
            .filter(
                cls.game_state.IN([
                    cls.GameState.WAITING_FOR_OPPONENT,
                    cls.GameState.PREPARING_BOARD,
                    cls.GameState.PLAYER_ONE_TURN,
                    cls.GameState.PLAYER_TWO_TURN
                ])
            )
            .order(-cls.last_update)
            .fetch()
        )
        return games

    def add_player(self, user):
        self.player_two = user.key
        self.game_state = Game.GameState.PREPARING_BOARD
        self.put()
        return self

    def has_player(self, user):
        return self.player_one == user.key or self.player_two == user.key

    def cancel_game(self):
        self.game_state = Game.GameState.GAME_CANCELLED
        self.put()
        return self

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


class Position(messages.Message):
    x = messages.IntegerField(1, required=True)
    y = messages.IntegerField(2, required=True)


class ShipPlacement(messages.Message):
    position = messages.MessageField(Position, 1, required=True)
    length = messages.IntegerField(2, required=True)
    vertical = messages.BooleanField(3, default=False)


class ShipPlacementForm(messages.Message):
    ships = messages.MessageField(ShipPlacement, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
