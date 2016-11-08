"""utils.py - File for collecting general utility functions."""

import endpoints


def get_auth_user():
    auth_user = endpoints.get_current_user()
    if not auth_user:
        raise endpoints.UnauthorizedException('Unauthorized.')
    return auth_user
