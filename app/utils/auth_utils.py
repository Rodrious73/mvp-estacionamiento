"""
Utilidades para manejo de sesiones y autenticación
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorador que requiere que el usuario esté logueado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorador que requiere que el usuario tenga uno de los roles especificados"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesión para acceder a esta página', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = session.get('user_role')
            if user_role not in roles:
                flash('No tienes permisos para acceder a esta página', 'error')
                return redirect(url_for('index.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def security_required(f):
    """Decorador que requiere que el usuario sea de seguridad"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'seguridad':
            flash('Acceso restringido al personal de seguridad', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Obtiene la información del usuario actual de la sesión"""
    if 'user_id' not in session:
        return None
    
    return {
        'id': session.get('user_id'),
        'name': session.get('user_name'),
        'type': session.get('user_type'),
        'role': session.get('user_role'),
        'dni': session.get('user_dni'),
        'codigo': session.get('user_codigo'),
        'username': session.get('username')  # Para usuarios de seguridad
    }

def is_logged_in():
    """Verifica si hay un usuario logueado"""
    return 'user_id' in session

def is_student():
    """Verifica si el usuario actual es estudiante"""
    return session.get('user_role') == 'estudiante'

def is_teacher():
    """Verifica si el usuario actual es docente"""
    return session.get('user_role') == 'docente'

def is_visitor():
    """Verifica si el usuario actual es visitante"""
    return session.get('user_role') == 'visita'

def is_security():
    """Verifica si el usuario actual es de seguridad"""
    return session.get('user_type') == 'seguridad'

def admin_required(f):
    """Decorador que requiere que el usuario sea administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('auth.login'))
        
        user_role = session.get('user_role')
        user_codigo = session.get('user_codigo')
        
        # Permitir acceso si es administrador O si es el usuario especial ADMIN001
        if user_role != 'administrador' and user_codigo != 'ADMIN001':
            flash('Acceso restringido solo para administradores', 'error')
            return redirect(url_for('index.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    """Verifica si el usuario actual es administrador"""
    user_role = session.get('user_role')
    user_codigo = session.get('user_codigo')
    return user_role == 'administrador' or user_codigo == 'ADMIN001'
