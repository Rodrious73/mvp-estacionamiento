from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.utils.auth_utils import login_required, role_required, get_current_user

visitante_bp = Blueprint('visitante', __name__, url_prefix='/visitante')

@visitante_bp.route('/dashboard')
@login_required
@role_required('visita')
def dashboard():
    user = get_current_user()
    return f'''
    <h1>Dashboard de Visitante</h1>
    <p>Bienvenido, {user['name']}</p>
    <p>DNI: {user['dni']}</p>
    <a href="{url_for('auth.logout')}">Cerrar Sesión</a>
    '''
