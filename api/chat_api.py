"""
=============================================================================
CHAT API - User to Admin Messaging
=============================================================================
Endpoints:
  POST   /api/chat/send          - Send a message
  GET    /api/chat/messages       - Get messages between two users
  GET    /api/chat/conversations  - Admin only: list all users who have messaged
  GET    /api/chat/unread         - Get unread message count
  PUT    /api/chat/read           - Mark messages as read
=============================================================================
"""

from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_login import current_user, login_required
from __init__ import db
from model.chat import ChatMessage
from model.user import User

chat_api = Blueprint('chat_api', __name__, url_prefix='/api/chat')
api = Api(chat_api)


def is_admin(user):
    try:
        role = getattr(user, '_role', None) or getattr(user, 'role', None) or ''
        if str(role).lower() == 'admin':
            return True
        if getattr(user, 'is_admin', False):
            return True
        return False
    except Exception:
        return False


def find_admin():
    admin = User.query.filter(User._role == 'Admin').first()
    if not admin:
        admin = User.query.filter(User._role == 'admin').first()
    return admin


class Send(Resource):
    @login_required
    def post(self):
        data = request.get_json() or {}
        message_text = data.get('message', '').strip()
        receiver_uid = data.get('receiver_uid', '').strip()

        if not message_text:
            return {'success': False, 'error': 'Message cannot be empty'}, 400

        if not is_admin(current_user):
            admin = find_admin()
            if not admin:
                return {'success': False, 'error': 'No admin available'}, 404
            receiver_uid = admin._uid
        else:
            if not receiver_uid:
                return {'success': False, 'error': 'receiver_uid is required for admin'}, 400
            receiver = User.query.filter_by(_uid=receiver_uid).first()
            if not receiver:
                return {'success': False, 'error': 'User not found'}, 404

        msg = ChatMessage(
            sender_uid=current_user._uid,
            receiver_uid=receiver_uid,
            message=message_text
        )
        db.session.add(msg)
        db.session.commit()

        return {'success': True, 'message': msg.to_dict()}, 201


class Messages(Resource):
    @login_required
    def get(self):
        other_uid = request.args.get('with')

        if not is_admin(current_user):
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
                    ChatMessage.sender_uid == current_user._uid,
                    ChatMessage.receiver_uid == other_uid
                ),
                db.and_(
                    ChatMessage.sender_uid == other_uid,
                    ChatMessage.receiver_uid == current_user._uid
                )
            )
        ).order_by(ChatMessage.timestamp.asc()).all()

        for m in messages:
            if m.receiver_uid == current_user._uid and not m.is_read:
                m.is_read = True
        db.session.commit()

        return {
            'success': True,
            'messages': [m.to_dict() for m in messages],
            'current_uid': current_user._uid
        }, 200


class Conversations(Resource):
    @login_required
    def get(self):
        if not is_admin(current_user):
            return {'success': False, 'error': 'Admin only'}, 403

        sent = db.session.query(ChatMessage.sender_uid).filter(
            ChatMessage.receiver_uid == current_user._uid
        ).distinct()
        received = db.session.query(ChatMessage.receiver_uid).filter(
            ChatMessage.sender_uid == current_user._uid
        ).distinct()

        uids = set()
        for row in sent:
            uids.add(row[0])
        for row in received:
            uids.add(row[0])
        uids.discard(current_user._uid)

        users = []
        for uid in uids:
            user = User.query.filter_by(_uid=uid).first()
            if user:
                unread = ChatMessage.query.filter_by(
                    sender_uid=uid,
                    receiver_uid=current_user._uid,
                    is_read=False
                ).count()
                users.append({
                    'uid': user._uid,
                    'name': user._name,
                    'unread': unread
                })

        return {'success': True, 'conversations': users}, 200


class Unread(Resource):
    @login_required
    def get(self):
        count = ChatMessage.query.filter_by(
            receiver_uid=current_user._uid,
            is_read=False
        ).count()
        return {'success': True, 'unread': count}, 200


class MarkRead(Resource):
    @login_required
    def put(self):
        data = request.get_json() or {}
        other_uid = data.get('other_uid')
        if not other_uid:
            return {'success': False, 'error': 'other_uid required'}, 400

        ChatMessage.query.filter_by(
            sender_uid=other_uid,
            receiver_uid=current_user._uid,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
        return {'success': True}, 200


api.add_resource(Send,          '/send')
api.add_resource(Messages,      '/messages')
api.add_resource(Conversations, '/conversations')
api.add_resource(Unread,        '/unread')
api.add_resource(MarkRead,      '/read')