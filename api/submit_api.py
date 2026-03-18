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
                
                # Handle image upload - store the filename
                image_filename = None
                if base64_image:
                    image_filename = submission_image_base64_upload(base64_image)
                    print(f"Uploaded base64 image: {image_filename}")
                elif 'image' in request.files:
                    image_file = request.files['image']
                    image_filename = submission_image_file_upload(image_file)
                    print(f"Uploaded file image: {image_filename}")
                
                if image_filename:
                    submission.image = image_filename
                    submission.update(image=image_filename)
                    print(f"Saved image filename to submission: {image_filename}")
                
                return submission.read(), 201
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
                # Debug logging
                print(f"DEBUG: Submission {id} retrieved. Image field: {submission.image}")
                return result
            else:
                # Get current user's submissions
                user = g.current_user
                if not user:
                    return {'message': 'User not found'}, 404
                
                submissions = Submissions.get_by_user(user.id)
                json_ready = [s.read() for s in submissions]
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
                image_filename = None
                if base64_image:
                    # Delete old image if exists
                    if submission.image:
                        submission_image_delete(submission.image)
                    image_filename = submission_image_base64_upload(base64_image)
                elif 'image' in request.files:
                    image_file = request.files['image']
                    # Delete old image if exists
                    if submission.image:
                        submission_image_delete(submission.image)
                    image_filename = submission_image_file_upload(image_file)
                
                if image_filename:
                    submission.update(image=image_filename)
                    print(f"Updated image for submission {id}: {image_filename}")
                
                return submission.read()
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
                # Delete the image file if it exists
                if submission.image:
                    submission_image_delete(submission.image)
                    print(f"Deleted image for submission {id}: {submission.image}")
                
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
                print(f"No image for submission {id} (image field is NULL)")
                return {'message': f'No image for submission {id}'}, 404
            
            print(f"Retrieving image for submission {id}: {submission.image}")
            # submission.image now contains the filename
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
                
                # Handle image upload - store the filename
                image_filename = None
                if base64_image:
                    image_filename = submission_image_base64_upload(base64_image)
                    print(f"Uploaded base64 image: {image_filename}")
                elif 'image' in request.files:
                    image_file = request.files['image']
                    image_filename = submission_image_file_upload(image_file)
                    print(f"Uploaded file image: {image_filename}")
                
                if image_filename:
                    submission.image = image_filename
                    submission.update(image=image_filename)
                    print(f"Saved image filename to submission: {image_filename}")
                
                return submission.read(), 201
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