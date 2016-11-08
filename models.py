import endpoints
from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
import json


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    games_won = ndb.IntegerProperty(required=True, default=0)
    games_played = ndb.IntegerProperty(required=True, default=0)
    win_ratio = ndb.ComputedProperty(
        lambda u: 1. * u.games_played and 1. * u.games_won / u.games_played)

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

    @classmethod
    def get_user_rankings(cls, limit=10):
        rankings = cls.query().order(-cls.win_ratio).fetch(limit)
        form_rankings = []
        for ranking in rankings:
            form_rankings.append(Ranking(
                    player=ranking.name,
                    games_won=ranking.games_won,
                    games_played=ranking.games_played,
                    win_ratio=ranking.win_ratio
                ))
        return RankingForm(rankings=form_rankings)


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
                game_settings=settings,
                game_board={},
                game_history=[]
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

    def player_place_ships(self, user, form):
        if not self.game_state == Game.GameState.PREPARING_BOARD:
            raise endpoints.ForbiddenException(
                    'Game is not accepting ship placements')
        # Validate ship placements
        ships = []
        ship_coord_set = set()
        ship_counts = {
            2: self.game_settings.ship_2,
            3: self.game_settings.ship_3,
            4: self.game_settings.ship_4,
            5: self.game_settings.ship_5
        }
        total_coords = (ship_counts[2] * 2 + ship_counts[3] * 3 +
                        ship_counts[4] * 4 + ship_counts[5] * 5)

        for ship in form.ships:
            if ship.length not in [2, 3, 4, 5]:
                raise endpoints.BadRequestException('Invalid ship length.')
            ship_counts[ship.length] -= 1
            x = ship.position.x
            y = ship.position.y
            max_x = not ship.vertical and x+ship.length-1 or x
            max_y = ship.vertical and y+ship.length-1 or y
            if (x < 1 or max_x > self.game_settings.width or
                    y < 1 or max_y > self.game_settings.height):
                raise endpoints.BadRequestException('Ship out of bounds.')

            s = []
            for i in xrange(x, max_x+1):
                for j in xrange(y, max_y+1):
                    coord = '{},{}'.format(i, j)
                    s.append(coord)
                    ship_coord_set.add(coord)
            ships.append(s)

        # Check for correct number of ships
        if (ship_counts[2] or ship_counts[3] or
                ship_counts[4] or ship_counts[5]):
            raise endpoints.BadRequestException('Invalid ship count.')

        # Check for ship collisions
        if len(ship_coord_set) != total_coords:
            raise endpoints.BadRequestException('Ships cannot overlap.')

        # Save the ships to game board
        if self.player_one == user.key:
            if 'player_one' in self.game_board:
                raise endpoints.ConflictException(
                    'You have already submitted your ships.')
            self.game_board['player_one'] = ships
        elif self.player_two == user.key:
            if 'player_two' in self.game_board:
                raise endpoints.ConflictException(
                    'You have already submitted your ships.')
            self.game_board['player_two'] = ships
        else:
            raise endpoints.UnauthorizedException(
                'You are not a player of this game.')

        if 'player_one' in self.game_board and 'player_two' in self.game_board:
            self.game_state = Game.GameState.PLAYER_ONE_TURN
            message = StringMessage(
                message=('Your ship placement has been set.'
                         ' Game is ready to begin'))
        else:
            message = StringMessage(
                message=('Your ship placement has been set.'
                         ' Waiting for opponent to place ships.'))
        self.put()
        return message

    def player_action(self, user, form):
        if self.game_state not in [Game.GameState.PLAYER_ONE_TURN,
                                   Game.GameState.PLAYER_TWO_TURN]:
            raise endpoints.ForbiddenException(
                    'Game is not in play.')

        if self.player_one == user.key:
            ships = self.game_board['player_two']
            if self.game_state == Game.GameState.PLAYER_TWO_TURN:
                raise endpoints.ForbiddenException(
                    'It is not your turn.')
        elif self.player_two == user.key:
            ships = self.game_board['player_one']
            if self.game_state == Game.GameState.PLAYER_ONE_TURN:
                raise endpoints.ForbiddenException(
                    'It is not your turn.')
        else:
            raise endpoints.UnauthorizedException(
                'You are not a player of this game.')

        x = form.x
        y = form.y
        if (x < 1 or x > self.game_settings.width or
                y < 1 or y > self.game_settings.height):
            raise endpoints.BadRequestException('Coordinates out of bounds.')

        coord = '{},{}'.format(x, y)
        message = StringMessage()
        hit = False
        for ship in ships:
            if coord in ship:
                hit = True
                ship.remove(coord)
                if(len(ship) == 0):
                    message.message = 'Ship sunk!'
                else:
                    message.message = 'Hit!'
                break
        if not hit:
            message.message = 'Miss.'

        # Switch turns
        if self.game_state == Game.GameState.PLAYER_ONE_TURN:
            self.game_state = Game.GameState.PLAYER_TWO_TURN
        else:
            self.game_state = Game.GameState.PLAYER_ONE_TURN
        self.game_history.append([user.name, coord, message.message])

        self.put()

        # Check remaining ships
        ships_remaining = 0
        for ship in ships:
            if len(ship) > 0:
                ships_remaining += 1

        if ships_remaining == 0:  # 0 remaining ships, game is over.
            message.message += ' You have won!'
            self.record_win(user.key)
        else:  # Game not over. Switch turns.
            message.message += ' {} ship{} remaining.'.format(
                ships_remaining,
                's' if ships_remaining > 1 else ''
                )

        return message

    @ndb.transactional(xg=True)
    def record_win(self, winner):
        # Get a new game instance in context of transaction
        game = self.key.get()
        p1 = game.player_one.get()
        p2 = game.player_two.get()
        p1.games_played += 1
        p2.games_played += 1

        game.player_winner = winner

        if game.player_winner == game.player_one:
            p1.games_won += 1
        else:
            p2.games_won += 1
        game.game_state = Game.GameState.GAME_COMPLETE
        game.put()
        p1.put()
        p2.put()

    def get_history(self):
        game_actions = []
        for action in self.game_history:
            game_action = GameAction()
            position = action[1].split(',')
            game_action.player = action[0]
            game_action.position = Position(
                x=int(position[0]),
                y=int(position[1]))
            game_action.result = action[2]
            game_actions.append(game_action)
        return GameHistoryForm(actions=game_actions)

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


class GameAction(messages.Message):
    player = messages.StringField(1, required=True)
    position = messages.MessageField(Position, 2, required=True)
    result = messages.StringField(3, required=True)


class GameHistoryForm(messages.Message):
    actions = messages.MessageField(GameAction, 1, repeated=True)


class Ranking(messages.Message):
    player = messages.StringField(1, required=True)
    games_won = messages.IntegerField(2, required=True)
    games_played = messages.IntegerField(3, required=True)
    win_ratio = messages.FloatField(4, required=True)


class RankingForm(messages.Message):
    rankings = messages.MessageField(Ranking, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
