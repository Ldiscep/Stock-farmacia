import sqlite3
import os
from datetime import datetime
import openpyxl
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, Listbox
from ttkbootstrap.widgets import DateEntry


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmacia.db")

# --------- INICIALIZAR BASE ---------
def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS drogas (
            codigo TEXT PRIMARY KEY,
            nombre TEXT,
            stock INTEGER DEFAULT 0
        )
    ''')
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

    c.execute('''
        CREATE TABLE IF NOT EXISTS ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER,
            fecha_vencimiento TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS vencidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER,
            fecha_vencimiento TEXT,
            fecha_detectado TEXT
        )
    ''')

    conn.commit()
    conn.close()

def procesar_vencidos():
    hoy = datetime.today().date()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nombre, cantidad, fecha_vencimiento FROM ingresos WHERE fecha_vencimiento IS NOT NULL")
    for id_, nombre, cantidad, fecha_str in c.fetchall():
        try:
            fecha_vto = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_vto < hoy:
                c.execute("UPDATE drogas SET stock = stock - ? WHERE nombre = ?", (cantidad, nombre))
                c.execute("INSERT INTO vencidos (nombre, cantidad, fecha_vencimiento, fecha_detectado) VALUES (?, ?, ?, ?)",
                          (nombre, cantidad, fecha_str, hoy.isoformat()))
                c.execute("DELETE FROM ingresos WHERE id = ?", (id_,))
        except:
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
    c.execute("SELECT codigo, nombre, stock FROM drogas ORDER BY nombre ASC")
    datos = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock Drogas"

    # Encabezados
    ws.append(["Código", "Nombre", "Stock Actual", "Próximo Vto", "Cantidad a Vencer"])

    for codigo, nombre, stock in datos:
        fecha_vto, cantidad_vto = obtener_proximo_vencimiento(nombre)
        if fecha_vto:
            fecha_str = datetime.strptime(fecha_vto, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            fecha_str = ""
            cantidad_vto = ""
        ws.append([codigo, nombre, stock, fecha_str, cantidad_vto])

    archivo = os.path.join(os.path.dirname(__file__), f"stock_farmacia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb.save(archivo)
    messagebox.showinfo("Exportación Exitosa", f"Archivo guardado:\n{archivo}")


def mostrar_vencidos():
    limpiar_ventana()
    ttk.Label(app, text="Elementos Vencidos", font=('Segoe UI', 18)).pack(pady=10)
    lista = Listbox(app, width=70, height=20)
    lista.pack(pady=10)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nombre, cantidad, fecha_vencimiento, fecha_detectado FROM vencidos ORDER BY fecha_detectado DESC")
    for nombre, cantidad, vencimiento, detectado in c.fetchall():
        lista.insert('end', f"{nombre} - Cant: {cantidad} - Vto: {vencimiento} - Detectado: {detectado}")
    conn.close()
    ttk.Button(app, text="Volver al Menú", bootstyle=SECONDARY, command=abrir_menu_principal).pack(pady=10)

def abrir_operacion(tipo):
    limpiar_ventana()
    ttk.Label(app, text=f"{tipo.capitalize()} de Producto", font=('Segoe UI', 18)).pack(pady=10)
    ttk.Label(app, text="Buscar droga:").pack()
    entry_busqueda = ttk.Entry(app, width=50)
    entry_busqueda.pack(pady=5)
    lista = Listbox(app, width=70, height=10)
    lista.pack(pady=5)

    def buscar(event=None):
        lista.delete(0, 'end')
        texto = entry_busqueda.get().upper()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        if texto:
            c.execute("SELECT nombre, stock FROM drogas WHERE nombre LIKE ? ORDER BY stock DESC", (f"%{texto}%",))
        else:
            c.execute("SELECT nombre, stock FROM drogas ORDER BY stock DESC")

        hoy = datetime.today().date()

        for idx, (nombre, stock) in enumerate(c.fetchall()):
            fecha_vto, cantidad_vto = obtener_proximo_vencimiento(nombre)
            extra = ""
            color = "black"  # color por defecto

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




    entry_busqueda.bind("<KeyRelease>", buscar)
    buscar()

    ttk.Label(app, text="Cantidad:").pack()
    entry_cantidad = ttk.Entry(app)
    entry_cantidad.pack(pady=5)

    ttk.Label(app, text="Fecha de vencimiento (opcional):").pack()
    entry_fecha = DateEntry(app, dateformat="%d/%m/%Y", width=20)
    entry_fecha.pack(pady=5)


    def confirmar():
        seleccion = lista.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Seleccioná una droga.")
            return
        nombre = lista.get(seleccion[0]).split("    ")[0].strip()
        try:
            cantidad = int(entry_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Cantidad inválida.")
            return
        actualizar_stock(nombre, cantidad, tipo)
        if tipo == "ingreso":
            fecha = entry_fecha.entry.get()

        if fecha:
            try:
                fecha_vto = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO ingresos (nombre, cantidad, fecha_vencimiento) VALUES (?, ?, ?)",
                        (nombre, cantidad, fecha_vto))
                conn.commit()
                conn.close()
            except:
                pass
                
        abrir_menu_principal()

    ttk.Button(app, text="Confirmar", bootstyle=SUCCESS, command=confirmar, width=30).pack(pady=5)
    ttk.Button(app, text="Volver al Menú", bootstyle=SECONDARY, command=abrir_menu_principal, width=30).pack(pady=5)

def abrir_menu_principal():
    limpiar_ventana()
    ttk.Label(app, text="Control de Stock de Drogas", font=('Segoe UI', 20)).pack(pady=20)
    ttk.Button(app, text="Ingreso de Producto", width=30, bootstyle=SUCCESS, command=lambda: abrir_operacion("ingreso")).pack(pady=10)
    ttk.Button(app, text="Egreso de Producto", width=30, bootstyle=WARNING, command=lambda: abrir_operacion("egreso")).pack(pady=10)
    ttk.Button(app, text="Exportar stock a Excel", width=30, bootstyle=INFO, command=exportar_a_excel).pack(pady=10)
    ttk.Button(app, text="Elementos vencidos", width=30, bootstyle=SECONDARY, command=mostrar_vencidos).pack(pady=10)
    # Leyenda de colores - productos por vencer
    frame_leyenda = ttk.Frame(app)
    frame_leyenda.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-20)

    ttk.Label(frame_leyenda, text="● Vencido", foreground="red", font=('Segoe UI', 9)).pack(anchor="e", pady=1)
    ttk.Label(frame_leyenda, text="● Vence en ≤7 días", foreground="orange", font=('Segoe UI', 9)).pack(anchor="e", pady=1)
    ttk.Label(frame_leyenda, text="● Sin vencimiento próximo", foreground="black", font=('Segoe UI', 9)).pack(anchor="e", pady=1)

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
