from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS NATIVA ---
# Esta función abre el archivo de la base de datos
def obtener_conexion():
    conexion = sqlite3.connect('tareas.db')
    conexion.row_factory = sqlite3.Row # Para leer los datos fácilmente
    return conexion

# Esta función crea la tabla "tareas" la primera vez que prendes el programa
def inicializar_bd():
    conexion = obtener_conexion()
    conexion.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            estado TEXT DEFAULT 'Pendiente'
        )
    ''')
    conexion.commit()
    conexion.close()

# Llamamos a la función para que prepare todo antes de arrancar
inicializar_bd()

# --- RUTAS DE LA PÁGINA ---
@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/tareas')
def tareas():
    conexion = obtener_conexion()
    # Le pedimos a SQLite que nos traiga todas las tareas guardadas
    tareas_db = conexion.execute('SELECT * FROM tareas').fetchall()
    conexion.close()
    
    return render_template('tareas.html', tareas_html=tareas_db)

@app.route('/agregar_tarea', methods=['POST'])
def agregar_tarea():
    nueva_desc = request.form.get('descripcion')
    
    # Abrimos conexión, guardamos la tarea nueva y cerramos
    conexion = obtener_conexion()
    conexion.execute('INSERT INTO tareas (descripcion) VALUES (?)', (nueva_desc,))
    conexion.commit()
    conexion.close()
    
    return redirect('/tareas')
@app.route('/eliminar_tarea/<int:id>')
def eliminar_tarea(id):
    conexion = obtener_conexion()
    # Le decimos a SQLite que borre la tarea que tenga este ID exacto
    conexion.execute('DELETE FROM tareas WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    return redirect('/tareas')

@app.route('/completar_tarea/<int:id>')
def completar_tarea(id):
    conexion = obtener_conexion()
    # Le decimos a SQLite que actualice el estado a "Completada"
    conexion.execute("UPDATE tareas SET estado = 'Completada' WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect('/tareas')

if __name__ == '__main__':
    app.run(debug=True)
    