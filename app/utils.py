"""
Utilidades para trabajar con los modelos del sistema de estacionamientos
"""
from app.models import *
from app import db
from datetime import date, timedelta
import secrets
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user

def admin_required(f):
    """Decorador para requerir permisos de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function

class UsuarioService:
    @staticmethod
    def crear_usuario(nombre, dni, rol, contraseña, **kwargs):
        """Crea un nuevo usuario en el sistema"""
        usuario = Usuario(
            nombre=nombre,
            dni=dni,
            rol=rol,
            contraseña=contraseña,
            **kwargs
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario
    
    @staticmethod
    def autenticar(dni, contraseña):
        """Autentica un usuario por DNI y contraseña"""
        usuario = Usuario.query.filter_by(dni=dni).first()
        if usuario and usuario.check_password(contraseña):
            return usuario
        return None

class VehiculoService:
    @staticmethod
    def registrar_vehiculo(usuario_id, placa, **kwargs):
        """Registra un nuevo vehículo para un usuario"""
        vehiculo = Vehiculo(
            usuario_id=usuario_id,
            placa=placa,
            **kwargs
        )
        db.session.add(vehiculo)
        db.session.commit()
        return vehiculo

class PaseService:
    @staticmethod
    def solicitar_pase(usuario_id, vehiculo_id, tipo_pase, ciclo_id=None):
        """Crea una nueva solicitud de pase"""
        solicitud = SolicitudPase(
            usuario_id=usuario_id,
            vehiculo_id=vehiculo_id,
            tipo_pase=tipo_pase,
            ciclo_id=ciclo_id
        )
        db.session.add(solicitud)
        db.session.commit()
        return solicitud
    
    @staticmethod
    def aprobar_solicitud(solicitud_id, comentarios=None):
        """Aprueba una solicitud y genera el pase vehicular"""
        solicitud = SolicitudPase.query.get(solicitud_id)
        if not solicitud or solicitud.estado != 'pendiente':
            return None
        
        # Aprobar solicitud
        solicitud.aprobar(comentarios)
        
        # Determinar fechas del pase
        if solicitud.tipo_pase == 'ciclo' and solicitud.ciclo_id:
            ciclo = CicloAcademico.query.get(solicitud.ciclo_id)
            fecha_inicio = ciclo.fecha_inicio
            fecha_fin = ciclo.fecha_fin
        else:  # temporal
            fecha_inicio = date.today()
            fecha_fin = fecha_inicio + timedelta(days=30)  # 30 días por defecto
        
        # Crear pase vehicular
        pase = PaseVehicular(
            usuario_id=solicitud.usuario_id,
            vehiculo_id=solicitud.vehiculo_id,
            ciclo_id=solicitud.ciclo_id,
            tipo_pase=solicitud.tipo_pase,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        db.session.add(pase)
        db.session.commit()
        return pase
    
    @staticmethod
    def verificar_qr(qr_code):
        """Verifica si un código QR es válido y está vigente"""
        pase = PaseVehicular.query.filter_by(qr_code=qr_code).first()
        if not pase:
            return {'valido': False, 'mensaje': 'Código QR no encontrado'}
        
        if not pase.esta_vigente():
            return {'valido': False, 'mensaje': 'Pase expirado o revocado'}
        
        return {
            'valido': True,
            'pase': pase,
            'usuario': pase.usuario,
            'vehiculo': pase.vehiculo
        }

class AccesoService:
    @staticmethod
    def registrar_escaneo(qr_code, usuario_seguridad_id=None):
        """Registra un escaneo de QR y determina si el acceso es permitido"""
        verificacion = PaseService.verificar_qr(qr_code)
        
        if not verificacion['valido']:
            # Registrar acceso denegado
            # Nota: No podemos registrar si no existe el pase
            return {
                'permitido': False,
                'mensaje': verificacion['mensaje']
            }
        
        pase = verificacion['pase']
        
        # Registrar acceso permitido
        registro = RegistroAcceso.registrar_acceso(
            pase_id=pase.id,
            permitido=True,
            usuario_seguridad_id=usuario_seguridad_id,
            observaciones='Acceso autorizado'
        )
        
        db.session.commit()
        
        return {
            'permitido': True,
            'mensaje': 'Acceso autorizado',
            'usuario': pase.usuario.nombre,
            'vehiculo': pase.vehiculo.placa,
            'tipo_pase': pase.tipo_pase
        }

class CicloService:
    @staticmethod
    def crear_ciclo(nombre, fecha_inicio, fecha_fin):
        """Crea un nuevo ciclo académico"""
        ciclo = CicloAcademico(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        db.session.add(ciclo)
        db.session.commit()
        return ciclo
    
    @staticmethod
    def activar_ciclo(ciclo_id):
        """Activa un ciclo académico específico"""
        ciclo = CicloAcademico.query.get(ciclo_id)
        if ciclo:
            ciclo.activar()
            return ciclo
        return None
