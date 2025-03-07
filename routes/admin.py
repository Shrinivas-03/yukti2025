from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import text
from app import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/events-statistics')
@admin_required
def get_events_statistics():
    try:
        result = db.session.execute(text('SELECT * FROM get_event_statistics()')).fetchall()
        
        events_stats = []
        for row in result:
            events_stats.append({
                'id': str(row.event_id),
                'name': row.event_name,
                'category': row.category_name,
                'type': row.event_type,
                'team_size': row.team_size,
                'cost': float(row.cost),
                'total_registrations': int(row.total_registrations),
                'paid_registrations': int(row.paid_registrations),
                'pending_registrations': int(row.pending_registrations),
                'individual_count': int(row.individual_count),
                'team_count': int(row.team_count),
                'total_amount': float(row.cost) * int(row.total_registrations)
            })

        return jsonify({
            'success': True,
            'events': events_stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })
