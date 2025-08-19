import mysql.connector
from mysql.connector import Error
from datetime import datetime
import subprocess
import re
from mac_vendor_lookup import MacLookup

mac_lookup = MacLookup()
try:
    mac_lookup.update_vendors()
except Exception as e:
    print(f"[ERROR] No se pudo actualizar la base de fabricantes: {e}")

def conectar():
    try:
        return mysql.connector.connect(
            host='localhost', user='root', password='', database='monitoreo_red')
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def guardar_dispositivo(ip, mac=None, fabricante=None):
    conexion = conectar()
    if not conexion:
        return None
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM dispositivos WHERE ip = %s", (ip,))
    resultado = cursor.fetchone()
    ahora = datetime.now()

    if mac is None:
        macs = obtener_macs()
        mac = next((m for i, m in macs if i == ip), None)
        if mac:
            mac = mac.upper().replace("-", ":").strip()
        else:
            mac = f"Desconocido-{ip}"
    else:
        mac = mac.upper().replace("-", ":").strip()

    if mac.lower().startswith("desconocido"):
        mac = f"Desconocido-{ip}"

    if fabricante is None:
        fabricante = obtener_fabricante(mac) if not mac.lower().startswith("desconocido") else "Desconocido"

    print(f"[FABRICANTE DEBUG] IP: {ip} | MAC: {mac} | Fabricante: {fabricante}")

    if resultado:
        dispositivo_id = resultado[0]
        cursor.execute("UPDATE dispositivos SET ultima_actividad = %s WHERE id = %s", (ahora, dispositivo_id))
        cursor.execute("UPDATE dispositivos SET mac = %s, fabricante = %s WHERE id = %s", (mac, fabricante, dispositivo_id))
        if fabricante != "Desconocido":
            cursor.execute("UPDATE historial_dispositivos SET fabricante = %s WHERE ip = %s AND fabricante = 'Desconocido'", (fabricante, ip))
    else:
        cursor.execute("INSERT INTO dispositivos (ip, mac, fabricante, ultima_actividad) VALUES (%s, %s, %s, %s)", (ip, mac, fabricante, ahora))
        dispositivo_id = cursor.lastrowid

        cursor.execute("SELECT id FROM historial_dispositivos WHERE ip = %s AND mac = %s", (ip, mac))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO historial_dispositivos (ip, mac, fabricante, primera_vez_detectado) VALUES (%s, %s, %s, %s)", (ip, mac, fabricante, ahora))

    conexion.commit()
    cursor.close()
    conexion.close()
    return dispositivo_id

def guardar_puertos_abiertos(dispositivo_id, puertos):
    conexion = conectar()
    if not conexion:
        return
    cursor = conexion.cursor()
    ahora = datetime.now()

    for puerto in puertos:
        cursor.execute("INSERT INTO escaneos_puertos (dispositivo_id, puerto, fecha_escaneo) VALUES (%s, %s, %s)", (dispositivo_id, puerto, ahora))

    conexion.commit()
    cursor.close() 
    conexion.close()

def obtener_historico_escaneos():
    conexion = conectar()
    if not conexion:
        return []
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.ip, e.puerto, e.fecha_escaneo
        FROM escaneos_puertos e
        JOIN dispositivos d ON e.dispositivo_id = d.id
        ORDER BY e.fecha_escaneo DESC
    """)
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()
    return resultados

def obtener_historico_por_ip(ip):
    conexion = conectar()
    if not conexion:
        return []
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.ip, e.puerto, e.fecha_escaneo
        FROM escaneos_puertos e
        JOIN dispositivos d ON e.dispositivo_id = d.id
        WHERE d.ip = %s
        ORDER BY e.fecha_escaneo DESC
    """, (ip,))
    resultados = cursor.fetchall()
    cursor.close()
    conexion.close()
    return resultados

def obtener_macs():
    try:
        resultado = subprocess.check_output("arp -a", shell=True).decode(errors='ignore')
        macs = []
        for line in resultado.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                ip = parts[0]
                mac = parts[1]
                if re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", mac):
                    macs.append((ip, mac))
        return macs
    except Exception as e:
        print(f"[ERROR] obtener_macs(): {e}")
        return []

def obtener_fabricante(mac):
    if not mac:
        return "Desconocido"
    mac = mac.upper().replace("-", ":")
    try:
        return mac_lookup.lookup(mac) or "Desconocido"
    except Exception as e:
        print(f"[ERROR] Error buscando fabricante para {mac}: {e}")
        return "Desconocido"

def guardar_alerta(tipo, mensaje, ip):
    conexion = conectar()
    if not conexion:
        return
    cursor = conexion.cursor()
    ahora = datetime.now()
    cursor.execute(
        "INSERT INTO alertas (tipo, mensaje, ip, fecha) VALUES (%s, %s, %s, %s)",
        (tipo, mensaje, ip, ahora))
    conexion.commit()
    cursor.close()
    conexion.close()

def obtener_alertas(limite=5):
    conexion = conectar()
    if not conexion:
        return []

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT tipo, mensaje, ip, fecha
        FROM alertas
        ORDER BY fecha DESC
        LIMIT %s
    """, (limite,))
    alertas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return alertas

def guardar_en_historial(mac, ip):
    conexion = conectar()
    if not conexion:
        return
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id FROM historial_dispositivos WHERE mac = %s AND ip = %s",
        (mac, ip))
    existe = cursor.fetchone()
    if not existe:
        cursor.execute(
            "INSERT INTO historial_dispositivos (mac, ip, primera_vez_detectado) VALUES (%s, %s, %s)",
            (mac, ip, datetime.now()))
        conexion.commit()
    cursor.close()
    conexion.close()

def obtener_historial_dispositivos():
    conexion = conectar()
    if not conexion:
        return []

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT ip, mac, fabricante, primera_vez_detectado
        FROM historial_dispositivos
        ORDER BY primera_vez_detectado DESC
    """)
    historial = cursor.fetchall()
    cursor.close()
    conexion.close()
    return historial

def guardar_historial_dispositivo(mac, ip):
    if not mac or not ip:
        return
    conexion = conectar()
    if not conexion:
        return
    cursor = conexion.cursor()
    # Verificar si existe el registro
    cursor.execute(
        "SELECT id FROM historial_dispositivos WHERE mac = %s AND ip = %s",
        (mac, ip))
    resultado = cursor.fetchone()
    if not resultado:
        cursor.execute(
            "INSERT INTO historial_dispositivos (mac, ip, primera_vez_detectado) VALUES (%s, %s, NOW())",
            (mac, ip))
    else:
        # Opcional: actualizar fecha si quieres reflejar la última detección
        cursor.execute(
            "UPDATE historial_dispositivos SET primera_vez_detectado = NOW() WHERE id = %s",
            (resultado[0],))
    conexion.commit()
    cursor.close()
    conexion.close()

def obtener_mac_por_ip(ip_objetivo):
    macs = obtener_macs()
    for ip, mac in macs:
        if ip == ip_objetivo:
            return mac
    return None

def bloquear_ip(ip):
    conexion = conectar()
    if not conexion:
        return False
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT IGNORE INTO ip_bloqueadas (ip) VALUES (%s)", (ip,))
        conexion.commit()
        return True
    except Exception as e:
        print(f"[ERROR] bloquear_ip: {e}")
        return False
    finally:
        cursor.close()
        conexion.close()

def desbloquear_ip(ip):
    conexion = conectar()
    if not conexion:
        return False
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM ip_bloqueadas WHERE ip = %s", (ip,))
        conexion.commit()
        return True
    except Exception as e:
        print(f"[ERROR] desbloquear_ip: {e}")
        return False
    finally:
        cursor.close()
        conexion.close()

def obtener_ips_bloqueadas():
    conexion = conectar()
    if not conexion:
        return []
    cursor = conexion.cursor()
    cursor.execute("SELECT ip FROM ip_bloqueadas")
    ips = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conexion.close()
    return ips

def es_ip_bloqueada(ip):
    conexion = conectar()
    if not conexion:
        return False
    cursor = conexion.cursor()
    cursor.execute("SELECT 1 FROM ip_bloqueadas WHERE ip = %s", (ip,))
    existe = cursor.fetchone() 
    cursor.close()
    conexion.close()
    return existe is not None

def registrar_actividad(ip):
    conexion = conectar()
    if not conexion:
        return
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO actividad_dispositivos (ip, timestamp) VALUES (%s, %s)",
        (ip, datetime.now()))
    conexion.commit()
    cursor.close()
    conexion.close()

def obtener_actividad_por_ip(ip):
    conexion = conectar()
    if not conexion:
        return []
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT timestamp FROM actividad_dispositivos WHERE ip = %s ORDER BY timestamp ASC", (ip,))
    datos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return datos

def obtener_estadisticas():
    conexion = conectar()
    if not conexion:
        return {}
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM dispositivos")
    total_dispositivos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM dispositivos WHERE TIMESTAMPDIFF(MINUTE, ultima_actividad, NOW()) < 5")
    online = cursor.fetchone()[0]
    offline = total_dispositivos - online

    cursor.execute("""
        SELECT AVG(num_puertos) FROM (
            SELECT COUNT(*) AS num_puertos
            FROM escaneos_puertos
            GROUP BY dispositivo_id
        ) AS sub
    """)
    avg_puertos = round(cursor.fetchone()[0] or 0, 2)

    cursor.execute("""
        SELECT AVG(diff) FROM (
            SELECT TIMESTAMPDIFF(SECOND, 
                LAG(fecha_escaneo) OVER (ORDER BY fecha_escaneo),
                fecha_escaneo
            ) AS diff
            FROM escaneos_puertos
        ) AS tiempos
    """)
    avg_entre_escaneos = cursor.fetchone()[0] or 0
    avg_entre_escaneos_min = round(avg_entre_escaneos / 60, 2)

    cursor.close()
    conexion.close()

    return {
        'total_dispositivos': total_dispositivos,
        'online': online,
        'offline': offline,
        'avg_puertos': avg_puertos,
        'avg_entre_escaneos': avg_entre_escaneos_min}