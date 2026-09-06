# -*- coding: utf-8 -*-
"""
Conversor MarkItDown - Herramienta de escritorio para Windows
=============================================================
Convierte archivos (PDF, Word, Excel, PowerPoint, imagenes, HTML, CSV, etc.)
a formato Markdown (.md) usando el motor oficial MarkItDown de Microsoft.

Funciones:
  - Convertir uno o varios archivos (elige archivos y donde guardarlos).
  - Convertir una carpeta completa (un .md por cada archivo compatible),
    con opcion de incluir subcarpetas espejando su estructura en el destino.
  - Cancelar un lote en curso.
  - Abrir la carpeta de destino al terminar.

Interfaz grafica con Tkinter (nativa de Windows).
"""

import os
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Conversor MarkItDown"
APP_VERSION = "1.1"

# Extensiones que MarkItDown suele soportar. Se usan para filtrar en lote.
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
    ".html", ".htm", ".xml", ".json", ".txt", ".md", ".rtf", ".epub",
    ".zip", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
    ".mp3", ".wav", ".m4a", ".msg",
}


class MarkItDownApp:
    def __init__(self, root, dnd_enabled=False):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("720x560")
        self.root.minsize(640, 500)

        # Cola para comunicar el hilo de trabajo con la interfaz.
        self.log_queue = queue.Queue()
        self._md = None  # instancia MarkItDown (carga perezosa)
        self._working = False
        self._cancel = threading.Event()  # senal de cancelacion del lote
        self._last_output_dir = None  # ultima carpeta con resultados
        self._dnd_enabled = dnd_enabled  # arrastrar y soltar disponible

        self._build_ui()
        if self._dnd_enabled:
            self._setup_dnd()
        self._poll_log_queue()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        header = tk.Frame(self.root)
        header.pack(fill="x", **pad)
        tk.Label(
            header, text="Conversor MarkItDown",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Convierte documentos a Markdown (.md) con el motor oficial de Microsoft.",
            font=("Segoe UI", 9), fg="#555555",
        ).pack(anchor="w")

        # Botones de accion principales
        actions = tk.Frame(self.root)
        actions.pack(fill="x", **pad)

        self.btn_file = tk.Button(
            actions, text="  Convertir archivo(s)  ",
            font=("Segoe UI", 11), command=self.on_convert_file,
            height=2, bg="#0067c0", fg="white", activebackground="#005ba1",
            cursor="hand2",
        )
        self.btn_file.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.btn_folder = tk.Button(
            actions, text="  Convertir una carpeta  ",
            font=("Segoe UI", 11), command=self.on_convert_folder,
            height=2, bg="#107c10", fg="white", activebackground="#0b5a0b",
            cursor="hand2",
        )
        self.btn_folder.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # Botones secundarios: cancelar y abrir carpeta
        secondary = tk.Frame(self.root)
        secondary.pack(fill="x", **pad)

        self.btn_cancel = tk.Button(
            secondary, text="Cancelar", font=("Segoe UI", 10),
            command=self.on_cancel, state="disabled", cursor="hand2",
        )
        self.btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.btn_open = tk.Button(
            secondary, text="Abrir carpeta de destino", font=("Segoe UI", 10),
            command=self.on_open_output, state="disabled", cursor="hand2",
        )
        self.btn_open.pack(side="left", expand=True, fill="x", padx=(6, 0))

        # Barra de progreso
        prog_frame = tk.Frame(self.root)
        prog_frame.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill="x")

        # Registro de resultados
        log_frame = tk.LabelFrame(self.root, text="Registro")
        log_frame.pack(fill="both", expand=True, **pad)

        self.log_text = tk.Text(
            log_frame, wrap="word", font=("Consolas", 9),
            state="disabled", bg="#1e1e1e", fg="#d4d4d4",
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

        # Barra de estado
        self.status = tk.Label(
            self.root, text="Listo.", anchor="w", relief="sunken",
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", side="bottom")

        self._log("Bienvenido. Elige 'Convertir archivo(s)' o 'Convertir una carpeta'.")
        if self._dnd_enabled:
            self._log("Consejo: tambien puedes arrastrar archivos o carpetas a esta ventana.")

    # -------------------------------------------------- Arrastrar y soltar
    def _setup_dnd(self):
        """Registra la ventana como destino de arrastrar y soltar (tkinterdnd2)."""
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:  # noqa: BLE001
            self._dnd_enabled = False

    def on_drop(self, event):
        if self._working:
            return
        # tk.splitlist maneja correctamente rutas con espacios ({...}).
        paths = [p for p in self.root.tk.splitlist(event.data) if os.path.exists(p)]
        if not paths:
            return

        # Un unico archivo: se ofrece "Guardar como".
        if len(paths) == 1 and os.path.isfile(paths[0]):
            src = paths[0]
            base = os.path.splitext(os.path.basename(src))[0]
            dst = filedialog.asksaveasfilename(
                title="Guardar Markdown como",
                defaultextension=".md",
                initialfile=base + ".md",
                filetypes=[("Archivo Markdown", "*.md"), ("Todos los archivos", "*.*")],
            )
            if not dst:
                return
            self._start_worker(self._worker_single, src, dst)
            return

        # Varios elementos o carpetas: se pide una carpeta de destino comun.
        dst_dir = filedialog.askdirectory(
            title="Selecciona la carpeta donde guardar los .md"
        )
        if not dst_dir:
            return
        self._start_worker(self._worker_dropped, paths, dst_dir)

    def _worker_dropped(self, paths, dst_dir):
        """Convierte una mezcla de archivos y carpetas soltados en la ventana."""
        self._set_status("Preparando archivos...")
        jobs = []  # (src, out_dir, nombre_a_mostrar)
        for p in paths:
            if os.path.isfile(p):
                jobs.append((p, dst_dir, os.path.basename(p)))
            elif os.path.isdir(p):
                folder = os.path.basename(os.path.normpath(p))
                for root_dir, _dirs, names in os.walk(p):
                    for n in names:
                        if os.path.splitext(n)[1].lower() in SUPPORTED_EXTENSIONS:
                            full = os.path.join(root_dir, n)
                            rel = os.path.relpath(full, p)
                            out_dir = os.path.join(dst_dir, folder, os.path.dirname(rel))
                            jobs.append((full, out_dir, os.path.join(folder, rel)))

        total = len(jobs)
        if total == 0:
            self._log("No se encontraron archivos compatibles en lo que soltaste.")
            self._set_status("Sin archivos compatibles.")
            self.log_queue.put(("done", None))
            self._popup_info("Sin archivos",
                             "No se encontraron archivos compatibles.")
            return

        self._log(f"\n> Se procesaran {total} archivo(s). Iniciando conversion...")
        self._set_progress(0, total)
        ok_count = err_count = 0
        used_names = set()
        cancelled = False

        for i, (src, out_dir, disp) in enumerate(jobs, start=1):
            if self._cancel.is_set():
                cancelled = True
                break
            self._set_status(f"Convirtiendo {i} de {total}...")
            base = os.path.splitext(os.path.basename(src))[0]
            candidate = self._unique_name(out_dir, base, used_names)
            dst = os.path.join(out_dir, candidate)
            ok, info = self._convert_one(src, dst)
            if ok:
                ok_count += 1
                self._log(f"  [{i}/{total}] OK: {disp}")
            else:
                err_count += 1
                self._log(f"  [{i}/{total}] ERROR: {disp} :: {info}")
            self._set_progress(i, total)

        self._finish_batch(ok_count, err_count, dst_dir, cancelled)

    # ------------------------------------------------------------- Logging
    def _log(self, message):
        self.log_queue.put(("log", message))

    def _set_status(self, message):
        self.log_queue.put(("status", message))

    def _set_progress(self, value, maximum=None):
        self.log_queue.put(("progress", (value, maximum)))

    def _poll_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self.log_text.config(state="normal")
                    self.log_text.insert("end", payload + "\n")
                    self.log_text.see("end")
                    self.log_text.config(state="disabled")
                elif kind == "status":
                    self.status.config(text=payload)
                elif kind == "progress":
                    value, maximum = payload
                    if maximum is not None:
                        self.progress.config(maximum=maximum)
                    self.progress.config(value=value)
                elif kind == "done":
                    self._working = False
                    self.btn_file.config(state="normal")
                    self.btn_folder.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    # payload es la carpeta de salida (o None).
                    if payload:
                        self._last_output_dir = payload
                        self.btn_open.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    # ---------------------------------------------------------- Motor MID
    def _get_engine(self):
        if self._md is None:
            self._log("Inicializando motor MarkItDown (puede tardar unos segundos)...")
            from markitdown import MarkItDown  # import perezoso
            self._md = MarkItDown()
        return self._md

    def _convert_one(self, src_path, dst_path):
        """Convierte un archivo y escribe el .md. Devuelve (ok, mensaje)."""
        try:
            engine = self._get_engine()
            result = engine.convert(src_path)
            text = getattr(result, "text_content", None)
            if text is None:
                text = getattr(result, "markdown", "") or ""
            # Asegura que exista la carpeta de destino (espejo de subcarpetas).
            os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True, dst_path
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"

    # ------------------------------------------------------ Accion: archivo(s)
    def on_convert_file(self):
        if self._working:
            return
        srcs = filedialog.askopenfilenames(
            title="Selecciona el/los archivo(s) a convertir",
            filetypes=[
                ("Todos los soportados",
                 "*.pdf *.docx *.pptx *.xlsx *.csv *.html *.htm *.xml "
                 "*.json *.txt *.rtf *.epub *.zip *.png *.jpg *.jpeg "
                 "*.mp3 *.wav *.msg"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not srcs:
            return
        srcs = list(srcs)

        if len(srcs) == 1:
            # Un solo archivo: se mantiene el dialogo "Guardar como".
            src = srcs[0]
            base = os.path.splitext(os.path.basename(src))[0]
            dst = filedialog.asksaveasfilename(
                title="Guardar Markdown como",
                defaultextension=".md",
                initialfile=base + ".md",
                filetypes=[("Archivo Markdown", "*.md"), ("Todos los archivos", "*.*")],
            )
            if not dst:
                return
            self._start_worker(self._worker_single, src, dst)
        else:
            # Varios archivos: se pide una carpeta de destino comun.
            dst_dir = filedialog.askdirectory(
                title="Selecciona la carpeta donde guardar los .md"
            )
            if not dst_dir:
                return
            self._start_worker(self._worker_files, srcs, dst_dir)

    def _worker_single(self, src, dst):
        self._set_status("Convirtiendo...")
        self._set_progress(0, 1)
        self._log(f"\n> Convirtiendo: {src}")
        ok, info = self._convert_one(src, dst)
        self._set_progress(1, 1)
        out_dir = os.path.dirname(dst)
        if ok:
            self._log(f"  OK -> {info}")
            self._set_status("Conversion completada.")
            self.log_queue.put(("done", out_dir))
            self._popup_info("Listo", f"Archivo convertido correctamente:\n\n{info}")
        else:
            self._log(f"  ERROR: {info}")
            self._set_status("Error en la conversion.")
            self.log_queue.put(("done", None))
            self._popup_error("Error", f"No se pudo convertir el archivo:\n\n{info}")

    def _worker_files(self, srcs, dst_dir):
        """Convierte una lista de archivos sueltos hacia una carpeta comun."""
        total = len(srcs)
        self._log(f"\n> Se seleccionaron {total} archivo(s). Iniciando conversion...")
        self._set_progress(0, total)
        used_names = set()
        ok_count = err_count = 0
        cancelled = False

        for i, src in enumerate(srcs, start=1):
            if self._cancel.is_set():
                cancelled = True
                break
            self._set_status(f"Convirtiendo {i} de {total}...")
            base = os.path.splitext(os.path.basename(src))[0]
            candidate = self._unique_name(dst_dir, base, used_names)
            dst = os.path.join(dst_dir, candidate)
            ok, info = self._convert_one(src, dst)
            if ok:
                ok_count += 1
                self._log(f"  [{i}/{total}] OK: {os.path.basename(src)} -> {candidate}")
            else:
                err_count += 1
                self._log(f"  [{i}/{total}] ERROR: {os.path.basename(src)} :: {info}")
            self._set_progress(i, total)

        self._finish_batch(ok_count, err_count, dst_dir, cancelled)

    # ------------------------------------------------------ Accion: carpeta
    def on_convert_folder(self):
        if self._working:
            return
        src_dir = filedialog.askdirectory(
            title="Selecciona la carpeta con los archivos a convertir"
        )
        if not src_dir:
            return

        dst_dir = filedialog.askdirectory(
            title="Selecciona la carpeta donde guardar los .md"
        )
        if not dst_dir:
            return

        include_sub = messagebox.askyesno(
            "Subcarpetas",
            "Incluir tambien los archivos de las subcarpetas?\n\n"
            "(Se respetara la estructura de carpetas en el destino.)",
        )

        self._start_worker(self._worker_folder, src_dir, dst_dir, include_sub)

    def _worker_folder(self, src_dir, dst_dir, include_sub):
        self._set_status("Buscando archivos...")
        # Guarda (ruta_completa, ruta_relativa_al_origen) para espejar el arbol.
        files = []
        if include_sub:
            for root_dir, _dirs, names in os.walk(src_dir):
                for n in names:
                    if os.path.splitext(n)[1].lower() in SUPPORTED_EXTENSIONS:
                        full = os.path.join(root_dir, n)
                        rel = os.path.relpath(full, src_dir)
                        files.append((full, rel))
        else:
            for n in os.listdir(src_dir):
                full = os.path.join(src_dir, n)
                if os.path.isfile(full) and \
                        os.path.splitext(n)[1].lower() in SUPPORTED_EXTENSIONS:
                    files.append((full, n))

        total = len(files)
        if total == 0:
            self._log("No se encontraron archivos compatibles en la carpeta.")
            self._set_status("Sin archivos compatibles.")
            self.log_queue.put(("done", None))
            self._popup_info("Sin archivos",
                             "No se encontraron archivos compatibles en la carpeta.")
            return

        self._log(f"\n> Se encontraron {total} archivo(s). Iniciando conversion en lote...")
        self._set_progress(0, total)

        ok_count = err_count = 0
        used_names = set()
        cancelled = False

        for i, (src, rel) in enumerate(files, start=1):
            if self._cancel.is_set():
                cancelled = True
                break
            self._set_status(f"Convirtiendo {i} de {total}...")

            # Espeja la subcarpeta de origen dentro del destino.
            rel_dir = os.path.dirname(rel)
            out_dir = os.path.join(dst_dir, rel_dir) if rel_dir else dst_dir
            base = os.path.splitext(os.path.basename(rel))[0]
            candidate = self._unique_name(out_dir, base, used_names)
            dst = os.path.join(out_dir, candidate)

            ok, info = self._convert_one(src, dst)
            shown = os.path.join(rel_dir, candidate) if rel_dir else candidate
            if ok:
                ok_count += 1
                self._log(f"  [{i}/{total}] OK: {os.path.basename(src)} -> {shown}")
            else:
                err_count += 1
                self._log(f"  [{i}/{total}] ERROR: {os.path.basename(src)} :: {info}")
            self._set_progress(i, total)

        self._finish_batch(ok_count, err_count, dst_dir, cancelled)

    # ------------------------------------------------------------ Helpers
    def _unique_name(self, out_dir, base, used_names):
        """Devuelve un nombre .md unico dentro de out_dir (evita sobrescribir)."""
        candidate = base + ".md"
        count = 0
        while os.path.join(out_dir, candidate) in used_names or \
                os.path.exists(os.path.join(out_dir, candidate)):
            count += 1
            candidate = f"{base}_{count}.md"
        used_names.add(os.path.join(out_dir, candidate))
        return candidate

    def _finish_batch(self, ok_count, err_count, dst_dir, cancelled):
        if cancelled:
            self._log(f"\nCancelado por el usuario. "
                      f"Correctos: {ok_count} | Con error: {err_count}")
            self._set_status(f"Cancelado. {ok_count} ok, {err_count} con error.")
            self.log_queue.put(("done", dst_dir if ok_count else None))
            self._popup_info(
                "Cancelado",
                f"Conversion cancelada.\n\n"
                f"Convertidos: {ok_count}\nCon error: {err_count}\n\n"
                f"Guardados en:\n{dst_dir}",
            )
            return
        self._log(f"\nFinalizado. Correctos: {ok_count} | Con error: {err_count}")
        self._set_status(f"Lote completado. {ok_count} ok, {err_count} con error.")
        self.log_queue.put(("done", dst_dir if ok_count else None))
        self._popup_info(
            "Lote completado",
            f"Conversion finalizada.\n\n"
            f"Convertidos: {ok_count}\nCon error: {err_count}\n\n"
            f"Guardados en:\n{dst_dir}",
        )

    def on_cancel(self):
        if self._working:
            self._cancel.set()
            self.btn_cancel.config(state="disabled")
            self._set_status("Cancelando... (terminando el archivo actual)")

    def on_open_output(self):
        path = self._last_output_dir
        if not path or not os.path.isdir(path):
            self._popup_error("Sin carpeta", "No hay una carpeta de destino valida.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:  # noqa: BLE001
            self._popup_error("Error", f"No se pudo abrir la carpeta:\n\n{e}")

    def _start_worker(self, target, *args):
        self._working = True
        self._cancel.clear()
        self.btn_file.config(state="disabled")
        self.btn_folder.config(state="disabled")
        self.btn_cancel.config(state="normal")
        t = threading.Thread(target=self._safe_run, args=(target, args), daemon=True)
        t.start()

    def _safe_run(self, target, args):
        try:
            target(*args)
        except Exception:  # noqa: BLE001
            self._log("ERROR INESPERADO:\n" + traceback.format_exc())
            self._set_status("Error inesperado.")
            self.log_queue.put(("done", None))

    def _popup_info(self, title, msg):
        self.root.after(0, lambda: messagebox.showinfo(title, msg))

    def _popup_error(self, title, msg):
        self.root.after(0, lambda: messagebox.showerror(title, msg))


def _make_root():
    """Crea la ventana raiz. Usa TkinterDnD (arrastrar y soltar) si esta disponible."""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk(), True
    except Exception:  # noqa: BLE001
        return tk.Tk(), False


def main():
    root, dnd_enabled = _make_root()
    try:
        # Mejora el escalado en pantallas de alta resolucion (Windows).
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    MarkItDownApp(root, dnd_enabled=dnd_enabled)
    root.mainloop()


if __name__ == "__main__":
    main()
