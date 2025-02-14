from flask import Blueprint, render_template

gallery_bp = Blueprint('gallery', __name__,template_folder="templates",static_folder="static")

@gallery_bp.route("/gallery")
def gallery():
    return render_template("gallery.html")
