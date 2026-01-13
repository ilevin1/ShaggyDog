from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv
from generate_transformation import analyze_dog_breed, extract_dog_breed, generate_progressive_images

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-secret-key-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shaggydog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_IMAGES_FOLDER'] = 'static/generated_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_IMAGES_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to images
    images = db.relationship('GeneratedImage', backref='user', lazy=True, cascade='all, delete-orphan')

class GeneratedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    original_image_path = db.Column(db.String(255), nullable=True)
    dog_breed = db.Column(db.String(100), nullable=False)
    image1_path = db.Column(db.String(255), nullable=False)
    image2_path = db.Column(db.String(255), nullable=False)
    image3_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Only get images for the current user, ordered by most recent first
    images = GeneratedImage.query.filter_by(user_id=current_user.id).order_by(GeneratedImage.created_at.desc()).all()
    return render_template('dashboard.html', images=images)

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        # Validate file type
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            flash('Invalid file type. Please upload an image file (PNG, JPG, JPEG, GIF, or WEBP).', 'error')
            return redirect(request.url)
        
        try:
            # Save uploaded file
            filename = secure_filename(file.filename)
            user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            os.makedirs(user_upload_dir, exist_ok=True)
            
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(user_upload_dir, filename)
            file.save(filepath)
            
            # Analyze breed and generate images
            breed_description = analyze_dog_breed(filepath)
            dog_breed = extract_dog_breed(breed_description)
            
            # Generate images and save to user-specific folder
            user_images_dir = os.path.join(app.config['GENERATED_IMAGES_FOLDER'], str(current_user.id))
            os.makedirs(user_images_dir, exist_ok=True)
            
            # Generate images (this may take a while)
            images = generate_progressive_images(filepath, dog_breed, output_dir=user_images_dir)
            
            # Save to database
            generated_image = GeneratedImage(
                user_id=current_user.id,
                original_filename=file.filename,
                original_image_path=filepath,
                dog_breed=dog_breed,
                image1_path=images[0][0],
                image2_path=images[1][0],
                image3_path=images[2][0]
            )
            db.session.add(generated_image)
            db.session.commit()
            
            flash(f'Images generated successfully! Detected breed: {dog_breed}', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Error generating images: {error_msg}")
            print(f"Traceback: {error_trace}")
            flash(f'Error generating images: {error_msg}', 'error')
            return redirect(request.url)
    
    return render_template('generate.html')

@app.route('/images/<path:filename>')
@login_required
def serve_image(filename):
    """Serve generated images with user authentication check"""
    # Extract user_id from path
    parts = filename.split('/')
    if len(parts) >= 2 and parts[0].isdigit():
        user_id = int(parts[0])
        # Only allow users to view their own images
        if user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        directory = os.path.join(app.config['GENERATED_IMAGES_FOLDER'], parts[0])
        filepath = '/'.join(parts[1:])
        return send_from_directory(directory, filepath)
    
    flash('Invalid image path', 'error')
    return redirect(url_for('dashboard'))

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Serve uploaded original images with user authentication check"""
    # Extract user_id from path
    parts = filename.split('/')
    if len(parts) >= 2 and parts[0].isdigit():
        user_id = int(parts[0])
        # Only allow users to view their own images
        if user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        directory = os.path.join(app.config['UPLOAD_FOLDER'], parts[0])
        filepath = '/'.join(parts[1:])
        return send_from_directory(directory, filepath)
    
    flash('Invalid image path', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

