import endpoints
from protorpc import remote

from models import Game
from models import GameInfoForm
from models import NewGameForm
from models import RegisterUserForm
from models import StringMessage
from models import User
from settings import WEB_CLIENT_ID

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

USER_REQUEST = endpoints.ResourceContainer(RegisterUserForm)
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)


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

api = endpoints.api_server([BattleshipApi])  # register API
