from flask import Flask, render_template, request
app = Flask(__name__)
from app.routes import main
app.register_blueprint(main)

@app.route('/dashboard')
def dashboard():
    filtro = request.args.get('filtro', 'todos')
    
    # Simulación de dispositivos; deberías usar los reales.
    dispositivos = [
        {'ip': '192.168.0.10', 'hostname': 'Router', 'online': True, 'puertos': [{'numero': 80, 'nombre': 'http'}]},
        {'ip': '192.168.0.20', 'hostname': None, 'online': False, 'puertos': []},]

    # Filtrado según el parámetro
    if filtro == 'online':
        dispositivos = [d for d in dispositivos if d['online']]
    elif filtro == 'offline':
        dispositivos = [d for d in dispositivos if not d['online']]
    
    return render_template('dashboard.html', dispositivos=dispositivos, filtro=filtro)