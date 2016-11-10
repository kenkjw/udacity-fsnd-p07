"""models.py - This file contains the class definitions for the Datastore
entities used by the BattleShips Game. """

import datetime
import endpoints
from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop


class User(ndb.Model):
    """ Google AppEngine Datastore Entity representing a User.

    Properties:
        name: A string property representing the username of the User.
        email: A string property representing the user's email.
        games_won: An integer property count of the user's total wins.
        games_played: An integer property count of the user's total
            completed games.
        win_ratio: A computed property float value of games_won/games_played.
    """
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    games_won = ndb.IntegerProperty(required=True, default=0)
    games_played = ndb.IntegerProperty(required=True, default=0)
    win_ratio = ndb.ComputedProperty(
        lambda u: 1. * u.games_played and 1. * u.games_won / u.games_played)

    @classmethod
    def create_user(cls, auth_user, user_name):
        """ Register a username to a user's email address"""
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
        if not user:
            raise endpoints.UnauthorizedException(
                'You must register a user name first.')
        return user

    @classmethod
    def get_user_rankings(cls, limit=10):
        """ Returns a RankingForm of a User's match history """
        # Query for users ordering by win ratio
        rankings = cls.query().order(-cls.win_ratio).fetch(limit)

        # Create the form
        form_rankings = []
        for ranking in rankings:
            form_rankings.append(Ranking(
                    player=ranking.name,
                    games_won=ranking.games_won,
                    games_played=ranking.games_played,
                    win_ratio=ranking.win_ratio
                ))
        return form_rankings


class Game(ndb.Model):
    """ Google AppEngine Datastore Entity representing a Battleship match.

    Properties:
        player_one: ndb Key to the player that hosted the game.
        player_two: ndb Key to the player that joined the game.
        game_state: GameState representing the state of the game.
        game_settings: The BoardRules set for the game at creation.
        game_board: JsonProperty that holds the players' ship positions.
            A dictionary in the form:
            {
                'player_one': [{ship list}]
                'player_two': [{ship list}]
            }
                ship_list: A list of all the ships in the players fleet.
                    A ship is a list of string representations of each
                    coordinate that the ship occupies.
        game_history: JsonProperty that holds the history of players' guesses.
            A python list of each guess in the form:
                [{user_name},{coords},{result}]
                    user_name: string of the name of user who made guess
                    coords: string in form 'x,y' of user's guess
                    result: string result of the guess. Typically hit or miss.
        player_winner: ndb Key to the winner of the match.
        last_update: A datetime of the last time the game was updated.
    """
    class GameState(messages.Enum):
        """ Enum for representing the different states of the game. """
        # Game has just been created and is waiting for second player.
        WAITING_FOR_OPPONENT = 0
        # Second player has just joined the game. Waiting for ship placements.
        PREPARING_BOARD = 1
        # Waiting for player one to guess.
        PLAYER_ONE_TURN = 2
        # Waiting for player two to guess.
        PLAYER_TWO_TURN = 3
        # A player has sunk all their opponent's ships.
        GAME_COMPLETE = 4
        # A player has cancelled the game.
        GAME_CANCELLED = 5

    class BoardRules(messages.Message):
        """ Message that describes the rules of a game.

        Properties:
            width: The width of the game board. Must be between 8-20.
            height: The height of the game board. Must be between 8-20.
            ship_2: The number of ships of length 2. Must be between 0-5.
            ship_3: The number of ships of length 3. Must be between 0-5.
            ship_4: The number of ships of length 4. Must be between 0-5.
            ship_5: The number of ships of length 5. Must be between 0-5.
        """
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
        """ Creates a new Game.

        Args:
            user: User that is creating the game
            form: NewGameForm containing the game's rules

        Returns:
            Returns the newly created Game.
        """

        settings = form.get_assigned_value('rules') or cls.BoardRules()

        # Fix an issue with default values not saving until assigned.
        settings.width = settings.width
        settings.height = settings.height
        settings.ship_2 = settings.ship_2
        settings.ship_3 = settings.ship_3
        settings.ship_4 = settings.ship_4
        settings.ship_5 = settings.ship_5

        # Check that rules are valid
        if (settings.width < 8 or
                settings.width > 20 or
                settings.height < 8 or
                settings.height > 20):
            raise endpoints.BadRequestException(
                'Board dimensions must be between 8-20')
        if (settings.ship_2 < 0 or
                settings.ship_2 > 5 or
                settings.ship_3 < 0 or
                settings.ship_3 > 5 or
                settings.ship_4 < 0 or
                settings.ship_4 > 5 or
                settings.ship_5 < 0 or
                settings.ship_5 > 5):
            raise endpoints.BadRequestException(
                'Ship count must be between 0-5')
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
        """ Search for a game by its urlsafe key """
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
        """ Search for games by their game state """
        games = (
                cls.query()
                .filter(cls.game_state == game_state)
                .order(-cls.last_update)
                .fetch(limit)
            )
        return games

    @classmethod
    def get_active_games(cls, user, limit=10):
        """ Search for games that are not complete or cancelled. """
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

    @classmethod
    def get_inactive_games(cls):
        """ Search for active games that have not been updated in more than
        an hour. Limit to games """
        one_hour_ago = datetime.datetime.now() + datetime.timedelta(hours=-1)
        games = (
            cls.query()
            .filter(
                cls.game_state.IN([
                    cls.GameState.WAITING_FOR_OPPONENT,
                    cls.GameState.PREPARING_BOARD,
                    cls.GameState.PLAYER_ONE_TURN,
                    cls.GameState.PLAYER_TWO_TURN
                ]))
            .filter(cls.last_update <= one_hour_ago)
            .order(-cls.last_update)
            .fetch()
        )
        return games

    def add_player(self, user):
        """ Add a second player to a game. """
        if not self.game_state == Game.GameState.WAITING_FOR_OPPONENT:
            raise endpoints.ForbiddenException(
                    'Game is not accepting additional players.')
        if self.player_one == user.key:
            raise endpoints.ConflictException('You cannot join your own game.')
        self.player_two = user.key
        self.game_state = Game.GameState.PREPARING_BOARD
        self.put()
        return self

    def has_player(self, user):
        """ Check that a user is one of the two players of the game. """
        return self.player_one == user.key or self.player_two == user.key

    def player_place_ships(self, user, form):
        """ Save a user's ship placements

        Args:
            user: User that owns the ship
            form: ShipPlacementForm of the ships

        Returns:
            A StringMessage of the resulting state of the game.

        Raises:
            ForbiddenException:
                -If the game is not in PREPARING_BOARD state.
            BadRequestException:
                -If the ship data is invalid.
            ConflictException:
                -If the user has already submitted ships.
            UnauthorizedException:
                -If the user is not a player of the game.
        """
        # Check that the game state is correct
        if not self.game_state == Game.GameState.PREPARING_BOARD:
            raise endpoints.ForbiddenException(
                    'Game is not accepting ship placements')

        ships = []
        # Keep a set of coordinates to check for overlap.
        ship_coord_set = set()
        # The count of each ship length
        ship_counts = {
            2: self.game_settings.ship_2,
            3: self.game_settings.ship_3,
            4: self.game_settings.ship_4,
            5: self.game_settings.ship_5
        }
        # The total unique coordinates of ships.
        total_coords = (ship_counts[2] * 2 + ship_counts[3] * 3 +
                        ship_counts[4] * 4 + ship_counts[5] * 5)

        for ship in form.ships:
            if ship.length not in [2, 3, 4, 5]:
                raise endpoints.BadRequestException('Invalid ship length.')
            # Decrement ship count to keep track of total number of ships
            ship_counts[ship.length] -= 1
            x = ship.position.x
            y = ship.position.y

            # Check the ship lies within the board bounds.
            max_x = not ship.vertical and x+ship.length-1 or x
            max_y = ship.vertical and y+ship.length-1 or y
            if (x < 1 or max_x > self.game_settings.width or
                    y < 1 or max_y > self.game_settings.height):
                raise endpoints.BadRequestException('Ship out of bounds.')

            # Save the ship as an array of strings of their coordinates.
            s = []
            for i in xrange(x, max_x+1):
                for j in xrange(y, max_y+1):
                    coord = '{},{}'.format(i, j)
                    s.append(coord)
                    # Add the string to set for checking overlap
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
                # User has already submitted
                raise endpoints.ConflictException(
                    'You have already submitted your ships.')
            self.game_board['player_one'] = ships
        elif self.player_two == user.key:
            if 'player_two' in self.game_board:
                # User has already submitted
                raise endpoints.ConflictException(
                    'You have already submitted your ships.')
            self.game_board['player_two'] = ships
        else:
            # User wasn't a player of the game
            raise endpoints.UnauthorizedException(
                'You are not a player of this game.')

        if 'player_one' in self.game_board and 'player_two' in self.game_board:
            # Both players have submitted their ships. Game begins.
            self.game_state = Game.GameState.PLAYER_ONE_TURN
            message = StringMessage(
                message=('Your ship placement has been set.'
                         ' Game is ready to begin'))
        else:
            # Only one player has submitted.
            message = StringMessage(
                message=('Your ship placement has been set.'
                         ' Waiting for opponent to place ships.'))
        self.put()
        return message

    def player_guess(self, user, form):
        """ Record a player's guess.

        Args:
            user: User taking the guess.
            form: Position of the user's guess.

        Returns:
            A StringMessage of the result of the guess.

        Raises:
            ForbiddenException:
                -If the game is in wrong state.
            UnauthorizedException:
                -If the user is not a player of the game.
            BadRequestException:
                -If the coordinates are out of bounds.

        """
        # Check that game state is correct.
        if self.game_state not in [Game.GameState.PLAYER_ONE_TURN,
                                   Game.GameState.PLAYER_TWO_TURN]:
            raise endpoints.ForbiddenException(
                    'Game is not in play.')
        # Check that it is correct player and get opposite player's ships.
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
            # User is not a player of the game.
            raise endpoints.UnauthorizedException(
                'You are not a player of this game.')

        x = form.x
        y = form.y
        # Check that guess is inbounds.
        if (x < 1 or x > self.game_settings.width or
                y < 1 or y > self.game_settings.height):
            raise endpoints.BadRequestException('Coordinates out of bounds.')

        # String representation of the guess.
        coord = '{},{}'.format(x, y)
        message = StringMessage()

        # Check guess against ships.
        hit = False
        for ship in ships:
            if coord in ship:
                # Guess matches a ship coordinate.
                hit = True
                # Remove coordinate from ship.
                ship.remove(coord)
                # Check if ship has remaining coordinates.
                if(len(ship) == 0):
                    # Ship has no remaining coordinates.
                    message.message = 'Ship sunk!'
                else:
                    message.message = 'Hit!'
                break
        if not hit:
            # Ship was not hit.
            message.message = 'Miss.'

        # Switch turns
        if self.game_state == Game.GameState.PLAYER_ONE_TURN:
            self.game_state = Game.GameState.PLAYER_TWO_TURN
        else:
            self.game_state = Game.GameState.PLAYER_ONE_TURN

        # Save the result into the game's history
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
        else:  # Game not over.
            message.message += ' {} ship{} remaining.'.format(
                ships_remaining,
                's' if ships_remaining > 1 else ''
                )

        return message

    @ndb.transactional(xg=True)
    def record_win(self, winner):
        """ Transaction for setting game to complete and updating
        player records """
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
        """ Get the player guess history of the game. """
        game_guesses = []
        for guess in self.game_history:
            game_guess = GameGuess()
            position = guess[1].split(',')
            game_guess.player = guess[0]
            game_guess.position = Position(
                x=int(position[0]),
                y=int(position[1]))
            game_guess.result = guess[2]
            game_guesses.append(game_guess)
        return game_guesses

    def cancel_game(self):
        """ Cancels a game in progress """
        if self.game_state == Game.GameState.GAME_COMPLETE:
            raise endpoints.ForbiddenException(
                    'Cannot cancel a completed game.')
        self.game_state = Game.GameState.GAME_CANCELLED
        self.put()
        return self

    def to_form(self):
        """Returns a GameInfoForm representation of the Game"""
        form = GameInfoForm()
        form.urlsafe_key = self.key.urlsafe()
        form.player_one = self.player_one.get().name
        form.player_two = self.player_two and self.player_two.get().name
        form.game_state = self.game_state
        form.rules = self.game_settings
        return form


class RegisterUserForm(messages.Message):
    """ Form used when registering a user's name """
    user_name = messages.StringField(1, required=True)


class NewGameForm(messages.Message):
    """ Form used when creating a new game """
    rules = messages.MessageField(Game.BoardRules, 1)


class GameInfoForm(messages.Message):
    """ Form used when returning a game's info """
    urlsafe_key = messages.StringField(1)
    player_one = messages.StringField(2)
    player_two = messages.StringField(3)
    game_state = messages.EnumField(Game.GameState, 4,
                                    default='WAITING_FOR_OPPONENT')
    rules = messages.MessageField(Game.BoardRules, 5)


class GameListForm(messages.Message):
    """ Form used when returning a list of games' info """
    games = messages.MessageField(GameInfoForm, 1, repeated=True)


class Position(messages.Message):
    """ Message representing coordinates """
    x = messages.IntegerField(1, required=True)
    y = messages.IntegerField(2, required=True)


class ShipPlacement(messages.Message):
    """ Message representing placement of a ship

    Properties:
        position: Position message of the ship's upper-left position.
        length: The length of the ship. Should be between 2 and 5.
        vertical: Orientation of ship. True=Vertical, False=Horizontal.
    """
    position = messages.MessageField(Position, 1, required=True)
    length = messages.IntegerField(2, required=True)
    vertical = messages.BooleanField(3, default=False)


class ShipPlacementForm(messages.Message):
    """ Form used for a list of ShipPlacements """
    ships = messages.MessageField(ShipPlacement, 1, repeated=True)


class GameGuess(messages.Message):
    """ Message representing the result of a user's guess """
    player = messages.StringField(1, required=True)
    position = messages.MessageField(Position, 2, required=True)
    result = messages.StringField(3, required=True)


class GameHistoryForm(messages.Message):
    """ Form used to list the history of GameGuesses of a game """
    guesses = messages.MessageField(GameGuess, 1, repeated=True)


class Ranking(messages.Message):
    """ Message representing a player's match win/played history """
    player = messages.StringField(1, required=True)
    games_won = messages.IntegerField(2, required=True)
    games_played = messages.IntegerField(3, required=True)
    win_ratio = messages.FloatField(4, required=True)


class RankingForm(messages.Message):
    """ Form used to list multiple users' Rankings """
    rankings = messages.MessageField(Ranking, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
