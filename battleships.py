import endpoints
from protorpc import message_types
from protorpc import messages
from protorpc import remote

from models import Game
from models import GameInfoForm
from models import GameListForm
from models import NewGameForm
from models import RegisterUserForm
from models import StringMessage
from models import User
from settings import WEB_CLIENT_ID

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

USER_REQUEST = endpoints.ResourceContainer(RegisterUserForm)
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
LIST_GAMES_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    limit=messages.IntegerField(1, default=10))


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
        user = endpoints.get_current_user()
        if User.query(User.email == user.email()).get():
            raise endpoints.ConflictException(
                    'You have already registered!')

        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=user.email())
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameInfoForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        auth_user = endpoints.get_current_user()
        user = User.query(User.email == auth_user.email()).get()
        game = Game.create_game(user, request)
        return game.to_form()

    @endpoints.method(request_message=LIST_GAMES_REQUEST,
                      response_message=GameListForm,
                      path='game',
                      name='list_games',
                      http_method='GET')
    def list_games(self, request):
        games = Game.query(
            Game.game_state == Game.GameState.WAITING_FOR_OPPONENT).fetch(
            request.limit)
        return GameListForm(games=[game.to_form() for game in games])

api = endpoints.api_server([BattleshipApi])  # register API
