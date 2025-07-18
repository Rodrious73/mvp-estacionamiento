from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    codigo_universitario = db.Column(db.String(20), nullable=True)  # Solo para estudiantes/docentes
    dni = db.Column(db.String(15), nullable=False, unique=True)
    email = db.Column(db.String(100), unique=True)
    telefono = db.Column(db.String(20))
    rol = db.Column(db.String(20), nullable=False)  # 'estudiante', 'docente', 'visita', 'administrador'
    contraseña = db.Column(db.String(255), nullable=False)  # Hasheada
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    vehiculos = db.relationship('Vehiculo', back_populates='propietario', lazy=True, cascade='all, delete-orphan')
    pertenencias = db.relationship('Pertenencia', back_populates='propietario', lazy=True, cascade='all, delete-orphan')
    solicitudes_pases = db.relationship('SolicitudPase', back_populates='usuario', lazy=True, cascade='all, delete-orphan')
    pases_vehiculares = db.relationship('PaseVehicular', back_populates='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, nombre, dni, rol, contraseña, codigo_universitario=None, email=None, telefono=None):
        self.nombre = nombre
        self.codigo_universitario = codigo_universitario
        self.dni = dni
        self.email = email
        self.telefono = telefono
        self.rol = rol
        self.set_password(contraseña)
    
    def set_password(self, contraseña):
        """Hashea y guarda la contraseña"""
        self.contraseña = generate_password_hash(contraseña)
    
    def check_password(self, contraseña):
        """Verifica si la contraseña proporcionada es correcta"""
        return check_password_hash(self.contraseña, contraseña)
    
    def __repr__(self):
        return f'<Usuario {self.nombre} - {self.rol}>'
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'codigo_universitario': self.codigo_universitario,
            'dni': self.dni,
            'email': self.email,
            'telefono': self.telefono,
            'rol': self.rol,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }
