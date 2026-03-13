from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from __init__ import db

# Create Blueprint
submit_api = Blueprint('submit_api', __name__, url_prefix='/api/submit')
api = Api(submit_api)


class SubmitApi(Resource):
    def get(self):
        return jsonify({"message": "Hello"})
    

api.add_resource(SubmitApi, '/test')