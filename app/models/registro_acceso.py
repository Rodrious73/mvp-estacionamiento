from app import db
from datetime import datetime

class RegistroAcceso(db.Model):
    __tablename__ = 'registros_accesos'
    
    id = db.Column(db.Integer, primary_key=True)
    pase_id = db.Column(db.Integer, db.ForeignKey('pases_vehiculares.id', ondelete='CASCADE'), nullable=False)
    usuario_seguridad_id = db.Column(db.Integer, db.ForeignKey('usuarios_seguridad.id'), nullable=True)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False)  # 'permitido', 'denegado'
    tipo = db.Column(db.String(10))
    observaciones = db.Column(db.String(255))
    
    # Relaciones
    pase = db.relationship('PaseVehicular', back_populates='registros_accesos')
    usuario_seguridad = db.relationship('UsuarioSeguridad', back_populates='registros_accesos')

    def __init__(self, pase_id, estado, tipo=None, usuario_seguridad_id=None, observaciones=None):
        self.pase_id = pase_id
        self.usuario_seguridad_id = usuario_seguridad_id
        self.estado = estado
        self.tipo = tipo
        self.observaciones = observaciones
    
    def __repr__(self):
        return f'<RegistroAcceso {self.estado} - {self.fecha_hora}>'
    
    @classmethod
    def registrar_acceso(cls, pase_id, permitido, usuario_seguridad_id=None, observaciones=None):
        """Método de clase para registrar un nuevo acceso"""
        estado = 'permitido' if permitido else 'denegado'
        registro = cls(
            pase_id=pase_id,
            estado=estado,
            usuario_seguridad_id=usuario_seguridad_id,
            observaciones=observaciones
        )
        db.session.add(registro)
        return registro
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'pase_id': self.pase_id,
            'usuario_seguridad_id': self.usuario_seguridad_id,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None,
            'estado': self.estado,
            'tipo': self.tipo,
            'observaciones': self.observaciones
        }
