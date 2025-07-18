from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/escuelas')
def escuelas():
    return {'message': 'API de escuelas'}
