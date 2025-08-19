from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()

def create_app():
    app = Flask(__name__)

    # Configuración de conexión a MySQL
    app.config['SECRET_KEY'] = 'clave_secreta_para_sesiones'
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = 'monitoreo_red'

    mysql.init_app(app)

    # Importación y registro del blueprint
    from app.routes import main
    app.register_blueprint(main)

    return app