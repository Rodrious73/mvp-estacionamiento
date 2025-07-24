from datetime import datetime
import smtplib
import os
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from flask import render_template_string
import codecs
import base64

load_dotenv()

# Función para cargar plantilla HTML como string
def cargar_plantilla_html(ruta_plantilla):
    try:
        with codecs.open(ruta_plantilla, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"❌ Error al cargar la plantilla: {e}")
        return None

# Función para renderizar plantilla con Jinja2
def renderizar_plantilla(plantilla_html, **context):
    """Renderiza una plantilla HTML usando Jinja2"""
    try:
        return render_template_string(plantilla_html, **context)
    except Exception as e:
        print(f"❌ Error al renderizar plantilla: {e}")
        return f"Error renderizando email: {str(e)}"

# Función para envío de bienvenida
def enviar_bienvenida(destinatario_email, destinatario_nombre, link_login=""):
    plantilla_html = cargar_plantilla_html("app/templates/email/bienvenida.html")
    
    if not plantilla_html:
        return False
    
    # Preparar contexto para Jinja2
    context = {
        'nombre': destinatario_nombre,
        'link_login': link_login or "#",
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'tiene_link_login': bool(link_login and link_login.strip())
    }
    
    mensaje_html = renderizar_plantilla(plantilla_html, **context)
    
    return enviar_correo_base(
        destinatario_email=destinatario_email,
        destinatario_nombre=destinatario_nombre,
        asunto="¡Bienvenido al Sistema QR Universitario!",
        mensaje_html=mensaje_html,
        mensaje_texto=f"¡Hola {destinatario_nombre}! Tu cuenta ha sido creada exitosamente en el Sistema QR Universitario. Accede al sistema en: {link_login if link_login else 'Portal web'}"
    )

# Función para envío de asignación de espacio
def enviar_espacio_asignado(destinatario_email, destinatario_nombre, numero_espacio, placa_vehiculo, tipo_pase, fecha_asignacion):
    plantilla_html = cargar_plantilla_html("app/templates/email/asignacion_espacio.html")
    
    if not plantilla_html:
        return False
    
    # Preparar contexto para Jinja2
    context = {
        'nombre': destinatario_nombre,
        'numero_espacio': numero_espacio,
        'placa_vehiculo': placa_vehiculo,
        'tipo_pase': tipo_pase,
        'fecha_asignacion': fecha_asignacion,
        'fecha_actual': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'es_temporal': tipo_pase == 'temporal',
        'es_ciclo': tipo_pase == 'ciclo',
        'tipo_pase_titulo': tipo_pase.title()
    }
    
    mensaje_html = renderizar_plantilla(plantilla_html, **context)
    
    return enviar_correo_base(
        destinatario_email=destinatario_email,
        destinatario_nombre=destinatario_nombre,
        asunto=f"Espacio #{numero_espacio} Asignado - Sistema QR",
        mensaje_html=mensaje_html,
        mensaje_texto=f"""¡Hola {destinatario_nombre}!

Se te ha asignado el espacio #{numero_espacio} para tu vehículo {placa_vehiculo}.

Detalles de la asignación:
- Espacio: #{numero_espacio}
- Vehículo: {placa_vehiculo}
- Tipo de pase: {tipo_pase}
- Fecha de asignación: {fecha_asignacion}

Presenta tu código QR al personal de seguridad para acceder.

Saludos,
Sistema QR Universitario"""
    )

# Función para envío de solicitud aprobada
def enviar_solicitud_aprobada(destinatario_email, destinatario_nombre, **kwargs):
    plantilla_html = cargar_plantilla_html("app/templates/email/solicitud_aprobada.html")
    
    if not plantilla_html:
        return False
    
    # Preparar contexto para Jinja2
    context = {
        'nombre': destinatario_nombre,
        'codigo_qr': kwargs.get('codigo_qr', ''),
        'qr_image_base64': kwargs.get('qr_image_base64', ''),
        'placa_vehiculo': kwargs.get('placa_vehiculo', ''),
        'marca_vehiculo': kwargs.get('marca_vehiculo', 'No especificado'),
        'modelo_vehiculo': kwargs.get('modelo_vehiculo', 'No especificado'),
        'fecha_inicio': kwargs.get('fecha_inicio', ''),
        'fecha_fin': kwargs.get('fecha_fin', ''),
        'tipo_pase': kwargs.get('tipo_pase', ''),
        'id_solicitud': kwargs.get('id_solicitud', ''),
        'link_ver_pase': kwargs.get('link_ver_pase', '#'),
        'link_descargar_qr': kwargs.get('link_descargar_qr', '#'),
        'comentarios_admin': kwargs.get('comentarios_admin', ''),
        # Flags para condicionales
        'tiene_qr_image': bool(kwargs.get('qr_image_base64', '').strip()),
        'tiene_comentarios': bool(kwargs.get('comentarios_admin', '').strip())
    }
    
    mensaje_html = renderizar_plantilla(plantilla_html, **context)
    
    return enviar_correo_base(
        destinatario_email=destinatario_email,
        destinatario_nombre=destinatario_nombre,
        asunto="¡Solicitud Aprobada! - Tu Pase QR está Listo",
        mensaje_html=mensaje_html,
        mensaje_texto=f"¡Hola {destinatario_nombre}! Tu solicitud de pase vehicular ha sido aprobada. Tu código QR: {kwargs.get('codigo_qr', 'No disponible')}."
    )

# Función para envío de visitante aprobado con espacio asignado
def enviar_visitante_aprobado(destinatario_email, destinatario_nombre, **kwargs):
    plantilla_html = cargar_plantilla_html("app/templates/email/solicitud_aprobada_visitante.html")
    
    if not plantilla_html:
        return False
    
    # Preparar contexto para Jinja2
    context = {
        'nombre': destinatario_nombre,
        'numero_espacio': kwargs.get('numero_espacio', 'N/A'),
        'codigo_qr': kwargs.get('codigo_qr', ''),
        'qr_image_base64': kwargs.get('qr_image_base64', ''),
        'placa_vehiculo': kwargs.get('placa_vehiculo', ''),
        'marca_vehiculo': kwargs.get('marca_vehiculo', 'No especificado'),
        'modelo_vehiculo': kwargs.get('modelo_vehiculo', 'No especificado'),
        'color_vehiculo': kwargs.get('color_vehiculo', 'No especificado'),
        'fecha_inicio': kwargs.get('fecha_inicio', ''),
        'fecha_fin': kwargs.get('fecha_fin', ''),
        'duracion_visita': kwargs.get('duracion_visita', ''),
        'tipo_pase': kwargs.get('tipo_pase', ''),
        'id_solicitud': kwargs.get('id_solicitud', ''),
        'link_ver_pase': kwargs.get('link_ver_pase', '#'),
        'link_descargar_qr': kwargs.get('link_descargar_qr', '#'),
        'comentarios_admin': kwargs.get('comentarios_admin', ''),
        # Flags para condicionales
        'tiene_qr_image': bool(kwargs.get('qr_image_base64', '').strip()),
        'tiene_comentarios': bool(kwargs.get('comentarios_admin', '').strip())
    }
    
    mensaje_html = renderizar_plantilla(plantilla_html, **context)
    
    # Crear asunto dinámico
    numero_espacio = kwargs.get('numero_espacio', 'N/A')
    asunto = f"¡Pase de Visitante Aprobado! - Espacio #{numero_espacio} Asignado"
    
    # Mensaje de texto plano
    mensaje_texto = f"""¡Hola {destinatario_nombre}!

Tu pase de visitante ha sido aprobado exitosamente.

Detalles del pase:
- Espacio asignado: #{numero_espacio}
- Vehículo: {kwargs.get('placa_vehiculo', 'N/A')}
- Válido desde: {kwargs.get('fecha_inicio', 'N/A')}
- Válido hasta: {kwargs.get('fecha_fin', 'N/A')}
- Código QR: {kwargs.get('codigo_qr', 'No disponible')}

Presenta tu código QR al personal de seguridad para acceder al campus.

Saludos,
Sistema QR Universitario"""
    
    return enviar_correo_base(
        destinatario_email=destinatario_email,
        destinatario_nombre=destinatario_nombre,
        asunto=asunto,
        mensaje_html=mensaje_html,
        mensaje_texto=mensaje_texto
    )

# Función base para enviar correo (mejorada)
def enviar_correo_base(destinatario_email, destinatario_nombre, asunto, mensaje_html, mensaje_texto):
    email_account = os.getenv("email_account")
    password_account = os.getenv("password_account")
    name_account = os.getenv("name_account", "Sistema QR Universitario")
    
    if not email_account or not password_account:
        print("❌ Error: Credenciales de email no configuradas en .env")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{name_account} <{email_account}>"
    msg['To'] = f"{destinatario_nombre} <{destinatario_email}>"
    msg['Subject'] = asunto
    
    msg.attach(MIMEText(mensaje_texto, 'plain', 'utf-8'))
    msg.attach(MIMEText(mensaje_html, 'html', 'utf-8'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_account, password_account)
            server.sendmail(email_account, destinatario_email, msg.as_string())
            print(f"✅ Correo enviado exitosamente a {destinatario_nombre} ({destinatario_email})")
            return True
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False