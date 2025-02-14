from flask import Blueprint, render_template, request, redirect, session, url_for
from supabase import create_client  # ensure supabase package is installed

SUPABASE_URL = "https://kccbgaxhhdgzkyazjnnk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtjY2JnYXhoaGRnemt5YXpqbm5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk0NDA2MTAsImV4cCI6MjA1NTAxNjYxMH0.MW4ndTDp-6tvWluoHcb5NzVycNjmU0Vzlxl_mL0VdgA"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

signin_bp = Blueprint("signin", __name__)

@signin_bp.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        # Update table name to "has_auth" if your Supabase table name doesn't have a space.
        result = supabase.table("auth").select("*").eq("user_id", user_id).eq("password", password).execute()
        # Alternatively, if your table name has a space, use:
        # result = supabase.table('"has auth"').select("*").eq("user_id", user_id).eq("password", password).execute()
        if result.data:
            session["authenticated"] = True
            return redirect(url_for("registration.register"))
        else:
            return render_template("signin.html", error="Invalid credentials")
    return render_template("signin.html")
