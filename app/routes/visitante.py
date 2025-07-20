from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.utils.auth_utils import login_required, role_required, get_current_user
from app import db
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.models.solicitud_pase import SolicitudPase
from app.models.pase_vehicular import PaseVehicular
from app.models.ciclo_academico import CicloAcademico
from datetime import datetime, date

visitante_bp = Blueprint('visitante', __name__, url_prefix='/visitante')

@visitante_bp.route('/dashboard')
@login_required
@role_required('visita')
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
    
    return render_template('visitante/dashboard.html', 
                         user=user, 
                         vehiculos=vehiculos,
                         solicitudes=solicitudes,
                         pases_activos=pases_activos)

@visitante_bp.route('/solicitar-pase', methods=['GET', 'POST'])
@login_required
@role_required('visita')
def solicitar_pase():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            vehiculo_id = request.form.get('vehiculo_id')
            fecha_inicio = request.form.get('fecha_inicio')
            fecha_fin = request.form.get('fecha_fin')
            
            # Validaciones
            if not vehiculo_id or not fecha_inicio or not fecha_fin:
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('visitante.solicitar_pase'))
            
            # Verificar que el vehículo pertenece al usuario
            vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
            if not vehiculo:
                flash('Vehículo no válido', 'error')
                return redirect(url_for('visitante.solicitar_pase'))
            
            # Validar fechas para pases temporales (visitantes solo pueden solicitar pases temporales)
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            if fecha_inicio_obj < date.today():
                flash('La fecha de inicio no puede ser anterior a hoy', 'error')
                return redirect(url_for('visitante.solicitar_pase'))
            
            if fecha_fin_obj <= fecha_inicio_obj:
                flash('La fecha de fin debe ser posterior a la fecha de inicio', 'error')
                return redirect(url_for('visitante.solicitar_pase'))
            
            # Crear la solicitud (visitantes solo pueden solicitar pases temporales)
            nueva_solicitud = SolicitudPase(
                usuario_id=user['id'],
                vehiculo_id=vehiculo_id,
                tipo_pase='temporal',
                ciclo_id=None
            )
            
            # Asignar fechas de reservación
            nueva_solicitud.fecha_reservacion_inicio = fecha_inicio_obj
            nueva_solicitud.fecha_reservacion_fin = fecha_fin_obj
            
            db.session.add(nueva_solicitud)
            db.session.commit()
            
            flash('Solicitud enviada correctamente. Será revisada por el personal administrativo.', 'success')
            return redirect(url_for('visitante.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intenta nuevamente.', 'error')
            print(f"Error en solicitud: {e}")
    
    # GET request
    vehiculos = Vehiculo.query.filter_by(usuario_id=user['id']).all()
    
    return render_template('visitante/solicitar_pase.html', 
                         user=user,
                         user_type='visitante',
                         vehiculos=vehiculos)

@visitante_bp.route('/vehiculos', methods=['GET', 'POST'])
@login_required
@role_required('visita')
def vehiculos():
    user = get_current_user()
    
    if request.method == 'POST':
        try:
            vehiculo_id = request.form.get('vehiculo_id')
            placa = request.form.get('placa', '').strip().upper()
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            color = request.form.get('color', '').strip()
            tipo = request.form.get('tipo', '').strip()
            year = request.form.get('year')
            
            # Validaciones
            if not placa or not marca or not modelo or not color or not tipo or not year:
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('visitante.vehiculos'))
            
            # Validar año
            try:
                year = int(year)
                current_year = datetime.now().year
                if year < 1950 or year > current_year:
                    flash(f'El año debe estar entre 1950 y {current_year}', 'error')
                    return redirect(url_for('visitante.vehiculos'))
            except ValueError:
                flash('El año debe ser un número válido', 'error')
                return redirect(url_for('visitante.vehiculos'))
            
            # Verificar que la placa no esté en uso por otro vehículo
            vehiculo_existente = Vehiculo.query.filter_by(placa=placa).first()
            
            if vehiculo_id:  # Actualizar vehículo existente
                vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
                if not vehiculo:
                    flash('Vehículo no encontrado', 'error')
                    return redirect(url_for('visitante.vehiculos'))
                
                # Verificar si la placa ya existe en otro vehículo
                if vehiculo_existente and vehiculo_existente.id != int(vehiculo_id):
                    flash('La placa ya está registrada en otro vehículo', 'error')
                    return redirect(url_for('visitante.vehiculos'))
                
                vehiculo.placa = placa
                vehiculo.marca = marca
                vehiculo.modelo = modelo
                vehiculo.color = color
                vehiculo.tipo = tipo
                vehiculo.year = year
                
                flash('Vehículo actualizado correctamente', 'success')
                
            else:  # Crear nuevo vehículo
                if vehiculo_existente:
                    flash('La placa ya está registrada', 'error')
                    return redirect(url_for('visitante.vehiculos'))
                
                nuevo_vehiculo = Vehiculo(
                    usuario_id=user['id'],
                    placa=placa,
                    marca=marca,
                    modelo=modelo,
                    color=color,
                    tipo=tipo,
                    year=year
                )
                
                db.session.add(nuevo_vehiculo)
                flash('Vehículo registrado correctamente', 'success')
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intenta nuevamente.', 'error')
            print(f"Error en vehículo: {e}")
    
    # GET request
    vehiculos_usuario = Vehiculo.query.filter_by(usuario_id=user['id']).all()
    
    return render_template('visitante/vehiculos.html', 
                         user=user,
                         vehiculos=vehiculos_usuario)

@visitante_bp.route('/eliminar-vehiculo/<int:vehiculo_id>')
@login_required
@role_required('visita')
def eliminar_vehiculo(vehiculo_id):
    user = get_current_user()
    
    try:
        vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, usuario_id=user['id']).first()
        if not vehiculo:
            flash('Vehículo no encontrado', 'error')
            return redirect(url_for('visitante.vehiculos'))
        
        # Verificar si el vehículo tiene pases activos
        pases_activos = PaseVehicular.query.filter_by(
            vehiculo_id=vehiculo_id, 
            estado='vigente'
        ).count()
        
        if pases_activos > 0:
            flash('No se puede eliminar un vehículo con pases activos', 'error')
            return redirect(url_for('visitante.vehiculos'))
        
        db.session.delete(vehiculo)
        db.session.commit()
        
        flash('Vehículo eliminado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el vehículo. Intenta nuevamente.', 'error')
        print(f"Error eliminando vehículo: {e}")
    
    return redirect(url_for('visitante.vehiculos'))

@visitante_bp.route('/ver-pase/<int:pase_id>')
@login_required
@role_required('visita')
def ver_pase(pase_id):
    user = get_current_user()
    
    pase = PaseVehicular.query.filter_by(id=pase_id, usuario_id=user['id']).first()
    if not pase:
        flash('Pase no encontrado', 'error')
        return redirect(url_for('visitante.dashboard'))
    
    estacionamiento_asignado = pase.obtener_estacionamiento_reservado()
    
    return render_template('visitante/ver_pase.html', 
                     user=user,
                     pase=pase,
                     estacionamiento_asignado=estacionamiento_asignado)

@visitante_bp.route('/ver-solicitud/<int:solicitud_id>')
@login_required
@role_required('visita')
def ver_solicitud(solicitud_id):
    user = get_current_user()
    
    solicitud = SolicitudPase.query.filter_by(id=solicitud_id, usuario_id=user['id']).first()
    if not solicitud:
        flash('Solicitud no encontrada', 'error')
        return redirect(url_for('visitante.dashboard'))
    
    return render_template('visitante/ver_solicitud.html', 
                         user=user,
                         solicitud=solicitud)
