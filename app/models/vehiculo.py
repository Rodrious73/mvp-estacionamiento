from app import db
from datetime import datetime

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    placa = db.Column(db.String(20), nullable=False, unique=True)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    color = db.Column(db.String(30))
    tipo = db.Column(db.String(30))
    year = db.Column(db.Integer) 
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    propietario = db.relationship('Usuario', back_populates='vehiculos')
    solicitudes_pases = db.relationship('SolicitudPase', back_populates='vehiculo', lazy=True, cascade='all, delete-orphan')
    pases_vehiculares = db.relationship('PaseVehicular', back_populates='vehiculo', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, usuario_id, placa, marca=None, modelo=None, color=None, tipo=None, year=None):
        self.usuario_id = usuario_id
        self.placa = placa.upper()  # Guardamos la placa en mayúsculas
        self.marca = marca
        self.modelo = modelo
        self.color = color
        self.tipo = tipo
        self.year = year
    
    def __repr__(self):
        return f'<Vehiculo {self.placa} - {self.marca} {self.modelo}>'
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'placa': self.placa,
            'marca': self.marca,
            'modelo': self.modelo,
            'color': self.color,
            'tipo': self.tipo,
            'year': self.year,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }
