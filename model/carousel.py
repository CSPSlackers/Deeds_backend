from __init__ import db
from datetime import datetime

class Carousel(db.Model):
    __tablename__ = 'carousel_submissions'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('public_submissions.id'), nullable=False, unique=True)
    position = db.Column(db.Integer, default=0)  # Order in carousel
    added_at = db.Column(db.DateTime, default=datetime.now)
    submission = db.relationship("Submissions", backref=db.backref("carousel_rel", cascade="all, delete-orphan"))

    def __init__(self, submission_id, position=0):
        self.submission_id = submission_id
        self.position = position
        self.added_at = datetime.now()

    def read(self):
        """Return carousel entry with submission details"""
        if self.submission:
            submission_data = self.submission.read()
            # Decode image to base64 if it exists (handled in API layer)
            return {
                "carousel_id": self.id,
                "submission_id": self.submission_id,
                "position": self.position,
                "submission": submission_data,
                "added_at": self.added_at.isoformat() if self.added_at else None
            }
        return None

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_by_id(carousel_id):
        return Carousel.query.get(carousel_id)

    @staticmethod
    def get_by_submission_id(submission_id):
        return Carousel.query.filter_by(submission_id=submission_id).first()

    @staticmethod
    def get_all_ordered():
        """Get all carousel submissions ordered by position"""
        return Carousel.query.order_by(Carousel.position).all()

    @staticmethod
    def get_count():
        """Get total carousel submissions"""
        return Carousel.query.count()
