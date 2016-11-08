import endpoints
from protorpc import message_types
from protorpc import messages
from protorpc import remote

from models import Game
from models import GameInfoForm
from models import GameListForm
from models import NewGameForm
from models import Position
from models import RegisterUserForm
from models import ShipPlacementForm
from models import StringMessage
from models import User
from settings import WEB_CLIENT_ID

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

USER_REQUEST = endpoints.ResourceContainer(RegisterUserForm)
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
VOID_REQUEST = endpoints.ResourceContainer(message_types.VoidMessage)
LIST_GAMES_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    limit=messages.IntegerField(1, default=10))
GAME_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    game_key=messages.StringField(1, required=True))
POSITION_REQUEST = endpoints.ResourceContainer(
    Position,
    game_key=messages.StringField(1, required=True))
SHIP_PLACEMENT_REQUEST = endpoints.ResourceContainer(
    ShipPlacementForm,
    game_key=messages.StringField(1, required=True))


@endpoints.api(
    name='battleship',
    version='v1',
    allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class BattleshipApi(remote.Service):
    """Battleship Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='register_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        auth_user = endpoints.get_current_user()
        user = User.create_user(auth_user, request.user_name)
        return StringMessage(message='User {} created!'.format(
                user.name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameInfoForm,
                      path='game',
                      name='game_new',
                      http_method='POST')
    def new_game(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        game = Game.create_game(user, request)
        return game.to_form()

    @endpoints.method(request_message=LIST_GAMES_REQUEST,
                      response_message=GameListForm,
                      path='game/open',
                      name='get_open_games',
                      http_method='GET')
    def list_open_games(self, request):
        games = Game.by_game_state(
            Game.GameState.WAITING_FOR_OPPONENT,
            request.limit)
        return GameListForm(games=[game.to_form() for game in games])

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameInfoForm,
                      path='game/{game_key}/join',
                      name='game_join',
                      http_method='POST')
    def join_game(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        game = Game.by_urlsafe(request.game_key)
        game.add_player(user)
        return game.to_form()

    @endpoints.method(request_message=VOID_REQUEST,
                      response_message=GameListForm,
                      path='game/active',
                      name='get_active_games',
                      http_method='GET')
    def get_user_games(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        games = Game.get_active_games(user)
        return GameListForm(games=[game.to_form() for game in games])

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameInfoForm,
                      path='game/{game_key}/cancel',
                      name='game_cancel',
                      http_method='POST')
    def cancel_game(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        game = Game.by_urlsafe(request.game_key)
        game.cancel_game()
        return game.to_form()

    @endpoints.method(request_message=SHIP_PLACEMENT_REQUEST,
                      response_message=StringMessage,
                      path='game/{game_key}/ships',
                      name='game_place_ships',
                      http_method='POST')
    def player_place_ships(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        game = Game.by_urlsafe(request.game_key)

        message = game.player_place_ships(user, request)
        return message

    @endpoints.method(request_message=POSITION_REQUEST,
                      response_message=StringMessage,
                      path='game/{game_key}/action',
                      name='game_action',
                      http_method='POST')
    def player_action(self, request):
        auth_user = endpoints.get_current_user()
        user = User.by_email(auth_user.email())
        game = Game.by_urlsafe(request.game_key)

    def get_user_rankings(self, request):
        pass

    def get_game_history(self, request):
        pass

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameInfoForm,
                      path='game/{game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        game = Game.by_urlsafe(request.game_key)
        return game.to_form()

api = endpoints.api_server([BattleshipApi])  # register API
