from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class UsuarioSeguridad(db.Model):
    __tablename__ = 'usuarios_seguridad'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)  # Hasheada
    
    # Relaciones
    registros_accesos = db.relationship('RegistroAcceso', back_populates='usuario_seguridad', lazy=True)
    
    def __init__(self, nombre, usuario, contraseña):
        self.nombre = nombre
        self.usuario = usuario
        self.set_password(contraseña)
    
    def set_password(self, contraseña):
        """Hashea y guarda la contraseña"""
        self.contraseña = generate_password_hash(contraseña)
    
    def check_password(self, contraseña):
        """Verifica si la contraseña proporcionada es correcta"""
        return check_password_hash(self.contraseña, contraseña)
    
    def __repr__(self):
        return f'<UsuarioSeguridad {self.nombre} - {self.usuario}>'
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'usuario': self.usuario
            # No incluimos la contraseña por seguridad
        }
