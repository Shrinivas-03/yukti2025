from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from supabase import create_client, Client
from datetime import datetime
import random
import string

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)
app.secret_key = "sdjksafbsahifgahif56549"

# Supabase credentials
SUPABASE_URL = "https://kccbgaxhhdgzkyazjnnk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjY2JnYXhoaGRnemt5YXpqbm5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk0NDA2MTAsImV4cCI6MjA1NTAxNjYxMH0.MW4ndTDp-6tvWluoHcb5NzVycNjmU0Vzlxl_mL0VdgA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Basic routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

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

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        try:
            response = supabase.table('auth').select('*').eq('user_id', user_id).eq('password', password).execute()
            
            if response.data and len(response.data) > 0:
                return redirect(url_for('register'))
            else:
                return render_template('signin.html', error="Invalid user ID or password")
                
        except Exception as e:
            print("Authentication Error:", str(e))
            return render_template('signin.html', error=f"Authentication error: {str(e)}")
            
    return render_template('signin.html')

def generate_ack_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"YUKTI{timestamp}{random_str}"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
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
            
            response = supabase.table('registrations').insert(registration_data).execute()
            
            # Check if data exists in response
            if hasattr(response, 'data') and response.data:
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

@app.route('/acknowledgement/<ack_id>')
def acknowledgement(ack_id):
    try:
        # Fetch registration data from Supabase
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        print("Fetch registration response:", response)  # Debug print
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            return render_template('registration_success.html', ack_id=ack_id, details=registration)
        else:
            flash('Registration not found')
            return redirect(url_for('register'))
            
    except Exception as e:
        print(f"Error fetching registration: {str(e)}")
        flash('Error fetching registration details')
        return redirect(url_for('register'))

if __name__ == "__main__":
    app.run(debug=True)
