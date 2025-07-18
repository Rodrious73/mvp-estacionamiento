from app import db
from datetime import datetime

class CicloAcademico(db.Model):
    __tablename__ = 'ciclos_academicos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)  # Ej: "2025-I", "2025-II"
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), default='inactivo')  # 'activo', 'inactivo'
    
    # Relaciones
    solicitudes_pases = db.relationship('SolicitudPase', back_populates='ciclo', lazy=True)
    pases_vehiculares = db.relationship('PaseVehicular', back_populates='ciclo', lazy=True)
    
    def __init__(self, nombre, fecha_inicio, fecha_fin, estado='inactivo'):
        self.nombre = nombre
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.estado = estado
    
    def __repr__(self):
        return f'<CicloAcademico {self.nombre} - {self.estado}>'
    
    @classmethod
    def get_ciclo_activo(cls):
        """Obtiene el ciclo académico activo actual"""
        return cls.query.filter_by(estado='activo').first()
    
    def activar(self):
        """Activa este ciclo y desactiva todos los demás"""
        # Desactivar todos los ciclos
        CicloAcademico.query.update({'estado': 'inactivo'})
        # Activar este ciclo
        self.estado = 'activo'
        db.session.commit()
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'estado': self.estado
        }
