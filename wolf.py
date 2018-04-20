#!/usr/bin/env python3

import enum
import sys
import settings
from datetime import date

from flask import (Flask,
                   flash,
                   jsonify,
                   Markup,
                   redirect,
                   render_template,
                   request,
                   session,
                   url_for,
                  )
from flask_sqlalchemy import SQLAlchemy

SQLALCHEMY_DATABASE_URI = settings.SQLALCHEMY_DATABASE_URI
DEBUG = settings.DEBUG
SECRET_KEY = settings.SECRET_KEY

def configure_app_logging():
    logger = logging.getLogger('Wolf')

    # log to a file
    fh = logging.FileHandler(os.path.join(os.getcwd(), settings.LOG_FILE_PATH), 'w')
    # convert the log level string into its numerical value and set the level
    fh.setLevel(getattr(logging, settings.LOG_LEVEL, None))
    # set the format string for the file log
    fh.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
    logger.addHandler(fh)

    return logger

app = Flask(__name__)

# set a session time so that users have to login again or that the data we've stored in the
# session doesn't stay around for ever
if settings.SESSION_TIMEOUT:
    app.permanent_session_lifetime = timedelta(seconds=settings.SESSION_TIMEOUT)

# this will look for config items in this file and set them in the app factory object
app.config.from_object(__name__)



# set up SQL Alchemy for database access
db = SQLAlchemy(app)

# this will look for config items in this file and set them in the app factory object
app.config.from_object(__name__)
app.secret_key = 'secret'

class PartnerType(enum.Enum):
    BLIND = 'Blind'
    EARLY_LONE = 'Early'
    LONE = 'Lone'
    NORMAL = 'Normal'


class Game(db.Model):
    pkey = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.Date)
    course = db.Column(db.Text)
    num_holes = db.Column(db.Integer)
    starting_hole = db.Column(db.Integer)
    carry_overs = db.Column(db.Boolean)
    players = db.Column(db.Text)
    holes = db.relationship('Hole', backref=db.backref('game', lazy='joined'), lazy='dynamic')

    def __init__(self, date, course, holes=18, start=1, carry_overs=True, players=None):
        self.date = date
        self.course = course
        self.num_holes = holes
        self.starting_hole = start
        self.carry_overs = carry_overs
        self.players = players

class Hole(db.Model):
    pkey = db.Column(db.Integer, primary_key = True)
    game_fkey = db.Column(db.Integer, db.ForeignKey('game.pkey'))
    num = db.Column(db.Integer)
    wolf = db.Column(db.String)
    mode = db.Column(db.Enum(PartnerType), default=PartnerType.NORMAL)
    partner = db.Column(db.String)
    scores = db.Column(db.String)
    carry_over = db.Column(db.Integer, default=0)

    def __init__(self, game, hole, wolf, mode, partner, scores, carry_over=0):
        self.game_fkey = game.pkey
        self.num = hole
        self.wolf = wolf
        self.mode = mode
        self.partner = partner
        self.scores = scores
        self.set_carryover(game)

    def get_winners(self, game=None):
        winners = list()
        lowest = sys.maxsize
        if game:
            player_list = game.players.split(',')
        else:
            player_list = self.game.players.split(',')

        for person, score in zip(player_list, eval(self.scores)):
            score = int(score)
            if score == lowest:
                #outstr += person+'\n'
                winners.append(person)
            elif score < lowest:
                #outstr += 'starting over\n'
                del winners
                winners = list()
                winners.append(person)
                #outstr += person+'\n'
                lowest = score

        outcome = 'tie'
        # the wolf went alone
        if self.mode != PartnerType.NORMAL:
            # wolf went alone so
            if self.wolf in winners:
                # he has to be the only person in the winners list
                if len(winners) == 1:
                    # the wolf is the sole winner
                    outcome = 'win'
            else:
                outcome = 'loss'

        # the wolf had a partner
        else:
            # either the wolf or partner has to be a winner
            # and they can be only winners
            before_count = len(winners)
            if (self.wolf in winners):
                winners.remove(self.wolf)
            if (self.partner in winners):
                winners.remove(self.partner)
            # one of the other players is in the winners list
            if len(winners) > 0:
                if len(winners) != before_count:
                    # if the list changed then the hole was carried over
                    outcome = 'tie'
                else:
                    # if the list did not change then the wolf and partner lost
                    outcome = 'loss'

            elif len(winners) == 0:
                # the wolf and/or partner were the only ones in the list so they won
                outcome = 'win'

        winners = list()
        if outcome == 'tie':
            pass
        elif outcome == 'win':
            winners.append(self.wolf)
            if self.mode == PartnerType.NORMAL:
                winners.append(self.partner)
        elif outcome == 'loss':
            winners += player_list
            winners.remove(self.wolf)
            if self.mode == PartnerType.NORMAL:
                winners.remove(self.partner)

        return winners

    def get_points(self):
        if self.mode == PartnerType.NORMAL:
            return self.carry_over + 1
        elif self.mode == PartnerType.LONE:
            return self.carry_over + 2
        elif self.mode == PartnerType.EARLY_LONE:
            return self.carry_over + 3
        elif self.mode == PartnerType.BLIND:
            return self.carry_over + 4

    def set_carryover(self, game):
        self.carry_over = 0
        points = self.get_points()
        winners = self.get_winners(game)
        lasthole = self.get_lasthole()
        if lasthole:
            carry_over = lasthole.carry_over
        else:
            carry_over = 0
        if len(winners) == 0:
            self.carry_over = self.get_points() + carry_over
        else:
            # carry over stays at 0
            pass

    def get_lasthole(self):
        if self.num > 1:
            lasthole = Hole.query.filter_by(game_fkey=game.pkey, num=self.num - 1).first()
        else:
            lasthole = None
        return lasthole

@app.route('/', methods=['GET'])
def games():
    game_list = Game.query.order_by(Game.date.desc()).all()
    return render_template('index.html', games=game_list)

@app.route('/new_game', methods=['GET','POST'])
def new_game():
    if request.method == 'GET':
        today = date.today()
        return render_template('new_game.html', today=today)
    else:
        y, m, d = map(int, request.form.get('date').split('-'))
        game = Game(date(y, m, d),
                    request.form.get('course'),
                    int(request.form.get('holes')),
                    int(request.form.get('start')),
                    request.form.get('players'),
                   )
        db.session.add(game)
        db.session.commit()
        # get values from the form and create a new game
        flash ('Successfully created a new game')
        return redirect(url_for('games'))

#@app.route('/hole/<int:holenum>', methods=['GET'])
@app.route('/game/<int:gamenum>/<int:holenum>', methods=['GET','POST'])
def score(gamenum, holenum):
    game = Game.query.filter_by(pkey=gamenum).first()
    hole = Hole.query.filter_by(game_fkey=gamenum, num=holenum).first()
    if game.carry_overs:
        # FIXME - the hole needs to be calculated for rollover because the round
        # FIXME - might not have started on 1 or 10.
        last_hole = hole.get_lasthole()
        if
            last_hole = Hole.query.filter_by(game_fkey=gamenum, num=holenum-1).first()
            carry_over = last_hole.carry_over
        else:
            carry_over = 0
    else:
        carry_over = 0

    if not hole:
        players = game.players.split(',')
        wolf = players[(holenum - 1) % len(players)]
        if request.method == 'GET':
            return render_template('enter_score.html', game = game,
                                                       wolf = wolf,
                                                       partner = None,
                                                       players = players,
                                                       scores = [],
                                                       points = [],
                                                       carry_over = carry_over,
                                                       gamenum = gamenum,
                                                       holenum = holenum)
        else:
            partner = request.form.get('partner', None)
            option = request.form.get('wolf_option', None)
            mode = PartnerType.NORMAL
            if option == 'blind':
                mode = PartnerType.BLIND
            elif option == 'early':
                mode = PartnerType.EARLY_LONE
            elif option == 'lone':
                mode = PartnerType.LONE
            if mode == PartnerType.NORMAL:
                if not partner:
                    flash('You must pick a parter or set the wolf', 'error')
                    return render_template('enter_score.html', game = game,
                                           wolf = wolf,
                                           partner = None,
                                           players = players,
                                           scores = [],
                                           points = [],
                                           gamenum = gamenum,
                                           holenum = holenum)
            else:
                partner = None

            scores = request.form.getlist('score')
            print (scores)
            if len(scores) < 4:
                flash('You must enter all player scores', 'error')
                return render_template('enter_score.html', game = game,
                                       wolf = wolf,
                                       partner = None,
                                       players = players,
                                       scores = [],
                                       points = [],
                                       gamenum = gamenum,
                                       holenum = holenum)
            hole = Hole(game,
                        holenum,
                        wolf,
                        mode,
                        partner,
                        str(scores),
                       )
            db.session.add(hole)
            db.session.commit()
            flash('Saved score for hole #%d' % holenum)

            return redirect(url_for('score', gamenum=gamenum, holenum=holenum))

    game = Game.query.filter_by(pkey=gamenum).first()
    hole = Hole.query.filter_by(game_fkey=gamenum, num=holenum).first()
    lasthole = hole.get_lasthole()
    players = game.players.split(',')
    if holenum == 0:
        points = [0, 0, 0, 0]
    else:
        # get list of winners
        winners = hole.get_winners()
        # get points for the hole
        points_for_hole = hole.get_points()
        points = []
        for player in players:
            if player in winners:
                points.append(points_for_hole + carry_over)
            else:
                points.append(0)

    scores = eval(hole.scores)
    return render_template('hole.html', wolf = hole.wolf,
                                        partner = hole.partner,
                                        players = players,
                                        scores = scores,
                                        points = points,
                                        carry_over = hole.carry_over,
                                        game = game,
                                        gamenum = gamenum,
                                        holenum = holenum)


if __name__ == '__main__':
    app.run(debug=settings.DEBUG, host='0.0.0.0', port=settings.PORT)
