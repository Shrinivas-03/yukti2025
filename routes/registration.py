from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db

registration_bp = Blueprint('registration', __name__)

@registration_bp.route('/registration', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute('''
                INSERT INTO registrations (name, email, phone, college, branch, year)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request.form['name'],
                request.form['email'],
                request.form['phone'],
                request.form['college'],
                request.form['branch'],
                request.form['year']
            ))
            
            db.commit()
            reg_id = cursor.lastrowid
            session['reg_id'] = reg_id
            
            return redirect(url_for('acknowledgement.show_acknowledgement'))
            
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('registration.register'))
        finally:
            db.close()
            
    return render_template('registration.html')
