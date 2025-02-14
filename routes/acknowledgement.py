from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

ack_bp = Blueprint('acknowledgement', __name__)

@ack_bp.route('/acknowledgement')
def show_acknowledgement():
    reg_id = session.get('reg_id')
    if reg_id:
        db = get_db()
        cursor = db.cursor()
        registration = cursor.execute(
            'SELECT * FROM registrations WHERE id = ?', 
            (reg_id,)
        ).fetchone()
        db.close()
        
        if registration:
            return render_template('acknowledgement.html', registration=registration)
    
    return redirect(url_for('registration.register'))  # Updated this line
