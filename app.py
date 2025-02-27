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
        response.headers['Cache-Control'] = 'public, max-age=300'  # Cache for 5 minutes
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

                <p class="bg-[rgba(255,0,255,0.1)] border-2 border-[#FF00FF] p-3 sm:p-4 md:p-6 rounded-lg text-white font-bold text-sm sm:text-base text-center">
    Please pay the registration fees at the registration desk on the event day or submit a Demand Draft (DD) in the favor of "The Finance Officer, VTU Belagavi, Yukti Cultural Account" on 10th March 2025 before 10:30 AM.
</p>
<p class="bg-[rgba(255,0,255,0.1)] border-2 border-[#FF00FF] p-3 sm:p-4 md:p-6 rounded-lg text-white font-bold text-sm sm:text-base text-center">
    Bring a hard copy of the acknowledgment receipt – failure to do so will result in cancellation of registration and restricted entry.
</p>
<p class="bg-[rgba(255,0,255,0.1)] border-2 border-[#FF00FF] p-3 sm:p-4 md:p-6 rounded-lg text-white font-bold text-sm sm:text-base text-center">
    Carry a valid college ID for event entry.
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

def send_spot_registration_email(to_email, ack_id, details):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['GMAIL_USER']
        msg['To'] = to_email
        msg['Subject'] = f"YUKTI 2025 Spot Registration Confirmation - {ack_id}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1c1c1c; padding: 20px; color: #ffffff;">
                <h2 style="color: #FFD700; text-align: center;">Spot Registration Successful!</h2>
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #FFD700;">Registration Details</h3>
                    <p><strong>Acknowledgement ID:</strong> {ack_id}</p>
                    <p><strong>USN/College ID:</strong> {details['usn']}</p>
                    <p><strong>UTR Number:</strong> {details['utr_number']}</p>
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
                    Please keep this acknowledgement for your records.
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(app.config['GMAIL_USER'], app.config['GMAIL_PASSWORD'])
            server.send_message(msg)
        
        print(f"Spot registration email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send spot registration email: {str(e)}")
        return False


def generate_ack_id():
    # Create a new formatted ID with sequential number padded to 5 digits
    current_num = len(supabase.table('registrations').select('ack_id').execute().data) + 1
    formatted_num = str(current_num).zfill(5)  # Pad with zeros to make 5 digits
    return f"YUKTI-2025-{formatted_num}"

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

@app.route('/spot-page')
def spot_page():
    return render_template('spot.html')

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

@app.route('/spot-register', methods=['GET', 'POST'])
def spot_register():
    if request.method == 'GET':
        return render_template('spot.html')
    
    if request.method == "POST":
        try:
            data = request.get_json(silent=True)
            
            if not data:
                return jsonify({'success': False, 'message': 'No data received'})
            
            ack_id = generate_ack_id()
            
            # Calculate total participants from event details
            total_participants = 0
            event_details = data['selectedEvents']
            
            for event in event_details:
                if event.get('type') == 'team' and event.get('members'):
                    total_participants += len(event['members'])
                elif event.get('participant'):
                    total_participants += 1
            
            # Prepare registration data without separate USN field
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': total_participants,
                'total_cost': data['totalCost'],
                'event_details': event_details,  # USN is now included within event details
                'registration_date': datetime.now().isoformat(),
                'utr_number': data['utrNumber']
            }
            
            # Insert into Supabase
            response = supabase.table('spot_registrations').insert(registration_data).execute()
            
            if response.data:
                # Format event details for email
                event_details_html = []
                for event in event_details:
                    event_html = f"""<div style="padding: 10px; border: 1px solid #ccc; margin: 5px 0;">
                        <p><strong>Event:</strong> {event['event']}</p>
                        <p><strong>Type:</strong> {event['type']}</p>
                        <p><strong>Cost:</strong> ₹{event['cost']}</p>"""
                    
                    if event.get('members'):
                        members_list = [f"{m['name']} ({m['usn']})" for m in event['members']]
                        event_html += f"<p><strong>Team Members:</strong> {', '.join(members_list)}</p>"
                    elif event.get('participant'):
                        participant = event['participant']
                        event_html += f"<p><strong>Participant:</strong> {participant['name']} ({participant['usn']})</p>"
                    
                    event_html += "</div>"
                    event_details_html.append(event_html)

                email_details = {
                    'email': data['email'],
                    'phone': data['phone'],
                    'college': data['college'],
                    'total_cost': data['totalCost'],
                    'utr_number': data['utrNumber'],
                    'event_details_html': ''.join(event_details_html)
                }
                
                send_spot_registration_email(data['email'], ack_id, email_details)
                return jsonify({'success': True, 'ack_id': ack_id})
            
            return jsonify({'success': False, 'message': 'Registration failed'})
            
        except Exception as e:
            print(f"Error in spot registration: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    
    return render_template("spot.html")

# Update show_spot_ack to handle USN from event_details
@app.route('/spot-acknowledgement/<ack_id>')
def show_spot_ack(ack_id):
    try:
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
                'utr_number': registration['utr_number']
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
                        'total_cost': reg.get('total_cost', 0),
                        'registration_date': reg.get('registration_date', ''),
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

# Keep the API endpoints protected with login_required
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
        reg_type = request.args.get('type', 'online')
        event_name = request.args.get('event')
        
        if not event_name:
            return jsonify({
                'success': False,
                'message': 'Event name is required'
            })
        
        # Get registrations for the specific event
        norm_event = normalize_event_name(event_name)
        table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
        matches = get_matching_registrations(table_name, norm_event, reg_type)

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
        if reg_type == 'spot':
            headers.append('UTR Number')
            
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
            
            if reg_type == 'spot':
                row.append(reg.get('utr_number', ''))
                
            writer.writerow(row)
        
        # Get CSV content and create response
        csv_output = output.getvalue()
        output.close()
        response = Response(
            csv_output.encode('utf-8-sig'),
            mimetype='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': f'attachment; filename={norm_event}_{reg_type}_registrations.csv',
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

# Add this new function to handle unauthorized access
@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        'success': False,
        'message': 'Authentication required'
    }), 401

if __name__ == "__main__":
    app.run(debug=app.config['DEBUG'])