"""Utility functions for the app"""
import os
from werkzeug.utils import secure_filename
from flask import current_app
import secrets
import urllib.request
from urllib.parse import urlparse

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_picture(form_picture):
    """Save uploaded picture and return filename"""
    if form_picture:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_picture.filename)
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)

        # Create uploads folder if it doesn't exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        form_picture.save(picture_path)
        return picture_fn
    return None

def delete_picture(filename):
    """Delete a picture file"""
    if filename:
        try:
            picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(picture_path):
                os.remove(picture_path)
        except OSError:
            pass

def save_picture_from_url(image_url):
    """Download and save a picture from URL"""
    if not image_url:
        return None

    try:
        # Create uploads folder if it doesn't exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Get file extension from URL
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        if '.' in path:
            ext = '.' + path.rsplit('.', 1)[1].lower()
        else:
            ext = '.jpg'  # Default to jpg if no extension

        # Generate random filename
        random_hex = secrets.token_hex(8)
        picture_fn = random_hex + ext
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)

        # Download image with timeout
        req = urllib.request.Request(
            image_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(picture_path, 'wb') as out_file:
                out_file.write(response.read())

        return picture_fn
    except Exception as e:
        # If download fails, return None (graceful degradation)
        return None
