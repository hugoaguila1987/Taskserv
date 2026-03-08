from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
# Esta llave secreta es obligatoria para que Flask encripte las sesiones de los usuarios
app.secret_key = 'llave_super_secreta_de_taskserv' 

# --- CONFIGURACIÓN DE LA BASE DE DATOS NATIVA ---
def obtener_conexion():
    conexion = sqlite3.connect('tareas.db')
    conexion.row_factory = sqlite3.Row 
    return conexion

def inicializar_bd():
    conexion = obtener_conexion()
    
    # 1. Creamos la nueva tabla de USUARIOS
    conexion.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 2. Actualizamos la tabla de TAREAS (¡Ahora tienen dueño!)
    conexion.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    conexion.commit()
    conexion.close()

# Llamamos a la función para que prepare todo antes de arrancar
inicializar_bd()

# --- RUTAS DE ACCESO (LOGIN Y REGISTRO) ---
@app.route('/')
def inicio():
    # Si el usuario ya inició sesión, lo mandamos directo a sus tareas
    if 'usuario_id' in session:
        return redirect('/tareas')
    # Si no, le mostramos la pantalla de login
    return render_template('login.html')

@app.route('/registro', methods=['POST'])
def registro():
    nombre = request.form.get('nombre_usuario')
    password = request.form.get('password') # Nota: En un sistema real esto se encripta
    
    conexion = obtener_conexion()
    try:
        # Intentamos guardar al nuevo usuario
        conexion.execute('INSERT INTO usuarios (nombre_usuario, password) VALUES (?, ?)', (nombre, password))
        conexion.commit()
    except sqlite3.IntegrityError:
        # Si el usuario ya existe, SQLite nos avisa y no hace nada
        pass 
    conexion.close()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    nombre = request.form.get('nombre_usuario')
    password = request.form.get('password')
    
    conexion = obtener_conexion()
    # Buscamos si existe alguien con ese usuario y contraseña
    usuario = conexion.execute('SELECT * FROM usuarios WHERE nombre_usuario = ? AND password = ?', (nombre, password)).fetchone()
    conexion.close()
    
    if usuario:
        # Si existe, guardamos su ID en la "memoria" (session)
        session['usuario_id'] = usuario['id']
        session['nombre'] = usuario['nombre_usuario']
        return redirect('/tareas')
    else:
        # Si se equivocó, lo regresamos al login
        return redirect('/')

@app.route('/logout')
def logout():
    # Borramos la memoria de la sesión
    session.clear()
    return redirect('/')

# --- RUTAS DE TAREAS (PROTEGIDAS) ---
@app.route('/tareas')
def tareas():
    # ¡SEGURIDAD! Si alguien intenta entrar aquí sin iniciar sesión, lo pateamos al inicio
    if 'usuario_id' not in session:
        return redirect('/')
        
    conexion = obtener_conexion()
    # Magia de BD: Le pedimos SOLO las tareas del usuario actual
    tareas_db = conexion.execute('SELECT * FROM tareas WHERE usuario_id = ?', (session['usuario_id'],)).fetchall()
    conexion.close()
    
    return render_template('tareas.html', tareas_html=tareas_db)

@app.route('/agregar_tarea', methods=['POST'])
def agregar_tarea():
    if 'usuario_id' not in session:
        return redirect('/')
        
    nueva_desc = request.form.get('descripcion')
    mi_id = session['usuario_id'] # Sacamos quién es el usuario de la memoria
    
    conexion = obtener_conexion()
    # Guardamos la tarea y le pegamos la etiqueta de quién es el dueño
    conexion.execute('INSERT INTO tareas (descripcion, usuario_id) VALUES (?, ?)', (nueva_desc, mi_id))
    conexion.commit()
    conexion.close()
    
    return redirect('/tareas')

@app.route('/eliminar_tarea/<int:id>')
def eliminar_tarea(id):
    conexion = obtener_conexion()
    conexion.execute('DELETE FROM tareas WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    return redirect('/tareas')

@app.route('/completar_tarea/<int:id>')
def completar_tarea(id):
    conexion = obtener_conexion()
    conexion.execute("UPDATE tareas SET estado = 'Completada' WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect('/tareas')

if __name__ == '__main__':
    app.run(debug=True)
    