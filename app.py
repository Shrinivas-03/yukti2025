from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from datetime import datetime
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
from PIL import Image
import uuid
import json
load_dotenv()  # Load the .env file


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






def send_registration_email(to_email, ack_id, details):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['GMAIL_USER']
        msg['To'] = to_email
        msg['Subject'] = f"YUKTI 2025 Registration Confirmation - {ack_id}"

        # Modified email body to conditionally include UTR number
        body = f"""
        <html>
        <body>
            <h2>Registration Successful!</h2>
            <p><strong>Acknowledgement ID:</strong> {ack_id}</p>
            <p><strong>Event Details:</strong> {details['event_name']}</p>
            <p><strong>College:</strong> {details['college']}</p>
            <p><strong>Team Members:</strong> {details['team_members']}</p>
            <p><strong>Total Cost:</strong> ₹{details['total_cost']}</p>
            {f'<p><strong>UTR Number:</strong> {details["utr_number"]}</p>' if 'utr_number' in details else ''}
            <p>Thank you for registering!</p>
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
            # Handle ISO format string with timezone
            dt = datetime.fromisoformat(value.split('+')[0])  # Remove timezone part
        else:
            dt = value
        return dt.strftime('%d-%m-%Y %I:%M %p')  # Format: DD-MM-YYYY HH:MM AM/PM
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

def compress_image(image_file, max_size_kb=100):
    try:
        print(f"Starting image compression for file: {image_file.filename}")
        # Open the image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            print(f"Converting image from {img.mode} to RGB")
            img = img.convert('RGB')
        
        # Initial quality
        quality = 95
        output = io.BytesIO()
        
        # Resize if too large
        max_dimension = 1500
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            print(f"Resizing image from {img.size} to {new_size}")
            img = img.resize(new_size, Image.LANCZOS)
        
        # Compress until file size is under max_size_kb
        while quality > 5:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            size_kb = len(output.getvalue()) / 1024
            print(f"Compressed size at quality {quality}: {size_kb:.2f}KB")
            if size_kb <= max_size_kb:
                break
            quality -= 5
        
        output.seek(0)
        print("Image compression completed successfully")
        return output
    except Exception as e:
        print(f"Error in compress_image: {str(e)}")
        raise

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        try:
            # Get form data
            payment_proof = request.files.get('paymentProof')
            utr_number = request.form.get('utrNumber')
            dd_number = request.form.get('ddNumber')
            payment_method = request.form.get('paymentMethod')
            
            print(f"Received payment_method: {payment_method}")
            print(f"UTR number: {utr_number}")
            print(f"DD number: {dd_number}")
            print(f"Payment proof file: {payment_proof.filename if payment_proof else 'No file'}")
            
            data = json.loads(request.form.get('registrationData'))
            
            # Validate payment method and requirements
            if (payment_method == 'utr'):
                if not payment_proof:
                    return jsonify({
                        'success': False, 
                        'message': 'Payment proof image is required for UTR payment'
                    })
                if not utr_number:
                    return jsonify({
                        'success': False, 
                        'message': 'UTR number is required for UTR payment'
                    })
            elif payment_method == 'dd':
                if not dd_number:
                    return jsonify({
                        'success': False, 
                        'message': 'DD number is required for DD payment'
                    })
            
            file_url = None
            if payment_method == 'utr' and payment_proof:
                try:
                    # Check file type
                    allowed_extensions = {'png', 'jpg', 'jpeg'}
                    if '.' not in payment_proof.filename or \
                       payment_proof.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                        return jsonify({
                            'success': False,
                            'message': 'Invalid file type. Please upload PNG or JPEG images only.'
                        })
                    
                    # Compress and upload image
                    compressed_image = compress_image(payment_proof, max_size_kb=100)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = str(uuid.uuid4())[:8]
                    file_extension = os.path.splitext(payment_proof.filename)[1]
                    new_filename = f"payment_{timestamp}_{unique_id}{file_extension}"
                    
                    file_path = f"payment_proofs/{new_filename}"
                    print(f"Uploading to path: {file_path}")
                    
                    # Upload to Supabase
                    upload_response = supabase.storage.from_('payment').upload(
                        path=file_path,
                        file=compressed_image.getvalue(),
                        file_options={"content-type": "image/jpeg"}
                    )
                    print(f"Upload response: {upload_response}")
                    
                    # Get public URL
                    file_url = supabase.storage.from_('payment').get_public_url(file_path)
                    print(f"File URL: {file_url}")
                    
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    return jsonify({
                        'success': False,
                        'message': f'Error processing payment proof: {str(e)}'
                    })

            # Create registration record with correct column names
            registration_data = {
                'ack_id': generate_ack_id(),
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': data['totalParticipants'],
                'total_cost': data['totalCost'],
                'registration_date': datetime.now().isoformat(),
                'event_details': data['selectedEvents'],
                'utr_number': utr_number if payment_method == 'utr' else None,  # Store in utr_number column
                'DD': dd_number if payment_method == 'dd' else None,  # Store in DD column
                'payment_proof_url': file_url
            }
            
            # Only add payment_method if it's supported by the database
            if payment_method in ['utr', 'dd']:
                registration_data['payment_method'] = payment_method

            # Insert into Supabase
            response = supabase.table('registrations').insert(registration_data).execute()
            
            if not response.data:
                return jsonify({
                    'success': False,
                    'message': 'Failed to save registration'
                })

            # Prepare email details
            email_details = {
                'event_name': ", ".join(event['event'] for event in data['selectedEvents']),
                'college': data['college'],
                'team_members': ", ".join(
                    ", ".join(event.get('members', [])) if event.get('members') 
                    else event.get('participant', '') 
                    for event in data['selectedEvents']
                ),
                'total_cost': data['totalCost'],
                'payment_method': payment_method
            }

            # Add payment details to email
            if payment_method == 'utr':
                email_details['utr_number'] = utr_number
            elif payment_method == 'dd':
                email_details['dd_number'] = dd_number

            # Send confirmation email
            email_sent = send_registration_email(data['email'], registration_data['ack_id'], email_details)
            
            if not email_sent:
                print(f"Warning: Failed to send email to {data['email']}")

            return jsonify({
                'success': True,
                'ack_id': registration_data['ack_id'],
                'message': 'Registration successful' + ('' if email_sent else ' (email delivery failed)')
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
            
            # Prepare registration data
            registration_data = {
                'ack_id': ack_id,
                'email': data['email'],
                'phone': data['phone'],
                'college': data['college'],
                'total_participants': data['totalParticipants'],
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
                
                # Modified email_details to include UTR number
                email_details = {
                    'event_name': ", ".join(event['event'] for event in data['selectedEvents']),
                    'college': data['college'],
                    'team_members': ", ".join(
                        ", ".join(event.get('members', [])) if event.get('members') 
                        else event.get('participant', '') 
                        for event in data['selectedEvents']
                    ),
                    'total_cost': data['totalCost'],
                    'utr_number': data['utrNumber']  # Add UTR number to email details
                }
                send_registration_email(data['email'], ack_id, email_details)
                
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
    response = supabase.table(table_name).select('*').execute()
    print(f"Found {len(response.data)} total registrations in {table_name}")
    matches = []
    for reg in response.data:
        for event in reg['event_details']:
            stored_event = event.get('event', '')
            norm_stored = normalize_event_name(stored_event)
            print(f"[{table_name}] Comparing '{norm_event}' with '{norm_stored}'")
            # Use exact match instead of substring matching
            if norm_event == norm_stored:
                reg_data = {
                    'ack_id': reg['ack_id'],
                    'college': reg['college'],
                    'email': reg['email'],
                    'phone': reg['phone'],
                    'event_cost': event.get('cost', 0),
                    'type': reg_type,
                    'team_members': '',
                    'utr_number': reg.get('utr_number', ''),
                    'DD': reg.get('DD', '') or reg.get('dd', '')
                }
                if event.get('type') == 'team' and event.get('members'):
                    reg_data['team_members'] = ', '.join(event['members'])
                elif event.get('participant'):
                    reg_data['team_members'] = event['participant']
                matches.append(reg_data)
                print(f"Added registration from {table_name}: {reg_data}")
    return matches

@app.route('/api/get-event-registrations')
@login_required(allowed_pages=['admin'])
def get_event_registrations():
    try:
        event_name = request.args.get('event')
        reg_type = request.args.get('type', 'regular')
        norm_event = normalize_event_name(event_name)
        print(f"Searching for normalized event: '{norm_event}' with type: '{reg_type}'")
        
        # Special handling for CHANAKSH (CODING EVENT)
        if norm_event == normalize_event_name("CHANAKSH (CODING EVENT)"):
            if reg_type == 'regular':
                matches = []
                matches += get_matching_registrations('registrations', norm_event, 'regular')
                matches += get_matching_registrations('spot_registrations', norm_event, 'spot')
            else:  # reg_type == 'spot'
                matches = get_matching_registrations('spot_registrations', norm_event, 'spot')
        else:
            # Normal processing for other events using designated table
            table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
            matches = get_matching_registrations(table_name, norm_event, reg_type)
        
        print(f"Returning {len(matches)} matching registrations")
        return jsonify({
            'success': True,
            'registrations': matches,
            'isSpot': reg_type == 'spot'
        })

    except Exception as e:
        print(f"Error in get_event_registrations: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/get-registrations')
@login_required(allowed_pages=['admin'])
def get_registrations():
    try:
        reg_type = request.args.get('type', 'regular')
        table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
        
        response = supabase.table(table_name).select('*').execute()
        
        if response.data:
            registrations = [{
                'ack_id': reg['ack_id'],
                'college': reg['college'],
                'email': reg['email'],
                'phone': reg['phone'],
                'event_details': reg['event_details'],
                'payment_method': reg.get('payment_method'),
                'utr_number': reg.get('utr_number'),
                'DD': reg.get('DD') or reg.get('dd')
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
        reg_type = request.args.get('type', 'regular')
        event_name = request.args.get('event')
        matches = []

        if event_name:
            norm_event = normalize_event_name(event_name)
            # Special handling for CHANAKSH (CODING EVENT)
            if norm_event == normalize_event_name("CHANAKSH (CODING EVENT)"):
                if reg_type == 'regular':
                    matches += get_matching_registrations('registrations', norm_event, 'regular')
                    matches += get_matching_registrations('spot_registrations', norm_event, 'spot')
                else:
                    matches = get_matching_registrations('spot_registrations', norm_event, 'spot')
        else:
            # If no event filter, retrieve full table
            table_name = 'spot_registrations' if reg_type == 'spot' else 'registrations'
            response = supabase.table(table_name).select('*').execute()
            for reg in response.data:
                events_joined = ", ".join([e.get('event', '') for e in reg.get('event_details', [])])
                matches.append({
                    'ack_id': reg.get('ack_id', ''),
                    'college': reg.get('college', ''),
                    'email': reg.get('email', ''),
                    'phone': reg.get('phone', ''),
                    'team_members': events_joined,
                    'utr_number': reg.get('utr_number', ''),
                    'DD': reg.get('DD', '') or reg.get('dd', '')
                })

        # Prepare CSV output from matches
        output = io.StringIO()
        writer = csv.writer(output)
        header = ['Ack ID', 'College', 'Email', 'Phone', 'Participant/Team', 'UTR Number', 'DD Number']
        writer.writerow(header)
        for reg in matches:
            writer.writerow([
                reg.get('ack_id', ''),
                reg.get('college', ''),
                reg.get('email', ''),
                reg.get('phone', ''),
                reg.get('team_members', ''),
                reg.get('utr_number', ''),
                reg.get('DD', '')
            ])
        csv_output = output.getvalue()
        output.close()

        return Response(
            csv_output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=registrations_{reg_type}_{event_name or 'all'}.csv"}
        )
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
            
            # Handle payment proof URL
            payment_proof_url = registration.get('payment_proof_url')
            if payment_proof_url:
                print(f"Original payment_proof_url: {payment_proof_url}")  # Debug log
                
                try:
                    # Always regenerate the public URL
                    if payment_proof_url.startswith('payment_proofs/'):
                        file_path = payment_proof_url
                    else:
                        # Extract path from full URL if needed
                        file_path = payment_proof_url.split('/payment/')[-1]
                    
                    # Get fresh public URL with proper CORS headers
                    payment_proof_url = supabase.storage.from_('payment').create_signed_url(
                        path=file_path,
                        expires_in=3600  # URL valid for 1 hour
                    )
                    print(f"Generated signed URL: {payment_proof_url}")
                    
                    if isinstance(payment_proof_url, dict) and 'signedURL' in payment_proof_url:
                        payment_proof_url = payment_proof_url['signedURL']
                    
                except Exception as e:
                    print(f"Error generating signed URL: {str(e)}")
                    payment_proof_url = None
            
            return jsonify({
                'success': True,
                'registration': {
                    'email': registration['email'],
                    'college': registration['college'],
                    'phone': registration['phone'],
                    'payment_method': registration.get('payment_method', 'Not specified'),
                    'utr_number': registration.get('utr_number'),
                    'DD': registration.get('DD') or registration.get('dd'),
                    'payment_proof_url': payment_proof_url
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