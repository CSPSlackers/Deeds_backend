import base64
import zlib
from werkzeug.utils import secure_filename
from __init__ import app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def submission_image_base64_decode(compressed_image_data):
    """
    Converts compressed binary image data back to base64 for API responses.

    Parameters:
    - compressed_image_data (bytes): The compressed binary image data from database.

    Returns:
    - str: The base64 encoded image if successful; otherwise, None.
    """
    try:
        if not compressed_image_data:
            return None
        
        # Decompress the data
        decompressed = zlib.decompress(compressed_image_data)
        
        # Encode to base64 for API response
        base64_encoded = base64.b64encode(decompressed).decode('utf-8')
        print(f"Successfully decoded image to base64")
        return base64_encoded
    except Exception as e:
        print(f'Error decoding image: {str(e)}')
        return None

def submission_image_base64_upload(base64_image):
    """
    Converts base64 image to compressed binary for database storage.

    Parameters:
    - base64_image (str): The base64 encoded image (can include data URI prefix).

    Returns:
    - bytes: The compressed binary image data if successful; otherwise, None.
    """
    try:
        # Strip data URI prefix if present (e.g., "data:image/png;base64,")
        if ',' in base64_image:
            base64_image = base64_image.split(',', 1)[1]
        
        # Decode base64 to binary
        image_data = base64.b64decode(base64_image)
        
        # Compress with zlib (lossless compression)
        compressed_data = zlib.compress(image_data, level=9)  # level 9 = maximum compression
        
        print(f"Successfully processed image. Original: {len(image_data)} bytes, Compressed: {len(compressed_data)} bytes, Savings: {(1 - len(compressed_data)/len(image_data))*100:.1f}%")
        return compressed_data
    except Exception as e:
        print(f'An error occurred while processing the image: {str(e)}')
        return None

def submission_image_file_upload(file):
    """
    Converts uploaded image file to compressed binary for database storage.

    Parameters:
    - file: The file object from request.files.

    Returns:
    - bytes: The compressed binary image data if successful; otherwise, None.
    """
    try:
        if file and allowed_file(file.filename):
            # Read file data
            image_data = file.read()
            
            # Compress with zlib
            compressed_data = zlib.compress(image_data, level=9)
            
            print(f"Successfully processed image file. Original: {len(image_data)} bytes, Compressed: {len(compressed_data)} bytes, Savings: {(1 - len(compressed_data)/len(image_data))*100:.1f}%")
            return compressed_data
        else:
            print('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
            return None
    except Exception as e:
        print(f'An error occurred while processing the image: {str(e)}')
        return None

def submission_image_delete(image_data):
    """
    No-op function for backward compatibility. Images stored in DB don't need file deletion.

    Parameters:
    - image_data: Ignored (kept for backward compatibility).

    Returns:
    - bool: Always True.
    """
    # No file operations needed - data is in database
    print(f"Image data will be deleted when submission is deleted from database")
    return True



