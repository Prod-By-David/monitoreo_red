import platform
import subprocess

def hacer_ping(ip):
    """
    Hace ping a la IP especificada.
    Retorna True si responde, False si no.
    """
    param = '-n' if platform.system().lower()=='windows' else '-c'

    comando = ['ping', param, '1', ip]
    try:
        salida = subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return salida.returncode == 0
    except Exception as e:
        print(f"Error haciendo ping a {ip}: {e}")
        return False

OUI_DICT = {
    "00:1A:2B": "Cisco Systems",
    "00:1B:63": "Apple, Inc.",
    "00:1C:B3": "Samsung Electronics",
    "F4:5C:89": "Xiaomi Communications",}

def obtener_fabricante_por_mac(mac):
    """
    Recibe una dirección MAC (string).
    Retorna el nombre del fabricante basado en los primeros 3 octetos OUI.
    Si no se encuentra, retorna 'Desconocido'.
    """
    if not mac or len(mac) < 8:
        return "Desconocido"
    
    mac = mac.upper().replace("-", ":")
    oui = ":".join(mac.split(":")[0:3])
    
    return OUI_DICT.get(oui, "Desconocido")