from app import db
from datetime import datetime

class Pertenencia(db.Model):
    __tablename__ = 'pertenencias'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    propietario = db.relationship('Usuario', back_populates='pertenencias')
    
    def __init__(self, usuario_id, descripcion):
        self.usuario_id = usuario_id
        self.descripcion = descripcion
    
    def __repr__(self):
        return f'<Pertenencia {self.descripcion}>'
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'descripcion': self.descripcion,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }
