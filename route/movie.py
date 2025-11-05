from flask import Blueprint, session, render_template,request, jsonify
from app.mysql_conn import get_db_for_genre

movie_bp = Blueprint('movie', __name__)

@movie_bp.route('/',methods=['GET'])
def movieInfo():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400
    print("genre_id:", genre_id)
    try:
        conn = get_db_for_genre(genre_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM top_rated_en')
    movies = cursor.fetchall()
    cursor.close()
    session['username'] = 'shubham rajput'
    session['11'] = 123
    return {"movies": movies}
