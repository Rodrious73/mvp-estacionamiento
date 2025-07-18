import os
from dotenv import load_dotenv
from datetime import timedelta
# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    #Configuracion segura de cookies
    SESSION_COOKIE_HTTPONLY = True        #Protege contra Javascript malicioso (XSS)
    SESSION_COOKIE_SECURE = False         # CAMBIAR A TRUE en produccion con HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'       #Previene ataques CSRF basicos

    #Tiempo de expiracion de la sesion
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  #Expira tras 30 minutos de inactividad

    #Configuración para Google Maps
    GOOGLEMAPS_KEY = os.getenv('GOOGLEMAPS_KEY')

    # Configuración de Flask-Mail (Mailtrap)
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Configuración para manejo de archivos
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB máximo por request
    
    # Configuraciones de archivos
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB por imagen
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB por documento
    
    # Configuraciones de thumbnails
    THUMBNAIL_SIZES = {
        'small': (150, 150),
        'medium': (400, 300),
        'large': (800, 600)
    }
    
    # URL base para servir archivos
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
    
    # Límites de almacenamiento por plan
    STORAGE_LIMITS = {
        'free': 100 * 1024 * 1024,      # 100MB
        'basic': 500 * 1024 * 1024,     # 500MB
        'premium': 2 * 1024 * 1024 * 1024,  # 2GB
        'unlimited': -1  # Sin límite
    }
