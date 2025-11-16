# **SIVC — Sistema Integral de Vigilancia Vehicular**
### *Instituto Tecnológico de Culiacán*

## **Descripción General**
SIVC es un sistema integral diseñado para gestionar y controlar infracciones vehiculares dentro del Tecnológico de Culiacán.  
Incluye una aplicación móvil para el personal de seguridad y un backend que administra la lógica del sistema.

El sistema permite registrar infracciones, realizar lectura OCR de placas, obtener la ubicación geográfica y aplicar un esquema de sanciones basado en reincidencia. Todo queda asociado al empleado que genera el reporte.

---

## **Características Principales**

### **1. Autenticación de Empleado**
Acceso seguro mediante ID institucional.

### **2. Reconocimiento Automático de Placas (OCR)**
Lectura de matrículas usando Google ML Kit.

### **3. Geolocalización de Incidencias**
Registro automático de:
- Latitud  
- Longitud  
- Fecha y hora  

### **4. Sistema de Tres Faltas**
| Falta | Acción |
|-------|--------|
| **1ra Falta** | Notificación a conductor y administrador |
| **2da Falta** | Advertencia de reincidencia |
| **3ra Falta** | Bloqueo automático del acceso al vehículo |

### **5. Trazabilidad y Auditoría**
Cada infracción se relaciona con el empleado, la ubicación, fecha/hora y el vehículo involucrado.

---

## **Arquitectura del Sistema**


---

## **Pila Tecnológica**

### **Frontend — Aplicación Móvil (Flutter)**
| Tecnología | Uso |
|-----------|-----|
| **Flutter (Dart)** | Aplicación móvil Android/iOS |
| **google_mlkit_text_recognition** | OCR para reconocimiento de placas |
| **geolocator** | Obtención de coordenadas GPS |
| **http** | Comunicación con el backend |

---

### **Backend — Servidor (Python)**
| Tecnología | Uso |
|------------|-----|
| **FastAPI** | API REST |
| **PostgreSQL** | Base de datos |
| **SQLAlchemy** | ORM |
| **Uvicorn** | Servidor ASGI |

---

## **Instalación y Configuración**

## **Backend**
pip install -r requirements.txt
4.  ¡Inicia el servidor!
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 #localmente

uvicorn main:app --host 0.0.0.0 --port $PORT  #para render
```
### **1. Clonar el repositorio**
```bash
git clone https://github.com/usuario/sivc-backend.git
cd sivc-backend
```

