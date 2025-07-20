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
    
    def reservar(self, pase_id, observaciones=None):
        """Reservar el estacionamiento para un pase específico"""
        if self.estado != 'disponible':
            return False
        
        self.estado = 'reservado'
        self.pase_id = pase_id
        self.fecha_asignacion = datetime.now()
        self.observaciones = observaciones
        return True
    
    def confirmar_reserva(self, pase_id):
        """Confirmar la reserva y ocupar el espacio"""
        if self.estado != 'reservado' or self.pase_id != pase_id:
            return False
        
        self.estado = 'ocupado'
        self.fecha_asignacion = datetime.now()
        return True
    
    def liberar(self):
        """Liberar el estacionamiento"""
        self.estado = 'disponible'
        self.pase_id = None
        self.fecha_asignacion = None
        self.observaciones = None

    def liberar_temporal(self):
        """Liberar temporalmente (volver a reservado para pases temporales)"""
        self.estado = 'reservado'
        # Mantener pase_id y fecha_asignacion para preservar la reserva
        self.observaciones = f'Salida temporal - Reserva mantenida hasta vencimiento'
    
    def liberar_segun_tipo_pase(self):
        """Liberar el estacionamiento según el tipo de pase"""
        if self.pase and self.pase.es_pase_temporal() and self.pase.esta_vigente():
            # Si es pase temporal y aún está vigente, mantener reservado
            self.liberar_temporal()
            return 'reservado'
        else:
            # Para pases de ciclo o pases vencidos, liberar completamente
            self.liberar()
            return 'disponible'

    def esta_reservado_para(self, pase_id):
        """Verificar si está reservado para un pase específico"""
        return self.estado == 'reservado' and self.pase_id == pase_id
    
    def puede_regresar_hoy(self):
        """Verifica si el pase temporal puede regresar el mismo día"""
        return self.es_pase_temporal() and self.esta_vigente()

    def necesita_mantener_reserva(self):
        """Verifica si debe mantener la reserva del espacio al salir"""
        return self.es_pase_temporal() and self.esta_vigente()

    @classmethod
    def obtener_disponible(cls):
        """Obtener el primer estacionamiento disponible"""
        return cls.query.filter_by(estado='disponible').first()
    
    @classmethod
    def obtener_por_pase(cls, pase_id):
        """Obtener estacionamiento asignado a un pase (ocupado o reservado)"""
        return cls.query.filter_by(pase_id=pase_id).filter(
            cls.estado.in_(['ocupado', 'reservado'])
        ).first()
    
    @classmethod
    def obtener_ocupado_por_pase(cls, pase_id):
        """Obtener estacionamiento ocupado por un pase específico"""
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