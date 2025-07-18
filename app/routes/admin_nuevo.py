from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.usuario import Usuario
from app.models.usuario_seguridad import UsuarioSeguridad
from app.models.vehiculo import Vehiculo
from app.models.solicitud_pase import SolicitudPase
from app.models.pase_vehicular import PaseVehicular
from app.models.ciclo_academico import CicloAcademico
from app.utils.auth_utils import login_required, admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, desc, asc
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Dashboard principal del administrador"""
    # Estadísticas generales
    total_usuarios = Usuario.query.count()
    estudiantes = Usuario.query.filter_by(rol='estudiante').count()
    docentes = Usuario.query.filter_by(rol='docente').count()
    visitantes = Usuario.query.filter_by(rol='visita').count()
    total_vehiculos = Vehiculo.query.count()
    
    # Solicitudes pendientes
    solicitudes_pendientes = SolicitudPase.query.filter_by(estado='pendiente').count()
    
    # Estadísticas de pases
    pases_activos = PaseVehicular.query.filter(
        PaseVehicular.estado == 'vigente',
        PaseVehicular.fecha_fin >= datetime.now().date()
    ).count()
    
    # Ciclo académico actual
    ciclo_actual = CicloAcademico.query.filter_by(estado='activo').first()
    
    # Solicitudes recientes (últimos 7 días)
    fecha_limite = datetime.utcnow() - timedelta(days=7)
    solicitudes_recientes = SolicitudPase.query.filter(
        SolicitudPase.fecha_solicitud >= fecha_limite
    ).count()
    
    # Solicitudes por estado
    solicitudes_por_estado = db.session.query(
        SolicitudPase.estado,
        func.count(SolicitudPase.id).label('cantidad')
    ).group_by(SolicitudPase.estado).all()
    
    # Últimas solicitudes
    ultimas_solicitudes = SolicitudPase.query.order_by(
        desc(SolicitudPase.fecha_solicitud)
    ).limit(5).all()
    
    estadisticas = {
        'total_usuarios': total_usuarios,
        'estudiantes': estudiantes,
        'docentes': docentes,
        'visitantes': visitantes,
        'total_vehiculos': total_vehiculos,
        'solicitudes_pendientes': solicitudes_pendientes,
        'pases_activos': pases_activos,
        'solicitudes_recientes': solicitudes_recientes,
        'ciclo_actual': ciclo_actual,
        'solicitudes_por_estado': solicitudes_por_estado,
        'ultimas_solicitudes': ultimas_solicitudes
    }
    
    return render_template('admin/dashboard.html', **estadisticas)

@admin_bp.route('/solicitudes')
@login_required
@admin_required
def solicitudes():
    """Ver todas las solicitudes de pases"""
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', 'todas')
    tipo = request.args.get('tipo', 'todos')
    
    query = SolicitudPase.query
    
    # Filtrar por estado
    if estado != 'todas':
        query = query.filter(SolicitudPase.estado == estado)
    
    # Filtrar por tipo
    if tipo != 'todos':
        query = query.filter(SolicitudPase.tipo_pase == tipo)
    
    # Ordenar por fecha más reciente
    query = query.order_by(desc(SolicitudPase.fecha_solicitud))
    
    # Paginación
    solicitudes = query.paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/solicitudes.html', 
                         solicitudes=solicitudes, 
                         estado_actual=estado, 
                         tipo_actual=tipo)

@admin_bp.route('/solicitud/<int:id>')
@login_required
@admin_required
def ver_solicitud(id):
    """Ver detalles de una solicitud específica"""
    solicitud = SolicitudPase.query.get_or_404(id)
    return render_template('admin/ver_solicitud.html', solicitud=solicitud)

@admin_bp.route('/solicitud/<int:id>/aprobar', methods=['POST'])
@login_required
@admin_required
def aprobar_solicitud(id):
    """Aprobar una solicitud de pase"""
    solicitud = SolicitudPase.query.get_or_404(id)
    
    if solicitud.estado != 'pendiente':
        flash('Esta solicitud ya ha sido procesada', 'error')
        return redirect(url_for('admin.ver_solicitud', id=id))
    
    comentarios = request.form.get('comentarios', '')
    
    try:
        # Aprobar la solicitud
        solicitud.aprobar(comentarios)
        
        # Crear el pase vehicular
        if solicitud.tipo_pase == 'ciclo':
            # Para pases de ciclo, usar las fechas del ciclo académico
            ciclo = CicloAcademico.query.filter_by(estado='activo').first()
            if not ciclo:
                flash('No hay ciclo académico activo', 'error')
                return redirect(url_for('admin.ver_solicitud', id=id))
            
            fecha_inicio = ciclo.fecha_inicio
            fecha_fin = ciclo.fecha_fin
            ciclo_id = ciclo.id
        else:
            # Para pases temporales, usar fechas específicas (30 días)
            fecha_inicio = datetime.now().date()
            fecha_fin = fecha_inicio + timedelta(days=30)
            ciclo_id = None
        
        pase = PaseVehicular(
            usuario_id=solicitud.usuario_id,
            vehiculo_id=solicitud.vehiculo_id,
            tipo_pase=solicitud.tipo_pase,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            ciclo_id=ciclo_id
        )
        
        db.session.add(pase)
        db.session.commit()
        
        flash('Solicitud aprobada exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al aprobar la solicitud: {str(e)}', 'error')
    
    return redirect(url_for('admin.ver_solicitud', id=id))

@admin_bp.route('/solicitud/<int:id>/rechazar', methods=['POST'])
@login_required
@admin_required
def rechazar_solicitud(id):
    """Rechazar una solicitud de pase"""
    solicitud = SolicitudPase.query.get_or_404(id)
    
    if solicitud.estado != 'pendiente':
        flash('Esta solicitud ya ha sido procesada', 'error')
        return redirect(url_for('admin.ver_solicitud', id=id))
    
    comentarios = request.form.get('comentarios', '')
    
    if not comentarios:
        flash('Debe proporcionar un motivo para rechazar la solicitud', 'error')
        return redirect(url_for('admin.ver_solicitud', id=id))
    
    try:
        solicitud.rechazar(comentarios)
        db.session.commit()
        flash('Solicitud rechazada', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al rechazar la solicitud: {str(e)}', 'error')
    
    return redirect(url_for('admin.ver_solicitud', id=id))

@admin_bp.route('/ciclos')
@login_required
@admin_required
def ciclos():
    """Gestionar ciclos académicos"""
    ciclos = CicloAcademico.query.order_by(desc(CicloAcademico.fecha_inicio)).all()
    return render_template('admin/ciclos.html', ciclos=ciclos)

@admin_bp.route('/ciclo/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_ciclo():
    """Crear un nuevo ciclo académico"""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        # Validaciones
        if not all([nombre, fecha_inicio, fecha_fin]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('admin/nuevo_ciclo.html')
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            if fecha_inicio >= fecha_fin:
                flash('La fecha de inicio debe ser anterior a la fecha de fin', 'error')
                return render_template('admin/nuevo_ciclo.html')
            
            # Crear ciclo
            ciclo = CicloAcademico(
                nombre=nombre,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            db.session.add(ciclo)
            db.session.commit()
            
            flash(f'Ciclo académico "{nombre}" creado exitosamente', 'success')
            return redirect(url_for('admin.ciclos'))
            
        except ValueError:
            flash('Formato de fecha inválido', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el ciclo: {str(e)}', 'error')
    
    return render_template('admin/nuevo_ciclo.html')

@admin_bp.route('/ciclo/<int:id>/activar', methods=['POST'])
@login_required
@admin_required
def activar_ciclo(id):
    """Activar un ciclo académico"""
    ciclo = CicloAcademico.query.get_or_404(id)
    
    try:
        ciclo.activar()
        flash(f'Ciclo académico "{ciclo.nombre}" activado', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al activar el ciclo: {str(e)}', 'error')
    
    return redirect(url_for('admin.ciclos'))

@admin_bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    """Gestionar usuarios"""
    page = request.args.get('page', 1, type=int)
    rol = request.args.get('rol', 'todos')
    buscar = request.args.get('buscar', '')
    
    query = Usuario.query
    
    # Filtrar por rol
    if rol != 'todos':
        query = query.filter(Usuario.rol == rol)
    
    # Buscar por nombre o DNI
    if buscar:
        query = query.filter(
            db.or_(
                Usuario.nombre.ilike(f'%{buscar}%'),
                Usuario.dni.ilike(f'%{buscar}%'),
                Usuario.email.ilike(f'%{buscar}%')
            )
        )
    
    # Paginación
    usuarios = Usuario.query.order_by(desc(Usuario.fecha_registro)).all()
    administradores = Usuario.query.filter_by(rol='administrador').all()
    usuarios_seguridad = UsuarioSeguridad.query.all()
    
    return render_template('admin/usuarios.html', 
                         usuarios=usuarios,
                         administradores=administradores,
                         usuarios_seguridad=usuarios_seguridad,
                         rol_actual=rol, 
                         buscar_actual=buscar)

@admin_bp.route('/pases')
@login_required
@admin_required
def pases():
    """Gestionar pases vehiculares"""
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', 'todos')
    tipo = request.args.get('tipo', 'todos')
    
    query = PaseVehicular.query
    
    # Filtrar por estado
    if estado != 'todos':
        query = query.filter(PaseVehicular.estado == estado)
    
    # Filtrar por tipo
    if tipo != 'todos':
        query = query.filter(PaseVehicular.tipo_pase == tipo)
    
    # Ordenar por fecha más reciente
    query = query.order_by(desc(PaseVehicular.fecha_emision))
    
    # Paginación
    pases = query.paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('admin/pases.html', 
                         pases=pases, 
                         estado_actual=estado, 
                         tipo_actual=tipo)

@admin_bp.route('/pase/<int:id>/revocar', methods=['POST'])
@login_required
@admin_required
def revocar_pase(id):
    """Revocar un pase vehicular"""
    pase = PaseVehicular.query.get_or_404(id)
    
    if pase.estado != 'vigente':
        flash('Este pase ya no está vigente', 'error')
        return redirect(url_for('admin.pases'))
    
    try:
        pase.estado = 'revocado'
        db.session.commit()
        flash('Pase revocado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al revocar el pase: {str(e)}', 'error')
    
    return redirect(url_for('admin.pases'))

@admin_bp.route('/estadisticas')
@login_required
@admin_required
def estadisticas():
    """Ver estadísticas avanzadas"""
    # Estadísticas por mes
    solicitudes_por_mes = db.session.query(
        func.date_trunc('month', SolicitudPase.fecha_solicitud).label('mes'),
        func.count(SolicitudPase.id).label('cantidad')
    ).group_by('mes').order_by('mes').all()
    
    # Pases por tipo
    pases_por_tipo = db.session.query(
        PaseVehicular.tipo_pase,
        func.count(PaseVehicular.id).label('cantidad')
    ).group_by(PaseVehicular.tipo_pase).all()
    
    # Usuarios más activos
    usuarios_activos = db.session.query(
        Usuario.nombre,
        func.count(SolicitudPase.id).label('solicitudes')
    ).join(SolicitudPase).group_by(Usuario.id, Usuario.nombre).order_by(
        desc('solicitudes')
    ).limit(10).all()
    
    estadisticas = {
        'solicitudes_por_mes': solicitudes_por_mes,
        'pases_por_tipo': dict(pases_por_tipo),
        'usuarios_activos': usuarios_activos
    }
    
    return render_template('admin/estadisticas.html', **estadisticas)

@admin_bp.route('/crear-usuario', methods=['POST'])
@login_required
@admin_required
def crear_usuario():
    """Crear un nuevo usuario"""
    try:
        nombre = request.form.get('nombre', '').strip()
        dni = request.form.get('dni', '').strip()
        rol = request.form.get('rol', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        codigo_universitario = request.form.get('codigo_universitario', '').strip()
        contraseña = request.form.get('contraseña', '').strip()
        
        # Validaciones
        if not all([nombre, dni, rol, contraseña]):
            flash('Nombre, DNI, rol y contraseña son obligatorios', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Verificar que el DNI no existe
        if Usuario.query.filter_by(dni=dni).first():
            flash('Ya existe un usuario con ese DNI', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Verificar que el email no existe (si se proporciona)
        if email and Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Crear el usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            dni=dni,
            rol=rol,
            contraseña=contraseña,
            codigo_universitario=codigo_universitario if codigo_universitario else None,
            email=email if email else None,
            telefono=telefono if telefono else None
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash(f'Usuario {nombre} creado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear el usuario: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/crear-administrador', methods=['POST'])
@login_required
@admin_required
def crear_administrador():
    """Crear un nuevo administrador"""
    try:
        nombre = request.form.get('nombre', '').strip()
        dni = request.form.get('dni', '').strip()
        email = request.form.get('email', '').strip()
        contraseña = request.form.get('contraseña', '').strip()
        
        # Validaciones
        if not all([nombre, dni, contraseña]):
            flash('Nombre, DNI y contraseña son obligatorios', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Verificar que el DNI no existe
        if Usuario.query.filter_by(dni=dni).first():
            flash('Ya existe un usuario con ese DNI', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Verificar que el email no existe (si se proporciona)
        if email and Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Crear el administrador
        nuevo_admin = Usuario(
            nombre=nombre,
            dni=dni,
            rol='administrador',
            contraseña=contraseña,
            email=email if email else None
        )
        
        db.session.add(nuevo_admin)
        db.session.commit()
        
        flash(f'Administrador {nombre} creado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear el administrador: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/crear-usuario-seguridad', methods=['POST'])
@login_required
@admin_required
def crear_usuario_seguridad():
    """Crear un nuevo usuario de seguridad"""
    try:
        nombre = request.form.get('nombre', '').strip()
        usuario = request.form.get('usuario', '').strip()
        contraseña = request.form.get('contraseña', '').strip()
        
        # Validaciones
        if not all([nombre, usuario, contraseña]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Verificar que el usuario no existe
        if UsuarioSeguridad.query.filter_by(usuario=usuario).first():
            flash('Ya existe un usuario de seguridad con ese nombre de usuario', 'error')
            return redirect(url_for('admin.usuarios'))
        
        # Crear el usuario de seguridad
        nuevo_seguridad = UsuarioSeguridad(
            nombre=nombre,
            usuario=usuario,
            contraseña=contraseña
        )
        
        db.session.add(nuevo_seguridad)
        db.session.commit()
        
        flash(f'Personal de seguridad {nombre} creado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear el usuario de seguridad: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/usuarios/<int:id>/eliminar', methods=['GET'])
@login_required
@admin_required
def eliminar_usuario(id):
    """Eliminar un usuario"""
    try:
        usuario = Usuario.query.get_or_404(id)
        
        # Verificar que no es el último administrador
        if usuario.rol == 'administrador':
            admins_count = Usuario.query.filter_by(rol='administrador').count()
            if admins_count <= 1:
                flash('No se puede eliminar el último administrador del sistema', 'error')
                return redirect(url_for('admin.usuarios'))
        
        # Verificar que no tiene solicitudes o pases activos
        solicitudes_activas = SolicitudPase.query.filter_by(
            usuario_id=id, 
            estado='pendiente'
        ).count()
        
        if solicitudes_activas > 0:
            flash('No se puede eliminar un usuario con solicitudes pendientes', 'error')
            return redirect(url_for('admin.usuarios'))
        
        pases_activos = PaseVehicular.query.filter_by(
            usuario_id=id, 
            estado='vigente'
        ).count()
        
        if pases_activos > 0:
            flash('No se puede eliminar un usuario con pases activos', 'error')
            return redirect(url_for('admin.usuarios'))
        
        nombre = usuario.nombre
        db.session.delete(usuario)
        db.session.commit()
        
        flash(f'Usuario {nombre} eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/usuarios-seguridad/<int:id>/eliminar', methods=['GET'])
@login_required
@admin_required
def eliminar_usuario_seguridad(id):
    """Eliminar un usuario de seguridad"""
    try:
        usuario_seguridad = UsuarioSeguridad.query.get_or_404(id)
        
        # Verificar que no tiene registros de acceso recientes
        # (opcional, dependiendo de tus necesidades)
        
        nombre = usuario_seguridad.nombre
        db.session.delete(usuario_seguridad)
        db.session.commit()
        
        flash(f'Personal de seguridad {nombre} eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario de seguridad: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))
