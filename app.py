import os
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from flask import Flask, redirect, render_template, request, url_for, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    UserMixin,
    current_user,
)
from itertools import groupby
from urllib.parse import urlparse
import re

# Initialize app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

# Session config
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
# Ensure instance directory exists
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(instance_dir, 'storelink.sqlite')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize ORM
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."

# Inject current year for footer or anywhere
@app.context_processor
def inject_year():
    return {"current_year": datetime.now(timezone.utc).year}

# Models
class User(UserMixin, db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash  = db.Column(db.String(128), nullable=False)
    
    # Add relationship to links
    links = db.relationship('Link', backref='user', lazy=True, cascade='all, delete-orphan')

class Link(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    url         = db.Column(db.String(500), nullable=False)
    title       = db.Column(db.String(300), nullable=False)
    preview_url = db.Column(db.String(500), nullable=False)
    comment     = db.Column(db.String(500))
    timestamp   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Add user relationship
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Create tables once at startup
with app.app_context():
    db.create_all()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def is_valid_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_valid_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def normalize_url(url):
    """Add https:// if no scheme is provided"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def fetch_link_data(url):
    """Helper to fetch OG preview and title with better error handling"""
    preview = url_for("static", filename="img/default-preview.png")
    title = url
    
    try:
        # Add user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()  # Raise exception for bad status codes
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Try to get Open Graph image
        if og_image := soup.find("meta", property="og:image"):
            img_url = og_image.get("content")
            if img_url and img_url.startswith('http'):
                preview = img_url
        
        # Try to get Open Graph title, then regular title
        if og_title := soup.find("meta", property="og:title"):
            title = og_title.get("content") or title
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()
            
    except requests.RequestException as e:
        print(f"Error fetching data for {url}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching data for {url}: {e}")
    
    return preview, title

# ------------------- ROUTES -------------------

# Main landing page
@app.route("/")
def landing():
    return render_template("landing.html")

# Registration
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        print("DEBUG: POST request received at signup route")
        email   = request.form.get('email', '').strip().lower()
        pwd     = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

         # Debug prints
        print(f"DEBUG: Email: '{email}', Password length: {len(pwd) if pwd else 0}, Confirm length: {len(confirm) if confirm else 0}")
        
        # Validation
        if not email or not pwd:
            flash('Email and password are required.', 'error')
            return render_template('signup.html')
            
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('signup.html')
            
        if len(pwd) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('signup.html')
            
        if pwd != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html')
        
        # Create new user
        try:
            user = User(
                email=email,
                hash=generate_password_hash(pwd, method='pbkdf2:sha256:260000')
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account.', 'error')
            return render_template('signup.html')
    
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pwd   = request.form.get('password', '')
        
        if not email or not pwd:
            flash('Email and password are required.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.hash, pwd):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
        
        login_user(user)
        flash('Logged in successfully!', 'success')
        
        # Redirect to next page if available
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('dashboard'))
    
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))

# Dashboard (grouped by dates) - now user-specific
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        comment = request.form.get("comment", "").strip()
        
        if not url:
            flash('URL is required.', 'error')
            return redirect(url_for("dashboard"))
        
        # Normalize and validate URL
        url = normalize_url(url)
        if not is_valid_url(url):
            flash('Please enter a valid URL.', 'error')
            return redirect(url_for("dashboard"))
        
        try:
            preview, title = fetch_link_data(url)
            
            new_link = Link(
                url=url,
                title=title,
                preview_url=preview,
                comment=comment,
                user_id=current_user.id
            )
            db.session.add(new_link)
            db.session.commit()
            flash('Link added successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the link.', 'error')
        
        return redirect(url_for("dashboard"))

    # Get only current user's links
    links = Link.query.filter_by(user_id=current_user.id).order_by(Link.timestamp.desc()).all()
    grouped = []
    
    if links:
        links_sorted = sorted(
            links,
            key=lambda x: x.timestamp.strftime("%Y-%m-%d"),
            reverse=True
        )
        for date_str, items in groupby(
            links_sorted,
            key=lambda x: x.timestamp.strftime("%d.%m.%Y")
        ):
            grouped.append((date_str, list(items)))

    return render_template("dashboard.html", grouped_links=grouped)

# Edit link - with user permission check
@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_link(id):
    link = Link.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        comment = request.form.get('comment', '').strip()
        
        if not url:
            flash('URL is required.', 'error')
            return render_template('edit.html', link=link)
        
        # Normalize and validate URL
        url = normalize_url(url)
        if not is_valid_url(url):
            flash('Please enter a valid URL.', 'error')
            return render_template('edit.html', link=link)
        
        try:
            link.url = url
            link.comment = comment
            
            # Re-fetch metadata if URL changed
            if url != link.url:
                link.preview_url, link.title = fetch_link_data(url)
            
            db.session.commit()
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the link.', 'error')
    
    return render_template('edit.html', link=link)

# Delete link - with user permission check
@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_link(id):
    link = Link.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(link)
        db.session.commit()
        flash('Link deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the link.', 'error')
    
    return redirect(url_for("dashboard"))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ------------------- RUN -------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)