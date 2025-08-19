# Sistema de Monitoreo de Red - TFG ASIR

Este proyecto es un sistema web desarrollado como Trabajo de Fin de Grado (TFG) para el ciclo formativo de **ASIR**.

Permite escanear la red local, identificar dispositivos conectados, analizar su historial, registrar anotaciones, gestionar capturas de pantalla y exportar informes. También cuenta con herramientas para bloquear IPs sospechosas y visualizar estadísticas de uso.

---

# Tecnologías utilizadas

- Python 3
- Flask
- MySQL
- HTML5 + CSS3
- JavaScript (opcional para gráficos)
- PDFKit (para exportación de reportes)

---

# Estructura del proyecto

monitoreo_red/
├── app.py
├── run.py
├── requerimientos.txt
├── app/
│ ├── init.py
│ ├── db.py
│ ├── monitor.py
│ ├── routes.py
│ ├── utils.py
│ ├── estatico/css/
│ ├── static/uploads/
│ └── templates/

---

# Instalación y uso

1. **Clona este repositorio** o descomprime el archivo `.zip` en tu máquina.

2. **Instala las dependencias** (se recomienda entorno virtual):

```bash
pip install -r requerimientos.txt

---

Configura la base de datos:

Crea una base de datos MySQL.

Crea las tablas necesarias según el esquema usado en app/db.py.

Ajusta los datos de conexión en db.py si es necesario.

Ejecuta la aplicación:

python run.py

Accede en tu navegador a: http://localhost:5000

---

# Funcionalidades principales

📡 Escaneo de red local (ping + MAC)

🟢/🔴 Visualización de dispositivos online/offline

📊 Estadísticas generales

🧾 Historial de escaneos

📁 Capturas de pantalla de eventos

📝 Anotaciones del administrador

🔒 Bloqueo y desbloqueo de IPs

📤 Exportación de reportes a CSV y PDF