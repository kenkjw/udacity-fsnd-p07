# Udacity Full Stack Nanodegree Project: Design a Game

##Project Description:
From the Udacity course:
In this project you will use these skills to develop your own game! You will write an
API with endpoints that will allow anyone to develop a front-end for your game.
Since you aren't required to write a front-end you can use API explorer to test your API.

For this project, the Battleships game was chosen.

##Game Description:
Battleships is a multiplayer guessing game where two players compete to guess their
opponent's ship placement locations. Each player can have multiple ships and ships
can have different lengths. The ships are placed non-overlapping in a 2 dimensional
space at the beginning of the game and cannot be moved. Players take turns guessing
a single coordinate and they are told whether their guess hit or miss. A player is
notified if a hit results in a ship sinking. The game ends when one player's ships
are all sunk.

For more information about Battleship, you can read the [Battleship Wikipedia Article](https://en.wikipedia.org/wiki/Battleship_(game))

In the variation of Battleship that this API uses, the player that creates the game
is able to customize the rules of the game. The board is allowed dimensions between
8-20, ship lengths are between 2-5 and there can be 0-5 of each ship.

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.


##Files Included:
 - app.yaml: App configuration.
 - battleships.py: Contains endpoints.
 - cron.yaml: Cronjob configuration.
 - Design.txt: Reflection on design decisions
 - main.py: Handler for cron handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper functions

##Endpoints Included:
 - **user_register**
    - Path: 'user'
    - Method: POST
    - Parameters: RegisterUserForm
    - Returns: StringMessage confirming creation of the User.
    - Description: Registers a name to a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists or
    the User has already registered.

 - **game_new**
    - Path: 'game'
    - Method: POST
    - Parameters: NewGameForm
    - Returns: GameInfoForm with initial game state.
    - Description: Creates a new Game. If rules are supplied, they are used. Otherwise,
    a default set of rules are used. If invalid rules are supplied, raise a
    BadRequestException.

 - **get_games_list**
    - Path: 'game/list'
    - Method: GET
    - Parameters: limit(optional), state(optional)
    - Returns: GameListForm with games at state game_state.
    - Description: Returns a list of games at a current state of game. If state is not supplied
    then the default state to search is games that are waiting for opponents

 - **game_join**
    - Path: 'game/{game_key}/join'
    - Method: POST
    - Parameters: game_key
    - Returns: GameInfoForm with current game state.
    - Description: Assigns the current User as the second player of the game with key game_key
    Returns the current state of the game. Raises ForbiddenException if the game is not
    accepting players. Raises ConflictException if the player is trying to join his own game.

 - **get_user_games**
    - Path: 'game/active'
    - Method: GET
    - Parameters: none
    - Returns: GameListForm with active games.
    - Description: Returns the list of games that are waiting for an opponent, waiting for
    ship placements, or waiting for a player's guess, that the current User is a player of.

 - **game_cancel**
    - Path: 'game/{game_key}/cancel'
    - Method: DELETE
    - Parameters: game_key
    - Returns: GameInfoForm with current game state.
    - Description: Sets the game identified by game_key to cancelled state.
    Raises ForbiddenException if the game is already completed.

 - **game_place_ships**
    - Path: 'game/{game_key}/ships'
    - Method: PUT
    - Parameters: game_key, ShipPlacementForm
    - Returns: StringMessage confirming ship placement and state of game.
    - Description: Submit the player's placement of ships. Raises ForbiddenException if the game is
    not accepting ship placements, BadRequestException if the ship data is invalid, and ConflictException
    if the player has already submitted ships.

 - **game_guess**
    - Path: 'game/{game_key}/guess'
    - Method: POST
    - Parameters: game_key, Position
    - Returns: StringMessage of the result of the guess.
    - Description: Accept's the player's guess and returns the result. Raises ForbiddenException if
    it is not the player's turn, BadRequestException if the guess is invalid.

 - **get_user_rankings**
    - Path: 'user/ranking'
    - Method: GET
    - Parameters: None
    - Returns: RankingForm
    - Description: Returns win/loss ratio of all players.

 - **get_game_history**
    - Path: 'game/{game_key}/history'
    - Method: GET
    - Parameters: game_key
    - Returns: GameHistoryForm
    - Description: Returns the guess history of the game.

 - **get_game**
    - Path: 'game/{game_key}'
    - Method: GET
    - Parameters: game_key
    - Returns: StringMessage
    - Description: Returns the current state of a game.

##Models Included:
 - **User**
    - Stores unique user_name and email address.
 - **Game**
    - Stores unique game states.

##Custom Message Enum:
 - **GameState**
    - Represents the current State of the game.
    Values:
        - WAITING_FOR_OPPONENT: Game is waiting for Player Two to join.
        - PREPARING_BOARD: Game is waiting for one or more player to submit ship placements.
        - PLAYER_ONE_TURN: Game is waiting for player one's guess.
        - PLAYER_TWO_TURN: Game is waiting for player two's guess.
        - GAME_COMPLETE: Game is completed.
        - GAME_CANCELLED: Game has been cancelled by a player.

##Custom Message Fields Included:
 - **Position**
    - Represents a coordinate on game board (x, y)
 - **ShipPlacement**
    - Represents where a user places a ship on the board
    (position, length, vertical)
 - **BoardRules**
    - Represents the rules of a game
    (width, height, ship_2, ship_3, ship_4, ship_5)
 - **GameGuess**
    - Represents a guess by a player and the result
    (player, position, result)
 - **Ranking**
    - Represents a player's win/games played history
    (player, games_won, games_played, win_ratio)

##Forms Included:
 - **RegisterUserForm**
    - Used to register a new user (user_name)
 - **NewGameForm**
    - Used to create a new game (rules)
 - **GameInfoForm**
    - Representation of a Game's state (urlsafe_key, player_one, player_two,
    game_state, rules).
 - **GameListForm**
    - A list of GameInfoForms (games)
 - **ShipPlacementForm**
    - A list of ShipPlacements (ships)
 - **GameHistoryForm**
    - A list of GameGuesses (guesses)
 - **RankingForm**
    - A list of Rankings (rankings)
 - **StringMessage**
    - General purpose String container.
