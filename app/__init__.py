from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

limiter = Limiter(get_remote_address)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    limiter.init_app(app)
    db.init_app(app)

    # Importar y registrar los Blueprints
    from app.routes.index import index_bp
    app.register_blueprint(index_bp)

    from app.routes.prueba import prueba_bp
    app.register_blueprint(prueba_bp)
     
    from app.routes.auth import auth
    app.register_blueprint(auth)

    from app.routes.api.escuelas import api_bp
    app.register_blueprint(api_bp)
    
    # Blueprints para diferentes tipos de usuarios
    from app.routes.estudiante import estudiante_bp
    app.register_blueprint(estudiante_bp)
    
    from app.routes.docente import docente_bp
    app.register_blueprint(docente_bp)
    
    from app.routes.visitante import visitante_bp
    app.register_blueprint(visitante_bp)
    
    from app.routes.seguridad import seguridad_bp
    app.register_blueprint(seguridad_bp)
    
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    # Context processor para hacer current_user disponible en todos los templates
    @app.context_processor
    def inject_current_user():
        from app.utils.auth_utils import get_current_user
        from datetime import datetime, date
        return dict(current_user=get_current_user(), now=datetime.now, date=date)
    
    return app
