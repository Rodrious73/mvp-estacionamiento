# app/models/__init__.py
from .usuario import Usuario
from .vehiculo import Vehiculo
from .pertenencia import Pertenencia
from .ciclo_academico import CicloAcademico
from .solicitud_pase import SolicitudPase
from .pase_vehicular import PaseVehicular
from .usuario_seguridad import UsuarioSeguridad
from .registro_acceso import RegistroAcceso

__all__ = [
    'Usuario',
    'Vehiculo', 
    'Pertenencia',
    'CicloAcademico',
    'SolicitudPase',
    'PaseVehicular',
    'UsuarioSeguridad',
    'RegistroAcceso'
]
