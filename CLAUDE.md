# CLAUDE.md — Conversor MarkItDown

Guía para trabajar en este proyecto. Escrita en español (el proyecto y sus usuarios lo son).

## Qué es

Aplicación de escritorio para **Windows** que convierte documentos (PDF, Word, Excel,
PowerPoint, imágenes, HTML, CSV, audio, etc.) a **Markdown (`.md`)** usando el motor
oficial [MarkItDown de Microsoft](https://github.com/microsoft/markitdown).

Interfaz gráfica en **Tkinter** (nativa, sin dependencias de UI externas por defecto).
Se distribuye como un único `.exe` empaquetado con PyInstaller.

## Arquitectura

Todo el código vive en `app.py` (un solo archivo). Piezas clave:

- **`MarkItDownApp`** — clase única que construye la UI y orquesta el trabajo.
- **Hilo de trabajo + `queue.Queue`** — la conversión corre en un hilo daemon
  (`_start_worker` / `_safe_run`) y se comunica con la UI vía `self.log_queue`.
  La UI la drena con `_poll_log_queue` cada 100 ms usando `root.after`.
  **Regla de oro:** nunca tocar widgets Tkinter desde el hilo de trabajo; siempre
  pasar mensajes por la cola (`_log`, `_set_status`, `_set_progress`) o usar
  `root.after(0, ...)` para popups (`_popup_info` / `_popup_error`).
- **Carga perezosa del motor** — `_get_engine()` importa e instancia `MarkItDown`
  solo la primera vez (arranque del `.exe` más rápido).
- **`_convert_one(src, dst)`** — convierte un archivo y devuelve `(ok, mensaje)`.
- **`SUPPORTED_EXTENSIONS`** — set hardcodeado usado para filtrar en modo carpeta.

Acciones de UI: `on_convert_file` (archivo individual) y `on_convert_folder` (lote,
con opción de subcarpetas y deduplicación de nombres).

## Cómo ejecutar y compilar

```bat
REM Desarrollo (requiere Python en PATH)
python -m pip install -r requirements.txt
python app.py

REM Generar el .exe (o doble clic en build_exe.bat)
python -m PyInstaller --onefile --windowed --name "ConversorMarkItDown" ^
    --version-file version_info.txt --collect-all markitdown --collect-all magika app.py
```

El resultado queda en `dist\ConversorMarkItDown.exe`. `--collect-all markitdown` y
`--collect-all magika` son **imprescindibles** (magika = detección de tipos de MarkItDown).
Tras recompilar, volver a firmar (ver README, sección "Firma digital").

## Convenciones

- **Idioma:** todo (UI, comentarios, mensajes, commits) en español.
- **Sin tildes en el código fuente** de `app.py` (los comentarios/strings existentes
  evitan acentos para curarse en salud con encodings al empaquetar). Mantener ese estilo
  en strings que van a consola/logs; en la UI Tkinter los acentos sí funcionan.
- **Estilo:** stdlib pura donde se pueda; toda dependencia nueva encarece el `.exe`
  (~100 MB ya) y complica el empaquetado con PyInstaller.
- **Sin tests todavía** — la lógica está acoplada a la UI. Si se separa `converter.py`,
  añadir pruebas de la lógica de conversión.

## Estado / trabajo en curso

Ver `docs/MEJORAS.md` (si existe) y la memoria del asistente. Mejoras acordadas
(2026-09-05) a implementar: selección multi-archivo, botón cancelar, drag & drop
(tkinterdnd2), espejar subcarpetas en el destino, abrir carpeta al terminar, y
fijar versiones en `requirements.txt`.

## No versionar

`dist/`, `build/`, `*.exe` (ya en `.gitignore`, verificado). El `.exe` se regenera.
