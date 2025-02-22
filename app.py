from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_from_directory
from datetime import datetime, timedelta
import string
import secrets
import os
from supabase import create_client, Client
from functools import wraps
from werkzeug.security import check_password_hash
import re
import io
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import cryptography
from flask_minify import Minify


load_dotenv() 


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL', "https://kccbgaxhhdgzkyazjnnk.supabase.co")
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    GMAIL_USER = os.environ.get('GMAIL_USER')
    GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')



app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)
Minify(app=app, html=True, js=True, cssless=True)
# Remove Compress(app) line

# Apply configuration
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Initialize Supabase client
supabase: Client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])

app.config.update(
    SESSION_COOKIE_SECURE=True,   # Ensures cookies are sent only over HTTPS
    SESSION_COOKIE_HTTPONLY=True, # Prevents JavaScript from accessing cookies
    SESSION_COOKIE_SAMESITE='Lax' # Helps prevent CSRF attacks
)

# Function to set cache headers
# Set Cache-Control headers for static responses
@app.after_request
def add_cache_headers(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
    return response

# Serve images from multiple static subdirectories
@app.route('/static/<folder>/<path:filename>')
def serve_static_files(folder, filename):
    allowed_folders = ['assets', 'gallery', 'images']  # Define allowed folders
    if folder not in allowed_folders:
        return "Folder not found", 404
    return send_from_directory(f'static/{folder}', filename)

def send_registration_email(to_email, ack_id, details):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['GMAIL_USER']
        msg['To'] = to_email
        msg['Subject'] = f"YUKTI 2025 Registration Confirmation - {ack_id}"

        # Create email body with better formatting
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1c1c1c; padding: 20px; color: #ffffff;">
                <h2 style="color: #FFD700; text-align: center;">Registration Successful!</h2>
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700;">Registration Details</h3>
                    <p><strong>Acknowledgement ID:</strong> {ack_id}</p>
                    <p><strong>Email:</strong> {details['email']}</p>
                    <p><strong>Phone:</strong> {details['phone']}</p>
                    <p><strong>College:</strong> {details['college']}</p>
                    <p><strong>Total Cost:</strong> ₹{details['total_cost']}</p>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700;">Event Details</h3>
                    {details['event_details_html']}
                </div>

                <p style="background-color: #8B0000; padding: 10px; text-align: center; margin: 20px 0;">
                    Please pay the registration fees at the registration desk on the event day.
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(app.config['GMAIL_USER'], app.config['GMAIL_PASSWORD'])
            server.send_message(msg)
        
        print(f"Registration email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def generate_ack_id():
    timestamp = datetime.now().strftime("%Y")
    # Use secrets instead of random for cryptographic operations
    random_chars = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
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

# Add this after creating the Flask app
@app.template_filter('format_datetime')
def format_datetime(value):
    if not value:
        return ''
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except Exception as e:
        print(f"Date formatting error: {str(e)}")
        return value

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


@app.route('/spot')
@login_required(allowed_pages=['spot'])
def spot():
    return render_template('spot.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'success': False, 'message': 'No data received'})
            
            print("Received registration data:", data)
            
            ack_id = generate_ack_id()
            
            # Format event details
            formatted_events = []
            total_participants = 0
            
            for event in data['selectedEvents']:
                print("Processing event:", event)  # Debug log
                formatted_event = {
                    'event': event.get('event'),  # Get event name from 'event' field
                    'type': event.get('type'),
                    'cost': event.get('cost'),
                    'category': event.get('category')
                }
                
                # Handle team members or individual participant
                if event.get('type') == 'team' and event.get('members'):
                    formatted_event['members'] = event['members']
                    total_participants += len(event['members'])
                elif event.get('participant'):
                    formatted_event['participant'] = event['participant']
                    total_participants += 1
                
                formatted_events.append(formatted_event)
            
            # Registration data for database
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': total_participants,
                'total_cost': data['totalCost'],
                'registration_date': datetime.now().isoformat(),
                'event_details': formatted_events
            }
            
            print("Formatted registration data:", registration_data)  # Debug log
            
            # Insert into Supabase
            response = supabase.table('registrations').insert(registration_data).execute()
            
            if response.data:
                # Format event details for email
                event_details_html = []
                for event in formatted_events:
                    event_html = f"""
                    <div style="background-color: #2c2c2c; padding: 15px; margin: 10px 0; border-radius: 5px;">
                        <h4 style="color: #FFD700; margin: 0 0 10px 0;">{event['event']}</h4>
                        <p><strong>Category:</strong> {event['category']}</p>
                        <p><strong>Type:</strong> {event['type'].title()}</p>
                        <p><strong>Cost:</strong> ₹{event['cost']}</p>
                    """
                    
                    if 'members' in event:
                        event_html += f"<p><strong>Team Members:</strong> {', '.join(event['members'])}</p>"
                    elif 'participant' in event:
                        event_html += f"<p><strong>Participant:</strong> {event['participant']}</p>"
                    
                    event_html += "</div>"
                    event_details_html.append(event_html)

                email_details = {
                    'email': data['email'],
                    'phone': data['phone'],
                    'college': data['college'],
                    'total_cost': data['totalCost'],
                    'event_details_html': ''.join(event_details_html)
                }
                
                # Send the email without the PDF attachment
                send_registration_email(data['email'], ack_id, email_details)

                return jsonify({'success': True, 'ack_id': ack_id})
            else:
                return jsonify({'success': False, 'message': 'Registration failed'})
                
        except Exception as e:
            print(f"Registration Error: {str(e)}")
            print("Full error details:", str(e.__dict__))  # More detailed error info
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
            
            # Format events for display
            formatted_events = []
            for event in registration['event_details']:
                event_info = {
                    'name': event['event'],
                    'type': event['type'],
                    'category': event.get('category', ''),
                    'cost': event['cost'],
                    'participants': []
                }
                
                if event['type'] == 'team' and 'members' in event:
                    event_info['participants'] = event['members']
                elif 'participant' in event:
                    event_info['participants'] = [event['participant']]
                
                formatted_events.append(event_info)
            
            details = {
                'email': registration['email'],
                'phone': registration['phone'],
                'college': registration['college'],
                'total_participants': registration['total_participants'],
                'total_cost': registration['total_cost'],
                'events': formatted_events,
                'registration_date': registration['registration_date']
            }
            
            # Set headers to prevent caching
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            return render_template("registration_success.html", 
                ack_id=ack_id,
                details=details
            ), 200, headers
            
        return "Registration not found", 404
        
    except Exception as e:
        print(f"Error fetching registration: {str(e)}")
        return "Error fetching registration details", 500

@app.route('/spot-register', methods=['GET', 'POST'])
@login_required(allowed_pages=['spot'])
def spot_register():
    if request.method == "POST":
        try:
            print("Received POST request at /spot-register")  # Debug log
            data = request.get_json(silent=True)
            
            if not data:
                print("No JSON data received")  # Debug log
                return jsonify({'success': False, 'message': 'No data received'})
            
            print("Received data:", data)  # Debug log
            
            ack_id = generate_ack_id()
            
            # Calculate total participants from event details
            total_participants = 0
            for event in data['selectedEvents']:
                if event.get('type') == 'team' and event.get('members'):
                    total_participants += len(event['members'])
                elif event.get('participant'):
                    total_participants += 1
            
            # Prepare registration data
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': total_participants,  # Use calculated value
                'total_cost': data['totalCost'],
                'event_details': data['selectedEvents'],
                'registration_date': datetime.now().isoformat(),
                'utr_number': data['utrNumber']
            }
            
            print("Attempting to insert data:", registration_data)  # Debug log
            
            # Insert into Supabase
            response = supabase.table('spot_registrations').insert(registration_data).execute()
            print("Supabase response:", response)  # Debug log
            
            if response.data:
                print(f"Successfully created registration with ack_id: {ack_id}")  # Debug log
                return jsonify({
                    'success': True,
                    'ack_id': ack_id
                })
            else:
                print("Registration failed - no data in response")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Registration failed'
                })
                
        except Exception as e:
            print(f"Error in spot registration: {str(e)}")  # Debug log
            return jsonify({
                'success': False,
                'message': str(e)
            })
    
    return render_template("spot.html")

@app.route('/spot-acknowledgement/<ack_id>')
@login_required(allowed_pages=['spot', 'admin'])
def show_spot_ack(ack_id):
    try:
        # Query spot_registrations table instead of registrations
        response = supabase.table('spot_registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            details = {
                'email': registration['email'],
                'phone': registration['phone'],
                'college': registration['college'],
                'total_participants': registration['total_participants'],
                'total_cost': registration['total_cost'],
                'event_details': registration['event_details'],
                'registration_date': registration['registration_date'],
                'utr_number': registration['utr_number']  # Include UTR number in details
            }
            
            return render_template('spot_success.html', 
                ack_id=ack_id,
                details=details
            )
            
        flash('Registration not found')
        return redirect(url_for('spot_register'))
            
    except Exception as e:
        print(f"Error fetching registration: {str(e)}")
        flash('Error fetching registration details')
        return redirect(url_for('spot_register'))

def normalize_event_name(name):
    # Remove non-alphanumeric characters and lower the string
    return re.sub(r'\W+', '', name).lower()

def get_matching_registrations(table_name, norm_event, reg_type):
    try:
        response = supabase.table(table_name).select('*').execute()
        print(f"Found {len(response.data)} total registrations in {table_name}")
        
        matches = []
        if not response.data:
            return matches
            
        for reg in response.data:
            if not reg.get('event_details'):
                continue
                
            for event in reg['event_details']:
                if not event or not isinstance(event, dict):
                    continue
                    
                stored_event = event.get('event', '')
                if not stored_event:
                    continue
                    
                norm_stored = normalize_event_name(stored_event)
                print(f"[{table_name}] Comparing '{norm_event}' with '{norm_stored}'")
                
                if norm_event in norm_stored:
                    reg_data = {
                        'ack_id': reg.get('ack_id', ''),
                        'college': reg.get('college', ''),
                        'email': reg.get('email', ''),
                        'phone': reg.get('phone', ''),
                        'total_participants': reg.get('total_participants', 0),
                        'registration_date': reg.get('registration_date', ''),
                        'total_cost': reg.get('total_cost', 0),
                        'event_cost': event.get('cost', 0),
                        'type': reg_type,
                        'team_members': '',
                        'event_details': reg.get('event_details', [])
                    }
                    
                    # Handle team members
                    if event.get('type') == 'team' and event.get('members'):
                        reg_data['team_members'] = ', '.join(event['members'])
                    elif event.get('participant'):
                        reg_data['team_members'] = event['participant']
                        
                    # Add UTR number only for spot registrations
                    if reg_type == 'spot':
                        reg_data['utr_number'] = reg.get('utr_number', '')
                        
                    matches.append(reg_data)
                    print(f"Added registration: {reg_data['ack_id']}")
                    
        return matches
    except Exception as e:
        print(f"Error in get_matching_registrations: {str(e)}")
        return []

@app.route('/api/get-event-registrations')
@login_required(allowed_pages=['admin'])
def get_event_registrations():
    try:
        event_name = request.args.get('event')
        reg_type = request.args.get('type', 'online')  # Default changed to 'online'
        
        if not event_name:
            return jsonify({
                'success': False,
                'message': 'Event name is required'
            })
            
        norm_event = normalize_event_name(event_name)
        print(f"Searching for normalized event: '{norm_event}' with type: '{reg_type}'")
        
        table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
        matches = get_matching_registrations(table_name, norm_event, reg_type)
        
        return jsonify({
            'success': True,
            'registrations': matches,
            'isSpot': reg_type == 'spot'
        })
    except Exception as e:
        print(f"Error in get_event_registrations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error processing request: {str(e)}"
        })

@app.route('/api/get-registrations')
@login_required(allowed_pages=['admin'])
def get_registrations():
    try:
        reg_type = request.args.get('type', 'online')  # Default changed to 'online'
        table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
        
        response = supabase.table(table_name).select('*').execute()
        
        if response.data:
            registrations = [{
                'ack_id': reg['ack_id'],
                'college': reg['college'],
                'email': reg['email'],
                'phone': reg['phone'],
                'event_details': reg['event_details'],
                'utr_number': reg.get('utr_number') if reg_type == 'spot' else None
            } for reg in response.data]
            
            return jsonify({
                'success': True,
                'registrations': registrations
            })
        
        return jsonify({
            'success': True,
            'registrations': []
        })
        
    except Exception as e:
        print(f"Error fetching registrations: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/download-registrations')
@login_required(allowed_pages=['admin'])
def download_registrations():
    try:
        reg_type = request.args.get('type', 'online')  # Default changed to 'online'
        event_name = request.args.get('event')
        matches = []

        if event_name:
            norm_event = normalize_event_name(event_name)
            if norm_event == normalize_event_name("CHANAKSH (CODING EVENT)"):
                if reg_type == 'online':  # Changed from 'regular' to 'online'
                    matches += get_matching_registrations('registrations', norm_event, 'online')
                    matches += get_matching_registrations('spot_registrations', norm_event, 'spot')
                else:
                    matches = get_matching_registrations('spot_registrations', norm_event, 'spot')
        else:
            # If no event filter, retrieve full table
            table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
            response = supabase.table(table_name).select('*').execute()
            for reg in response.data:
                # Process event_details field as CSV string
                events_joined = ", ".join([e.get('event', '') for e in reg.get('event_details', [])])
                utr = reg.get('utr_number', '') if reg_type == 'spot' else ''
                matches.append({
                    'ack_id': reg.get('ack_id', ''),
                    'college': reg.get('college', ''),
                    'email': reg.get('email', ''),
                    'phone': reg.get('phone', ''),
                    'events': events_joined,
                    'utr_number': utr
                })

        # Prepare CSV output from matches
        output = io.StringIO(newline='')
        
        # Write UTF-8-BOM to ensure Excel recognizes the encoding
        output.write('\ufeff')
        
        writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)
        header = ['Ack ID', 'College', 'Email', 'Phone', 'Participant', 'UTR Number']
        writer.writerow(header)
        
        def clean_text(text):
            if text is None:
                return ''
            # Convert to string and handle encoding
            try:
                # Try direct string conversion
                return str(text).strip()
            except UnicodeEncodeError:
                # If that fails, try encoding/decoding with error handling
                return text.encode('ascii', 'ignore').decode('ascii').strip()

        for reg in matches:
            # Clean and encode each field
            row = [
                clean_text(reg.get('ack_id')),
                clean_text(reg.get('college')),
                clean_text(reg.get('email')),
                clean_text(reg.get('phone')),
                clean_text(reg.get('team_members', reg.get('events', ''))),
                clean_text(reg.get('utr_number'))
            ]
            writer.writerow(row)

        # Get the CSV content
        csv_output = output.getvalue()
        output.close()

        # Create response with proper headers
        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename=registrations_{reg_type}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig',
                'Cache-Control': 'no-cache'
            }
        )
        
        return response

    except Exception as e:
        print(f"Error in download_registrations: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/search-registration/<ack_id>')
@login_required(allowed_pages=['admin'])
def search_registration(ack_id):
    try:
        # Search in registrations table
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if not response.data:
            # If not found in registrations, try spot_registrations
            response = supabase.table('spot_registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            print(f"Found registration: {registration}")  # Debug log
            
            return jsonify({
                'success': True,
                'registration': {
                    'email': registration['email'],
                    'college': registration['college'],
                    'phone': registration['phone'],
                    'payment_method': registration.get('payment_method')
                }
            })
        
        return jsonify({
            'success': False,
            'message': 'Registration not found'
        })
        
    except Exception as e:
        print(f"Error searching registration: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == "__main__":

    app.run(debug=app.config['DEBUG'])

