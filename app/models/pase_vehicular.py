from app import db
from datetime import datetime, date
import secrets
import qrcode
import io
import base64

class PaseVehicular(db.Model):
    __tablename__ = 'pases_vehiculares'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id', ondelete='CASCADE'), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_academicos.id'), nullable=True)
    tipo_pase = db.Column(db.String(20), nullable=False)  # 'ciclo', 'temporal'
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), default='vigente')  # 'vigente', 'expirado', 'revocado'
    qr_code = db.Column(db.Text, nullable=False)  # Token QR (cifrado o firmado)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    solicitud_pase_id = db.Column(db.Integer, db.ForeignKey('solicitudes_pases.id'), nullable=True)
    espacio_reservado = db.Column(db.Integer, nullable=True)  # Nuevo campo para espacios reservados (visitas)
    
    # Relaciones
    usuario = db.relationship('Usuario', back_populates='pases_vehiculares')
    vehiculo = db.relationship('Vehiculo', back_populates='pases_vehiculares')
    ciclo = db.relationship('CicloAcademico', back_populates='pases_vehiculares')
    solicitud_pase = db.relationship('SolicitudPase', back_populates='pase_vehicular')
    registros_accesos = db.relationship('RegistroAcceso', back_populates='pase', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, usuario_id, vehiculo_id, tipo_pase, fecha_inicio, fecha_fin, ciclo_id=None, espacio_reservado=None):
        self.usuario_id = usuario_id
        self.vehiculo_id = vehiculo_id
        self.ciclo_id = ciclo_id
        self.tipo_pase = tipo_pase
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.espacio_reservado = espacio_reservado
        self.qr_code = self.generar_qr_token()
    
    def generar_qr_token(self):
        """Genera un token único para el QR"""
        # Aquí puedes implementar tu lógica de cifrado/firma
        token = secrets.token_urlsafe(32)
        return f"PASE_{self.tipo_pase.upper()}_{token}"
    
    def generar_qr_image(self):
        """Genera la imagen QR en formato base64"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_code)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def generar_qr_image_email(self):
        """Genera la imagen QR en formato base64"""
        # Crear el objeto QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Agregar los datos del pase
        qr_data = {
            'id': self.id,
            'token': self.qr_code,
            'usuario': self.usuario_id,
            'vehiculo': self.vehiculo_id,
            'valido_hasta': self.fecha_fin.strftime('%Y-%m-%d')
        }
        
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Crear la imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def esta_vigente(self):
        """Verifica si el pase está vigente en la fecha actual"""
        hoy = date.today()
        return (self.estado == 'vigente' and 
                self.fecha_inicio <= hoy <= self.fecha_fin)
    
    def es_pase_temporal(self):
        """Verifica si es un pase temporal (visita)"""
        return self.tipo_pase == 'temporal'
    
    def es_pase_ciclo(self):
        """Verifica si es un pase de ciclo académico"""
        return self.tipo_pase == 'ciclo'
    
    def tiene_espacio_reservado(self):
        """Verifica si tiene un espacio específico reservado"""
        return self.espacio_reservado is not None
    
    def revocar(self):
        """Revoca el pase"""
        self.estado = 'revocado'
    
    def marcar_expirado(self):
        """Marca el pase como expirado"""
        self.estado = 'expirado'
    
    def obtener_estacionamiento_reservado(self):
        """Obtiene el estacionamiento reservado/ocupado para este pase"""
        from .estacionamiento import Estacionamiento
        return Estacionamiento.query.filter_by(pase_id=self.id).filter(
            Estacionamiento.estado.in_(['ocupado', 'reservado'])
        ).first()
    
    def tiene_estacionamiento_asignado(self):
        """Verifica si tiene un estacionamiento asignado"""
        return self.obtener_estacionamiento_reservado() is not None
    
    def __repr__(self):
        return f'<PaseVehicular {self.tipo_pase} - {self.estado}>'
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'vehiculo_id': self.vehiculo_id,
            'ciclo_id': self.ciclo_id,
            'tipo_pase': self.tipo_pase,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'estado': self.estado,
            'qr_code': self.qr_code,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'esta_vigente': self.esta_vigente(),
            'espacio_reservado': self.espacio_reservado
        }