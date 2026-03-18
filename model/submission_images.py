import base64
import os
import uuid
from werkzeug.utils import secure_filename
from __init__ import app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def submission_image_base64_decode(filename):
    """
    Reads a submission image from the server and returns it as base64.

    Parameters:
    - filename (str): The filename of the image.

    Returns:
    - str: The base64 encoded image if successful; otherwise, None.
    """
    submissions_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'submissions')
    img_path = os.path.join(submissions_dir, filename)
    
    try:
        with open(img_path, 'rb') as img_file:
            base64_encoded = base64.b64encode(img_file.read()).decode('utf-8')
        print(f"Successfully read image: {img_path}")
        return base64_encoded
    except Exception as e:
        print(f'An error occurred while reading the image {filename}: {str(e)}')
        return None

def submission_image_base64_upload(base64_image):
    """
    Uploads a base64 encoded image for a submission.

    Parameters:
    - base64_image (str): The base64 encoded image to be uploaded (can include data URI prefix).

    Returns:
    - str: The filename of the saved image if successful; otherwise, None.
    """
    try:
        # Strip data URI prefix if present (e.g., "data:image/png;base64,")
        if ',' in base64_image:
            base64_image = base64_image.split(',', 1)[1]
        
        image_data = base64.b64decode(base64_image)
        
        # Create submissions directory
        submissions_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'submissions')
        if not os.path.exists(submissions_dir):
            os.makedirs(submissions_dir)
        
        # Generate unique filename with UUID
        unique_id = str(uuid.uuid4())
        filename = f'submission_{unique_id}.png'
        file_path = os.path.join(submissions_dir, filename)
        with open(file_path, 'wb') as img_file:
            img_file.write(image_data)
        print(f"Successfully uploaded image: {filename} to {file_path}")
        return filename
    except Exception as e:
        print(f'An error occurred while uploading the image: {str(e)}')
        return None

def submission_image_file_upload(file):
    """
    Uploads an image file for a submission.

    Parameters:
    - file: The file object from request.files.

    Returns:
    - str: The filename of the saved image if successful; otherwise, None.
    """
    try:
        if file and allowed_file(file.filename):
            # Create submissions directory
            submissions_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'submissions')
            if not os.path.exists(submissions_dir):
                os.makedirs(submissions_dir)
            
            # Generate unique filename with UUID
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_id = str(uuid.uuid4())
            filename = f'submission_{unique_id}.{file_ext}'
            file_path = os.path.join(submissions_dir, filename)
            file.save(file_path)
            print(f"Successfully uploaded image: {filename} to {file_path}")
            return filename
        else:
            print('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
            return None
    except Exception as e:
        print(f'An error occurred while uploading the image: {str(e)}')
        return None

def submission_image_delete(filename):
    """
    Deletes a submission image from the server.

    Parameters:
    - filename (str): The filename to delete.

    Returns:
    - bool: True if deletion was successful; otherwise, False.
    """
    try:
        submissions_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'submissions')
        img_path = os.path.join(submissions_dir, filename)
        if os.path.exists(img_path):
            os.remove(img_path)
            print(f"Successfully deleted image: {img_path}")
        return True 
    except Exception as e:
        print(f'An error occurred while deleting the image {filename}: {str(e)}')
        return False


