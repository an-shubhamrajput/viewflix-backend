from app import db

class Videos(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, unique=True)
    title = db.Column(db.String, nullable=False)
    videoId = db.Column(db.String, nullable=False, unique=True)
    thumbnail = db.Column(db.String, nullable=False)
    genre = db.Column(db.String, nullable=False)
    createdAt = db.Column(db.DateTime, default=db.func.now())
    # timestamps=True equivalent handled by createdAt, for updatedAt add another column if needed
