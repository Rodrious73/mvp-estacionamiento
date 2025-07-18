from app import db
from datetime import datetime

class Estacionamiento(db.Model):
    __tablename__ = 'estacionamientos'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    estado = db.Column(db.String(20), default='disponible')  # 'disponible', 'ocupado', 'reservado', 'mantenimiento'
    pase_id = db.Column(db.Integer, db.ForeignKey('pases_vehiculares.id'), nullable=True)
    fecha_asignacion = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.String(255))
    
    # Relaciones
    pase = db.relationship('PaseVehicular', backref='estacionamiento_actual')
    
    def __init__(self, numero):
        self.numero = numero
        self.estado = 'disponible'
    
    def asignar(self, pase_id, observaciones=None):
        """Asignar el estacionamiento a un pase"""
        if self.estado != 'disponible':
            return False
        
        self.estado = 'ocupado'
        self.pase_id = pase_id
        self.fecha_asignacion = datetime.now()
        self.observaciones = observaciones
        return True
    
    def liberar(self):
        """Liberar el estacionamiento"""
        self.estado = 'disponible'
        self.pase_id = None
        self.fecha_asignacion = None
        self.observaciones = None
    
    @classmethod
    def obtener_disponible(cls):
        """Obtener el primer estacionamiento disponible"""
        return cls.query.filter_by(estado='disponible').first()
    
    @classmethod
    def obtener_por_pase(cls, pase_id):
        """Obtener estacionamiento asignado a un pase"""
        return cls.query.filter_by(pase_id=pase_id, estado='ocupado').first()
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'estado': self.estado,
            'pase_id': self.pase_id,
            'fecha_asignacion': self.fecha_asignacion.isoformat() if self.fecha_asignacion else None,
            'observaciones': self.observaciones
        }