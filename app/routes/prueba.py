from flask import Blueprint

prueba_bp = Blueprint('prueba', __name__)

@prueba_bp.route('/prueba')
def prueba():
    return '<h2>Ruta de Prueba</h2>'
