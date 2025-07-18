from app import db
from datetime import datetime

class SolicitudPase(db.Model):
    __tablename__ = 'solicitudes_pases'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id', ondelete='CASCADE'), nullable=False)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_academicos.id'), nullable=True)
    tipo_pase = db.Column(db.String(20), nullable=False)  # 'ciclo', 'temporal'
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='pendiente')  # 'pendiente', 'aprobado', 'rechazado', 'cancelado'
    comentarios_admin = db.Column(db.String(255))
    fecha_revision = db.Column(db.DateTime)
    fecha_reservacion_inicio = db.Column(db.Date, nullable=True)
    fecha_reservacion_fin = db.Column(db.Date, nullable=True)
    
    # Relaciones
    usuario = db.relationship('Usuario', back_populates='solicitudes_pases')
    vehiculo = db.relationship('Vehiculo', back_populates='solicitudes_pases')
    ciclo = db.relationship('CicloAcademico', back_populates='solicitudes_pases')
    pase_vehicular = db.relationship('PaseVehicular', back_populates='solicitud_pase', uselist=False)
    
    def __init__(self, usuario_id, vehiculo_id, tipo_pase, ciclo_id=None):
        self.usuario_id = usuario_id
        self.vehiculo_id = vehiculo_id
        self.ciclo_id = ciclo_id
        self.tipo_pase = tipo_pase
    
    def __repr__(self):
        return f'<SolicitudPase {self.tipo_pase} - {self.estado}>'
    
    def aprobar(self, comentarios_admin=None):
        """Aprueba la solicitud"""
        self.estado = 'aprobado'
        self.comentarios_admin = comentarios_admin
        self.fecha_revision = datetime.utcnow()
    
    def rechazar(self, comentarios_admin):
        """Rechaza la solicitud"""
        self.estado = 'rechazado'
        self.comentarios_admin = comentarios_admin
        self.fecha_revision = datetime.utcnow()
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'vehiculo_id': self.vehiculo_id,
            'ciclo_id': self.ciclo_id,
            'tipo_pase': self.tipo_pase,
            'fecha_solicitud': self.fecha_solicitud.isoformat() if self.fecha_solicitud else None,
            'estado': self.estado,
            'comentarios_admin': self.comentarios_admin,
            'fecha_reservacion_inicio': self.fecha_reservacion_inicio.isoformat() if self.fecha_reservacion_inicio else None,
            'fecha_reservacion_fin': self.fecha_reservacion_fin.isoformat() if self.fecha_reservacion_fin else None,
            'fecha_revision': self.fecha_revision.isoformat() if self.fecha_revision else None
        }
