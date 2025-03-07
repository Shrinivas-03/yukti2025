from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_from_directory
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

from functools import wraps

import functools  # Add this full import
from functools import wraps  # Keep this existing import
import re
import io
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from flask_minify import Minify
import hashlib
from flask_compress import Compress
from email_validator import validate_email, EmailNotValidError

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

# Update Compress configuration
compress = Compress()
app.config.update(
    # Prefer Brotli for supported browsers, fallback to gzip
    COMPRESS_ALGORITHM=['br', 'gzip'],
    
    # Use moderate Brotli compression level
    COMPRESS_BR_LEVEL=6,
    
    # Only compress these mime types
    COMPRESS_MIMETYPES=[
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript',
        'text/plain',
        'application/xml',
        'application/x-yaml'
    ],
    
    # Don't compress files smaller than 500 bytes
    COMPRESS_MIN_SIZE=500,
    
    # Remove the cache backend configuration that was causing the error
    # COMPRESS_CACHE_BACKEND='filesystem',
    # COMPRESS_CACHE_KEY='compression-cache',
    
    # Cache compressed files for 5 minutes (300 seconds)
    SEND_FILE_MAX_AGE_DEFAULT=300
)

# Initialize compression after config
compress.init_app(app)

Minify(app=app, html=True, js=True, cssless=True)
# Remove Compress(app) line

# Apply configuration
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Initialize Supabase client
supabase: Client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])

# Keep only one session config, remove all other session configs
app.config.update(

    SESSION_COOKIE_SECURE=True,   # Ensures cookies are sent only over HTTPS
    SESSION_COOKIE_HTTPONLY=True, # Prevents JavaScript from accessing cookies
    SESSION_COOKIE_SAMESITE='Lax', # Helps prevent CSRF attacks
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=5),  # Changed from 30 to 5 minutes
    SEND_FILE_MAX_AGE_DEFAULT=300,  # 5 minutes in seconds

    
  
    SESSION_REFRESH_EACH_REQUEST=False,  # Disable auto refresh

)

@app.after_request
def add_cache_control_headers(response):
    # Set stricter cache control headers
    response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"  # 5 minutes
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = (datetime.utcnow() + timedelta(minutes=5)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Add Vary header for proper cache invalidation
    response.vary.add('Cookie')
    response.vary.add('Accept-Encoding')
    
    return response

@app.after_request
def add_compression_headers(response):
    # Add Vary header to handle different compression algorithms
    if 'Content-Encoding' in response.headers:
        response.headers['Vary'] = 'Accept-Encoding'
    return response

# Remove the cache-related function and keep the static file serving route
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
                    Center for PG Studies And Regional Office Kalaburagi
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
            if not session.get('user_id'):
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            # Refresh the session timestamp on each request
            session['login_time'] = datetime.now().isoformat()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(f=None):
    if f is None:
        return functools.partial(login_required)
        
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
            
        return f(*args, **kwargs)
        
    return decorated_function

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

def validate_phone(phone):
    """Validate phone number format"""
    # Check if phone is exactly 10 digits and starts with 6-9
    if not phone:
        return False, "Phone number is required"
    
    phone = str(phone).strip()
    if not re.match(r'^[6-9]\d{9}$', phone):
        return False, "Phone number must be 10 digits and start with 6-9"
    
    return True, "Valid phone number"

def validate_email_address(email):
    """Validate email using email-validator library"""
    try:
        # Validate and get normalized email
        valid = validate_email(email)
        return True, "Valid email"
    except EmailNotValidError as e:
        return False, str(e)

@app.route('/register', methods=['POST'])
def register_submit():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'No data received'})

        # Validate email
        email_valid, email_msg = validate_email_address(data['email'])
        if not email_valid:
            return jsonify({
                'success': False, 
                'message': f'Invalid email: {email_msg}'
            })

        # Validate phone
        phone_valid, phone_msg = validate_phone(data['phone'])
        if not phone_valid:
            return jsonify({
                'success': False, 
                'message': f'Invalid phone: {phone_msg}'
            })

        # Continue with existing registration logic
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
                        'event_details': reg.get('event_details', []),
                        'payment_status': reg.get('payment_status', 'Pending'),  # Add payment status
                        'payment_type': reg.get('payment_type', 'N/A'),  # Add payment type
                        'utr_number': reg.get('utr_number', 'N/A'),  # Add UTR number
                        'dd_number': reg.get('dd_number', 'N/A')  # Add DD number
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
@login_required()  # Remove the allowed_pages parameter
def get_event_registrations_list():  # Changed function name
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
@login_required()  # Remove the allowed_pages parameter
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
@login_required()
def download_registrations():
    try:
        event_id = request.args.get('event')
        
        if not event_id:
            return jsonify({
                'success': False,
                'message': 'Event ID is required'
            })

        # Updated event mappings to include all events including cultural ones
        event_mappings = {
            'prakalpa_prastuthi': 'Prakalpa Prastuthi',
            'chanaksh': 'Chanaksh',
            'robo_samara_war': 'Robo Samara (Robo War)',
            'robo_samara_race': 'Robo Samara (Robo Race)',
            'pragyan': 'Pragyan',
            'vagmita': 'Vagmita',
            # Cultural events
            'ninaad_solo': 'Ninaad',
            'ninaad_group': 'Ninaad',
            'nritya_solo': 'Nritya Saadhana',
            'nritya_group': 'Nritya Saadhana',
            'navyataa': 'Navyataa',
            # Management events
            'daksha': 'Daksha',
            'shreshta_vitta': 'Shreshta Vitta',
            'manava_sansadhan': 'Manava Sansadhan',
            'sumedha': 'Sumedha',
            'vipanan': 'Vipanan',
            # Visual Art events
            'sthala_chitrapatha': 'Sthala Chitrapatha',
            'chitragatha': 'Chitragatha',
            'ruprekha': 'Ruprekha',
            'hastakala': 'Hastakala',
            'swachitra': 'Swachitra',
            # Games events
            'bgmi': 'BGMI',
            'mission_talaash': 'Mission Talaash'
        }

        # Get display name
        event_name = event_mappings.get(event_id)
        if not event_name:
            print(f"Invalid event ID: {event_id}")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Invalid event ID'
            })

        # Additional event type checks for events with variants
        event_variants = {
            'ninaad_solo': '(Singing Solo)',
            'ninaad_group': '(Singing Group)',
            'nritya_solo': '(Dance Solo)',
            'nritya_group': '(Dance Group)'
        }

        # Rest of the function remains the same
        response = supabase.table('registrations').select('*').execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'message': 'No registrations found'
            })

        matches = []
        for reg in response.data:
            if not reg.get('event_details'):
                continue

            for event in reg.get('event_details', []):
                # Get stored event name
                stored_event = event.get('event', '').split('(')[0].strip()
                variant_suffix = event_variants.get(event_id, '')
                
                # Check if the event matches either the base name or with variant
                if stored_event.startswith(event_name) and (not variant_suffix or variant_suffix in event.get('event', '')):
                    # Format participant info - only names without USN
                    participants = []
                    if event.get('type') == 'team' and event.get('members'):
                        participants = [m['name'] for m in event['members']]  # Only get names
                    elif event.get('participant'):
                        participant = event['participant']
                        participants = [participant['name']]  # Only get name

                    # Get payment reference (UTR or DD number)
                    payment_ref = reg.get('utr_number') or reg.get('dd_number') or 'N/A'

                    matches.append({
                        'ack_id': reg['ack_id'],
                        'college': reg['college'],
                        'phone': reg['phone'],
                        'participants': '; '.join(participants),  # Join participant names
                        'event_cost': event.get('cost', 0),
                        'payment_reference': payment_ref  # Added payment reference
                    })

        if not matches:
            return jsonify({
                'success': False,
                'message': 'No registrations found for this event'
            })

        # Create CSV with updated headers
        output = io.StringIO(newline='')
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)
        
        headers = [
            'Acknowledgement ID',
            'College',
            'Phone',
            'Participant Details',
            'Event Cost',
            'Payment Reference'  # Added new header
        ]
        
        writer.writerow(headers)

        for reg in matches:
            row = [
                reg['ack_id'],
                reg['college'],
                reg['phone'],
                reg['participants'],
                f"₹{reg['event_cost']}",
                reg['payment_reference']  # Added payment reference
            ]
            writer.writerow(row)

        csv_output = output.getvalue()
        output.close()
        
        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename={event_id}_registrations.csv',
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
@login_required()  # Remove the allowed_pages parameter
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

# Add these new routes and functions after your existing routes

@app.route('/admin')
def admin():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('admin'))
        
    # Updated categories with normalized event IDs

        return redirect(url_for('admin'))
    
    # Remove any session modifications

    categories = [
        {
            'id': 'technical',
            'name': 'Manthana (Technical Events)',
            'events': [
                {'id': 'prakalpa_prastuthi', 'name': 'Prakalpa Prastuthi (Ideathon)'},
                {'id': 'chanaksh', 'name': 'Chanaksh (Code Quest)'},
                {'id': 'robo_samara_war', 'name': 'Robo Samara (Robo War)'},
                {'id': 'robo_samara_race', 'name': 'Robo Samara (Robo Race)'},
                {'id': 'pragyan', 'name': 'Pragyan (Quiz)'},
                {'id': 'vagmita', 'name': 'Vagmita (Elocution)'}
            ]
        },
        {
            'id': 'cultural',
            'name': 'Manoranjana (Cultural Events)',
            'events': [
                {'id': 'ninaad_solo', 'name': 'Ninaad (Singing Solo)'},
                {'id': 'ninaad_group', 'name': 'Ninaad (Singing Group)'},
                {'id': 'nritya_solo', 'name': 'Nritya Saadhana (Dance Solo)'},
                {'id': 'nritya_group', 'name': 'Nritya Saadhana (Dance Group)'},
                {'id': 'navyataa', 'name': 'Navyataa (Ramp Walk)'}
            ]
        },
        {
            'id': 'management',
            'name': 'Chintana (Management Events)',
            'events': [
                {'id': 'daksha', 'name': 'Daksha (Best Manager)'},
                {'id': 'shreshta_vitta', 'name': 'Shreshta Vitta (Finance)'},
                {'id': 'manava_sansadhan', 'name': 'Manava Sansadhan (HR)'},
                {'id': 'sumedha', 'name': 'Sumedha (Start-Up)'},
                {'id': 'vipanan', 'name': 'Vipanan (Marketing)'}
            ]
        },
        {
            'id': 'visual_art',
            'name': 'Kalachitrana (Visual Art)',
            'events': [
                {'id': 'sthala_chitrapatha', 'name': 'Sthala Chitrapatha (Spot Photography)'},
                {'id': 'chitragatha', 'name': 'Chitragatha (Short Film)'},
                {'id': 'ruprekha', 'name': 'Ruprekha (Sketch Art)'},
                {'id': 'hastakala', 'name': 'Hastakala (Painting)'},
                {'id': 'swachitra', 'name': 'Swachitra (Selfie Point)'}
            ]
        },
        {
            'id': 'games',
            'name': 'Krida Ratna (Game Zone)',
            'events': [
                {'id': 'bgmi', 'name': 'BGMI'},
                {'id': 'mission_talaash', 'name': 'Mission Talaash (Treasure Hunt)'}
            ]
        }
    ]

    # Updated event name mappings
    event_names = {
        'prakalpa_prastuthi': 'Prakalpa Prastuthi (Ideathon)',
        'chanaksh': 'Chanaksh (Code Quest)',
        'robo_samara_war': 'Robo Samara (Robo War)',
        'robo_samara_race': 'Robo Samara (Robo Race)',
        'pragyan': 'Pragyan (Quiz)',
        'vagmita': 'Vagmita (Elocution)',
        'ninaad_solo': 'Ninaad (Singing Solo)',
        'ninaad_group': 'Ninaad (Singing Group)',
        'nritya_solo': 'Nritya Saadhana (Dance Solo)',
        'nritya_group': 'Nritya Saadhana (Dance Group)',
        'navyataa': 'Navyataa (Ramp Walk)',
        'daksh': 'Daksha (Best Manager)',
        'shreshta_vitta': 'Shreshta Vitta (Finance)',
        'manava_sansadhan': 'Manava Sansadhan (HR)',
        'sumedha': 'Sumedha (Start-Up)',
        'vipanan': 'Vipanan (Marketing)',
        'sthala_chitrapatha': 'Sthala Chitrapatha (Spot Photography)',
        'chitragatha': 'Chitragatha (Short Film)',
        'ruprekha': 'Ruprekha (Sketch Art)',
        'hastakala': 'Hastakala (Painting)',
        'swachitra': 'Swachitra (Selfie Point)',
        'bgmi': 'BGMI',
        'mission_talaash': 'Mission Talaash (Treasure Hunt)'
    }
    

    session['login_time'] = datetime.now().isoformat()


    return render_template('admin_dashboard.html', categories=categories, event_details=event_names)

# ...rest of existing code...

def get_event_name(event_id):
    # Simple event name mapping
    event_names = {
        'project_expo': 'Prakalpa Prastuthi (Ideathon)',
        'coding': 'Chanaksh (Code Quest)',
        'robo_war': 'Robo Samara (Robo War)',
        'robo_race': 'Robo Samara (Robo Race)',
        'quiz': 'Pragyan (Quiz)',
        'elocution': 'Vagmita (Elocution)',
        'singing_solo': 'Ninaad (Singing Solo)',
        'singing_group': 'Ninaad (Singing Group)',
        'dance_solo': 'Nritya Saadhana (Dance Solo)',
        'dance_group': 'Nritya Saadhana (Dance Group)',
        'ramp_walk': 'Navyataa (Ramp Walk)',
        'best_manager': 'Daksha (Best Manager)',
        'finance': 'Shreshta Vitta (Finance)',
        'hr': 'Manava Sansadhan (HR)',
        'startup': 'Sumedha (Start-Up)',
        'marketing': 'Vipanan (Marketing)',
        'photography': 'Sthala Chitrapatha (Spot Photography)',
        'short_film': 'Chitragatha (Short Film)',
        'sketch': 'Ruprekha (Sketch Art)',
        'painting': 'Hastakala (Painting)',
        'selfie': 'Swachitra (Selfie Point)',
        'bgmi': 'BGMI',
        'treasure_hunt': 'Mission Talaash (Treasure Hunt)'
    }
    return event_names.get(event_id, 'Unknown Event')

# ...rest of existing code...

@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        password = data.get('password')

        if not user_id or not password:
            return jsonify({
                'success': False,
                'message': 'Missing credentials'
            }), 400

        # Query admin_users table directly
        response = supabase.table('admin_users').select('*').eq('user_id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            admin = response.data[0]
            if password == admin['password']:
                session.permanent = True  # Make session permanent
                session.clear()
                session['user_id'] = user_id
                session['login_time'] = datetime.now().isoformat()
                session['is_admin'] = True
                
                return jsonify({'success': True})

        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

        if not (data and data.get('user_id') and data.get('password')):
            return jsonify({'success': False, 'message': 'Missing credentials'}), 400

        response = supabase.table('admin_users').select('*').eq('user_id', data['user_id']).execute()
        
        if response.data and response.data[0]['password'] == data['password']:
            session.clear()  # Clear any existing session
            session.permanent = True  # Enable session expiry
            session['user_id'] = data['user_id']
            return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# Helper function to create admin user (you can use this in development)
@app.route('/api/admin/create', methods=['POST'])
def create_admin():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        password = data.get('password')

        if not user_id or not password:
            return jsonify({
                'success': False,
                'message': 'Missing credentials'
            }), 400

        # Insert new admin user with plain password
        response = supabase.table('admin_users').insert({
            'user_id': user_id,
            'password': password,
            'created_at': datetime.now().isoformat()
        }).execute()

        if response.data:
            return jsonify({
                'success': True,
                'message': 'Admin user created successfully'
            })

        return jsonify({
            'success': False,
            'message': 'Failed to create admin user'
        })

    except Exception as e:
        print(f"Admin creation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    try:
        session.clear()
        return jsonify({
            'success': True,
            'redirect': '/admin'
        })
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error during logout'
        }), 500

@app.route('/api/admin/search/<ack_id>')
@login_required()  # Remove the allowed_pages parameter
def admin_search(ack_id):
    try:
        response = supabase.table('registrations').select('*').eq('ack_id', ack_id).execute()
        
        if response.data and len(response.data) > 0:
            registration = response.data[0]
            # Mask sensitive data in logs
            safe_log_data = mask_sensitive_data(registration)
            print(f"Found registration: {safe_log_data}")
            
            return jsonify({
                'success': True,
                'registration': registration
            })
        
        return jsonify({
            'success': False,
            'message': 'Registration not found'
        })
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        })

@app.route('/api/admin/dashboard-stats')
@login_required()
def get_dashboard_stats():
    try:
        # Get all registrations
        response = supabase.table('registrations').select('payment_status').execute()
        
        if response.data:
            total_registrations = len(response.data)
            total_paid = sum(1 for reg in response.data if reg.get('payment_status') == 'paid')
            total_pending = total_registrations - total_paid

            return jsonify({
                'success': True,
                'total_registrations': total_registrations,
                'total_paid': total_paid,
                'total_pending': total_pending
            })

        return jsonify({
            'success': True,
            'total_registrations': 0,
            'total_paid': 0,
            'total_pending': 0
        })

    except Exception as e:
        print(f"Error fetching dashboard stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching statistics'
        })

@app.route('/event-dashboard')
@login_required()
def event_dashboard():
    # Define categories and their events
    categories = [
        {
            'id': 'technical',
            'name': 'Manthana (Technical Events)',
            'events': [
                {'id': 'project_expo', 'name': 'Prakalpa Prastuthi (Ideathon)'},
                {'id': 'coding', 'name': 'Chanaksh (Code Quest)'},
                {'id': 'robo_war', 'name': 'Robo Samara (Robo War)'},
                {'id': 'robo_race', 'name': 'Robo Samara (Robo Race)'},
                {'id': 'quiz', 'name': 'Pragyan (Quiz)'},
                {'id': 'elocution', 'name': 'Vagmita (Elocution)'}
            ]
        },
        {
            'id': 'visual_art',
            'name': 'Kalachitrana (Visual Art)',
            'events': [
                {'id': 'photography', 'name': 'Sthala Chitrapatha (Spot Photography)'},
                {'id': 'short_film', 'name': 'Chitragatha (Short Film)'},
                {'id': 'sketch', 'name': 'Ruprekha (Sketch Art)'},
                {'id': 'painting', 'name': 'Hastakala (Painting)'},
                {'id': 'selfie', 'name': 'Swachitra (Selfie Point)'}
            ]
        },
        # Add other categories similarly...
    ]
    return render_template('event_dashboard.html', categories=categories)

@app.route('/api/admin/event-registrations/<event_id>')
@login_required()
def get_event_registrations_by_id(event_id):
    try:
        print(f"Looking up registrations for event ID: {event_id}")
        response = supabase.table('registrations').select('*').execute()
        
        if not response.data:
            return jsonify({
                'success': True,
                'eventName': get_event_name(event_id),
                'registrations': []
            })

        # Updated event mappings to be more specific with variants
        event_mappings = {
            'ninaad_solo': ['Ninaad (Singing Solo)', 'NINAAD (Singing Solo)'],
            'ninaad_group': ['Ninaad (Singing Group)', 'NINAAD (Singing Group)'],
            'nritya_solo': ['Nritya Saadhana (Dance Solo)'],
            'nritya_group': ['Nritya Saadhana (Dance Group)'],
            'prakalpa_prastuthi': ['Prakalpa Prastuthi', 'Prakalpa Prastuthi (Ideathon)'],
            'chanaksh': ['Chanaksh', 'Chanaksh (Code Quest)'],
            'robo_samara_war': ['Robo Samara (Robo War)'],
            'robo_samara_race': ['Robo Samara (Robo Race)'],
            'pragyan': ['Pragyan', 'Pragyan (Quiz)'],
            'vagmita': ['Vagmita', 'Vagmita (Elocution)'],
            'navyataa': ['Navyataa', 'Navyataa (Ramp Walk)'],
            'daksha': ['Daksha', 'Daksha (Best Manager)'],
            'shreshta_vitta': ['Shreshta Vitta', 'Shreshta Vitta (Finance)'],
            'manava_sansadhan': ['Manava Sansadhan', 'Manava Sansadhan (HR)'],
            'sumedha': ['Sumedha', 'Sumedha (Start-Up)'],
            'vipanan': ['Vipanan', 'Vipanan (Marketing)'],
            'sthala_chitrapatha': ['Sthala Chitrapatha', 'Sthala Chitrapatha (Spot Photography)'],
            'chitragatha': ['Chitragatha', 'Chitragatha (Short Film)'],
            'ruprekha': ['Ruprekha', 'Ruprekha (Sketch Art)'],
            'hastakala': ['Hastakala', 'Hastakala (Painting)'],
            'swachitra': ['Swachitra', 'Swachitra (Selfie Point)'],
            'bgmi': ['BGMI'],
            'mission_talaash': ['Mission Talaash', 'Mission Talaash (Treasure Hunt)']
        }

        event_name = get_event_name(event_id)
        valid_event_names = event_mappings.get(event_id, [])
        print(f"Looking for event: {event_name} with variants: {valid_event_names}")

        event_registrations = []
        for reg in response.data:
            if not reg.get('event_details'):
                continue

            for event in reg['event_details']:
                stored_event = event.get('event', '')
                # Check if the stored event matches any of the valid variants
                if any(variant in stored_event for variant in valid_event_names):
                    print(f"Found matching event: {stored_event}")
                    registration = {
                        'ack_id': reg['ack_id'],
                        'college': reg['college'],
                        'phone': reg['phone'],
                        'payment_status': reg.get('payment_status', 'pending'),
                        'payment_type': reg.get('payment_type'),
                        'utr_number': reg.get('utr_number'),
                        'dd_number': reg.get('dd_number'),
                        'event_cost': event.get('cost', 0)
                    }

                    # Add participant information
                    if event.get('type') == 'team' and event.get('members'):
                        participants = [f"{m['name']} ({m['usn']})" for m in event['members']]
                        registration['participants'] = participants
                    elif event.get('participant'):
                        participant = event['participant']
                        registration['participants'] = [f"{participant['name']} ({participant['usn']})"]

                    event_registrations.append(registration)

        print(f"Found {len(event_registrations)} registrations")

        return jsonify({
            'success': True,
            'eventName': event_name,
            'registrations': event_registrations
        })

    except Exception as e:
        print(f"Error fetching event registrations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching registrations: {str(e)}'
        })

# Update get_event_name function
def get_event_name(event_id):
    event_names = {
        'prakalpa_prastuthi': 'Prakalpa Prastuthi (Ideathon)',
        'chanaksh': 'Chanaksh (Code Quest)',
        'robo_samara_war': 'Robo Samara (Robo War)',
        'robo_samara_race': 'Robo Samara (Robo Race)',
        'pragyan': 'Pragyan (Quiz)',
        'vagmita': 'Vagmita (Elocution)',
        'ninaad_solo': 'Ninaad (Singing Solo)',
        'ninaad_group': 'Ninaad (Singing Group)',
        'nritya_solo': 'Nritya Saadhana (Dance Solo)',
        'nritya_group': 'Nritya Saadhana (Dance Group)',
        'navyataa': 'Navyataa (Ramp Walk)',
        'daksha': 'Daksha (Best Manager)',
        'shreshta_vitta': 'Shreshta Vitta (Finance)',
        'manava_sansadhan': 'Manava Sansadhan (HR)',
        'sumedha': 'Sumedha (Start-Up)',
        'vipanan': 'Vipanan (Marketing)',
        'sthala_chitrapatha': 'Sthala Chitrapatha (Spot Photography)',
        'chitragatha': 'Chitragatha (Short Film)',
        'ruprekha': 'Ruprekha (Sketch Art)',
        'hastakala': 'Hastakala (Painting)',
        'swachitra': 'Swachitra (Selfie Point)',
        'bgmi': 'BGMI',
        'mission_talaash': 'Mission Talaash (Treasure Hunt)'
    }
    return event_names.get(event_id, 'Unknown Event')


@app.route('/api/check-updates')
def check_updates():
    """Endpoint to check for updates and force refresh if needed"""
    try:
        last_update = session.get('last_update', datetime.utcnow())
        current_time = datetime.utcnow()
        
        # If more than 5 minutes have passed
        if current_time - datetime.fromisoformat(last_update) > timedelta(minutes=5):
            session['last_update'] = current_time.isoformat()
            return jsonify({'refresh_needed': True})
            
        return jsonify({'refresh_needed': False})
    except Exception as e:
        print(f"Update check error: {str(e)}")
        return jsonify({'refresh_needed': False})

@app.route('/api/stalls', methods=['GET', 'POST'])
@login_required()
def manage_stalls():
    if request.method == 'GET':
        try:
            order_by = request.args.get('order')
            query = supabase.table('stalls').select('*')
            if order_by:
                field, direction = order_by.split('.')
                query = query.order(field, desc=(direction == 'desc'))
            response = query.execute()
            if response.data:
                return jsonify({
                    'success': True,
                    'stalls': response.data
                })
            return jsonify({
                'success': True,
                'stalls': []
            })
        except Exception as e:
            print(f"Error fetching stalls: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })
    elif request.method == 'POST':
        try:
            data = request.get_json()
            # Convert transaction_date to ISO format
            transaction_date_str = data.get('transaction_date')
            if transaction_date_str:
                try:
                    data['transaction_date'] = datetime.strptime(transaction_date_str, '%Y-%m-%d').isoformat()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD.'
                    })
            response = supabase.table('stalls').insert(data).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Stall added successfully',
                    'id': response.data[0]['id']
                })
            return jsonify({
                'success': False,
                'message': 'Failed to add stall'
            })
        except Exception as e:
            print(f"Error adding stall: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })

@app.route('/api/stalls/<stall_id>', methods=['PUT', 'DELETE'])
@login_required()
def manage_stall(stall_id):
    if request.method == 'PUT':
        try:
            data = request.get_json()
            # Convert transaction_date to ISO format if it exists
            transaction_date_str = data.get('transaction_date')
            if transaction_date_str:
                try:
                    data['transaction_date'] = datetime.strptime(transaction_date_str, '%Y-%m-%d').isoformat()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD.'
                    })
            response = supabase.table('stalls').update(data).eq('id', stall_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Stall updated successfully'
                })
            return jsonify({
                    'success': False,
                    'message': 'Failed to update stall'
                })
        except Exception as e:
            print(f"Error updating stall: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })
    elif request.method == 'DELETE':
        try:
            response = supabase.table('stalls').delete().eq('id', stall_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Stall deleted successfully'
                })
            return jsonify({
                'success': False,
                'message': 'Failed to delete stall'
            })
        except Exception as e:
            print(f"Error deleting stall: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })

@app.route('/api/download-stalls')
@login_required()
def download_stalls():
    try:
        response = supabase.table('stalls').select('*').execute()

        if not response.data:
            return jsonify({
                'success': False,
                'message': 'No stall details found'
            })

        # Create CSV
        output = io.StringIO(newline='')
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)

        headers = [
            'Stall No',
            'Stall Category',
            'Items Description',
            'Stall Owner',
            'Contact Number',
            'Amount Paid',
            'Reference ID/UTR',
            'Transaction Date'
        ]

        writer.writerow(headers)

        for stall in response.data:
            row = [
                stall.get('stall_no', ''),
                stall.get('stall_category', ''),
                stall.get('items_description', ''),
                stall.get('stall_owner', ''),
                stall.get('contact_number', ''),
                stall.get('amount_paid', ''),
                stall.get('reference_id_utr', ''),
                stall.get('transaction_date', '')
            ]
            writer.writerow(row)

        csv_output = output.getvalue()
        output.close()

        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': 'attachment; filename=stall_details.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig',
                'Cache-Control': 'no-cache'
            }
        )

        return response

    except Exception as e:
        print(f"Error in download_stalls: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating CSV: {str(e)}"
        })

# Sponsor Management APIs
@app.route('/api/sponsors', methods=['GET', 'POST'])
@login_required()
def manage_sponsors():
    if request.method == 'GET':
        try:
            response = supabase.table('sponsors').select('*').execute()
            if response.data:
                return jsonify({
                    'success': True,
                    'sponsors': response.data
                })
            return jsonify({
                'success': True,
                'sponsors': []
            })
        except Exception as e:
            print(f"Error fetching sponsors: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })
    elif request.method == 'POST':
        try:
            data = request.get_json()
            # Convert transaction_date to ISO format
            transaction_date_str = data.get('transaction_date')
            if transaction_date_str:
                try:
                    data['transaction_date'] = datetime.strptime(transaction_date_str, '%Y-%m-%d').isoformat()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD.'
                    })
            response = supabase.table('sponsors').insert(data).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Sponsor added successfully',
                    'id': response.data[0]['id']
                })
            return jsonify({
                'success': False,
                'message': 'Failed to add sponsor'
            })
        except Exception as e:
            print(f"Error adding sponsor: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })

@app.route('/api/sponsors/<sponsor_id>', methods=['PUT', 'DELETE'])
@login_required()
def manage_sponsor(sponsor_id):
    if request.method == 'PUT':
        try:
            data = request.get_json()
             # Convert transaction_date to ISO format if it exists
            transaction_date_str = data.get('transaction_date')
            if transaction_date_str:
                try:
                    data['transaction_date'] = datetime.strptime(transaction_date_str, '%Y-%m-%d').isoformat()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid date format. Please use YYYY-MM-DD.'
                    })
            response = supabase.table('sponsors').update(data).eq('id', sponsor_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Sponsor updated successfully'
                })
            return jsonify({
                    'success': False,
                    'message': 'Failed to update sponsor'
                })
        except Exception as e:
            print(f"Error updating sponsor: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })
    elif request.method == 'DELETE':
        try:
            response = supabase.table('sponsors').delete().eq('id', sponsor_id).execute()

            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Sponsor deleted successfully'
                })
            return jsonify({
                'success': False,
                'message': 'Failed to delete sponsor'
            })
        except Exception as e:
            print(f"Error deleting sponsor: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            })

@app.route('/api/download-sponsors')
@login_required()
def download_sponsors():
    try:
        response = supabase.table('sponsors').select('*').execute()

        if not response.data:
            return jsonify({
                'success': False,
                'message': 'No sponsor details found'
            })

        # Create CSV
        output = io.StringIO(newline='')
        output.write('\ufeff')  # UTF-8 BOM
        writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)

        headers = [
            'Serial No',
            'Sponsored By',
            'Sponsored Category',
            'Amount Paid',
            'Reference ID/UTR',
            'Transaction Date'
        ]

        writer.writerow(headers)

        for sponsor in response.data:
            row = [
                sponsor.get('serial_no', ''),
                sponsor.get('sponsored_by', ''),
                sponsor.get('sponsored_category', ''),
                sponsor.get('amount_paid', ''),
                sponsor.get('reference_id_utr', ''),
                sponsor.get('transaction_date', '')
            ]
            writer.writerow(row)

        csv_output = output.getvalue()
        output.close()

        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': 'attachment; filename=sponsor_details.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig',
                'Cache-Control': 'no-cache'
            }
        )

        return response

    except Exception as e:
        print(f"Error in download_sponsors: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error generating CSV: {str(e)}"
        })

if __name__ == "__main__":
    # Disable the reloader by setting use_reloader to False
    app.run(debug=True, use_reloader=False)