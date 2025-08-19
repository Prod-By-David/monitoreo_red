import ipaddress
import concurrent.futures
import socket
import threading
import time

from ping3 import ping
from app.utils import hacer_ping, obtener_fabricante_por_mac
from app.db import (
    guardar_dispositivo, guardar_puertos_abiertos, guardar_alerta, obtener_historico_por_ip, guardar_historial_dispositivo, obtener_mac_por_ip, es_ip_bloqueada)

# Estado del escaneo automático
escaneo_activo = False
intervalo_minutos = 5
_timer = None

UMBRAL_MUCHOS_DISPOSITIVOS = 8

PUERTOS_COMUNES = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 3389]
PUERTOS_DESCRIPCION = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3", 139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB", 3389: "RDP"}

def escanear_ip(ip):
    try:
        return str(ip) if ping(str(ip), timeout=0.2) else None
    except Exception:
        return None

def escanear_red(rango="192.168.1.0/24", limite_hosts=150):
    red = ipaddress.ip_network(rango, strict=False)
    hosts = list(red.hosts())[:limite_hosts]

    max_workers = min(len(hosts), 80)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultados = list(executor.map(escanear_ip, hosts))
    
    return [ip for ip in resultados if ip is not None]

def escanear_puertos(ip, puertos=PUERTOS_COMUNES):
    abiertos = []
    for puerto in puertos:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex((ip, puerto)) == 0:
                    abiertos.append(puerto)
        except:
            continue
    return abiertos

def escanear_red_y_guardar(rango="192.168.1.0/24"):
    inicio = time.time()
    dispositivos = escanear_red(rango)

    if not dispositivos:
        print("[INFO] No se detectaron dispositivos.")
        return []

    dispositivos = [ip for ip in dispositivos if not es_ip_bloqueada(ip)]

    if len(dispositivos) > UMBRAL_MUCHOS_DISPOSITIVOS:
        guardar_alerta(
            tipo="Alerta de cantidad",
            mensaje=f"Se detectaron {len(dispositivos)} dispositivos activos en la red.",
            ip=None)

    resultados = []

    for ip in dispositivos:
        puertos = escanear_puertos(ip)
        online = hacer_ping(ip)

        historico_anterior = obtener_historico_por_ip(ip)
        puertos_anteriores = {h['puerto'] for h in historico_anterior} if historico_anterior else set()
        puertos_actuales = set(puertos)

        mac = obtener_mac_por_ip(ip)
        fabricante = obtener_fabricante_por_mac(mac) if mac else None

        dispositivo_id = guardar_dispositivo(ip, mac=mac, fabricante=fabricante)
        if dispositivo_id:
            guardar_puertos_abiertos(dispositivo_id, puertos)

        if not historico_anterior:
            guardar_alerta(
                tipo="Nuevo dispositivo",
                mensaje=f"Dispositivo nuevo detectado con IP {ip}",
                ip=ip)
            if mac:
                guardar_historial_dispositivo(mac, ip)
        else:
            puertos_nuevos = puertos_actuales - puertos_anteriores
            if puertos_nuevos:
                guardar_alerta(
                    tipo="Cambio en puertos",
                    mensaje=f"Nuevos puertos abiertos en {ip}: {', '.join(str(p) for p in puertos_nuevos)}",
                    ip=ip)

        resultados.append({
            'ip': ip,
            'online': online,
            'fabricante': fabricante,
            'puertos': [
                {'numero': p, 'nombre': PUERTOS_DESCRIPCION.get(p, "Desconocido")}
                for p in puertos]})

    duracion = time.time() - inicio
    print(f"[INFO] Escaneo completo en {duracion:.2f} segundos")
    return resultados

def iniciar_escaneo_automatico():
    global escaneo_activo, _timer
    if escaneo_activo:
        print("[INFO] Escaneo automático ya activo.")
        return
    escaneo_activo = True
    print("[INFO] Escaneo automático ACTIVADO.")

    def ejecutar_periodicamente():
        if not escaneo_activo:
            return
        print("[INFO] Ejecutando escaneo automático...")
        escanear_red_y_guardar()
        global _timer
        _timer = threading.Timer(intervalo_minutos * 60, ejecutar_periodicamente)
        _timer.start()

    ejecutar_periodicamente()

def detener_escaneo_automatico():
    global escaneo_activo, _timer
    if not escaneo_activo:
        print("[INFO] Escaneo automático ya estaba detenido.")
        return
    escaneo_activo = False
    if _timer:
        _timer.cancel()
        _timer = None
    print("[INFO] Escaneo automático DETENIDO.")

def estado_escaneo():
    return escaneo_activo