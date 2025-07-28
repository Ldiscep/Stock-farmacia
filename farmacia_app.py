import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import openpyxl
from datetime import datetime

import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmacia.db")

# --------- CONFIGURACIÓN DE LA BASE DE DATOS ---------
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
    conn.commit()
    conn.close()

# --------- FUNCIONES DE OPERACIÓN ---------
def actualizar_stock(nombre_droga, cantidad, operacion):
    conn = sqlite3.connect(DB_PATH)

    c = conn.cursor()
    c.execute("SELECT stock FROM drogas WHERE nombre LIKE ?", (nombre_droga,))
    result = c.fetchone()
    if result:
        nuevo_stock = result[0] + cantidad if operacion == 'ingreso' else result[0] - cantidad
        if nuevo_stock < 0:
            messagebox.showerror("Error", "Stock insuficiente para egreso.")
        else:
            c.execute("UPDATE drogas SET stock = ? WHERE nombre = ?", (nuevo_stock, nombre_droga))
            conn.commit()
            messagebox.showinfo("Éxito", f"Stock actualizado. Nuevo stock: {nuevo_stock}")
    else:
        messagebox.showerror("Error", "Droga no encontrada.")
    conn.close()
def limpiar_ventana():
    for widget in root.winfo_children():
        widget.destroy()

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
    ws.append(["Código", "Nombre", "Stock Actual"])

    # Filas de datos
    for fila in datos:
        ws.append(fila)

    # Guardar con timestamp en la misma carpeta que el script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stock_farmacia_{timestamp}.xlsx"
    filepath = os.path.join(script_dir, filename)
    wb.save(filepath)

    messagebox.showinfo("Exportación Exitosa", f"Se exportó correctamente a:\n{filepath}")

# --------- INTERFAZ ---------
def abrir_operacion(tipo):
    limpiar_ventana()

    root.title(f"{tipo.capitalize()} de Producto")

    tk.Label(root, text=f"{tipo.capitalize()} de Producto", font=('Arial', 16)).pack(pady=10)

    tk.Label(root, text="Buscar droga:").pack()
    entry_busqueda = tk.Entry(root, width=50)
    entry_busqueda.pack()

    lista = tk.Listbox(root, width=70, height=10)
    lista.pack(pady=5)

    def buscar(event=None):
        lista.delete(0, tk.END)
        texto = entry_busqueda.get().upper()
        conn = sqlite3.connect(DB_PATH)

        c = conn.cursor()
        c.execute("SELECT nombre, stock FROM drogas WHERE nombre LIKE ?", (f"%{texto}%",))
        for nombre, stock in c.fetchall():
            lista.insert(tk.END, f"{nombre}    Actual: {stock}")
        conn.close()

    entry_busqueda.bind("<KeyRelease>", buscar)

    tk.Label(root, text="Cantidad:").pack()
    entry_cantidad = tk.Entry(root)
    entry_cantidad.pack()

    def confirmar():
        seleccion = lista.curselection()
        if not seleccion:
            messagebox.showerror("Error", "Seleccioná una droga.")
            return
        nombre_con_stock = lista.get(seleccion[0])
        nombre = nombre_con_stock.split("    Actual:")[0].strip()
        try:
            cantidad = int(entry_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida.")
            return
        actualizar_stock(nombre, cantidad, tipo)
        abrir_menu_principal()  # volver al menú principal luego del ingreso/egreso

    tk.Button(root, text="Confirmar", command=confirmar, width=30).pack(pady=5)
    tk.Button(root, text="Volver al Menú", command=abrir_menu_principal, width=30).pack(pady=5)

# --------- MENÚ PRINCIPAL ---------
root = tk.Tk()
root.geometry("800x600")  # Tamaño más grande
def abrir_menu_principal():
    limpiar_ventana()

    root.title("Control de Stock de Drogas")
    tk.Label(root, text="Menú principal", font=('Arial', 16)).pack(pady=10)

    tk.Button(root, text="Ingreso de Producto", width=30, command=lambda: abrir_operacion("ingreso")).pack(pady=5)
    tk.Button(root, text="Egreso de Producto", width=30, command=lambda: abrir_operacion("egreso")).pack(pady=5)
    tk.Button(root, text="Exportar stock a Excel", width=30, command=exportar_a_excel).pack(pady=5)
    tk.Button(root, text="Salir", width=30, command=root.quit).pack(pady=5)

inicializar_db()
abrir_menu_principal()
root.mainloop()
