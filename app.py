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
import logging
from logging.handlers import RotatingFileHandler
from flask_minify import Minify
import hashlib  # Add this import at the top


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
    SESSION_COOKIE_SAMESITE='Lax', # Helps prevent CSRF attacks
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=5)  # Changed from 1 hour to 5 minutes
)



#Function to set cache headers
# Set Cache-Control headers for static responses
@app.after_request
def add_cache_headers(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
    return response  # Always return the response

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
        <!-- Header Section -->
        <div style="position: relative; border-bottom: 2px solid #FFD700; padding-bottom: 20px; margin-bottom: 30px;">
           
            
            <div style="text-align: center; margin: 0 auto;">
                <h1 style="margin: 0 0 5px 0; font-size: 24px; color: #FFD700;">
                    Visvesvaraya Technological University
                </h1>
                <h2 style="margin: 0 0 5px 0; font-size: 20px;">
                    Center of PG Studies And Regional Office Kalaburagi
                </h2>
                <div style="font-size: 22px; font-weight: bold; letter-spacing: 2px; color: #FFD700;">
                    Yukti-2025
                </div>
            </div>
        </div>

        <!-- Existing Content -->
        <h2 style="color: #FFD700; text-align: center; margin-top: 0;">Registration Successful!</h2>
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

        <p style="background-color: rgba(139, 0, 0, 0.2); 
          border: 2px solid #FF00FF;
          padding: 15px;
          text-align: center;
          margin: 20px 0;
          border-radius: 8px;
          font-family: 'Orbitron', sans-serif;
          color: #00FFFF;">
    <span style="font-size: 1.1em; font-weight: bold; display: block; margin-bottom: 10px;">
        PAYMENT INSTRUCTIONS
    </span>
    
    Kindly ensure fees are paid either:<br>
    - At registration desk <strong style="color: #FF00FF; margin: 0 5px;">OR</strong> 
    - Via Demand Draft<br><br>
    
    <span style="color: #FF00FF;">◆ Event Date:</span> 10 March 2025<br>
    <span style="color: #FF00FF;">◆ Payment Window:</span> 8:00 AM - 10:30 A.M.<br><br>
    
    <span style="font-size: 0.9em; display: block; margin-top: 10px;">
        ※ DD Details:<br>
        Account: The Finance Officer VTU Belagavi Yukti Cultural Account<br>
        A/C: 110226756934 | IFSC: CNRB0001829<br>
        Bank: Canara Bank | Payable at Kalaburagi
    </span>
</p>
         <p style="background-color: #8B0000; padding: 10px; text-align: center; margin: 20px 0;">
              Please bring valid college Id while coming to the event..
        </p>
         <p style="background-color: #8B0000; padding: 10px; text-align: center; margin: 20px 0;">
              Please bring HardCopy Of Acknowledgement Pdf
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


def get_last_ack_number():
    try:
        # Get all registrations ordered by ack_id in descending order
        response = supabase.table('registrations').select('ack_id').order('ack_id', desc=True).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            # Extract number from last ack_id (format: YUKTI-2025-00001)
            last_ack = response.data[0]['ack_id']
            last_number = int(last_ack.split('-')[-1])
            return last_number
        return 0
    except Exception as e:
        print(f"Error getting last ack number: {str(e)}")
        return 0

def generate_ack_id():
    year = datetime.now().strftime("%Y")
    last_number = get_last_ack_number()
    new_number = last_number + 1
    # Format number as 5 digits with leading zeros
    formatted_number = f"{new_number:05d}"
    return f"YUKTI-{year}-{formatted_number}"

# Authentication decorator
def login_required(allowed_pages=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # For API endpoints, return 401 JSON response instead of redirect
            if not session.get('user_id'):
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            # Check if session has expired
            login_time = datetime.fromisoformat(session.get('login_time', ''))
            if datetime.now() - login_time > timedelta(minutes=5):
                return jsonify({
                    'success': False,
                    'message': 'Session expired'
                }), 401
            
            # Check permissions
            if allowed_pages and session.get('page') not in allowed_pages:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
            
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

@app.route('/admin-page')
def admin_page():
    # Only protect the admin API endpoints, not the page itself
    return render_template('admin.html')

@app.route('/register-page')
def register_page():
    return render_template('registration.html')

@app.route('/register', methods=['POST'])
def register_submit():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'No data received'})
        
        print("Received registration data:", data)  # Debug log
        
        ack_id = generate_ack_id()
        
        # Format event details
        formatted_events = []
        total_participants = 0
        
        for event in data['selectedEvents']:
            formatted_event = {
                'event': event['event'],
                'type': event['type'],
                'cost': event['cost'],
                'category': event['category']
            }
            
            if event['type'] == 'team' and event.get('members'):
                # Handle team members with USN
                formatted_event['members'] = []
                for member in event['members']:
                    if isinstance(member, dict):
                        formatted_event['members'].append({
                            'name': member.get('name', ''),
                            'usn': member.get('usn', '')
                        })
                    else:
                        # Handle legacy format
                        formatted_event['members'].append({
                            'name': member,
                            'usn': ''
                        })
                total_participants += len(event['members'])
            elif event.get('participant'):
                # Handle individual participant with USN
                if isinstance(event['participant'], dict):
                    formatted_event['participant'] = {
                        'name': event['participant'].get('name', ''),
                        'usn': event['participant'].get('usn', '')
                    }
                else:
                    # Handle legacy format
                    formatted_event['participant'] = {
                        'name': event['participant'],
                        'usn': ''
                    }
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
        print("Supabase response:", response)  # Debug log
        
        if response.data:
            # Format email details with USN
            event_details_html = []
            for event in formatted_events:
                event_html = f"""<div style="padding: 10px; border: 1px solid #ccc; margin: 5px 0;">
                    <p><strong>Event:</strong> {event['event']}</p>
                    <p><strong>Type:</strong> {event['type']}</p>
                    <p><strong>Cost:</strong> ₹{event['cost']}</p>"""
                
                if 'members' in event:
                    members_list = [f"{m['name']} ({m['usn']})" for m in event['members'] if m.get('name')]
                    event_html += f"<p><strong>Team Members:</strong> {', '.join(members_list)}</p>"
                elif 'participant' in event:
                    participant = event['participant']
                    event_html += f"<p><strong>Participant:</strong> {participant['name']} ({participant['usn']})</p>"
                
                event_html += "</div>"
                event_details_html.append(event_html)

            email_details = {
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_cost': data['totalCost'],
                'event_details_html': ''.join(event_details_html)
            }
            
            # Send confirmation email
            send_registration_email(data['email'], ack_id, email_details)
            return jsonify({'success': True, 'ack_id': ack_id})
        
        return jsonify({'success': False, 'message': 'Registration failed'})
        
    except Exception as e:
        print(f"Registration Error: {str(e)}")  # Debug log
        return jsonify({'success': False, 'message': str(e)})

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
                    event_info['participants'] = [
                        {'name': member['name'], 'usn': member['usn']}
                        for member in event['members']
                    ]
                elif 'participant' in event:
                    event_info['participants'] = [
                        {'name': event['participant']['name'], 
                         'usn': event['participant']['usn']}
                    ]
                
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

def normalize_event_name(name):
    # Remove non-alphanumeric characters and lower the string
    return re.sub(r'\W+', '', name).lower()

def get_matching_registrations(table_name, norm_event, reg_type):
    try:
        response = supabase.table('registrations').select('*').execute()  # Only use registrations table
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
                        'total_cost': reg.get('total_cost', 0),
                        'registration_date': reg.get('registration_date', ''),
                        'event_cost': event.get('cost', 0),
                        'type': 'online',  # Always use online type
                        'team_members': '',
                        'event_details': reg.get('event_details', [])
                    }
                    
                    # Handle team members
                    if event.get('type') == 'team' and 'members' in event:
                        reg_data['team_members'] = ', '.join(event['members'])
                    elif 'participant' in event:
                        reg_data['team_members'] = event['participant']
                    
                    matches.append(reg_data)
                    print(f"Added registration: {reg_data['ack_id']}")
                    
        return matches
        
    except Exception as e:
        print(f"Error in get_matching_registrations: {str(e)}")
        return []

# Keep the API endpoints protected with login_required
@app.route('/api/get-event-registrations')
@login_required(allowed_pages=['admin'])
def get_event_registrations():
    try:
        event_name = request.args.get('event')
        # Remove reg_type parameter
        if not event_name:
            return jsonify({
                'success': False,
                'message': 'Event name is required'
            })
            
        norm_event = normalize_event_name(event_name)
        print(f"Searching for normalized event: '{norm_event}'")
        
        matches = get_matching_registrations('registrations', norm_event, 'online')
        
        return jsonify({
            'success': True,
            'registrations': matches,
            'isSpot': False  # Always false since spot is removed
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
        response = supabase.table('registrations').select('*').execute()
        
        if response.data:
            registrations = [{
                'ack_id': reg['ack_id'],
                'college': reg['college'],
                'email': reg['email'],
                'phone': reg['phone'],
                'event_details': reg['event_details']
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
        event_name = request.args.get('event')
        
        if not event_name:
            return jsonify({
                'success': False,
                'message': 'Event name is required'
            })
        
        # Get registrations for the specific event
        norm_event = normalize_event_name(event_name)
        matches = get_matching_registrations('registrations', norm_event, 'online')

        if not matches:
            return jsonify({
                'success': False,
                'message': 'No registrations found for this event'
            })
        
        # Prepare CSV output
        output = io.StringIO(newline='')
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)
        
        # Define headers based on registration type
        headers = ['Ack ID', 'College', 'Email', 'Phone', 'Participants', 'Total Cost', 'Registration Date']
            
        writer.writerow(headers)

        # Write data rows
        for reg in matches:
            row = [
                reg.get('ack_id', ''),
                reg.get('college', ''),
                reg.get('email', ''),
                reg.get('phone', ''),
                reg.get('team_members', ''),
                f"₹{reg.get('total_cost', 0)}",
                reg.get('registration_date', '').split('T')[0]
            ]
            
            writer.writerow(row)
        
        # Get CSV content and create response
        csv_output = output.getvalue()
        output.close()
        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename={norm_event}_online_registrations.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig',
                'Cache-Control': 'no-cache'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Error in download_registrations: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f"Error generating CSV: {str(e)}"
        })

@app.route('/api/search-registration/<ack_id>')
@login_required(allowed_pages=['admin'])
def search_registration(ack_id):
    try:
        # Search in registrations table
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            print(f"Found registration: {registration}")  # Debug log
            
            return jsonify({
                'success': True,
                'registration': {
                    'email': registration['email'],
                    'college': registration['college'],
                    'phone': registration['phone']
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

# Add this new function to handle unauthorized access
@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        'success': False,
        'message': 'Authentication required'
    }), 401

# Add these new routes after your existing routes
@app.route('/utr-management')
def utr_management():
    return render_template('utr_management.html')

# Add this function to hash sensitive data
def mask_sensitive_data(data):
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if key in ['email', 'phone', 'utr_number', 'dd_number', 'payment_reference']:
                if value:
                    masked[key] = value[:3] + '*' * (len(value) - 3)
            else:
                masked[key] = value
        return masked
    return data

@app.route('/api/search-registration-utr/<ack_id>')
def search_registration_utr(ack_id):
    try:
        print(f"Processing registration lookup") # Generic log without ID
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            # Mask sensitive data before logging
            safe_log_data = mask_sensitive_data(registration)
            print(f"Found registration data: {safe_log_data}")
            
            return jsonify({
                'success': True,
                'registration': registration
            })
        
        print("No matching registration found")
        return jsonify({
            'success': False,
            'message': 'Registration not found'
        })
        
    except Exception as e:
        print(f"Error in registration lookup: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred'  # Generic error message
        })

@app.route('/api/update-payment', methods=['POST'])
def update_payment():
    try:
        data = request.get_json()
        if not all([data.get('ack_id'), data.get('payment_type'), data.get('reference_number')]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            })
        
        # Hash the reference number for logging
        hashed_ref = hashlib.sha256(data['reference_number'].encode()).hexdigest()[:8]
        print(f"Processing payment update with ref: {hashed_ref}")

        ack_id = data.get('ack_id')
        payment_type = data.get('payment_type')
        reference_number = data.get('reference_number')
        
        update_data = {
            'payment_type': payment_type,
            'payment_status': 'paid',  # Set status to paid
            'payment_date': datetime.now().isoformat(),
            'payment_reference': reference_number
        }
        update_data['utr_number'] = None
        update_data['dd_number'] = None
        
        if payment_type == 'utr':
            update_data['utr_number'] = reference_number
        else:
            update_data['dd_number'] = reference_number

        response = supabase.table('registrations').update(update_data).eq('ack_id', ack_id).execute()
        print("Update Payment response:", response)  # New logging line

        if response.data:
            return jsonify({
                'success': True,
                'message': 'Payment details updated successfully'
            })
        return jsonify({
            'success': False,
            'message': 'Failed to update payment details'
        })
    except Exception as e:
        print(f"Error updating payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == "__main__":
    app.run(debug=app.config['DEBUG'])