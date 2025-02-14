from flask import Blueprint, render_template

about_bp = Blueprint('about', __name__, template_folder="templates", static_folder="static")

@about_bp.route("/about")
def about():    # This function name will be used in url_for as 'about.about'
    return render_template("about.html")
