from flask import Blueprint, jsonify, session
from routes.notification_service import (
    get_user_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_read,
    delete_notification
)

notifications_bp = Blueprint('notifications', __name__)

def get_current_user_id():
    return session.get('username')

@notifications_bp.route('/notifications')
def get_notifications():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    notifications = get_user_notifications(user_id)
    return jsonify(notifications)

@notifications_bp.route('/notifications/unread-count')
def unread_count():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'count': 0})
    count = get_unread_count(user_id)
    return jsonify({'count': count})

@notifications_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
def mark_read(notif_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    mark_as_read(notif_id, user_id)
    return jsonify({'success': True})

@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
def mark_all():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    mark_all_read(user_id)
    return jsonify({'success': True})

@notifications_bp.route('/notifications/delete/<int:notif_id>', methods=['POST'])
def delete_notif(notif_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    delete_notification(notif_id, user_id)
    return jsonify({'success': True})