from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models.usuario import Usuario
from app.models.usuario_seguridad import UsuarioSeguridad
from sqlalchemy.exc import IntegrityError

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            identificador = request.form.get('identificador', '').strip()
            contraseña = request.form.get('contraseña', '')
            tipo_login = request.form.get('tipo_login', 'usuario')  # 'usuario' o 'seguridad'
            
            # Validaciones básicas
            if not all([identificador, contraseña]):
                flash('Todos los campos son obligatorios', 'error')
                return render_template('login.html')
            
            if tipo_login == 'seguridad':
                # Login para personal de seguridad
                usuario_seguridad = UsuarioSeguridad.query.filter_by(usuario=identificador).first()
                
                if usuario_seguridad and usuario_seguridad.check_password(contraseña):
                    # Autenticación exitosa
                    session['user_id'] = usuario_seguridad.id
                    session['user_type'] = 'seguridad'
                    session['user_name'] = usuario_seguridad.nombre
                    session['username'] = usuario_seguridad.usuario
                    
                    flash(f'¡Bienvenido, {usuario_seguridad.nombre}!', 'success')
                    return redirect(url_for('seguridad.dashboard'))  # Crear esta ruta después
                else:
                    flash('Usuario o contraseña incorrectos', 'error')
                    
            else:
                # Login para usuarios (estudiantes, docentes, visitantes)
                usuario = None
                
                # Determinar si es código universitario o DNI
                if identificador.isdigit() and len(identificador) == 8:
                    # Es un DNI (8 dígitos)
                    usuario = Usuario.query.filter_by(dni=identificador).first()
                else:
                    # Es código universitario (alfanumérico)
                    usuario = Usuario.query.filter_by(codigo_universitario=identificador).first()
                
                if usuario and usuario.check_password(contraseña):
                    # Autenticación exitosa
                    session['user_id'] = usuario.id
                    session['user_type'] = 'usuario'
                    session['user_name'] = usuario.nombre
                    session['user_role'] = usuario.rol
                    session['user_dni'] = usuario.dni
                    session['user_codigo'] = usuario.codigo_universitario
                    
                    flash(f'¡Bienvenido, {usuario.nombre}!', 'success')
                    
                    # Redirigir según el rol
                    if usuario.rol == 'estudiante':
                        return redirect(url_for('estudiante.dashboard'))
                    elif usuario.rol == 'docente':
                        # Verificar si es el administrador especial
                        if usuario.codigo_universitario == 'ADMIN001':
                            return redirect(url_for('admin.dashboard'))
                        else:
                            return redirect(url_for('docente.dashboard'))
                    elif usuario.rol == 'visita':
                        return redirect(url_for('visitante.dashboard'))
                    elif usuario.rol == 'administrador':
                        return redirect(url_for('admin.dashboard'))
                    else:
                        return redirect(url_for('index.index'))
                        
                else:
                    flash('Identificador o contraseña incorrectos', 'error')
            
        except Exception as e:
            flash('Error interno del servidor. Intenta nuevamente', 'error')
            print(f"Error en login: {e}")  # Para debugging
    
    # GET request - mostrar formulario
    return render_template('login.html')

@auth.route('/logout')
def logout():
    # Limpiar la sesión
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('index.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre', '').strip()
            dni = request.form.get('dni', '').strip()
            email = request.form.get('email', '').strip()
            telefono = request.form.get('telefono', '').strip()
            rol = request.form.get('rol', '').strip()
            codigo_universitario = request.form.get('codigo_universitario', '').strip()
            contraseña = request.form.get('contraseña', '')
            confirmar_contraseña = request.form.get('confirmar_contraseña', '')
            
            # Validaciones básicas
            if not all([nombre, dni, email, rol, contraseña]):
                flash('Todos los campos obligatorios deben ser completados', 'error')
                return render_template('register.html')
            
            # Validar que las contraseñas coincidan
            if contraseña != confirmar_contraseña:
                flash('Las contraseñas no coinciden', 'error')
                return render_template('register.html')
            
            # Validar longitud de contraseña
            if len(contraseña) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'error')
                return render_template('register.html')
            
            # Validar DNI
            if len(dni) != 8 or not dni.isdigit():
                flash('El DNI debe tener exactamente 8 dígitos', 'error')
                return render_template('register.html')
            
            # Validar teléfono si se proporciona
            if telefono and (len(telefono) != 9 or not telefono.isdigit()):
                flash('El teléfono debe tener exactamente 9 dígitos', 'error')
                return render_template('register.html')
            
            # Validar código universitario para estudiantes y docentes
            if rol in ['estudiante', 'docente'] and not codigo_universitario:
                flash('El código universitario es obligatorio para estudiantes y docentes', 'error')
                return render_template('register.html')
            
            # Si es visitante, no debe tener código universitario
            if rol == 'visita':
                codigo_universitario = None
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario(
                nombre=nombre,
                dni=dni,
                rol=rol,
                contraseña=contraseña,
                codigo_universitario=codigo_universitario if codigo_universitario else None,
                email=email,
                telefono=telefono if telefono else None
            )
            
            # Guardar en la base de datos
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            flash('¡Registro exitoso! Ya puedes iniciar sesión', 'success')
            return redirect(url_for('auth.login'))
            
        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e.orig).lower()
            
            if 'dni' in error_msg:
                flash('Este DNI ya está registrado en el sistema', 'error')
            elif 'email' in error_msg:
                flash('Este email ya está registrado en el sistema', 'error')
            else:
                flash('Error: Los datos proporcionados ya existen en el sistema', 'error')
                
            return render_template('register.html')
            
        except Exception as e:
            db.session.rollback()
            flash('Error interno del servidor. Intenta nuevamente', 'error')
            print(f"Error en registro: {e}")  # Para debugging
            return render_template('register.html')
    
    # GET request - mostrar formulario
    return render_template('register.html')
