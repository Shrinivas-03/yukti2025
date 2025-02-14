from flask import Blueprint, render_template

events_bp = Blueprint('events', __name__)

@events_bp.route('/tech')
def tech():
    return render_template('events/tech.html')

@events_bp.route('/cultural')
def cultural():
    return render_template('events/cultural.html')

@events_bp.route('/management')
def management():
    return render_template('events/management.html')

@events_bp.route('/games')
def games():
    return render_template('events/games.html')
