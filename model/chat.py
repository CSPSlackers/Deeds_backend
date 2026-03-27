from __init__ import db
from datetime import datetime


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_uid = db.Column(db.String(64), nullable=False)       # who sent it
    receiver_uid = db.Column(db.String(64), nullable=False)     # who it's addressed to
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_uid': self.sender_uid,
            'receiver_uid': self.receiver_uid,
            'message': self.message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': self.is_read
        }


def initChatMessages():
    """Create the table if it doesn't exist."""
    db.create_all()