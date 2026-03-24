from flask import Blueprint, request, g
from flask_restful import Api, Resource
from api.authorize import token_required
from model.carousel import Carousel
from model.submissions import Submissions
from model.submission_images import submission_image_base64_decode
from __init__ import db

# Create Blueprint
carousel_api = Blueprint('carousel_api', __name__, url_prefix='/carousel')
api = Api(carousel_api)

class CarouselAPI:
    class _List(Resource):
        def get(self):
            """Get all carousel submissions (public endpoint)"""
            carousel_items = Carousel.get_all_ordered()
            result = []
            
            for item in carousel_items:
                data = item.read()
                # Decode image to base64 if it exists
                if data and data['submission']:
                    submission = Submissions.get_by_id(item.submission_id)
                    if submission and submission.image:
                        data['submission']['image'] = submission_image_base64_decode(submission.image)
                if data:
                    result.append(data)
            
            return result, 200

    class _Add(Resource):
        @token_required()
        def post(self, submission_id):
            """Add a submission to carousel (admin only)"""
            current_user = g.current_user
            
            # Check if user is admin
            if not current_user.is_admin():
                return {'message': 'Permission denied. Only admins can manage carousel.'}, 403
            
            # Check if submission exists
            submission = Submissions.get_by_id(submission_id)
            if not submission:
                return {'message': f'Submission {submission_id} not found'}, 404
            
            # Check if already in carousel
            existing = Carousel.get_by_submission_id(submission_id)
            if existing:
                return {'message': f'Submission {submission_id} already in carousel'}, 409
            
            try:
                # Get next position
                count = Carousel.get_count()
                carousel_item = Carousel(submission_id=submission_id, position=count)
                carousel_item.create()
                
                # Prepare response with decoded image
                result = carousel_item.read()
                if submission.image:
                    result['submission']['image'] = submission_image_base64_decode(submission.image)
                
                return result, 201
            except Exception as e:
                db.session.rollback()
                print(f"Error adding to carousel: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500

    class _Remove(Resource):
        @token_required()
        def delete(self, carousel_id):
            """Remove a submission from carousel (admin only)"""
            current_user = g.current_user
            
            # Check if user is admin
            if not current_user.is_admin():
                return {'message': 'Permission denied. Only admins can manage carousel.'}, 403
            
            carousel_item = Carousel.get_by_id(carousel_id)
            if not carousel_item:
                return {'message': f'Carousel item {carousel_id} not found'}, 404
            
            try:
                carousel_item.delete()
                
                # Reorder remaining items
                remaining = Carousel.get_all_ordered()
                for idx, item in enumerate(remaining):
                    item.update(position=idx)
                
                return {'message': 'Removed from carousel'}, 200
            except Exception as e:
                db.session.rollback()
                print(f"Error removing from carousel: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500

    class _Reorder(Resource):
        @token_required()
        def put(self):
            """Reorder carousel items (admin only)"""
            current_user = g.current_user
            
            # Check if user is admin
            if not current_user.is_admin():
                return {'message': 'Permission denied. Only admins can manage carousel.'}, 403
            
            try:
                body = request.get_json()
                order = body.get('order', [])  # List of carousel_ids in desired order
                
                if not order:
                    return {'message': 'Order list required'}, 400
                
                # Update positions
                for position, carousel_id in enumerate(order):
                    item = Carousel.get_by_id(carousel_id)
                    if item:
                        item.update(position=position)
                
                # Return updated carousel
                carousel_items = Carousel.get_all_ordered()
                result = []
                for item in carousel_items:
                    data = item.read()
                    if data and data['submission']:
                        submission = Submissions.get_by_id(item.submission_id)
                        if submission and submission.image:
                            data['submission']['image'] = submission_image_base64_decode(submission.image)
                    if data:
                        result.append(data)
                
                return result, 200
            except Exception as e:
                db.session.rollback()
                print(f"Error reordering carousel: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500

    class _RemoveBySubmissionId(Resource):
        @token_required()
        def delete(self, submission_id):
            """Remove a submission from carousel by submission ID (admin only)"""
            current_user = g.current_user
            
            # Check if user is admin
            if not current_user.is_admin():
                return {'message': 'Permission denied. Only admins can manage carousel.'}, 403
            
            carousel_item = Carousel.get_by_submission_id(submission_id)
            if not carousel_item:
                return {'message': f'Submission {submission_id} not in carousel'}, 404
            
            try:
                carousel_item.delete()
                
                # Reorder remaining items
                remaining = Carousel.get_all_ordered()
                for idx, item in enumerate(remaining):
                    item.update(position=idx)
                
                return {'message': 'Removed from carousel'}, 200
            except Exception as e:
                db.session.rollback()
                print(f"Error removing from carousel: {str(e)}")
                return {'message': f'Error: {str(e)}'}, 500

    # Register endpoints
    api.add_resource(_List, '/')
    api.add_resource(_Add, '/add/<int:submission_id>')
    api.add_resource(_Remove, '/remove/<int:carousel_id>')
    api.add_resource(_RemoveBySubmissionId, '/remove-submission/<int:submission_id>')
    api.add_resource(_Reorder, '/reorder')
