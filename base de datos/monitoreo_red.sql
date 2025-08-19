-- Crear base de datos
DROP DATABASE IF EXISTS monitoreo_red;
CREATE DATABASE monitoreo_red CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE monitoreo_red;

-- Tabla: dispositivos
CREATE TABLE dispositivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL UNIQUE,
    mac VARCHAR(50) UNIQUE,
    fabricante VARCHAR(100),
    ultima_actividad DATETIME
);

-- Tabla: escaneos_puertos
CREATE TABLE escaneos_puertos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dispositivo_id INT NOT NULL,
    puerto INT NOT NULL,
    fecha_escaneo DATETIME NOT NULL,
    FOREIGN KEY (dispositivo_id) REFERENCES dispositivos(id) ON DELETE CASCADE
);

-- Tabla: historial_dispositivos
CREATE TABLE historial_dispositivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    mac VARCHAR(50) NOT NULL,
    fabricante VARCHAR(100),
    primera_vez_detectado DATETIME,
    UNIQUE KEY unica_mac_ip (mac, ip)
);

-- Tabla: alertas
CREATE TABLE alertas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(100),
    mensaje TEXT,
    ip VARCHAR(45),
    fecha DATETIME NOT NULL
);

-- Tabla: ip_bloqueadas
CREATE TABLE ip_bloqueadas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL UNIQUE
);

-- Tabla: capturas
CREATE TABLE capturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: anotaciones
CREATE TABLE anotaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(255),
    contenido TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: actividad_dispositivos
CREATE TABLE actividad_dispositivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45),
    timestamp DATETIME
);

-- Tabla: reportes
CREATE TABLE reportes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(255),
    descripcion TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
