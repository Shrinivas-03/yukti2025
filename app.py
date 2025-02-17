from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import random
import string
from supabase import create_client, Client
from functools import wraps
from werkzeug.security import check_password_hash

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)
app.secret_key = "sdjksafbsahifgahif56549"

# Set your Supabase credentials
SUPABASE_URL = "https://kccbgaxhhdgzkyazjnnk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjY2JnYXhoaGRnemt5YXpqbm5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk0NDA2MTAsImV4cCI6MjA1NTAxNjYxMH0.MW4ndTDp-6tvWluoHcb5NzVycNjmU0Vzlxl_mL0VdgA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_ack_id():
    timestamp = datetime.now().strftime("%Y")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"YUKTI-{timestamp}-{random_chars}"

# Authentication decorator
def login_required(allowed_pages=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first')
                return redirect(url_for('signin'))
            
            if allowed_pages and session.get('page') not in allowed_pages:
                flash('Access denied')
                return redirect(url_for('signin'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/events')
def events():
    return render_template('events.html')



@app.route('/tech')
def tech():
    return render_template('events/tech.html')

@app.route('/cultural')
def cultural():
    return render_template('events/cultural.html')

@app.route('/management')
def management():
    return render_template('events/management.html')

@app.route('/games')
def games():
    return render_template('events/games.html')

@app.route('/kalachitrana')
def kalachitrana():
    return render_template('events/kalachitrana.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        try:
            # Query Supabase auth table
            response = supabase.table('auth').select('*').eq('user_id', user_id).execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                
                # Verify password (assuming passwords are stored as-is for now)
                if user['password'] == password:
                    # Store user info in session
                    session['user_id'] = user['user_id']
                    session['page'] = user['page']
                    
                    # Redirect based on user role
                    if user['page'] == 'admin':
                        return redirect(url_for('admin'))
                    elif user['page'] == 'college':
                        return redirect(url_for('register'))
                    elif user['page'] == 'spot':
                        return redirect(url_for('spot'))
                
                flash('Invalid credentials')
            else:
                flash('User not found')
                
        except Exception as e:
            print(f"Login Error: {str(e)}")
            flash('Login error occurred')
            
    return render_template('signin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('signin'))

@app.route('/admin')
@login_required(allowed_pages=['admin'])
def admin():
    return render_template('admin.html')

@app.route('/register', methods=['GET', 'POST'])
@login_required(allowed_pages=['college'])
def register():
    if request.method == "POST":
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'success': False, 'message': 'No data received'})
            
            ack_id = generate_ack_id()
            
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': data['totalParticipants'],
                'total_cost': data['totalCost'],
                'event_details': data['selectedEvents'],
                'registration_date': datetime.now().isoformat()
            }
            
            # Insert into Supabase
            response = supabase.table('registrations').insert(registration_data).execute()
            
            if response.data:
                return jsonify({
                    'success': True,
                    'ack_id': ack_id
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Registration failed'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
    
    return render_template("registration.html")

@app.route('/spot')
@login_required(allowed_pages=['spot'])
def spot():
    return render_template('spot.html')

@app.route('/acknowledgement/<ack_id>')
@login_required(allowed_pages=['college', 'spot', 'admin'])
def show_ack(ack_id):
    try:
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            details = {
                'email': registration['email'],
                'phone': registration['phone'],
                'college': registration['college'],
                'total_participants': registration['total_participants'],
                'total_cost': registration['total_cost'],
                'event_details': registration['event_details'],
                'registration_date': registration['registration_date']
            }
            
            return render_template('registration_success.html', 
                ack_id=ack_id,
                details=details
            )
            
        flash('Registration not found')
        return redirect(url_for('register'))
            
    except Exception as e:
        print(f"Error fetching registration: {str(e)}")
        flash('Error fetching registration details')
        return redirect(url_for('register'))

if __name__ == "__main__":
    app.run(debug=True)
