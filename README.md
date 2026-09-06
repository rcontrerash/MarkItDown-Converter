# Conversor MarkItDown

Aplicación de escritorio para Windows que convierte documentos a Markdown (`.md`)
usando el motor oficial [MarkItDown de Microsoft](https://github.com/microsoft/markitdown).

![Captura de la aplicación](docs/screenshot.png)

## Contenido del proyecto

| Archivo | Descripción |
|---|---|
| `app.py` | Código fuente de la aplicación (interfaz Tkinter). |
| `requirements.txt` | Dependencias de Python. |
| `build_exe.bat` | Script que genera el ejecutable `.exe`. |
| `dist/ConversorMarkItDown.exe` | **El ejecutable final que envías a tus usuarios.** |
| `LEEME - Instrucciones para usuarios.txt` | Instrucciones para el usuario final. |

## Qué enviar a los usuarios

Solo dos archivos (puedes comprimirlos en un `.zip`):

1. `dist\ConversorMarkItDown.exe`
2. `LEEME - Instrucciones para usuarios.txt`

No necesitan instalar Python ni nada más.

## Funciones

- **Convertir archivo(s)**: elige uno o varios archivos a la vez. Con uno solo se
  ofrece "Guardar como"; con varios se pide una carpeta de destino.
- **Convertir una carpeta**: convierte por lotes; genera un `.md` por documento,
  con opción de incluir subcarpetas **respetando su estructura** en el destino.
- **Arrastrar y soltar**: suelta archivos o carpetas sobre la ventana para
  convertirlos (requiere `tkinterdnd2`; si no está, la app funciona igual sin
  esta función).
- **Cancelar**: detiene un lote en curso (termina el archivo actual y para).
- **Abrir carpeta de destino**: botón para abrir los resultados al terminar.
- **Indicador de actividad**: cronómetro del archivo en curso, barra de actividad
  animada y aviso en el registro si un archivo tarda demasiado. Así se distingue
  fácilmente un archivo lento de un programa pegado.
- Registro de avance, barra de progreso y manejo de errores por archivo.

## Formatos soportados

PDF, Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`), CSV, HTML, XML, JSON,
TXT, EPUB, ZIP, imágenes (PNG/JPG…), audio (MP3/WAV, requiere internet), MSG, etc.

## Regenerar el ejecutable (si modificas `app.py`)

Doble clic en `build_exe.bat`, o desde la terminal:

```bat
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --windowed --name "ConversorMarkItDown" --collect-all markitdown --collect-all magika app.py
```

El resultado queda en `dist\ConversorMarkItDown.exe`.

## Ejecutar sin compilar (modo desarrollo)

```bat
python -m pip install -r requirements.txt
python app.py
```

## Notas técnicas

- Construido con Python 3.14 + Tkinter + PyInstaller (modo `--onefile --windowed`).
- El `.exe` incluye metadatos de versión (editor **Rodrigo Contreras**, motor
  **Microsoft MarkItDown**), definidos en `version_info.txt`.
- Tamaño aproximado del `.exe`: ~100 MB (incluye todas las dependencias).

## Firma digital

El `.exe` está firmado con un **certificado autofirmado** y sello de tiempo (DigiCert). Esto **no elimina** el aviso de Windows SmartScreen
en equipos ajenos, porque el certificado no proviene de una Autoridad
Certificadora (CA) de confianza pública.

```
