#!/usr/bin/env python

import webapp2

from google.appengine.api import app_identity
from google.appengine.api import mail

from models import User
from models import Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        inactive_games = Game.get_inactive_games()

        for game in inactive_games:
            p1 = game.player_one and game.player_one.get()
            p2 = game.player_two and game.player_two.get()
            subject = 'BattleShips - Ongoing game reminder!'
            body = ('Hello {}! You still have a BattleShips game in progress!'
                    ' If you have time, come back and finish your game!'
                    " If you're finished, you can cancel the game.")
            # This will send test emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           p1.email,
                           subject,
                           body.format(p1.name))
            if p2:
                mail.send_mail(
                    'noreply@{}.appspotmail.com'.format(app_id),
                    p2.email,
                    subject,
                    body.format(p2.name))


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail)
    ], debug=True)
