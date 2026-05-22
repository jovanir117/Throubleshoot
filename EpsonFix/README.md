# 🖨 EpsonFix Premium — Suite de Diagnóstico Profesional

**EpsonFix** es una solución avanzada e interactiva para el diagnóstico, soporte y reparación de impresoras Epson en sistemas Windows. Diseñada bajo una estética Material Dark premium, combina detección de hardware a bajo nivel (`pyusb` y consultas WMI), resolución automatizada de fallas de sistema y un asistente interactivo paso a paso guiado por una base de conocimiento inteligente.

---

## ✨ Características Principales

- 🔍 **Detección a Bajo Nivel**: Localización de impresoras Epson mediante consulta directa a buses USB (Vendor ID `0x04b8`) y mapeo a través de la API WMI moderna.
- ⚙️ **Auto-Fixes Automatizados**:
  - Reinicio automático del servicio de Cola de Impresión (*Spooler*).
  - Limpieza forzada de cola de trabajos atascados en `System32\spool\PRINTERS`.
  - Acceso directo a preferencias del dispositivo y colas de impresión.
- 🗺️ **Asistente de Soluciones Interactivo**: Wizard dinámico con pasos de resolución, soporte de imágenes y botones de ejecución de comandos directos.
- 💻 **Consola Virtual Integrada**: Terminal en tiempo real con estética retro monospacio para supervisar las operaciones elevadas de reparación del sistema.
- 📊 **Monitoreo en Tiempo Real**: Sidebar interactivo que muestra el estado de salud del disco principal y el estado del servicio *Spooler* de Windows en segundo plano.
- 🗄️ **Base de Conocimiento Local**: Respaldada por SQLite y SQLAlchemy 2.0, con persistencia para historial de errores y registros de reparación.

---

## 🛠️ Requisitos del Sistema

- **Sistema Operativo**: Windows 10 / 11 (Se recomiendan permisos de Administrador para los auto-fixes).
- **Python**: 3.8 o superior.
- **Librerías externas**:
  - `customtkinter` (Para la interfaz gráfica moderna)
  - `pywin32` (Para las APIs nativas de Windows)
  - `sqlalchemy` (Para la capa ORM de base de datos)
  - `pyusb` (Para la detección USB)
  - `wmi` (Para el inventario de hardware)
  - `Pillow` (Para soporte de imágenes en el asistente)

---

## 🚀 Instalación y Uso (Desarrollo)

1. Clonar el repositorio.
2. Abrir una consola (con privilegios de Administrador) en el directorio del proyecto.
3. Ejecutar la aplicación en modo desarrollo mediante el script por lotes:
   ```cmd
   run_epsonfix_admin.bat
   ```
   *Nota: Si no se encuentra compilada, este script iniciará el entorno en modo desarrollo utilizando la instalación de Python local.*

---

## 📦 Compilación a Ejecutable Independiente (EXE)

Para compilar un instalador único en formato `.exe` optimizado para distribución y que incluya los archivos de la base de conocimiento y los recursos visuales, ejecuta:

```cmd
build_exe.bat
```

Esto generará el ejecutable bajo la ruta `dist\EpsonFix.exe`.

---

## 🏗️ Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación.
- `config.py`: Definición de la paleta de colores premium, fuentes y constantes globales de UI.
- `core/`: Motores de detección, acciones de sistema, salud y diagnóstico inteligente.
- `database/`: Conectores SQLite, gestor de base de datos y scripts de siembra (seeds).
- `models/`: Esquemas de datos para perfiles de impresoras, sesiones de reparación y base de conocimiento.
- `presenters/`: Presentador principal del patrón MVP que coordina la interfaz y el dominio.
- `views/`: Vistas de ventana principal, wizard interactivo, diálogos y componentes visuales reutilizables.
- `knowledge/`: Base de conocimiento en JSON (`solutions.json`).
- `assets/`: Recursos estáticos (iconos, imágenes descriptivas).
