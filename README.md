Scraper para la plataforma Moodle de la Universidad Politécnica de Madrid (UPM). Automatiza la descarga de archivos (PDF, DOCX, ZIP, etc.) replicando la estructura de secciones y subsecciones del curso en un árbol de directorios local.

## Configuración

1. Clonar el archivo de configuración de entorno:

```bash
   cp .env.example .env

```

2. Editar el archivo `.env` con las credenciales correspondientes:
```dotenv
usuario=tu_usuario
pw=tu_contraseña
```



## Uso

Ejecutar el script principal:

```bash
python main.py

```
El script pedirá si descargar todos los cursos o algúnos en especifíco.
El script creará un directorio `downloads/` que contendrá la jerarquía de carpetas del curso con sus respectivos archivos descargables.

## Roadmap

* [ ] Soporte para descargas enlazadas dentro de subsecciones.
* [ ] Opciones de filtrado en la interfaz de línea de comandos (por fecha o tipo de archivo).
* [ ] Sortear los time-outs.