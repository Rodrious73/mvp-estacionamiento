from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.utils.auth_utils import login_required, role_required, get_current_user
from app import db
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.models.solicitud_pase import SolicitudPase
from app.models.pase_vehicular import PaseVehicular
from app.models.ciclo_academico import CicloAcademico
from datetime import datetime, date

docente_bp = Blueprint('docente', __name__, url_prefix='/docente')

# En cualquier route file
@docente_bp.route('/pase/<int:id>/imprimir')
@login_required
@role_required('docente')
def imprimir_pase(id):
    user = get_current_user()
    pase = PaseVehicular.query.filter_by(
        id=id, 
        usuario_id=user['id']
    ).first_or_404()
    return render_template('utils/pase_impresion.html', pase=pase)

@docente_bp.route('/dashboard')
@login_required
@role_required('docente')
def dashboard():
    user = get_current_user()
    usuario = Usuario.query.get(user['id'])
    
    # Obtener vehículos del usuario
    vehiculos = Vehiculo.query.filter_by(usuario_id=user['id']).all()
    
    # Obtener solicitudes del usuario
    solicitudes = SolicitudPase.query.filter_by(usuario_id=user['id']).order_by(SolicitudPase.fecha_solicitud.desc()).limit(5).all()
    
    # Obtener pases activos
    pases_activos = PaseVehicular.query.filter_by(
        usuario_id=user['id'], 
        estado='vigente'
    ).all()
    
    # Obtener ciclo académico actual
    ciclo_actual = CicloAcademico.get_ciclo_activo()
    
    return render_template('docente/dashboard.html', 
                         user=user, 
                         vehiculos=vehiculos,
                         solicitudes=solicitudes,
                         pases_activos=pases_activos,
                         ciclo_actual=ciclo_actual)

@docente_bp.route('/solicitar-pase', methods=['GET', 'POST'])
@login_required
@role_required('docente')
def solicitar_pase():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            vehiculo_id = request.form.get('vehiculo_id')
            tipo_pase = request.form.get('tipo_pase')
            fecha_inicio = request.form.get('fecha_inicio')
            fecha_fin = request.form.get('fecha_fin')
            motivo = request.form.get('motivo', '').strip()
            
            # Validaciones
            if not vehiculo_id or not tipo_pase:
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('docente.solicitar_pase'))
            
            # Verificar que el vehículo pertenece al usuario
            vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
            if not vehiculo:
                flash('Vehículo no válido', 'error')
                return redirect(url_for('docente.solicitar_pase'))
            
            # Obtener ciclo actual para pases de ciclo
            ciclo_id = None
            if tipo_pase == 'ciclo':
                ciclo_actual = CicloAcademico.get_ciclo_activo()
                if not ciclo_actual:
                    flash('No hay un ciclo académico activo', 'error')
                    return redirect(url_for('docente.solicitar_pase'))
                ciclo_id = ciclo_actual.id
                
                # Verificar si ya tiene una solicitud para este ciclo y vehículo
                solicitud_existente = SolicitudPase.query.filter_by(
                    usuario_id=user['id'],
                    vehiculo_id=vehiculo_id,
                    ciclo_id=ciclo_id,
                    tipo_pase='ciclo'
                ).first()
                
                if solicitud_existente:
                    # Si la solicitud está pendiente, no permitir nueva solicitud
                    if solicitud_existente.estado == 'pendiente':
                        flash('Ya tienes una solicitud pendiente para este vehículo en el ciclo actual', 'error')
                        return redirect(url_for('docente.solicitar_pase'))
                    
                    # Si la solicitud fue aprobada, no permitir nueva solicitud
                    elif solicitud_existente.estado == 'aprobado':
                        flash('Ya tienes una solicitud aprobada para este vehículo en el ciclo actual', 'error')
                        return redirect(url_for('docente.solicitar_pase'))
            
            # Validar fechas para pases temporales
            if tipo_pase == 'temporal':
                if not fecha_inicio or not fecha_fin:
                    flash('Las fechas son obligatorias para pases temporales', 'error')
                    return redirect(url_for('docente.solicitar_pase'))
                
                fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                
                if fecha_inicio_obj < date.today():
                    flash('La fecha de inicio no puede ser anterior a hoy', 'error')
                    return redirect(url_for('docente.solicitar_pase'))
                
                if fecha_fin_obj <= fecha_inicio_obj:
                    flash('La fecha de fin debe ser posterior a la fecha de inicio', 'error')
                    return redirect(url_for('docente.solicitar_pase'))
            
            # Crear la solicitud
            nueva_solicitud = SolicitudPase(
                usuario_id=user['id'],
                vehiculo_id=vehiculo_id,
                tipo_pase=tipo_pase,
                ciclo_id=ciclo_id,
                comentarios_solicitante=motivo
            )
            
            db.session.add(nueva_solicitud)
            db.session.commit()
            
            flash('Solicitud enviada correctamente. Será revisada por el personal administrativo.', 'success')
            return redirect(url_for('docente.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intenta nuevamente.', 'error')
            print(f"Error en solicitud: {e}")
    
    # GET request
    vehiculos = Vehiculo.query.filter_by(usuario_id=user['id']).all()
    ciclo_actual = CicloAcademico.get_ciclo_activo()
    
    return render_template('docente/solicitar_pase.html', 
                         user=user,
                         user_type='docente',
                         vehiculos=vehiculos,
                         ciclo_actual=ciclo_actual)

@docente_bp.route('/vehiculos', methods=['GET', 'POST'])
@login_required
@role_required('docente')
def vehiculos():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            vehiculo_id = request.form.get('vehiculo_id')
            placa = request.form.get('placa', '').strip().upper()
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            tipo = request.form.get('tipo', '').strip()
            color = request.form.get('color', '').strip()
            year = request.form.get('year', '')
            
            # Validaciones
            if not all([placa, marca, modelo, tipo, color]):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('docente.vehiculos'))
            
            if len(placa) < 6 or len(placa) > 10:
                flash('La placa debe tener entre 6 y 10 caracteres', 'error')
                return redirect(url_for('docente.vehiculos'))
            
            # Verificar si la placa ya existe (excepto si es edición)
            vehiculo_existente = Vehiculo.query.filter_by(placa=placa).first()
            if vehiculo_existente and str(vehiculo_existente.id) != vehiculo_id:
                flash('Ya existe un vehículo con esa placa', 'error')
                return redirect(url_for('docente.vehiculos'))
            
            if vehiculo_id:  # Editar vehículo existente
                vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
                if not vehiculo:
                    flash('Vehículo no encontrado', 'error')
                    return redirect(url_for('docente.vehiculos'))
                
                vehiculo.placa = placa
                vehiculo.marca = marca
                vehiculo.modelo = modelo
                vehiculo.tipo = tipo
                vehiculo.color = color
                vehiculo.year= int(year) if year else None
                
                flash('Vehículo actualizado correctamente', 'success')
            else:  # Crear nuevo vehículo
                nuevo_vehiculo = Vehiculo(
                    placa=placa,
                    marca=marca,
                    modelo=modelo,
                    tipo=tipo,
                    color=color,
                    year=int(year) if year else None,
                    usuario_id=user['id']
                )
                
                db.session.add(nuevo_vehiculo)
                flash('Vehículo registrado correctamente', 'success')
            
            db.session.commit()
            return redirect(url_for('docente.vehiculos'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intenta nuevamente.', 'error')
            print(f"Error en vehículos: {e}")
    
    # GET request
    vehiculos = Vehiculo.query.filter_by(usuario_id=user['id']).all()
    return render_template('docente/vehiculos.html', 
                         user=user, 
                         vehiculos=vehiculos)

@docente_bp.route('/eliminar-vehiculo', methods=['POST'])
@login_required
@role_required('docente')
def eliminar_vehiculo():
    user = get_current_user()
    vehiculo_id = request.form.get('vehiculo_id')
    
    if not vehiculo_id:
        flash('ID de vehículo no válido', 'error')
        return redirect(url_for('docente.vehiculos'))
    
    try:
        vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
        if not vehiculo:
            flash('Vehículo no encontrado', 'error')
            return redirect(url_for('docente.vehiculos'))
        
        # Verificar si el vehículo tiene solicitudes pendientes
        solicitudes_pendientes = SolicitudPase.query.filter_by(
            vehiculo_id=vehiculo_id, 
            estado='pendiente'
        ).count()
        
        if solicitudes_pendientes > 0:
            flash('No puedes eliminar un vehículo con solicitudes pendientes', 'error')
            return redirect(url_for('docente.vehiculos'))
        
        db.session.delete(vehiculo)
        db.session.commit()
        flash('Vehículo eliminado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el vehículo. Intenta nuevamente.', 'error')
        print(f"Error al eliminar vehículo: {e}")
    
    return redirect(url_for('docente.vehiculos'))

@docente_bp.route('/solicitud/<int:id>')
@login_required
@role_required('docente')
def ver_solicitud(id):
    user = get_current_user()
    solicitud = SolicitudPase.query.filter_by(id=id, usuario_id=user['id']).first_or_404()
    return render_template('docente/ver_solicitud.html', 
                         user=user, 
                         solicitud=solicitud)

@docente_bp.route('/pase/<int:id>')
@login_required
@role_required('docente')
def ver_pase(id):
    user = get_current_user()
    pase = PaseVehicular.query.filter_by(id=id, usuario_id=user['id']).first_or_404()
    return render_template('docente/ver_pase.html', 
                         user=user, 
                         pase=pase)

@docente_bp.route('/cancelar-solicitud', methods=['POST'])
@login_required
@role_required('docente')
def cancelar_solicitud():
    user = get_current_user()
    solicitud_id = request.form.get('solicitud_id')
    
    if not solicitud_id:
        flash('ID de solicitud no válido', 'error')
        return redirect(url_for('docente.dashboard'))
    
    try:
        solicitud = SolicitudPase.query.filter_by(
            id=solicitud_id, 
            usuario_id=user['id'],
            estado='pendiente'
        ).first()
        
        if not solicitud:
            flash('Solicitud no encontrada o no se puede cancelar', 'error')
            return redirect(url_for('docente.dashboard'))
        
        solicitud.estado = 'cancelado'
        solicitud.fecha_revision = datetime.utcnow()
        solicitud.observaciones = 'Cancelado por el usuario'
        
        db.session.commit()
        flash('Solicitud cancelada correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error al cancelar la solicitud. Intenta nuevamente.', 'error')
        print(f"Error al cancelar solicitud: {e}")
    
    return redirect(url_for('docente.dashboard'))
