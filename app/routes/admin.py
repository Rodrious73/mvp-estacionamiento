from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.estacionamiento import Estacionamiento
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

@admin_bp.route('/pase/<int:id>/imprimir')
@login_required
@admin_required
def imprimir_pase(id):
    """Página de impresión del pase vehicular"""
    pase = PaseVehicular.query.get_or_404(id)
    return render_template('utils/pase_impresion.html', pase=pase)

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
        'solicitudes_por_estado': dict(solicitudes_por_estado),
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
    
    comentarios = request.form.get('comentarios_admin', '')
    estacionamiento_id = request.form.get('estacionamiento_id')
    
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
            # Para pases temporales, usar fechas específicas
            if solicitud.usuario.rol == 'visita':
                # Para visitantes, usar fechas de la solicitud si están disponibles
                if hasattr(solicitud, 'fecha_reservacion_inicio') and solicitud.fecha_reservacion_inicio:
                    fecha_inicio = solicitud.fecha_reservacion_inicio
                    fecha_fin = solicitud.fecha_reservacion_fin
                else:
                    # Si no hay fechas específicas, usar fechas por defecto
                    fecha_inicio = datetime.now().date()
                    fecha_fin = fecha_inicio + timedelta(days=1)
            else:
                # Para otros usuarios temporales, usar 30 días
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
        db.session.flush()  # Para obtener el ID del pase
        
        # Si es un visitante con pase temporal y se seleccionó un estacionamiento, reservarlo
        if (solicitud.usuario.rol == 'visita' and 
            solicitud.tipo_pase == 'temporal' and 
            estacionamiento_id):
            
            estacionamiento = Estacionamiento.query.get(estacionamiento_id)
            if estacionamiento and estacionamiento.estado == 'disponible':
                # Reservar el estacionamiento
                estacionamiento.estado = 'reservado'
                estacionamiento.pase_id = pase.id
                estacionamiento.fecha_asignacion = datetime.now()
                estacionamiento.observaciones = f'Reservado para visitante {solicitud.usuario.nombre} - Pase #{pase.id}'
                
                flash(f'Solicitud aprobada y espacio {estacionamiento.numero} reservado exitosamente', 'success')
            else:
                flash('Solicitud aprobada pero el estacionamiento seleccionado ya no está disponible', 'warning')
        elif (solicitud.usuario.rol == 'visita' and 
              solicitud.tipo_pase == 'temporal' and 
              not estacionamiento_id):
            # Si es visitante temporal pero no se seleccionó estacionamiento
            flash('Solicitud aprobada pero no se reservó ningún estacionamiento', 'warning')
        else:
            # Para otros casos (no visitantes o pases de ciclo)
            flash('Solicitud aprobada exitosamente', 'success')
        
        db.session.commit()
        
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
    
    comentarios = request.form.get('comentarios_admin', '')
    
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

@admin_bp.route('/ciclo/crear', methods=['POST'])
@login_required
@admin_required
def crear_ciclo():
    """Crear un nuevo ciclo académico"""
    try:
        nombre = request.form.get('nombre', '').strip()
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        activar_inmediatamente = request.form.get('activar_inmediatamente') == 'on'
        
        # Validaciones
        if not all([nombre, fecha_inicio, fecha_fin]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.ciclos'))
        
        # Convertir fechas
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if fecha_inicio >= fecha_fin:
            flash('La fecha de inicio debe ser anterior a la fecha de fin', 'error')
            return redirect(url_for('admin.ciclos'))
        
        # Crear ciclo
        estado = 'activo' if activar_inmediatamente else 'inactivo'
        ciclo = CicloAcademico(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado
        )
        
        # Si se marca para activar inmediatamente, desactivar otros ciclos
        if activar_inmediatamente:
            CicloAcademico.query.update({'estado': 'inactivo'})
        
        db.session.add(ciclo)
        db.session.commit()
        
        flash(f'Ciclo académico "{nombre}" creado exitosamente', 'success')
        return redirect(url_for('admin.ciclos'))
        
    except ValueError:
        flash('Formato de fecha inválido', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear el ciclo: {str(e)}', 'error')
    
    return redirect(url_for('admin.ciclos'))

@admin_bp.route('/ciclo/<int:ciclo_id>/desactivar', methods=['POST'])
@login_required
@admin_required
def desactivar_ciclo(ciclo_id):
    """Desactivar un ciclo académico"""
    try:
        ciclo = CicloAcademico.query.get_or_404(ciclo_id)
        ciclo.estado = 'inactivo'
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Ciclo "{ciclo.nombre}" desactivado'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al desactivar el ciclo: {str(e)}'})

@admin_bp.route('/ciclo/<int:ciclo_id>/activar', methods=['POST'])
@login_required
@admin_required
def activar_ciclo_ajax(ciclo_id):
    """Activar un ciclo académico vía AJAX"""
    try:
        ciclo = CicloAcademico.query.get_or_404(ciclo_id)
        
        # Desactivar todos los ciclos
        CicloAcademico.query.update({'estado': 'inactivo'})
        
        # Activar este ciclo
        ciclo.estado = 'activo'
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Ciclo "{ciclo.nombre}" activado'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al activar el ciclo: {str(e)}'})

@admin_bp.route('/ciclo/<int:ciclo_id>/editar', methods=['POST'])
@login_required
@admin_required
def editar_ciclo(ciclo_id):
    """Editar un ciclo académico"""
    try:
        ciclo = CicloAcademico.query.get_or_404(ciclo_id)
        
        nombre = request.form.get('nombre', '').strip()
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        # Validaciones
        if not all([nombre, fecha_inicio, fecha_fin]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin.ciclos'))
        
        # Convertir fechas
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if fecha_inicio >= fecha_fin:
            flash('La fecha de inicio debe ser anterior a la fecha de fin', 'error')
            return redirect(url_for('admin.ciclos'))
        
        # Actualizar ciclo
        ciclo.nombre = nombre
        ciclo.fecha_inicio = fecha_inicio
        ciclo.fecha_fin = fecha_fin
        
        db.session.commit()
        
        flash(f'Ciclo académico "{nombre}" actualizado exitosamente', 'success')
        return redirect(url_for('admin.ciclos'))
        
    except ValueError:
        flash('Formato de fecha inválido', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al editar el ciclo: {str(e)}', 'error')
    
    return redirect(url_for('admin.ciclos'))

@admin_bp.route('/ciclo/<int:ciclo_id>/eliminar', methods=['DELETE'])
@login_required
@admin_required
def eliminar_ciclo(ciclo_id):
    """Eliminar un ciclo académico"""
    try:
        ciclo = CicloAcademico.query.get_or_404(ciclo_id)
        
        # Verificar que no tenga solicitudes o pases asociados
        if ciclo.solicitudes_pases or ciclo.pases_vehiculares:
            return jsonify({
                'success': False, 
                'message': 'No se puede eliminar el ciclo porque tiene solicitudes o pases asociados'
            })
        
        nombre = ciclo.nombre
        db.session.delete(ciclo)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Ciclo "{nombre}" eliminado exitosamente'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar el ciclo: {str(e)}'})

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
    
    # Ordenar por fecha de registro
    query = query.order_by(desc(Usuario.fecha_registro))
    
    # Paginación
    usuarios = query.paginate(
        page=page, per_page=20, error_out=False
    )

    usuarios_seguridad = UsuarioSeguridad.query.order_by(asc(UsuarioSeguridad.nombre)).all()

    administradores = Usuario.query.filter_by(rol='administrador').all()
    
    return render_template('admin/usuarios.html', 
                         usuarios=usuarios, 
                         rol_actual=rol, 
                         buscar_actual=buscar,
                         usuarios_seguridad=usuarios_seguridad,
                         administradores=administradores)

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
        
        nombre = usuario_seguridad.nombre
        db.session.delete(usuario_seguridad)
        db.session.commit()
        
        flash(f'Personal de seguridad {nombre} eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario de seguridad: {str(e)}', 'error')
    
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/pases')
@login_required
@admin_required
def pases():
    """Gestionar pases vehiculares"""
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', 'todos')
    tipo = request.args.get('tipo', 'todos')
    buscar = request.args.get('buscar', '')
    
    query = PaseVehicular.query
    
    # Filtrar por estado
    if estado != 'todos':
        query = query.filter(PaseVehicular.estado == estado)
    
    # Filtrar por tipo
    if tipo != 'todos':
        query = query.filter(PaseVehicular.tipo_pase == tipo)
    
    # Filtrar por búsqueda
    if buscar:
        query = query.join(Usuario).join(Vehiculo).filter(
            db.or_(
                Vehiculo.placa.ilike(f'%{buscar}%'),
                Usuario.nombre.ilike(f'%{buscar}%')
            )
        )
    
    # Ordenar por fecha más reciente
    query = query.order_by(desc(PaseVehicular.fecha_emision))
    
    # Paginación
    pases = query.paginate(
        page=page, per_page=15, error_out=False
    )
    
    # Estadísticas
    pases_vigentes = PaseVehicular.query.filter_by(estado='vigente').count()
    pases_expirados = PaseVehicular.query.filter_by(estado='expirado').count()
    pases_revocados = PaseVehicular.query.filter_by(estado='revocado').count()
    
    return render_template('admin/pases.html', 
                         pases=pases, 
                         estado_actual=estado, 
                         tipo_actual=tipo,
                         buscar_actual=buscar,
                         pases_vigentes=pases_vigentes,
                         pases_expirados=pases_expirados,
                         pases_revocados=pases_revocados)

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

@admin_bp.route('/vehiculos')
@login_required
@admin_required
def vehiculos():
    """Gestionar vehículos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '')
    
    query = Vehiculo.query.join(Usuario)
    
    # Buscar por placa, marca, modelo o propietario
    if buscar:
        query = query.filter(
            db.or_(
                Vehiculo.placa.ilike(f'%{buscar}%'),
                Vehiculo.marca.ilike(f'%{buscar}%'),
                Vehiculo.modelo.ilike(f'%{buscar}%'),
                Usuario.nombre.ilike(f'%{buscar}%')
            )
        )
    
    # Ordenar por fecha de registro
    query = query.order_by(desc(Vehiculo.fecha_registro))
    
    # Paginación
    vehiculos = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/vehiculos.html', 
                         vehiculos=vehiculos, 
                         buscar_actual=buscar)

@admin_bp.route('/vehiculo/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_vehiculo(id):
    """Eliminar un vehículo"""
    vehiculo = Vehiculo.query.get_or_404(id)
    
    # Verificar si tiene pases activos
    pases_activos = PaseVehicular.query.filter(
        PaseVehicular.vehiculo_id == id,
        PaseVehicular.estado == 'vigente'
    ).count()
    
    if pases_activos > 0:
        flash('No se puede eliminar el vehículo porque tiene pases activos', 'error')
        return redirect(url_for('admin.vehiculos'))
    
    try:
        db.session.delete(vehiculo)
        db.session.commit()
        flash(f'Vehículo {vehiculo.placa} eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el vehículo: {str(e)}', 'error')
    
    return redirect(url_for('admin.vehiculos'))

@admin_bp.route('/reportes')
@login_required
@admin_required
def reportes():
    """Ver reportes y estadísticas avanzadas"""
    # Reportes por fechas
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    if not fecha_desde:
        fecha_desde = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_hasta:
        fecha_hasta = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
    except ValueError:
        flash('Formato de fecha inválido', 'error')
        fecha_desde_dt = datetime.utcnow() - timedelta(days=30)
        fecha_hasta_dt = datetime.utcnow()
    
    # Solicitudes por día
    solicitudes_por_dia = db.session.query(
        func.date(SolicitudPase.fecha_solicitud).label('fecha'),
        func.count(SolicitudPase.id).label('cantidad')
    ).filter(
        SolicitudPase.fecha_solicitud >= fecha_desde_dt,
        SolicitudPase.fecha_solicitud <= fecha_hasta_dt
    ).group_by(func.date(SolicitudPase.fecha_solicitud)).all()
    
    # Pases por estado
    pases_por_estado = db.session.query(
        PaseVehicular.estado,
        func.count(PaseVehicular.id).label('cantidad')
    ).group_by(PaseVehicular.estado).all()
    
    # Usuarios más activos
    usuarios_activos = db.session.query(
        Usuario.nombre,
        Usuario.rol,
        func.count(SolicitudPase.id).label('solicitudes')
    ).join(SolicitudPase).filter(
        SolicitudPase.fecha_solicitud >= fecha_desde_dt,
        SolicitudPase.fecha_solicitud <= fecha_hasta_dt
    ).group_by(Usuario.id, Usuario.nombre, Usuario.rol).order_by(
        desc(func.count(SolicitudPase.id))
    ).limit(10).all()
    
    reportes = {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'solicitudes_por_dia': solicitudes_por_dia,
        'pases_por_estado': dict(pases_por_estado),
        'usuarios_activos': usuarios_activos
    }
    
    return render_template('admin/reportes.html', **reportes)

@admin_bp.route('/api/estadisticas')
@login_required
@admin_required
def api_estadisticas():
    """API para obtener estadísticas en tiempo real"""
    # Obtener estadísticas de los últimos 30 días
    fecha_limite = datetime.utcnow() - timedelta(days=30)
    
    # Solicitudes por día
    solicitudes_por_dia = db.session.query(
        func.date(SolicitudPase.fecha_solicitud).label('fecha'),
        func.count(SolicitudPase.id).label('cantidad')
    ).filter(
        SolicitudPase.fecha_solicitud >= fecha_limite
    ).group_by(func.date(SolicitudPase.fecha_solicitud)).all()
    
    # Convertir a formato JSON
    data = {
        'solicitudes_por_dia': [
            {
                'fecha': fecha.strftime('%Y-%m-%d'),
                'cantidad': cantidad
            } for fecha, cantidad in solicitudes_por_dia
        ],
        'total_usuarios': Usuario.query.count(),
        'solicitudes_pendientes': SolicitudPase.query.filter_by(estado='pendiente').count(),
        'pases_activos': PaseVehicular.query.filter(
            PaseVehicular.estado == 'vigente',
            PaseVehicular.fecha_fin >= datetime.now().date()
        ).count()
    }
    
    return jsonify(data)

@admin_bp.route('/pase/<int:id>')
@login_required
@admin_required
def ver_pase(id):
    """Ver detalles de un pase vehicular"""
    pase = PaseVehicular.query.get_or_404(id)
    return render_template('admin/ver_pase.html', pase=pase)

@admin_bp.route('/pase/<int:id>/descargar', methods=['GET'])
@login_required
@admin_required
def descargar_pase(id):
    """Descargar PDF de un pase vehicular"""
    pase = PaseVehicular.query.get_or_404(id)
    
    # Aquí puedes implementar la generación del PDF
    # Por ahora, redirigimos de vuelta a la lista de pases
    flash('Funcionalidad de descarga en desarrollo', 'info')
    return redirect(url_for('admin.pases'))

@admin_bp.route('/pase/<int:id>/historial')
@login_required
@admin_required
def historial_pase(id):
    """Ver historial de accesos de un pase vehicular"""
    pase = PaseVehicular.query.get_or_404(id)
    
    # Aquí puedes implementar el historial de accesos
    # Por ahora, redirigimos de vuelta a la lista de pases
    flash('Funcionalidad de historial en desarrollo', 'info')
    return redirect(url_for('admin.pases'))

@admin_bp.route('/api/solicitud/<int:solicitud_id>/info')
@login_required
@admin_required
def api_solicitud_info(solicitud_id):
    """API para obtener información de una solicitud"""
    try:
        solicitud = SolicitudPase.query.get_or_404(solicitud_id)
        
        data = {
            'id': solicitud.id,
            'usuario': {
                'id': solicitud.usuario.id,
                'nombre': solicitud.usuario.nombre,
                'rol': solicitud.usuario.rol
            },
            'vehiculo': {
                'id': solicitud.vehiculo.id,
                'placa': solicitud.vehiculo.placa,
                'marca': solicitud.vehiculo.marca,
                'modelo': solicitud.vehiculo.modelo
            },
            'tipo_pase': solicitud.tipo_pase,
            'estado': solicitud.estado,
            'fecha_solicitud': solicitud.fecha_solicitud.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({'success': True, 'solicitud': data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/estacionamientos/disponibles')
@login_required
@admin_required
def api_estacionamientos_disponibles():
    """API para obtener estacionamientos disponibles"""
    try:
        estacionamientos = Estacionamiento.query.filter_by(estado='disponible').all()
        
        data = []
        for est in estacionamientos:
            data.append({
                'id': est.id,
                'numero': est.numero,
                'estado': est.estado,
                'observaciones': est.observaciones
            })
        
        return jsonify({
            'success': True, 
            'estacionamientos': data,
            'total': len(data)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/pase/<int:id>/cambiar-espacio', methods=['POST'])
@login_required
@admin_required
def cambiar_espacio_pase(id):
    """Cambiar espacio reservado de un pase temporal"""
    pase = PaseVehicular.query.get_or_404(id)
    
    if pase.tipo_pase != 'temporal':
        flash('Solo se puede cambiar el espacio de pases temporales', 'error')
        return redirect(url_for('admin.ver_pase', id=id))
    
    nuevo_estacionamiento_id = request.form.get('nuevo_estacionamiento_id')
    motivo_cambio = request.form.get('motivo_cambio', '').strip()
    
    if not nuevo_estacionamiento_id or not motivo_cambio:
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('admin.ver_pase', id=id))
    
    try:
        from app.models.estacionamiento import Estacionamiento
        
        # Verificar que el nuevo estacionamiento esté disponible
        nuevo_estacionamiento = Estacionamiento.query.get_or_404(nuevo_estacionamiento_id)
        
        if nuevo_estacionamiento.estado != 'disponible':
            flash('El espacio seleccionado no está disponible', 'error')
            return redirect(url_for('admin.ver_pase', id=id))
        
        # Liberar espacio anterior si existe
        if pase.estacionamiento_reservado:
            pase.estacionamiento_reservado.estado = 'disponible'
            pase.estacionamiento_reservado.pase_id = None
        
        # Asignar nuevo espacio
        nuevo_estacionamiento.estado = 'reservado'
        nuevo_estacionamiento.pase_id = pase.id
        pase.estacionamiento_id = nuevo_estacionamiento.id
        
        # Agregar comentario sobre el cambio
        comentario_anterior = pase.comentarios_admin or ''
        nuevo_comentario = f"Espacio cambiado: {motivo_cambio}"
        pase.comentarios_admin = f"{comentario_anterior}\n{nuevo_comentario}" if comentario_anterior else nuevo_comentario
        
        db.session.commit()
        flash('Espacio reservado cambiado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar el espacio: {str(e)}', 'error')
    
    return redirect(url_for('admin.ver_pase', id=id))

@admin_bp.route('/pase/<int:id>/reactivar', methods=['GET'])
@login_required
@admin_required
def reactivar_pase(id):
    """Reactivar un pase revocado"""
    pase = PaseVehicular.query.get_or_404(id)
    
    if pase.estado != 'revocado':
        flash('Solo se pueden reactivar pases revocados', 'error')
        return redirect(url_for('admin.ver_pase', id=id))
    
    try:
        # Verificar que el pase no haya expirado
        if pase.tipo_pase == 'temporal' and pase.fecha_fin < datetime.now().date():
            flash('No se puede reactivar un pase temporal que ya expiró', 'error')
            return redirect(url_for('admin.ver_pase', id=id))
        
        pase.estado = 'vigente'
        db.session.commit()
        flash('Pase reactivado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al reactivar el pase: {str(e)}', 'error')
    
    return redirect(url_for('admin.ver_pase', id=id))