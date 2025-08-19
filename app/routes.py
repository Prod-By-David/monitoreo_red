from flask import Blueprint, render_template, request, abort, Response, make_response, redirect, url_for, jsonify, flash, send_file, session
from app.monitor import (
    escanear_red_y_guardar, iniciar_escaneo_automatico, detener_escaneo_automatico, estado_escaneo)
from app.db import (
    conectar, obtener_historico_escaneos, obtener_historico_por_ip, obtener_alertas, obtener_historial_dispositivos, bloquear_ip, desbloquear_ip, obtener_ips_bloqueadas, obtener_actividad_por_ip)
import csv
from io import StringIO
import ipaddress
import locale
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import pdfkit
from functools import wraps

main = Blueprint('main', __name__)

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain')
    except:
        locale.setlocale(locale.LC_TIME, '')

# ✅ Decorador para proteger rutas
def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debes iniciar sesión para continuar.', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    return redirect(url_for('main.login'))

# ✅ Ruta de login
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        clave = request.form['password']

        conexion = conectar()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (usuario, clave))
        user = cursor.fetchone()
        cursor.close()
        conexion.close()

        if user:
            session['usuario'] = user['username']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')

    return render_template('login.html')

# ✅ Ruta de logout
@main.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('main.login'))

@main.route('/dashboard')
@login_requerido
def dashboard():
    filtro = request.args.get('filtro', 'todos')
    dispositivos = escanear_red_y_guardar()

    if filtro == 'online':
        dispositivos = [d for d in dispositivos if d.get('online')]
    elif filtro == 'offline':
        dispositivos = [d for d in dispositivos if not d.get('online')]

    alertas = obtener_alertas()
    return render_template(
        'dashboard.html',
        dispositivos=dispositivos,
        filtro=filtro,
        alertas=alertas,
        escaneo_activo=estado_escaneo())

@main.route('/historico')
@login_requerido
def historico():
    datos = obtener_historico_escaneos()
    return render_template('historico.html', datos=datos)

@main.route('/dispositivo/<ip>')
@login_requerido
def dispositivo_detalle(ip):
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        abort(404)

    historico = obtener_historico_por_ip(ip)
    historico.sort(key=lambda x: x['fecha_escaneo'])

    datos_formateados = []
    for fila in historico:
        fila['fecha_escaneo_formateada'] = fila['fecha_escaneo'].strftime('%d de %B de %Y a las %H:%M')
        datos_formateados.append({
            'fecha': fila['fecha_escaneo'].strftime('%Y-%m-%d %H:%M'),
            'puerto': fila['puerto']})

    primer = historico[0]['fecha_escaneo_formateada'] if historico else "N/A"
    ultimo = historico[-1]['fecha_escaneo_formateada'] if historico else "N/A"

    return render_template('dispositivo_detalle.html', ip=ip, datos=historico, primer=primer, ultimo=ultimo, datos_grafico=datos_formateados)

@main.route('/exportar/csv')
@login_requerido
def exportar_csv():
    datos = obtener_historico_escaneos()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['IP', 'Puerto', 'Fecha'])

    for fila in datos:
        writer.writerow([fila['ip'], fila['puerto'], fila['fecha_escaneo']])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=historico_red.csv"})

@main.route('/exportar/pdf')
@login_requerido
def exportar_pdf():
    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    datos = obtener_historico_escaneos()
    html = render_template('exportar_pdf.html', datos=datos)
    pdf = pdfkit.from_string(html, False, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=historico_red.pdf'
    return response

@main.route('/historial')
@login_requerido
def ver_historial():
    historial = obtener_historial_dispositivos()
    return render_template('historial.html', historial=historial)

@main.route('/toggle-escaneo', methods=['POST'])
@login_requerido
def toggle_escaneo():
    if estado_escaneo():
        detener_escaneo_automatico()
    else:
        iniciar_escaneo_automatico()
    return jsonify({'status': 'ok', 'escaneo_activo': estado_escaneo()})

@main.route('/bloquear_ip', methods=['POST'])
@login_requerido
def route_bloquear_ip():
    ip = request.form.get('ip')
    if not ip:
        return jsonify({'error': 'IP no especificada'}), 400
    if bloquear_ip(ip):
        return jsonify({'status': 'IP bloqueada'})
    else:
        return jsonify({'error': 'Error al bloquear IP'}), 500

@main.route('/desbloquear_ip', methods=['POST'])
@login_requerido
def route_desbloquear_ip():
    ip = request.form.get('ip')
    if not ip:
        return jsonify({'error': 'IP no especificada'}), 400
    if desbloquear_ip(ip):
        return jsonify({'status': 'IP desbloqueada'})
    else:
        return jsonify({'error': 'Error al desbloquear IP'}), 500

@main.route('/ips_bloqueadas')
@login_requerido
def route_ips_bloqueadas():
    ips = obtener_ips_bloqueadas()
    return jsonify({'ips_bloqueadas': ips})

@main.route('/actividad_json/<ip>')
@login_requerido
def actividad_json(ip):
    datos = obtener_actividad_por_ip(ip)
    return jsonify([d['timestamp'].strftime('%Y-%m-%d %H:%M:%S') for d in datos])

def extension_permitida(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/capturas', methods=['GET', 'POST'])
@login_requerido
def capturas():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    if request.method == 'POST':
        archivo = request.files.get('imagen')
        descripcion = request.form.get('descripcion', '')

        if archivo and extension_permitida(archivo.filename):
            nombre_seguro = secure_filename(archivo.filename)
            ruta_completa = os.path.join(UPLOAD_FOLDER, nombre_seguro)
            archivo.save(ruta_completa)

            cursor.execute(
                "INSERT INTO capturas (nombre_archivo, descripcion) VALUES (%s, %s)",
                (nombre_seguro, descripcion))
            conexion.commit()
        return redirect(url_for('main.capturas'))

    cursor.execute("SELECT * FROM capturas ORDER BY fecha_subida DESC")
    imagenes = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template('capturas.html', imagenes=imagenes)

@main.route('/capturas/editar/<int:id>', methods=['POST'])
@login_requerido
def editar_captura(id):
    descripcion = request.form.get('descripcion')
    nueva_imagen = request.files.get('nueva_imagen')

    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT nombre_archivo FROM capturas WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    if not resultado:
        return "No encontrada", 404

    nombre_actual = resultado['nombre_archivo']

    if nueva_imagen and extension_permitida(nueva_imagen.filename):
        nuevo_nombre = secure_filename(nueva_imagen.filename)
        nueva_imagen.save(os.path.join(UPLOAD_FOLDER, nuevo_nombre))
        if nombre_actual and os.path.exists(os.path.join(UPLOAD_FOLDER, nombre_actual)):
            os.remove(os.path.join(UPLOAD_FOLDER, nombre_actual))
        cursor.execute("UPDATE capturas SET nombre_archivo = %s, descripcion = %s WHERE id = %s", (nuevo_nombre, descripcion, id))
    else:
        cursor.execute("UPDATE capturas SET descripcion = %s WHERE id = %s", (descripcion, id))

    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for('main.capturas'))

@main.route('/capturas/eliminar/<int:id>', methods=['POST'])
@login_requerido
def eliminar_captura(id):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT nombre_archivo FROM capturas WHERE id = %s", (id,))
    resultado = cursor.fetchone()

    if resultado:
        nombre_archivo = resultado['nombre_archivo']
        ruta_archivo = os.path.join(UPLOAD_FOLDER, nombre_archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
        cursor.execute("DELETE FROM capturas WHERE id = %s", (id,))
        conexion.commit()

    cursor.close()
    conexion.close()
    return redirect(url_for('main.capturas'))

@main.route('/anotaciones', methods=['GET', 'POST'])
@login_requerido
def anotaciones():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            cursor.execute(
                "INSERT INTO anotaciones (contenido) VALUES (%s)",
                (contenido,))
            conexion.commit()
            flash('Anotación creada correctamente.', 'success')
        else:
            flash('No puedes enviar una anotación vacía.', 'warning')
        cursor.close()
        conexion.close()
        return redirect(url_for('main.anotaciones'))

    cursor.execute("SELECT * FROM anotaciones ORDER BY fecha_creacion DESC")
    notas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template('anotaciones.html', notas=notas)

@main.route('/anotaciones/<int:id>/editar', methods=['POST'])
@login_requerido
def editar_anotacion(id):
    nuevo_contenido = request.form.get('contenido', '').strip()
    if not nuevo_contenido:
        return jsonify({'error': 'El contenido no puede estar vacío'}), 400

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("UPDATE anotaciones SET contenido = %s WHERE id = %s", (nuevo_contenido, id))
    conexion.commit()
    cursor.close()
    conexion.close()
    return jsonify({'status': 'ok', 'nuevo_contenido': nuevo_contenido})

@main.route('/anotaciones/<int:id>/eliminar', methods=['POST'])
@login_requerido
def eliminar_anotacion(id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM anotaciones WHERE id = %s", (id,))
    conexion.commit()
    cursor.close()
    conexion.close()
    return jsonify({'status': 'ok'})

@main.route('/estadisticas')
@login_requerido
def estadisticas():
    from app.db import obtener_estadisticas
    datos = obtener_estadisticas()
    return render_template('estadisticas.html', datos=datos)

@main.route('/reporte')
@login_requerido
def generar_reporte():
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')

    datos = []
    if inicio and fin:
        try:
            f_ini = datetime.strptime(inicio, '%Y-%m-%d')
            f_fin = datetime.strptime(fin, '%Y-%m-%d')
            f_fin = f_fin.replace(hour=23, minute=59, second=59)

            resultados = obtener_historico_escaneos()
            datos = [
                r for r in resultados
                if f_ini <= r['fecha_escaneo'] <= f_fin]
        except ValueError:
            pass

    return render_template('reporte.html', datos=datos, inicio=inicio, fin=fin)

@main.route('/reporte/pdf')
@login_requerido
def reporte_pdf():
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')

    f_ini = datetime.strptime(inicio, '%Y-%m-%d')
    f_fin = datetime.strptime(fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    resultados = obtener_historico_escaneos()
    datos = [
        r for r in resultados
        if f_ini <= r['fecha_escaneo'] <= f_fin]

    html = render_template('reporte.html', datos=datos, inicio=inicio, fin=fin)
    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdf = pdfkit.from_string(html, False, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_red.pdf'
    return response

@main.route('/reporte/csv')
@login_requerido
def reporte_csv():
    inicio = request.args.get('inicio')
    fin = request.args.get('fin')

    f_ini = datetime.strptime(inicio, '%Y-%m-%d')
    f_fin = datetime.strptime(fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    resultados = obtener_historico_escaneos()
    datos = [
        r for r in resultados
        if f_ini <= r['fecha_escaneo'] <= f_fin]

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['IP', 'Puerto', 'Fecha'])
    for fila in datos:
        writer.writerow([fila['ip'], fila['puerto'], fila['fecha_escaneo'].strftime('%d/%m/%Y %H:%M')])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=reporte_red.csv"})