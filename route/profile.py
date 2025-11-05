from flask import Blueprint, session

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('')
def getProfile():
  username = session.get('username', 'Guest')
  return f'profile visited your name is: {username}'