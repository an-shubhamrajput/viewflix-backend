# from flask import Flask
# from app import create_app
# from sqlalchemy import text
# from app import db
# from flask import Flask
# from flask_cors import CORS


# app = create_app()

# from route.movie import movie_bp
# app.register_blueprint(movie_bp, url_prefix='/movie')

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}})  # allow all origins or specific frontend origin
# @app.route('/')
# def mainFun():
#     return 'hii'

# @app.route('/db-test')
# def db_test():
#     try:
#         result = db.session.execute(text('SELECT 1'))
#         # Fetch the result of the query
#         output = result.scalar()
#         return f"Connected to the database successfully! Result: {output}"
#     except Exception as e:
#         return f"Failed to connect to database: {e}"


# if __name__ == "__main__":
#     app.run(debug=True)
from app import create_app
from route.movie import movie_bp
from flask_cors import CORS
from app import db
from sqlalchemy import text
from route.profile import profile_bp
app = create_app()
app.register_blueprint(movie_bp, url_prefix='/movie')
app.register_blueprint(profile_bp, url_prefix='/profile')

CORS(app, resources={r"/*": {"origins": "http://192.168.1.31:PORT"}})

@app.route('/')
def mainFun():
    return 'hii'

@app.route('/db-test')
def db_test():
    try:
        result = db.session.execute(text('SELECT 1'))
        # Fetch the result of the query
        output = result.scalar()
        return f"Connected to the database successfully! Result: {output}"
    except Exception as e:
        return f"Failed to connect to database: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
