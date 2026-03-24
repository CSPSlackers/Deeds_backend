from flask import Blueprint, request, g
from flask_restful import Api, Resource
from api.authorize import token_required
from model.submissions import Submissions, SUBMISSION_CATEGORIES
from model.submission_images import submission_image_base64_upload, submission_image_file_upload, submission_image_delete, submission_image_base64_decode
from model.user import User
from __init__ import db

# Create Blueprint
submit_api = Blueprint('submit_api', __name__, url_prefix='/submit')
api = Api(submit_api)

class SubmissionAPI:
    class _Create(Resource):
        @token_required()
        def post(self):
            """Create a new submission with optional image"""
            user = g.current_user
            if not user:
                return {'message': 'User not found'}, 404
            
            # Handle both JSON and multipart/form-data
            if request.content_type and 'application/json' in request.content_type:
                body = request.get_json()
                content = body.get('content')
                category = body.get('category', 'Misc')
                base64_image = body.get('image')  # Base64 encoded image
            else:
                content = request.form.get('content')
                category = request.form.get('category', 'Misc')
                base64_image = None
            
            if not content:
                return {'message': 'Content is required'}, 400
            
            submission = Submissions(content=content, user=user, category=category)
            
            try:
                submission.create()
                print(f"Created submission with ID: {submission.id}")
                
                # Handle image upload - store compressed binary data
                compressed_image_data = None
                if base64_image:
                    compressed_image_data = submission_image_base64_upload(base64_image)
                    print(f"Processed base64 image")
                elif 'image' in request.files:
                    image_file = request.files['image']
                    compressed_image_data = submission_image_file_upload(image_file)
                    print(f"Processed file image")
                
                if compressed_image_data:
                    submission.image = compressed_image_data
                    submission.update(image=compressed_image_data)
                    print(f"Saved compressed image data to submission {submission.id}")
                
                # Prepare response with base64 image if present
                result = submission.read()
                if submission.image:
                    result['image'] = submission_image_base64_decode(submission.image)
                    
                return result, 201
            except Exception as e:
                db.session.rollback()
                print(f"Error creating submission: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500
    
    class _Read(Resource):
        @token_required()
        def get(self, id=None):
            """Get submission(s)"""
            if id is not None:
                submission = Submissions.get_by_id(id)
                if not submission:
                    return {'message': f'Submission {id} not found'}, 404
                result = submission.read()
                # If there's an image, decode it to base64 for API response
                if submission.image:
                    result['image'] = submission_image_base64_decode(submission.image)
                return result
            else:
                # Check if requesting all submissions (for carousel)
                get_all = request.args.get('all', 'false').lower() == 'true'
                
                if get_all:
                    # Get all submissions
                    submissions = Submissions.query.all()
                else:
                    # Get current user's submissions
                    user = g.current_user
                    if not user:
                        return {'message': 'User not found'}, 404
                    submissions = Submissions.get_by_user(user.id)
                
                json_ready = []
                for s in submissions:
                    data = s.read()
                    # Decode image to base64 if it exists
                    if s.image:
                        data['image'] = submission_image_base64_decode(s.image)
                    json_ready.append(data)
                return json_ready
    
    class _Update(Resource):
        @token_required()
        def put(self, id):
            """Update a submission with optional image"""
            submission = Submissions.get_by_id(id)
            if not submission:
                return {'message': f'Submission {id} not found'}, 404
            
            # Handle both JSON and multipart/form-data
            if request.content_type and 'application/json' in request.content_type:
                body = request.get_json()
                content = body.get('content')
                category = body.get('category')
                base64_image = body.get('image')
            else:
                content = request.form.get('content')
                category = request.form.get('category')
                base64_image = None
            
            try:
                if content:
                    submission.update(content=content)
                if category:
                    submission.update(category=Submissions._validate_category(category))
                
                # Handle image upload/update
                compressed_image_data = None
                if base64_image:
                    # Old image will be overwritten automatically
                    compressed_image_data = submission_image_base64_upload(base64_image)
                elif 'image' in request.files:
                    image_file = request.files['image']
                    # Old image will be overwritten automatically
                    compressed_image_data = submission_image_file_upload(image_file)
                
                if compressed_image_data:
                    submission.update(image=compressed_image_data)
                    print(f"Updated image for submission {id}")
                
                # Prepare response with base64 image if present
                result = submission.read()
                if submission.image:
                    result['image'] = submission_image_base64_decode(submission.image)
                    
                return result
            except Exception as e:
                db.session.rollback()
                print(f"Error updating submission: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500
    
    class _Delete(Resource):
        @token_required()
        def delete(self, id):
            """Delete a submission and its associated image"""
            submission = Submissions.get_by_id(id)
            if not submission:
                return {'message': f'Submission {id} not found'}, 404
            
            json_data = submission.read()
            try:
                # Image data is stored in DB, will be deleted with submission
                submission.delete()
                return {'message': 'Submission deleted', 'submission': json_data}, 200
            except Exception as e:
                db.session.rollback()
                print(f"Error deleting submission: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500
    
    class _Categories(Resource):
        def get(self):
            """Get all available submission categories"""
            return {'categories': SUBMISSION_CATEGORIES}, 200
    
    class _Image(Resource):
        def get(self, id):
            """Get submission image as base64 (public endpoint)"""
            submission = Submissions.get_by_id(id)
            if not submission:
                return {'message': f'Submission {id} not found'}, 404
            
            if not submission.image:
                return {'message': f'No image for submission {id}'}, 404
            
            # Decompress and return as base64
            base64_image = submission_image_base64_decode(submission.image)
            if not base64_image:
                return {'message': 'Error retrieving image'}, 500
            
            return {'image': base64_image}, 200

    class _CreateForUser(Resource):
        @token_required()
        def post(self, user_id):
            """Create a submission for a specific user (admin/teacher only)"""
            current_user = g.current_user
            
            # Check if user is admin
            if not current_user.is_admin():
                return {'message': 'Permission denied. Only admins can create submissions for other users.'}, 403
            
            # Get the target user
            target_user = User.query.filter_by(id=user_id).first()
            if not target_user:
                return {'message': f'User {user_id} not found'}, 404
            
            # Handle both JSON and multipart/form-data
            if request.content_type and 'application/json' in request.content_type:
                body = request.get_json()
                content = body.get('content')
                category = body.get('category', 'Misc')
                base64_image = body.get('image')
            else:
                content = request.form.get('content')
                category = request.form.get('category', 'Misc')
                base64_image = None
            
            if not content:
                return {'message': 'Content is required'}, 400
            
            submission = Submissions(content=content, user=target_user, category=category)
            
            try:
                submission.create()
                print(f"Created submission with ID: {submission.id} for user {user_id}")
                
                # Handle image upload - store compressed binary data
                compressed_image_data = None
                if base64_image:
                    compressed_image_data = submission_image_base64_upload(base64_image)
                    print(f"Processed base64 image")
                elif 'image' in request.files:
                    image_file = request.files['image']
                    compressed_image_data = submission_image_file_upload(image_file)
                    print(f"Processed file image")
                
                if compressed_image_data:
                    submission.image = compressed_image_data
                    submission.update(image=compressed_image_data)
                    print(f"Saved compressed image data to submission {submission.id}")
                
                # Prepare response with base64 image if present
                result = submission.read()
                if submission.image:
                    result['image'] = submission_image_base64_decode(submission.image)
                    
                return result, 201
            except Exception as e:
                db.session.rollback()
                print(f"Error creating submission: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500
    
    # Register endpoints
    api.add_resource(_Create, '/create')
    api.add_resource(_CreateForUser, '/create/<int:user_id>')
    api.add_resource(_Read, '/', '/submission/<int:id>')
    api.add_resource(_Update, '/update/<int:id>')
    api.add_resource(_Delete, '/delete/<int:id>')
    api.add_resource(_Categories, '/categories')
    api.add_resource(_Image, '/image/<int:id>')