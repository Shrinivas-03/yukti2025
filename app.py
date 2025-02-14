from flask import Flask, render_template, url_for
from routes.about import about_bp
from routes.gallery import gallery_bp
from routes.home_page import home_bp
from routes.registration import registration_bp
from routes.events import events_bp
from routes.signin import signin_bp
from routes.acknowledgement import ack_bp
from database import init_db

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)
app.secret_key = "sdjksafbsahifgahifg56549"

# Initialize database
init_db()

# Register Blueprints
app.register_blueprint(about_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(home_bp)
app.register_blueprint(registration_bp)
app.register_blueprint(events_bp)
app.register_blueprint(signin_bp)
app.register_blueprint(ack_bp)

if __name__ == "__main__":
    app.run(debug=True)
