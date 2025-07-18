from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from app.models.estacionamiento import Estacionamiento
from app.utils.auth_utils import login_required, security_required, get_current_user
from app.models.registro_acceso import RegistroAcceso
from app.models.pase_vehicular import PaseVehicular
from app.models.vehiculo import Vehiculo
from app.models.usuario import Usuario
from app import db
from datetime import datetime, date
from sqlalchemy import and_, func

seguridad_bp = Blueprint('seguridad', __name__, url_prefix='/seguridad')

@seguridad_bp.route('/dashboard')
@login_required
@security_required
def dashboard():
    """Dashboard principal de seguridad"""
    user = get_current_user()
    
    # Obtener estadísticas del día
    hoy = date.today()
    
    # Contar todos los registros como accesos (sin distinguir tipo)
    accesos_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.estado == 'permitido'
    ).count()
    
    # Estimación de vehículos dentro (simplificado)
    vehiculos_dentro = max(0, accesos_hoy // 2)  # Asumiendo que la mitad están dentro
    espacios_disponibles = 50 - vehiculos_dentro  # Asumiendo 50 espacios totales
    
    # Obtener accesos recientes
    accesos_recientes = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy
    ).order_by(RegistroAcceso.fecha_hora.desc()).limit(10).all()
    
    # Alertas (ejemplo)
    alertas = []
    if vehiculos_dentro > 45:
        alertas.append({
            'tipo': 'warning',
            'icono': 'exclamation-triangle',
            'mensaje': 'Estacionamiento casi lleno'
        })
    
    return render_template('seguridad/dashboard.html',
                         current_user=user,
                         entradas_hoy=accesos_hoy,
                         salidas_hoy=0,  # Por ahora sin distinguir
                         vehiculos_dentro=vehiculos_dentro,
                         espacios_disponibles=espacios_disponibles,
                         accesos_recientes=accesos_recientes,
                         alertas=alertas)

@seguridad_bp.route('/scanner')
@login_required
@security_required
def scanner():
    """Página del escáner QR"""
    # Obtener validaciones recientes para mostrar en el panel
    validaciones_recientes = []
    accesos_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == date.today()
    ).order_by(RegistroAcceso.fecha_hora.desc()).limit(5).all()
    
    for acceso in accesos_hoy:
        if acceso.pase and acceso.pase.vehiculo:
            validaciones_recientes.append({
                'placa': acceso.pase.vehiculo.placa,
                'hora': acceso.fecha_hora.strftime('%H:%M'),
                'valido': acceso.estado == 'permitido'
            })
    
    return render_template('seguridad/scanner.html',
                         validaciones_recientes=validaciones_recientes)

# Función eliminada - usar la versión mejorada al final del archivo

@seguridad_bp.route('/accesos')
@login_required
@security_required
def accesos():
    """Página del registro de accesos"""
    return registro_accesos()

@seguridad_bp.route('/registro-accesos')
@login_required
@security_required
def registro_accesos():
    """Página de registro de accesos con filtros mejorados"""
    user = get_current_user()
    
    # Obtener parámetros de filtro
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    tipo_filtro = request.args.get('tipo')
    placa_filtro = request.args.get('placa')
    estado_filtro = request.args.get('estado')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Fecha por defecto (hoy)
    hoy = date.today()
    if not fecha_desde:
        fecha_desde = hoy.strftime('%Y-%m-%d')
    if not fecha_hasta:
        fecha_hasta = hoy.strftime('%Y-%m-%d')
    
    # Construir query base con joins
    query = RegistroAcceso.query.join(
        PaseVehicular, RegistroAcceso.pase_id == PaseVehicular.id
    ).join(
        Vehiculo, PaseVehicular.vehiculo_id == Vehiculo.id
    ).join(
        Usuario, PaseVehicular.usuario_id == Usuario.id
    )
    
    # Aplicar filtros
    if fecha_desde:
        query = query.filter(func.date(RegistroAcceso.fecha_hora) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(RegistroAcceso.fecha_hora) <= fecha_hasta)
    if tipo_filtro:
        query = query.filter(RegistroAcceso.tipo == tipo_filtro)
    if placa_filtro:
        query = query.filter(Vehiculo.placa.ilike(f'%{placa_filtro}%'))
    if estado_filtro:
        query = query.filter(RegistroAcceso.estado == estado_filtro)
    
    # Ordenar por fecha más reciente
    query = query.order_by(RegistroAcceso.fecha_hora.desc())
    
    # Paginación
    accesos = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Estadísticas del día
    entradas_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.tipo == 'entrada',
        RegistroAcceso.estado == 'permitido'
    ).count()
    
    salidas_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.tipo == 'salida',
        RegistroAcceso.estado == 'permitido'
    ).count()
    
    vehiculos_dentro = entradas_hoy - salidas_hoy
    
    # Calcular promedio de estancia
    estancias = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.tipo == 'salida',
        RegistroAcceso.estado == 'permitido',
        RegistroAcceso.duracion_estancia.isnot(None)
    ).all()
    
    promedio_estancia = "N/A"
    if estancias:
        promedio_minutos = sum(r.duracion_estancia for r in estancias) / len(estancias)
        horas = int(promedio_minutos // 60)
        minutos = int(promedio_minutos % 60)
        promedio_estancia = f"{horas}h {minutos}m" if horas > 0 else f"{minutos}m"
    
    # Accesos recientes para el sidebar
    accesos_recientes = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy
    ).order_by(RegistroAcceso.fecha_hora.desc()).limit(5).all()
    
    return render_template('seguridad/registro_acceso.html',
                         current_user=user,
                         accesos=accesos,
                         accesos_recientes=accesos_recientes,
                         entradas_hoy=entradas_hoy,
                         salidas_hoy=salidas_hoy,
                         vehiculos_dentro=vehiculos_dentro,
                         promedio_estancia=promedio_estancia,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         fecha_hoy=hoy.strftime('%Y-%m-%d'),
                         tipo_filtro=tipo_filtro,
                         placa_filtro=placa_filtro,
                         estado_filtro=estado_filtro)

@seguridad_bp.route('/registro-accesos/exportar')
@login_required
@security_required
def exportar_registros():
    """Exportar registros de accesos a CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    # Obtener parámetros de filtro
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    tipo_filtro = request.args.get('tipo')
    placa_filtro = request.args.get('placa')
    
    # Construir query
    query = RegistroAcceso.query.join(
        PaseVehicular, RegistroAcceso.pase_id == PaseVehicular.id
    ).join(
        Vehiculo, PaseVehicular.vehiculo_id == Vehiculo.id
    ).join(
        Usuario, PaseVehicular.usuario_id == Usuario.id
    )
    
    # Aplicar filtros
    if fecha_desde:
        query = query.filter(func.date(RegistroAcceso.fecha_hora) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(RegistroAcceso.fecha_hora) <= fecha_hasta)
    if tipo_filtro:
        query = query.filter(RegistroAcceso.tipo == tipo_filtro)
    if placa_filtro:
        query = query.filter(Vehiculo.placa.ilike(f'%{placa_filtro}%'))
    
    registros = query.order_by(RegistroAcceso.fecha_hora.desc()).all()
    
    # Crear CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Cabeceras
    writer.writerow([
        'Fecha/Hora', 'Tipo', 'Estado', 'Placa', 'Marca', 'Modelo', 
        'Propietario', 'Espacio', 'Duración', 'Observaciones'
    ])
    
    # Datos
    for registro in registros:
        writer.writerow([
            registro.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
            registro.tipo.title(),
            registro.estado.title(),
            registro.pase_vehicular.vehiculo.placa,
            registro.pase_vehicular.vehiculo.marca,
            registro.pase_vehicular.vehiculo.modelo,
            registro.pase_vehicular.usuario.nombre,
            registro.espacio_asignado or 'N/A',
            registro.tiempo_estancia_formateado,
            registro.observaciones or ''
        ])
    
    # Preparar respuesta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=registros_accesos_{date.today().strftime("%Y%m%d")}.csv'
    
    return response

@seguridad_bp.route('/registro-accesos/detalle/<int:id>')
@login_required
@security_required
def detalle_registro(id):
    """Obtener detalles de un registro específico"""
    registro = RegistroAcceso.query.get_or_404(id)
    
    # Buscar registro de entrada relacionado si es salida
    registro_entrada = None
    if registro.tipo == 'salida':
        registro_entrada = RegistroAcceso.query.filter_by(
            pase_id=registro.pase_id,
            tipo='entrada',
            estado='permitido'
        ).order_by(RegistroAcceso.fecha_hora.desc()).first()
    
    return jsonify({
        'registro': registro.to_dict(),
        'entrada_relacionada': registro_entrada.to_dict() if registro_entrada else None
    })

@seguridad_bp.route('/validar-codigo', methods=['POST'])
@login_required
@security_required
def validar_codigo():
    """Validar código QR desde formulario"""
    codigo_qr = request.form.get('codigo_qr')
    
    if not codigo_qr:
        flash('Código QR es requerido', 'error')
        return redirect(url_for('seguridad.scanner'))
    
    # Buscar el pase vehicular
    pase = PaseVehicular.query.filter_by(qr_code=codigo_qr).first()
    
    if not pase:
        flash('Código QR no válido', 'error')
        return redirect(url_for('seguridad.scanner'))
    
    if not pase.esta_vigente():
        flash('El pase ha expirado o no está vigente', 'error')
        return redirect(url_for('seguridad.scanner'))
    
    flash(f'Pase válido para {pase.usuario.nombre} - {pase.vehiculo.placa}', 'success')
    return redirect(url_for('seguridad.scanner'))

@seguridad_bp.route('/validar-codigo-ajax', methods=['POST'])
@login_required
@security_required
def validar_codigo_ajax():
    """Validar código QR via AJAX"""
    data = request.get_json()
    codigo = data.get('codigo')
    
    if not codigo:
        return jsonify({'valido': False, 'mensaje': 'Código QR no proporcionado'})
    
    # Buscar el pase vehicular
    pase = PaseVehicular.query.filter_by(qr_code=codigo).first()
    
    if not pase:
        return jsonify({'valido': False, 'mensaje': 'Código QR no válido'})
    
    if not pase.esta_vigente():
        return jsonify({'valido': False, 'mensaje': 'El pase ha expirado o no está vigente'})
    
    # Verificar si ya tiene un estacionamiento asignado
    estacionamiento_actual = Estacionamiento.obtener_por_pase(pase.id)
    
    # Determinar si es entrada o salida
    es_entrada = estacionamiento_actual is None
    
    # Obtener espacios disponibles si es entrada
    espacios_disponibles = []
    if es_entrada:
        espacios_db = Estacionamiento.query.filter_by(estado='disponible').order_by(Estacionamiento.numero).all()
        espacios_disponibles = [{'numero': e.numero, 'id': e.id} for e in espacios_db]
    
    # Información del estacionamiento actual si es salida
    estacionamiento_info = None
    if estacionamiento_actual:
        estacionamiento_info = {
            'numero': estacionamiento_actual.numero,
            'fecha_asignacion': estacionamiento_actual.fecha_asignacion.strftime('%d/%m/%Y %H:%M') if estacionamiento_actual.fecha_asignacion else None
        }
    
    return jsonify({
        'valido': True,
        'pase_id': pase.id,
        'usuario': pase.usuario.nombre,
        'placa': pase.vehiculo.placa,
        'marca': pase.vehiculo.marca,
        'modelo': pase.vehiculo.modelo,
        'tipo': pase.tipo_pase,
        'estado': pase.estado,
        'fecha_fin': pase.fecha_fin.strftime('%d/%m/%Y'),
        'es_entrada': es_entrada,
        'espacios_disponibles': espacios_disponibles,
        'estacionamiento_actual': estacionamiento_info
    })

@seguridad_bp.route('/registrar-acceso', methods=['POST'])
@login_required
@security_required
def registrar_acceso():
    """Registrar acceso"""
    data = request.get_json()
    pase_id = data.get('pase_id')
    permitir = data.get('permitir', True)  # Por defecto permitir acceso
    observaciones = data.get('observaciones', '')
    
    if not pase_id:
        return jsonify({'success': False, 'mensaje': 'ID de pase es requerido'})
    
    try:
        # Crear registro de acceso usando el método del modelo
        acceso = RegistroAcceso.registrar_acceso(
            pase_id=pase_id,
            permitido=permitir,
            usuario_seguridad_id=session.get('user_id'),
            observaciones=observaciones
        )
        
        db.session.commit()
        
        estado_mensaje = 'permitido' if permitir else 'denegado'
        return jsonify({'success': True, 'mensaje': f'Acceso {estado_mensaje} registrado correctamente'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'mensaje': f'Error al registrar acceso: {str(e)}'})

@seguridad_bp.route('/registrar-entrada-con-espacio-especifico', methods=['POST'])
@login_required
@security_required
def registrar_entrada_con_espacio_especifico():
    """Registrar entrada con espacio específico seleccionado"""
    data = request.get_json()
    pase_id = data.get('pase_id')
    espacio_numero = data.get('espacio_numero')
    
    if not pase_id or not espacio_numero:
        return jsonify({'success': False, 'mensaje': 'Faltan datos requeridos'})
    
    try:
        # Verificar que el pase existe
        pase = PaseVehicular.query.get(pase_id)
        if not pase:
            return jsonify({'success': False, 'mensaje': 'Pase no encontrado'})
        
        # Verificar que no tenga ya un estacionamiento asignado
        estacionamiento_actual = Estacionamiento.obtener_por_pase(pase_id)
        if estacionamiento_actual:
            return jsonify({'success': False, 'mensaje': f'El vehículo ya tiene asignado el espacio {estacionamiento_actual.numero}'})
        
        # Obtener el espacio específico
        estacionamiento = Estacionamiento.query.filter_by(numero=espacio_numero).first()
        if not estacionamiento:
            return jsonify({'success': False, 'mensaje': 'Espacio no encontrado'})
        
        if estacionamiento.estado != 'disponible':
            return jsonify({'success': False, 'mensaje': f'El espacio {espacio_numero} no está disponible'})
        
        # Asignar estacionamiento
        if not estacionamiento.asignar(pase_id, f'Asignación manual por entrada - Espacio {espacio_numero}'):
            return jsonify({'success': False, 'mensaje': 'Error al asignar el estacionamiento'})
        
        # Registrar acceso
        acceso = RegistroAcceso.registrar_acceso(
            pase_id=pase_id,
            permitido=True,
            usuario_seguridad_id=session.get('user_id'),
            observaciones=f'Entrada - Espacio {espacio_numero} asignado manualmente'
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'mensaje': 'Entrada registrada y estacionamiento asignado correctamente',
            'espacio_asignado': espacio_numero
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'mensaje': f'Error al procesar entrada: {str(e)}'})

@seguridad_bp.route('/asignar-espacio', methods=['POST'])
@login_required
@security_required
def asignar_espacio():
    """Asignar espacio de estacionamiento"""
    codigo_qr = request.form.get('codigo_qr')
    numero_espacio = request.form.get('numero_espacio')
    
    if not codigo_qr or not numero_espacio:
        flash('Todos los campos son requeridos', 'error')
        return redirect(url_for('seguridad.asignar_estacionamiento'))
    
    # Aquí implementarías la lógica de asignación
    flash(f'Espacio {numero_espacio} asignado correctamente', 'success')
    return redirect(url_for('seguridad.asignar_estacionamiento'))

@seguridad_bp.route('/liberar-espacio', methods=['POST'])
@login_required
@security_required
def liberar_espacio():
    """Liberar espacio de estacionamiento"""
    numero_espacio = request.form.get('numero_espacio')
    
    if not numero_espacio:
        flash('Número de espacio es requerido', 'error')
        return redirect(url_for('seguridad.asignar_estacionamiento'))
    
    # Aquí implementarías la lógica de liberación
    flash(f'Espacio {numero_espacio} liberado correctamente', 'success')
    return redirect(url_for('seguridad.asignar_estacionamiento'))

@seguridad_bp.route('/emergencia')
@login_required
@security_required
def emergencia():
    """Página de gestión de emergencias"""
    # Obtener alertas activas
    alertas_activas = []
    
    # Obtener estadísticas de emergencia
    hoy = date.today()
    accesos_denegados_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.estado == 'denegado'
    ).count()
    
    # Verificar capacidad
    accesos_hoy = RegistroAcceso.query.filter(
        func.date(RegistroAcceso.fecha_hora) == hoy,
        RegistroAcceso.estado == 'permitido'
    ).count()
    
    vehiculos_dentro = max(0, accesos_hoy // 2)
    capacidad_maxima = 50
    porcentaje_ocupacion = (vehiculos_dentro / capacidad_maxima) * 100
    
    # Generar alertas automáticas
    if porcentaje_ocupacion > 90:
        alertas_activas.append({
            'tipo': 'danger',
            'icono': 'exclamation-triangle',
            'titulo': 'Capacidad Crítica',
            'mensaje': f'Estacionamiento al {porcentaje_ocupacion:.1f}% de capacidad',
            'hora': datetime.now().strftime('%H:%M')
        })
    
    if accesos_denegados_hoy > 5:
        alertas_activas.append({
            'tipo': 'warning',
            'icono': 'ban',
            'titulo': 'Múltiples Accesos Denegados',
            'mensaje': f'{accesos_denegados_hoy} accesos denegados hoy',
            'hora': datetime.now().strftime('%H:%M')
        })
    
    # Últimos eventos de seguridad
    eventos_recientes = RegistroAcceso.query.filter(
        RegistroAcceso.estado == 'denegado'
    ).order_by(RegistroAcceso.fecha_hora.desc()).limit(10).all()
    
    return render_template('seguridad/emergencia.html',
                         alertas_activas=alertas_activas,
                         vehiculos_dentro=vehiculos_dentro,
                         capacidad_maxima=capacidad_maxima,
                         porcentaje_ocupacion=porcentaje_ocupacion,
                         accesos_denegados_hoy=accesos_denegados_hoy,
                         eventos_recientes=eventos_recientes)

@seguridad_bp.route('/activar-emergencia', methods=['POST'])
@login_required
@security_required
def activar_emergencia():
    """Activar protocolo de emergencia"""
    tipo_emergencia = request.form.get('tipo_emergencia')
    descripcion = request.form.get('descripcion', '')
    
    # Aquí implementarías la lógica de emergencia
    # Por ejemplo: bloquear accesos, notificar autoridades, etc.
    
    flash(f'Protocolo de emergencia {tipo_emergencia} activado', 'warning')
    return redirect(url_for('seguridad.emergencia'))

@seguridad_bp.route('/desactivar-emergencia', methods=['POST'])
@login_required
@security_required
def desactivar_emergencia():
    """Desactivar protocolo de emergencia"""
    # Aquí implementarías la lógica para desactivar la emergencia
    
    flash('Protocolo de emergencia desactivado', 'success')
    return redirect(url_for('seguridad.emergencia'))

@seguridad_bp.route('/registrar-entrada-con-estacionamiento', methods=['POST'])
@login_required
@security_required
def registrar_entrada_con_estacionamiento():
    """Registrar entrada y asignar estacionamiento automáticamente"""
    data = request.get_json()
    pase_id = data.get('pase_id')
    
    if not pase_id:
        return jsonify({'success': False, 'mensaje': 'ID de pase es requerido'})
    
    try:
        # Verificar que el pase existe
        pase = PaseVehicular.query.get(pase_id)
        if not pase:
            return jsonify({'success': False, 'mensaje': 'Pase no encontrado'})
        
        # Verificar si ya tiene un estacionamiento asignado
        estacionamiento_actual = Estacionamiento.obtener_por_pase(pase_id)
        if estacionamiento_actual:
            return jsonify({'success': False, 'mensaje': f'El vehículo ya tiene asignado el espacio {estacionamiento_actual.numero}'})
        
        # Buscar estacionamiento disponible
        estacionamiento = Estacionamiento.obtener_disponible()
        if not estacionamiento:
            return jsonify({'success': False, 'mensaje': 'No hay espacios de estacionamiento disponibles'})
        
        # Asignar estacionamiento
        if not estacionamiento.asignar(pase_id, 'Asignación automática por entrada'):
            return jsonify({'success': False, 'mensaje': 'Error al asignar el estacionamiento'})
        
        # Registrar acceso
        acceso = RegistroAcceso.registrar_acceso(
            pase_id=pase_id,
            permitido=True,
            usuario_seguridad_id=session.get('user_id'),
            observaciones=f'Entrada - Espacio {estacionamiento.numero} asignado'
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'mensaje': 'Entrada registrada y estacionamiento asignado correctamente',
            'espacio_asignado': estacionamiento.numero
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'mensaje': f'Error al procesar entrada: {str(e)}'})

@seguridad_bp.route('/registrar-salida-con-liberacion', methods=['POST'])
@login_required
@security_required
def registrar_salida_con_liberacion():
    """Registrar salida y liberar estacionamiento automáticamente"""
    data = request.get_json()
    pase_id = data.get('pase_id')
    
    if not pase_id:
        return jsonify({'success': False, 'mensaje': 'ID de pase es requerido'})
    
    try:
        # Verificar que el pase existe
        pase = PaseVehicular.query.get(pase_id)
        if not pase:
            return jsonify({'success': False, 'mensaje': 'Pase no encontrado'})
        
        # Buscar estacionamiento asignado
        estacionamiento = Estacionamiento.obtener_por_pase(pase_id)
        if not estacionamiento:
            return jsonify({'success': False, 'mensaje': 'No se encontró estacionamiento asignado a este vehículo'})
        
        numero_espacio = estacionamiento.numero
        
        # Liberar estacionamiento
        estacionamiento.liberar()
        
        # Registrar acceso
        acceso = RegistroAcceso.registrar_acceso(
            pase_id=pase_id,
            permitido=True,
            usuario_seguridad_id=session.get('user_id'),
            observaciones=f'Salida - Espacio {numero_espacio} liberado'
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'mensaje': 'Salida registrada y estacionamiento liberado correctamente',
            'espacio_liberado': numero_espacio
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'mensaje': f'Error al procesar salida: {str(e)}'})

@seguridad_bp.route('/asignar_estacionamiento')
@login_required
@security_required
def asignar_estacionamiento():
    """Página para asignar estacionamientos"""
    # Verificar si existen estacionamientos, si no crear 8 para MVP
    if Estacionamiento.query.count() == 0:
        for i in range(1, 9):  # Crear espacios 1-8 para MVP
            estacionamiento = Estacionamiento(numero=i)
            db.session.add(estacionamiento)
        db.session.commit()
    
    # Obtener espacios reales de la base de datos (limitado a 8 para MVP)
    espacios_estacionamiento = []
    estacionamientos = Estacionamiento.query.order_by(Estacionamiento.numero).limit(8).all()
    
    for estacionamiento in estacionamientos:
        espacio_info = {
            'numero': estacionamiento.numero,
            'estado': estacionamiento.estado,
            'vehiculo': None
        }
        
        if estacionamiento.estado == 'ocupado' and estacionamiento.pase:
            espacio_info['vehiculo'] = {
                'placa': estacionamiento.pase.vehiculo.placa if estacionamiento.pase.vehiculo else 'N/A',
                'propietario': estacionamiento.pase.usuario.nombre if estacionamiento.pase.usuario else 'N/A'
            }
        
        espacios_estacionamiento.append(espacio_info)
    
    # Crear listas separadas para el template
    espacios_disponibles = [e for e in espacios_estacionamiento if e['estado'] == 'disponible']
    espacios_ocupados = [e for e in espacios_estacionamiento if e['estado'] == 'ocupado']
    espacios_reservados = [e for e in espacios_estacionamiento if e['estado'] == 'reservado']
    
    # Vehículos en espera (ejemplo - puedes implementar la lógica que necesites)
    vehiculos_espera = []
    
    return render_template('seguridad/estacionamiento.html',
                         espacios_estacionamiento=espacios_estacionamiento,
                         espacios_disponibles=espacios_disponibles,  # Pasar lista, no conteo
                         espacios_ocupados=espacios_ocupados,        # Pasar lista, no conteo
                         espacios_reservados=espacios_reservados,    # Pasar lista, no conteo
                         vehiculos_espera=vehiculos_espera)

@seguridad_bp.route('/espacio/<int:numero>/detalles')
@login_required
@security_required
def obtener_detalles_espacio(numero):
    """Obtener detalles de un espacio específico"""
    estacionamiento = Estacionamiento.query.filter_by(numero=numero).first()
    
    if not estacionamiento:
        return jsonify({'success': False, 'mensaje': 'Espacio no encontrado'})
    
    resultado = {
        'success': True,
        'numero': estacionamiento.numero,
        'estado': estacionamiento.estado,
        'vehiculo': None,
        'hora_entrada': None
    }
    
    if estacionamiento.estado == 'ocupado' and estacionamiento.pase:
        resultado['vehiculo'] = {
            'placa': estacionamiento.pase.vehiculo.placa if estacionamiento.pase.vehiculo else 'N/A',
            'propietario': estacionamiento.pase.usuario.nombre if estacionamiento.pase.usuario else 'N/A',
            'marca': estacionamiento.pase.vehiculo.marca if estacionamiento.pase.vehiculo else 'N/A',
            'modelo': estacionamiento.pase.vehiculo.modelo if estacionamiento.pase.vehiculo else 'N/A'
        }
        
        if estacionamiento.fecha_asignacion:
            resultado['hora_entrada'] = estacionamiento.fecha_asignacion.strftime('%d/%m/%Y %H:%M')
    
    return jsonify(resultado)