"""
CHAT API - User to Admin Messaging (JWT-based auth)
"""

from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from __init__ import app, db
from model.chat import ChatMessage
from model.user import User
import jwt

chat_api = Blueprint('chat_api', __name__, url_prefix='/api/chat')
api = Api(chat_api)


def get_current_user():
    """Get current user from JWT cookie."""
    token_name = app.config.get('JWT_TOKEN_NAME', 'jwt_python_flask')
    token = request.cookies.get(token_name)
    if not token:
        return None
    try:
        secret = app.config.get('SECRET_KEY', 'SECRET_KEY')
        data = jwt.decode(token, secret, algorithms=['HS256'])
        uid = data.get('_uid')
        if not uid:
            return None
        return User.query.filter_by(_uid=uid).first()
    except Exception as e:
        print(f'JWT decode error: {e}')
        return None


def is_admin(user):
    """Check if user is admin - only use _role field."""
    if not user:
        return False
    try:
        role = str(getattr(user, '_role', '') or '').strip()
        return role.lower() == 'admin'
    except Exception:
        return False


def find_admin():
    """Find first admin user."""
    return User.query.filter(User._role == 'Admin').first() or \
           User.query.filter(User._role == 'admin').first()


class Send(Resource):
    def post(self):
        user = get_current_user()
        if not user:
            return {'success': False, 'error': 'Not logged in'}, 401

        data = request.get_json() or {}
        message_text = data.get('message', '').strip()
        receiver_uid = data.get('receiver_uid', '').strip()

        if not message_text:
            return {'success': False, 'error': 'Message cannot be empty'}, 400

        if not is_admin(user):
            admin = find_admin()
            if not admin:
                return {'success': False, 'error': 'No admin available'}, 404
            receiver_uid = admin._uid
        else:
            if not receiver_uid:
                return {'success': False, 'error': 'receiver_uid required'}, 400
            receiver = User.query.filter_by(_uid=receiver_uid).first()
            if not receiver:
                return {'success': False, 'error': 'User not found'}, 404

        msg = ChatMessage(
            sender_uid=user._uid,
            receiver_uid=receiver_uid,
            message=message_text
        )
        db.session.add(msg)
        db.session.commit()

        return {'success': True, 'message': msg.to_dict()}, 201


class Messages(Resource):
    def get(self):
        user = get_current_user()
        if not user:
            return {'success': False, 'error': 'Not logged in'}, 401

        other_uid = request.args.get('with')

        if not is_admin(user):
            admin = find_admin()
            if not admin:
                return {'success': False, 'error': 'No admin found'}, 404
            other_uid = admin._uid
        else:
            if not other_uid:
                return {'success': False, 'error': 'Provide ?with=uid'}, 400

        messages = ChatMessage.query.filter(
            db.or_(
                db.and_(
                    ChatMessage.sender_uid == user._uid,
                    ChatMessage.receiver_uid == other_uid
                ),
                db.and_(
                    ChatMessage.sender_uid == other_uid,
                    ChatMessage.receiver_uid == user._uid
                )
            )
        ).order_by(ChatMessage.timestamp.asc()).all()

        for m in messages:
            if m.receiver_uid == user._uid and not m.is_read:
                m.is_read = True
        db.session.commit()

        return {
            'success': True,
            'messages': [m.to_dict() for m in messages],
            'current_uid': user._uid
        }, 200


class Conversations(Resource):
    def get(self):
        user = get_current_user()
        if not user:
            return {'success': False, 'error': 'Not logged in'}, 401
        if not is_admin(user):
            return {'success': False, 'error': 'Admin only'}, 403

        sent = db.session.query(ChatMessage.sender_uid).filter(
            ChatMessage.receiver_uid == user._uid
        ).distinct()
        received = db.session.query(ChatMessage.receiver_uid).filter(
            ChatMessage.sender_uid == user._uid
        ).distinct()

        uids = set()
        for row in sent:
            uids.add(row[0])
        for row in received:
            uids.add(row[0])
        uids.discard(user._uid)

        users = []
        for uid in uids:
            u = User.query.filter_by(_uid=uid).first()
            if u:
                unread = ChatMessage.query.filter_by(
                    sender_uid=uid,
                    receiver_uid=user._uid,
                    is_read=False
                ).count()
                users.append({
                    'uid': u._uid,
                    'name': u._name,
                    'unread': unread
                })

        return {'success': True, 'conversations': users}, 200


class Unread(Resource):
    def get(self):
        user = get_current_user()
        if not user:
            return {'success': False, 'error': 'Not logged in'}, 401

        count = ChatMessage.query.filter_by(
            receiver_uid=user._uid,
            is_read=False
        ).count()
        return {'success': True, 'unread': count}, 200


class MarkRead(Resource):
    def put(self):
        user = get_current_user()
        if not user:
            return {'success': False, 'error': 'Not logged in'}, 401

        data = request.get_json() or {}
        other_uid = data.get('other_uid')
        if not other_uid:
            return {'success': False, 'error': 'other_uid required'}, 400

        ChatMessage.query.filter_by(
            sender_uid=other_uid,
            receiver_uid=user._uid,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
        return {'success': True}, 200


api.add_resource(Send,          '/send')
api.add_resource(Messages,      '/messages')
api.add_resource(Conversations, '/conversations')
api.add_resource(Unread,        '/unread')
api.add_resource(MarkRead,      '/read')