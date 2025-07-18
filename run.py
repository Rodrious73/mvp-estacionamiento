from app import create_app, db
from app.models import *

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Usuario': Usuario,
        'Vehiculo': Vehiculo,
        'Pertenencia': Pertenencia,
        'CicloAcademico': CicloAcademico,
        'SolicitudPase': SolicitudPase,
        'PaseVehicular': PaseVehicular,
        'UsuarioSeguridad': UsuarioSeguridad,
        'RegistroAcceso': RegistroAcceso
    }

if __name__ == '__main__':
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("Tablas creadas exitosamente!")
    
    app.run(debug=True)
