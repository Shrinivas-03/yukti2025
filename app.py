from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import random
import string
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)
app.secret_key = "sdjksafbsahifgahif56549"

# Supabase credentials
SUPABASE_URL = "https://kccbgaxhhdgzkyazjnnk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjY2JnYXhoaGRnemt5YXpqbm5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk0NDA2MTAsImV4cCI6MjA1NTAxNjYxMH0.MW4ndTDp-6tvWluoHcb5NzVycNjmU0Vzlxl_mL0VdgA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gmail configuration
GMAIL_USER = "shrinivasnadager03@gmail.com"
GMAIL_PASSWORD = "imlhrtplytxnhgia"

def send_registration_email(to_email, ack_id, details):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = f"YUKTI 2025 Registration Confirmation - {ack_id}"

        # Create email body
        body = f"""
        <html>
        <body>
            <h2>Registration Successful!</h2>
            <p><strong>Acknowledgement ID:</strong> {ack_id}</p>
            <p><strong>Event Details:</strong> {details['event_name']}</p>
            <p><strong>College:</strong> {details['college']}</p>
            <p><strong>Team Members:</strong> {details['team_members']}</p>
            <p><strong>Total Cost:</strong> ₹{details['total_cost']}</p>
            <p><em>Please pay the registration fees at the registration desk on the event day.</em></p>
            <p>Thank you for registering!</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Registration email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def generate_ack_id():
    timestamp = datetime.now().strftime("%Y")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"YUKTI-{timestamp}-{random_chars}"

# Basic routes remain the same
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
            # Query the auth table to check credentials
            response = supabase.table('auth').select('*').eq('user_id', user_id).eq('password', password).execute()
            
            print("Auth Response:", response)  # For debugging
            
            # Check if we found a matching user
            if response.data and len(response.data) > 0:
                return redirect(url_for('register'))
            else:
                return render_template('signin.html', error="Invalid user ID or password")
                
        except Exception as e:
            print("Authentication Error:", str(e))
            return render_template('signin.html', error=f"Authentication error: {str(e)}")
            
    return render_template('signin.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'success': False, 'message': 'No data received'})
            
            ack_id = generate_ack_id()
            
            # Prepare registration data for Supabase
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': data['totalParticipants'],
                'total_cost': data['totalCost'],
                'registration_date': datetime.now().isoformat(),
                'event_details': data['selectedEvents']  # Already in JSON format from frontend
            }
            
            # Insert into Supabase
            response = supabase.table('registrations').insert(registration_data).execute()
            
            if response.data:
                # Send confirmation email
                email_details = {
                    'event_name': ", ".join(event['event'] for event in data['selectedEvents']),
                    'college': data['college'],
                    'team_members': ", ".join(
                        ", ".join(event.get('members', [])) if event.get('members') 
                        else event.get('participant', '') 
                        for event in data['selectedEvents']
                    ),
                    'total_cost': data['totalCost']
                }
                send_registration_email(data['email'], ack_id, email_details)
                
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
            print(f"Registration Error: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })
    
    return render_template("registration.html")

@app.route('/acknowledgement/<ack_id>')
def show_ack(ack_id):
    try:
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            
            # Format the data for the template
            details = {
                'email': registration['email'],
                'phone': registration['phone'],
                'college': registration['college'],
                'total_participants': registration['total_participants'],
                'total_cost': registration['total_cost'],
                'event_details': registration['event_details'],  # Already in correct format
                'registration_date': registration['registration_date']
            }
            
            return render_template("registration_success.html", 
                ack_id=ack_id,
                details=details
            )
            
        return "Registration not found", 404
        
    except Exception as e:
        print(f"Error fetching registration: {str(e)}")
        return "Error fetching registration details", 500

if __name__ == "__main__":
    app.run(debug=True)
