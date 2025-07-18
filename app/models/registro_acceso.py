from app import db
from datetime import datetime

class RegistroAcceso(db.Model):
    __tablename__ = 'registros_accesos'
    
    id = db.Column(db.Integer, primary_key=True)
    pase_id = db.Column(db.Integer, db.ForeignKey('pases_vehiculares.id', ondelete='CASCADE'), nullable=False)
    usuario_seguridad_id = db.Column(db.Integer, db.ForeignKey('usuarios_seguridad.id'), nullable=True)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False)  # 'permitido', 'denegado'
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada', 'salida'
    espacio_asignado = db.Column(db.Integer, nullable=True)  # Número de espacio asignado
    duracion_estancia = db.Column(db.Integer, nullable=True)  # Duración en minutos
    observaciones = db.Column(db.String(255))
    
    # Relaciones
    pase = db.relationship('PaseVehicular', back_populates='registros_accesos')
    usuario_seguridad = db.relationship('UsuarioSeguridad', back_populates='registros_accesos')

    def __init__(self, pase_id, estado, tipo, usuario_seguridad_id=None, espacio_asignado=None, observaciones=None):
        self.pase_id = pase_id
        self.usuario_seguridad_id = usuario_seguridad_id
        self.estado = estado
        self.tipo = tipo
        self.espacio_asignado = espacio_asignado
        self.observaciones = observaciones
    
    def __repr__(self):
        return f'<RegistroAcceso {self.estado} - {self.tipo} - {self.fecha_hora}>'
    
    @classmethod
    def registrar_acceso(cls, pase_id, tipo, permitido=True, usuario_seguridad_id=None, espacio_asignado=None, observaciones=None):
        """Método mejorado para registrar accesos"""
        estado = 'permitido' if permitido else 'denegado'
        
        # Calcular duración si es salida
        duracion_estancia = None
        if tipo == 'salida' and permitido:
            entrada = cls.query.filter_by(
                pase_id=pase_id,
                tipo='entrada',
                estado='permitido'
            ).order_by(cls.fecha_hora.desc()).first()
            
            if entrada:
                duracion_estancia = int((datetime.utcnow() - entrada.fecha_hora).total_seconds() / 60)
        
        registro = cls(
            pase_id=pase_id,
            estado=estado,
            tipo=tipo,
            usuario_seguridad_id=usuario_seguridad_id,
            espacio_asignado=espacio_asignado,
            observaciones=observaciones
        )
        registro.duracion_estancia = duracion_estancia
        
        db.session.add(registro)
        return registro
    
    @property
    def tiempo_estancia_formateado(self):
        """Formatea la duración de estancia de manera legible"""
        if not self.duracion_estancia:
            return "N/A"
        
        horas = self.duracion_estancia // 60
        minutos = self.duracion_estancia % 60
        
        if horas > 0:
            return f"{horas}h {minutos}m"
        return f"{minutos}m"
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'id': self.id,
            'pase_id': self.pase_id,
            'usuario_seguridad_id': self.usuario_seguridad_id,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None,
            'estado': self.estado,
            'tipo': self.tipo,
            'espacio_asignado': self.espacio_asignado,
            'duracion_estancia': self.duracion_estancia,
            'observaciones': self.observaciones,
            'vehiculo': {
                'placa': self.pase_vehicular.vehiculo.placa if self.pase_vehicular and self.pase_vehicular.vehiculo else None,
                'marca': self.pase_vehicular.vehiculo.marca if self.pase_vehicular and self.pase_vehicular.vehiculo else None,
                'modelo': self.pase_vehicular.vehiculo.modelo if self.pase_vehicular and self.pase_vehicular.vehiculo else None
            }
        }
