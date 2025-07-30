import sqlite3
import os
from datetime import datetime, timedelta
import openpyxl
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, Listbox
from ttkbootstrap.widgets import DateEntry
import sys
from PIL import Image, ImageTk






def obtener_ruta_base():
    if getattr(sys, 'frozen', False):
        # Ejecutándose como .exe
        return os.path.dirname(sys.executable)
    else:
        # Ejecutándose como script .py
        return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(obtener_ruta_base(), "farmacia.db")

# --------- INICIALIZAR BASE ---------
def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Crear tabla principal de drogas
    c.execute('''
        CREATE TABLE IF NOT EXISTS drogas (
            codigo TEXT PRIMARY KEY,
            nombre TEXT,
            stock INTEGER DEFAULT 0
        )
    ''')

    # Drogas predefinidas
    drogas = [
            ("M-A01", "ACIDO TRANEXAMICO"), ("M-A02", "ADRENALINA"), ("M-A03", "AMINOFILINA"),
            ("M-A04", "ATRACURIO"), ("M-A05", "ATROPINA"), ("M-B06", "BETAMETASONA"),
            ("M-B07", "BETAMETASONA CRONO"), ("M-B08", "BETAMETASONA CRONO KIT"),
            ("M-B09", "BICARBONATO 100ML"), ("M-B10", "BUPIVACAINA HIPERBARICA"),
            ("M-B11", "BUPIVACAINA ISOBARICA"), ("M-C12", "CARTICAINA"), ("M-C13", "CEFAZOLINA"),
            ("M-C14", "CIPROFLOXACINA"), ("M-C15", "CLINDAMICINA"), ("M-C16", "CLONIDINA"),
            ("M-C17", "CLORURADA HIPERTONICA"), ("M-C18", "CLORURO DE CALCIO"), ("M-D19", "DEXAMETASONA"),
            ("M-D20", "DICLOFENAC"), ("M-D21", "DIFENHIDRAMINA"), ("M-D22", "DIPIRONA"),
            ("M-D23", "DOBUTAMINA"), ("M-D24", "DOPAMINA"), ("M-E25", "ETILEFRINA"),
            ("M-F26", "FENILEFRINA"), ("M-F27", "FENTANILO"), ("M-F28", "FLUMAZENIL"),
            ("M-G29", "GENTAMICINA"), ("M-G30", "GLUCONATO DE CALCIO"), ("M-G31", "GLUCOSADA HIPERTONICA"),
            ("M-H32", "HEPARINA"), ("M-H33", "HIDROCORTISONA"), ("M-K34", "KETOROLAC"),
            ("M-L35", "LIDOCAINA 20ML"), ("M-L36", "LIDOCAINA 5ML"), ("M-L37", "LIDOCAINA C/EPINEFRINA"),
            ("M-L38", "LIDOCAINA JALEA"), ("M-M39", "METOCLOPRAMIDA"), ("M-M40", "METRONIDAZOL"),
            ("M-M41", "MIDAZOLAM"), ("M-N42", "NORADRENALINA"), ("M-N43", "NTG"),
            ("M-O44", "ONDASENTRON"), ("M-P45", "PROPOFOL"), ("M-R46", "RANITIDINA"),
            ("M-R47", "REMIFENTANILO"), ("M-R48", "RINGER LACTATO"), ("M-S49", "SEVOFLURANO/ SEVORANE"),
            ("M-S50", "SOL. DEXTROSA EN AGUA"), ("M-S51", "SUCCINICOLINA"), ("M-T52", "TRAMADOL"),
            ("M-V53", "VANCOMICINA"), ("M-A54", "AMIODARONA"), ("M-G55", "GELATINA MODIFICADA"),
            ("M-N56", "NALOXONA")
        ]
    for codigo, nombre in drogas:
        c.execute("INSERT OR IGNORE INTO drogas (codigo, nombre, stock) VALUES (?, ?, 0)", (codigo, nombre))

    # Crear tabla ingresos con lote
    c.execute('''
        CREATE TABLE IF NOT EXISTS ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER,
            fecha_vencimiento TEXT,
            lote TEXT
        )
    ''')

    # Crear tabla vencidos con lote
    c.execute('''
        CREATE TABLE IF NOT EXISTS vencidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER,
            fecha_vencimiento TEXT,
            fecha_detectado TEXT,
            lote TEXT
        )
    ''')

    # Agregar columna lote si no existe (para bases antiguas)
    try:
        c.execute("ALTER TABLE ingresos ADD COLUMN lote TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE vencidos ADD COLUMN lote TEXT")
    except sqlite3.OperationalError:
        pass
            # Agregar columna recuperado si no existe
    try:
        c.execute("ALTER TABLE vencidos ADD COLUMN recuperado INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def procesar_vencidos():
    hoy = datetime.today().date()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, nombre, cantidad, fecha_vencimiento, lote FROM ingresos WHERE fecha_vencimiento IS NOT NULL")
    for id_, nombre, cantidad, fecha_str, lote in c.fetchall():
        try:
            fecha_vto = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_vto < hoy:
                # Verificamos si ya fue vencido y recuperado
                c.execute('''
                    SELECT 1 FROM vencidos
                    WHERE nombre = ? AND fecha_vencimiento = ? AND lote = ? AND recuperado = 1
                ''', (nombre, fecha_str, lote))
                if c.fetchone():
                    continue  # ya fue procesado y recuperado, no volver a vencerlo

                # Si no fue recuperado, se vence normalmente
                c.execute("UPDATE drogas SET stock = stock - ? WHERE nombre = ?", (cantidad, nombre))
                c.execute('''
                    INSERT INTO vencidos (nombre, cantidad, fecha_vencimiento, fecha_detectado, lote, recuperado)
                    VALUES (?, ?, ?, ?, ?, 0)
                ''', (nombre, cantidad, fecha_str, hoy.isoformat(), lote))
                c.execute("DELETE FROM ingresos WHERE id = ?", (id_,))
        except Exception as e:
            print(f"Error procesando vencido: {e}")
            continue

    conn.commit()
    conn.close()


def limpiar_ventana():
    for widget in app.winfo_children():
        widget.destroy()

def actualizar_stock(nombre_droga, cantidad, operacion):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT stock FROM drogas WHERE nombre = ?", (nombre_droga,))
    result = c.fetchone()
    if result:
        nuevo_stock = result[0] + cantidad if operacion == 'ingreso' else result[0] - cantidad
        if nuevo_stock < 0:
            messagebox.showerror("Error", "Stock insuficiente para egreso.")
        else:
            c.execute("UPDATE drogas SET stock = ? WHERE nombre = ?", (nuevo_stock, nombre_droga))
            conn.commit()
            messagebox.showinfo("Éxito", f"Nuevo stock: {nuevo_stock}")
    conn.close()

def exportar_a_excel():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    wb = openpyxl.Workbook()

    # Hoja 1: Stock por lote
    ws_stock = wb.active
    ws_stock.title = "Stock Drogas"
    ws_stock.append(["Código", "Nombre", "Lote", "Cantidad", "Fecha Vencimiento"])

    c.execute('''
        SELECT d.codigo, i.nombre, i.lote, i.cantidad, i.fecha_vencimiento
        FROM ingresos i
        JOIN drogas d ON i.nombre = d.nombre
        ORDER BY i.nombre, i.fecha_vencimiento ASC
    ''')

    for codigo, nombre, lote, cantidad, fecha_vto in c.fetchall():
        fecha_fmt = datetime.strptime(fecha_vto, "%Y-%m-%d").strftime("%d/%m/%Y") if fecha_vto else ""
        ws_stock.append([
            codigo,
            nombre,
            lote if lote else "N/A",
            cantidad,
            fecha_fmt
        ])

    # Hoja 2: Vencidos
    ws_vencidos = wb.create_sheet("Vencidos")
    ws_vencidos.append(["Nombre", "Cantidad", "Fecha Vencimiento", "Detectado", "Lote"])
    c.execute("SELECT nombre, cantidad, fecha_vencimiento, fecha_detectado, lote FROM vencidos ORDER BY fecha_detectado DESC")
    for nombre, cantidad, vto, detectado, lote in c.fetchall():
        ws_vencidos.append([nombre, cantidad, vto, detectado, lote or "N/A"])

    conn.close()

    archivo = os.path.join(obtener_ruta_base(), f"stock_farmacia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    wb.save(archivo)
    messagebox.showinfo("Exportación Exitosa", f"Archivo guardado:\n{archivo}")
def agregar_insumo():
    limpiar_ventana()
    ttk.Label(app, text="Agregar Nuevo Insumo", font=('Segoe UI', 18)).pack(pady=10)

    ttk.Label(app, text="Código del insumo (opcional):").pack()
    entry_codigo = ttk.Entry(app)
    entry_codigo.pack(pady=5)

    ttk.Label(app, text="Nombre del insumo:").pack()
    entry_nombre = ttk.Entry(app)
    entry_nombre.pack(pady=5)

    def confirmar_agregado():
        nombre = entry_nombre.get().strip().upper()
        codigo = entry_codigo.get().strip().upper()

        if not nombre:
            messagebox.showerror("Error", "Debe ingresar un nombre de insumo.")
            return

        if not codigo:
            # generar un código automático si no se proporciona
            codigo = f"AUTO-{datetime.now().strftime('%H%M%S')}"

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO drogas (codigo, nombre, stock) VALUES (?, ?, 0)", (codigo, nombre))
            conn.commit()
            messagebox.showinfo("Éxito", f"Insumo '{nombre}' agregado.")
            abrir_menu_principal()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ese código ya existe.")
        finally:
            conn.close()

    ttk.Button(app, text="Agregar", bootstyle=SUCCESS, command=confirmar_agregado).pack(pady=5)
    ttk.Button(app, text="Volver al menú", bootstyle=SECONDARY, command=abrir_menu_principal).pack(pady=5)

def borrar_base_de_datos():
    if not messagebox.askyesno("Confirmación", "¿Seguro que querés borrar todos los datos?\nTambién se borrarán los insumos añadidos al menú.\nEsta acción no se puede deshacer."):
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS drogas")
    c.execute("DROP TABLE IF EXISTS ingresos")
    c.execute("DROP TABLE IF EXISTS vencidos")

    conn.commit()
    conn.close()

    inicializar_db()
    messagebox.showinfo("Base de Datos", "La base de datos fue reiniciada correctamente.")
    abrir_menu_principal()



def mostrar_vencidos():
    limpiar_ventana()
    ttk.Label(app, text="Elementos Vencidos", font=('Segoe UI', 18)).pack(pady=10)
    lista = Listbox(app, width=110, height=20)
    lista.pack(pady=10)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nombre, cantidad, fecha_vencimiento, fecha_detectado, lote, recuperado FROM vencidos ORDER BY fecha_detectado DESC")
    vencidos_data = c.fetchall()
    conn.close()

    id_map = {}
    for idx, (id_, nombre, cantidad, fecha_vencimiento, fecha_detectado, lote, recuperado) in enumerate(vencidos_data):
        lote_str = f"Lote: {lote}" if lote else "Lote: N/A"
        estado = "✅ RECUPERADO" if recuperado else "🛑 NO RECUPERADO"
        lista.insert('end', f"{nombre} - Cant: {cantidad} - Vto: {fecha_vencimiento} - Detectado: {fecha_detectado} - {lote_str} - {estado}")
        id_map[idx] = (id_, nombre, cantidad, fecha_vencimiento, lote, recuperado)

    def recuperar_lote():
        seleccion = lista.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Seleccioná un lote para recuperar.")
            return

        idx = seleccion[0]
        id_, nombre, cantidad, fecha_vto, lote, recuperado = id_map[idx]

        if recuperado:
            messagebox.showinfo("Ya recuperado", "Este lote ya fue recuperado.")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # 1. Insertar en ingresos
        c.execute("INSERT INTO ingresos (nombre, cantidad, fecha_vencimiento, lote) VALUES (?, ?, ?, ?)",
                  (nombre, cantidad, fecha_vto, lote))

        # 2. Sumar al stock general
        c.execute("UPDATE drogas SET stock = stock + ? WHERE nombre = ?", (cantidad, nombre))

        # 3. Marcar como recuperado
        c.execute("UPDATE vencidos SET recuperado = 1 WHERE id = ?", (id_,))

        conn.commit()
        conn.close()

        messagebox.showinfo("Recuperado", f"Lote {lote or 'N/A'} de {nombre} fue recuperado al stock.")
        mostrar_vencidos()

    ttk.Button(app, text="Recuperar lote seleccionado", bootstyle=SUCCESS, command=recuperar_lote).pack(pady=5)
    ttk.Button(app, text="Volver al Menú", bootstyle=SECONDARY, command=abrir_menu_principal).pack(pady=5)



def consultar_stock_total():
    limpiar_ventana()
    ttk.Label(app, text="Stock Total de Drogas", font=('Segoe UI', 18, 'bold')).pack(pady=20)

    # Búsqueda
    frame_busqueda = ttk.Frame(app)
    frame_busqueda.pack(fill='x', padx=20, pady=(0, 5), anchor="ne")

    ttk.Label(frame_busqueda, text="Buscar:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 5))
    entry_busqueda = ttk.Entry(frame_busqueda, font=("Segoe UI", 11), width=30)
    entry_busqueda.pack(side="left", padx=(0, 5))

    # Treeview
    columns = ("nombre", "stock", "lote", "fecha_vto", "cantidad_vto")
    tree = ttk.Treeview(app, columns=columns, show="headings", bootstyle="info")
    tree.pack(fill='both', expand=True, padx=20, pady=10)

    for col, text, width in zip(columns, ["Nombre", "Stock", "Lote", "Próximo Vto", "A Vencer"],
                                 [250, 80, 150, 120, 100]):
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor="center" if col != "nombre" else "w")

    tree.tag_configure("vencido", foreground="red")
    tree.tag_configure("cercano", foreground="orange")
    tree.tag_configure("normal", foreground="black")

    combo_lotes = {}

    def cargar_datos(filtro=""):
        for item in tree.get_children():
            tree.delete(item)
        combo_lotes.clear()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        hoy = datetime.today().date()

        c.execute('SELECT nombre, stock FROM drogas ORDER BY nombre ASC')
        drogas = c.fetchall()

        for nombre, stock in drogas:
            c.execute("SELECT codigo FROM drogas WHERE nombre = ?", (nombre,))
            row = c.fetchone()
            codigo = row[0] if row else ""


            if filtro and filtro not in nombre.lower() and filtro not in codigo.lower():
                continue

            c.execute('''
                SELECT lote, fecha_vencimiento, SUM(cantidad)
                FROM ingresos
                WHERE nombre = ? AND lote IS NOT NULL
                GROUP BY lote, fecha_vencimiento
                ORDER BY fecha_vencimiento ASC
            ''', (nombre,))
            lotes = c.fetchall()

            if not lotes:
                tree.insert("", "end", values=(nombre, stock, "N/A", "", ""), tags=("normal",))
                continue

            for lote, fecha_str, cantidad in lotes:
                # Chequear si este lote fue recuperado
                c.execute('''
                    SELECT 1 FROM vencidos
                    WHERE nombre = ? AND fecha_vencimiento = ? AND lote = ? AND recuperado = 1
                ''', (nombre, fecha_str, lote))
                fue_recuperado = c.fetchone() is not None

                if not fecha_str:
                    fecha_fmt, tag = "", "normal"
                else:
                    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    fecha_fmt = fecha_dt.strftime("%d/%m/%Y")
                    dias = (fecha_dt - hoy).days
                    tag = "vencido" if dias < 0 else "cercano" if dias <= 7 else "normal"

                lote_mostrar = f"{lote} [RECUPERADO]" if fue_recuperado else lote
                item_id = tree.insert("", "end", values=(nombre, stock, lote_mostrar, fecha_fmt, cantidad), tags=(tag,))



    def actualizar_lote(event):
        item_id = tree.focus()
        if not item_id:
            return

        selected_lote = lote_selector.get()
        values = tree.item(item_id)["values"]
        nombre = values[0]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT fecha_vencimiento, SUM(cantidad)
            FROM ingresos
            WHERE nombre = ? AND lote = ? AND fecha_vencimiento IS NOT NULL
            GROUP BY fecha_vencimiento
            ORDER BY fecha_vencimiento ASC
            LIMIT 1
        ''', (nombre, selected_lote))
        row = c.fetchone()
        conn.close()

        if row:
            fecha_str, cantidad = row
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            fecha_fmt = fecha_dt.strftime("%d/%m/%Y")
            dias = (fecha_dt - datetime.today().date()).days
            tag = "vencido" if dias < 0 else "cercano" if dias <= 7 else "normal"
        else:
            fecha_fmt, cantidad, tag = "", "", "normal"

        tree.item(item_id, values=(nombre, values[1], selected_lote, fecha_fmt, cantidad), tags=(tag,))

    def filtrar_resultados(event=None):
        texto = entry_busqueda.get().strip().lower()
        cargar_datos(filtro=texto)

    entry_busqueda.bind("<KeyRelease>", filtrar_resultados)
    entry_busqueda.bind("<Return>", filtrar_resultados)
    ttk.Button(frame_busqueda, text="Buscar", bootstyle="primary", command=filtrar_resultados).pack(side="left")

    cargar_datos()

    # Combobox flotante
    lote_selector = ttk.Combobox(app, state="readonly", width=15)
    lote_selector.place_forget()

    def mostrar_combobox(event):
        item_id = tree.identify_row(event.y)
        col = tree.identify_column(event.x)

        if not item_id or col != "#3":  # Solo mostrar en columna "Lote"
            lote_selector.place_forget()
            return

        values = tree.item(item_id)["values"]
        lotes = combo_lotes.get(item_id, [])
        if not lotes:
            lote_selector.place_forget()
            return

        lote_selector['values'] = lotes
        lote_selector.set(values[2])  # Lote actual

        bbox = tree.bbox(item_id, column="lote")
        if bbox:
            x, y, width, height = bbox
            x_abs = tree.winfo_rootx() + x
            y_abs = tree.winfo_rooty() + y

            lote_selector.place_forget()  # Ocultar cualquier anterior
            lote_selector.place(x=x_abs - app.winfo_rootx(), y=y_abs - app.winfo_rooty(), width=width)
            lote_selector.lift()


    lote_selector.bind("<<ComboboxSelected>>", actualizar_lote)
    tree.bind("<Button-1>", mostrar_combobox)

    ttk.Button(app, text="Volver", bootstyle=SECONDARY, command=abrir_menu_principal).pack(pady=10)



seleccion_actual = None  # <-- para guardar droga seleccionada manualmente

def abrir_operacion(tipo):
    droga_seleccionada = {"nombre": None}  # usar dict mutable para alcance dentro de funciones internas

    limpiar_ventana()
    ttk.Label(app, text=f"{tipo.capitalize()} de Producto", font=('Segoe UI', 18)).pack(pady=10)
    ttk.Label(app, text="Buscar droga:").pack()

    entry_busqueda = ttk.Entry(app, width=50)
    entry_busqueda.pack(pady=5)
    lista = Listbox(app, width=70, height=10)
    lista.pack(pady=5)

    frame_dinamico = ttk.Frame(app)
    frame_dinamico.pack(pady=10)

    entry_cantidad = ttk.Entry(frame_dinamico)
    entry_lote = ttk.Entry(frame_dinamico)
    combo_lotes = ttk.Combobox(frame_dinamico, state="readonly", width=40)

    ttk.Label(frame_dinamico, text="Cantidad:").pack()
    entry_cantidad.pack(pady=5)

    ttk.Label(frame_dinamico, text="Número de lote (opcional):").pack()
    if tipo == "ingreso":
        entry_lote.pack(pady=5)
    else:
        combo_lotes.pack(pady=5)

    ttk.Label(frame_dinamico, text="Fecha de vencimiento (opcional):").pack()
    entry_fecha = DateEntry(frame_dinamico, dateformat="%d/%m/%Y", width=20)
    entry_fecha.pack(pady=5 if tipo == "ingreso" else 0)

    def buscar(event=None):
        lista.delete(0, 'end')
        texto = entry_busqueda.get().upper()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        if texto:
            c.execute("SELECT nombre, stock FROM drogas WHERE nombre LIKE ? OR codigo LIKE ? ORDER BY stock DESC", (f"%{texto}%", f"%{texto}%"))

        else:
            c.execute("SELECT nombre, stock FROM drogas ORDER BY stock DESC")

        hoy = datetime.today().date()
        for idx, (nombre, stock) in enumerate(c.fetchall()):
            fecha_vto, cantidad_vto = obtener_proximo_vencimiento(nombre)
            extra = ""
            color = "black"
            if fecha_vto:
                fecha_dt = datetime.strptime(fecha_vto, "%Y-%m-%d").date()
                dias_restantes = (fecha_dt - hoy).days
                fecha_str = fecha_dt.strftime("%d/%m/%Y")
                extra = f" | Vto más próximo: {fecha_str} ({cantidad_vto})"
                if dias_restantes <= 7:
                    color = "orange"
                if dias_restantes <= 0:
                    color = "red"

            item_text = f"{nombre}    Stock: {stock}{extra}"
            lista.insert('end', item_text)
            lista.itemconfig(idx, foreground=color)
        conn.close()

    def actualizar_lotes_disponibles(event=None):
        if tipo != "egreso":
            return

        seleccion = lista.curselection()
        if not seleccion:
            return

        nombre = lista.get(seleccion[0]).split("    ")[0].strip()
        droga_seleccionada["nombre"] = nombre  # guardamos la droga seleccionada

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT lote, SUM(cantidad) FROM ingresos WHERE nombre = ? AND lote IS NOT NULL GROUP BY lote", (nombre,))
        lotes = c.fetchall()
        conn.close()

        if lotes:
            combo_lotes['values'] = [f"{lote} (Stock: {cant})" for lote, cant in lotes]
            combo_lotes.set(combo_lotes['values'][0])
        else:
            combo_lotes.set('')
            combo_lotes['values'] = []


    def guardar_seleccion(event=None):
        global seleccion_actual
        sel = lista.curselection()
        if sel:
            seleccion_actual = sel[0]
            actualizar_lotes_disponibles()

    lista.bind("<<ListboxSelect>>", guardar_seleccion)

    entry_busqueda.bind("<KeyRelease>", buscar)
    entry_busqueda.bind("<Return>", buscar)
    buscar()

    def confirmar():
        global seleccion_actual
        if seleccion_actual is None:
            messagebox.showerror("Error", "Seleccioná una droga.")
            return
        nombre = lista.get(seleccion_actual).split("    ")[0].strip()

        try:
            cantidad = int(entry_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Cantidad inválida.")
            return

        lote = ""
        fecha_vto = None
        if tipo == "ingreso":
            lote = entry_lote.get().strip() or None
            fecha = entry_fecha.entry.get()
            if fecha:
                try:
                    fecha_vto = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
                except:
                    fecha_vto = None

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO ingresos (nombre, cantidad, fecha_vencimiento, lote) VALUES (?, ?, ?, ?)",
                      (nombre, cantidad, fecha_vto, lote))
            conn.commit()
            conn.close()

        elif tipo == "egreso":
            if combo_lotes.get():
                lote = combo_lotes.get().split(" (")[0]
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT cantidad FROM ingresos WHERE nombre = ? AND lote = ? ORDER BY fecha_vencimiento ASC",
                          (nombre, lote))
                fila = c.fetchone()
                if not fila or fila[0] < cantidad:
                    messagebox.showerror("Error", f"Stock insuficiente en lote {lote}.")
                    return
                c.execute("UPDATE ingresos SET cantidad = cantidad - ? WHERE nombre = ? AND lote = ?",
                          (cantidad, nombre, lote))
                c.execute("DELETE FROM ingresos WHERE cantidad = 0")
                conn.commit()
                conn.close()

        actualizar_stock(nombre, cantidad, tipo)
        buscar()  # recarga los datos actuales
        entry_cantidad.delete(0, 'end')
        entry_lote.delete(0, 'end') if tipo == "ingreso" else combo_lotes.set('')


    ttk.Button(app, text="Confirmar", bootstyle=SUCCESS, command=confirmar, width=30).pack(pady=5)
    ttk.Button(app, text="Volver al Menú", bootstyle=SECONDARY, command=abrir_menu_principal, width=30).pack(pady=5)

def editar_insumos():
    limpiar_ventana()
    ttk.Label(app, text="Modificar o Eliminar Insumos", font=('Segoe UI', 18)).pack(pady=10)

    lista = Listbox(app, width=60, height=15)
    lista.pack(pady=5)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT codigo, nombre FROM drogas ORDER BY nombre ASC")
    items = c.fetchall()
    conn.close()

    for cod, nom in items:
        lista.insert("end", f"{cod} - {nom}")

    ttk.Label(app, text="Nuevo nombre:").pack()
    entry_nuevo_nombre = ttk.Entry(app, width=50)
    entry_nuevo_nombre.pack(pady=5)

    def modificar():
        sel = lista.curselection()
        if not sel:
            messagebox.showerror("Error", "Seleccioná un insumo.")
            return
        idx = sel[0]
        cod = items[idx][0]
        nuevo_nombre = entry_nuevo_nombre.get().strip().upper()
        if not nuevo_nombre:
            messagebox.showerror("Error", "Ingresá un nuevo nombre.")
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE drogas SET nombre = ? WHERE codigo = ?", (nuevo_nombre, cod))
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", "Nombre modificado correctamente.")
        editar_insumos()

    def eliminar():
        sel = lista.curselection()
        if not sel:
            messagebox.showerror("Error", "Seleccioná un insumo.")
            return
        idx = sel[0]
        cod = items[idx][0]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el insumo {cod}?"):
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM drogas WHERE codigo = ?", (cod,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Eliminado", "Insumo eliminado correctamente.")
        editar_insumos()

    ttk.Button(app, text="Modificar nombre", bootstyle=PRIMARY, command=modificar).pack(pady=2)
    ttk.Button(app, text="Eliminar insumo", bootstyle=DANGER, command=eliminar).pack(pady=2)
    ttk.Button(app, text="Volver al menú", bootstyle=SECONDARY, command=abrir_menu_principal).pack(pady=10)


def abrir_menu_principal():
    limpiar_ventana()

    # Mostrar logo
    try:
        ruta_base = obtener_ruta_base()
        logo_path = os.path.join(ruta_base, "logo.png")  # o el nombre que uses

        img = Image.open(logo_path)
        img = img.resize((400, 200))  # Ajustá tamaño si querés
        logo_tk = ImageTk.PhotoImage(img)

        logo_label = ttk.Label(app, image=logo_tk)
        logo_label.image = logo_tk  # guardá referencia para evitar que se borre
        logo_label.pack(pady=(10, 0))
    except Exception as e:
        print("No se pudo cargar el logo:", e)

    ttk.Label(app, text="Control de Stock de Drogas e Insumos", font=('Segoe UI', 20)).pack(pady=20)
    ttk.Button(app, text="Ingreso de Producto", width=30, bootstyle=PRIMARY, command=lambda: abrir_operacion("ingreso")).pack(pady=10)
    ttk.Button(app, text="Egreso de Producto", width=30, bootstyle=WARNING, command=lambda: abrir_operacion("egreso")).pack(pady=10)
    ttk.Button(app, text="Consultar Stock Total", width=30, bootstyle=SECONDARY, command=consultar_stock_total).pack(pady=10)
    ttk.Button(app, text="Exportar stock a Excel", width=30, bootstyle=SUCCESS, command=exportar_a_excel).pack(pady=10)
    ttk.Button(app, text="Elementos vencidos", width=30, bootstyle=SECONDARY, command=mostrar_vencidos).pack(pady=10)
    ttk.Button(app, text="Agregar insumo", width=30, bootstyle=INFO, command=agregar_insumo).pack(pady=10)
    ttk.Button(app, text="Modificar/Eliminar Insumo", width=30, bootstyle=WARNING, command=editar_insumos).pack(pady=10)

    # Leyenda de colores - productos por vencer
    frame_leyenda = ttk.Frame(app)
    frame_leyenda.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-20)

    ttk.Label(frame_leyenda, text="● Vencido", foreground="red", font=('Segoe UI', 9)).pack(anchor="e", pady=1)
    ttk.Label(frame_leyenda, text="● Vence en ≤7 días", foreground="orange", font=('Segoe UI', 9)).pack(anchor="e", pady=1)
    ttk.Label(frame_leyenda, text="● Sin vencimiento próximo", foreground="black", font=('Segoe UI', 9)).pack(anchor="e", pady=1)
    # Botón para borrar base de datos (abajo a la izquierda)
    btn_borrar = ttk.Button(app, text="🗑 Borrar DB", bootstyle="danger-outline", command=borrar_base_de_datos)
    btn_borrar.place(relx=0.0, rely=1.0, anchor='sw', x=20, y=-20)

    ttk.Button(app, text="Salir", width=30, bootstyle=DANGER, command=app.quit).pack(pady=10)
    procesar_vencidos()


# --------- EJECUCIÓN ---------
app = ttk.Window(themename="cosmo")
app.title("Farmacia - Control de Stock")
app.geometry("800x600")
# --------- DETECTAR VENCIMIENTO MÁS PRÓXIMO ---------
def obtener_proximo_vencimiento(nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT fecha_vencimiento, SUM(cantidad)
        FROM ingresos
        WHERE nombre = ? AND fecha_vencimiento IS NOT NULL
        GROUP BY fecha_vencimiento
        ORDER BY fecha_vencimiento ASC
        LIMIT 1
    ''', (nombre,))
    row = c.fetchone()
    conn.close()
    return row if row else (None, 0)

inicializar_db()
procesar_vencidos()
abrir_menu_principal()
app.mainloop()
