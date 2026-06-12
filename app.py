from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
# Esta llave secreta es obligatoria para que Flask encripte las sesiones
app.secret_key = 'llave_super_secreta_de_taskserv' 

# Inicializamos el "walkie-talkie" (WebSockets)
socketio = SocketIO(app)

# --- CONFIGURACIÓN DE POSTGRESQL ---
DB_HOST = "localhost" 
DB_NAME = "taskserv_db"
DB_USER = "postgres"
DB_PASS = "root" 

def obtener_conexion():
    conexion = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conexion

def inicializar_bd():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nombre_usuario TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id SERIAL PRIMARY KEY,
                descripcion TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente',
                usuario_id INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        conexion.commit()
        cursor.close()
        conexion.close()
    except Exception as e:
        print(f"Aún no hay conexión a Postgres: {e}")

inicializar_bd()

# --- RUTAS DE ACCESO (LOGIN Y REGISTRO) ---
@app.route('/')
def inicio():
    if 'usuario_id' in session:
        return redirect('/tareas')
    return render_template('login.html')

@app.route('/registro', methods=['POST'])
def registro():
    nombre = request.form.get('nombre_usuario')
    password = request.form.get('password') 
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute('INSERT INTO usuarios (nombre_usuario, password) VALUES (%s, %s)', (nombre, password))
        conexion.commit()
    except psycopg2.IntegrityError:
        conexion.rollback() 
    
    cursor.close()
    conexion.close()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    nombre = request.form.get('nombre_usuario')
    password = request.form.get('password')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s AND password = %s', (nombre, password))
    usuario = cursor.fetchone()
    
    cursor.close()
    conexion.close()
    
    if usuario:
        session['usuario_id'] = usuario['id']
        session['nombre'] = usuario['nombre_usuario']
        return redirect('/tareas')
    else:
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- RUTAS DE TAREAS (PROTEGIDAS Y EN TIEMPO REAL) ---
@app.route('/tareas')
def tareas():
    if 'usuario_id' not in session:
        return redirect('/')
        
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('SELECT * FROM tareas WHERE usuario_id = %s ORDER BY id ASC', (session['usuario_id'],))
    tareas_db = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    return render_template('tareas.html', tareas_html=tareas_db)

@app.route('/agregar_tarea', methods=['POST'])
def agregar_tarea():
    if 'usuario_id' not in session:
        return redirect('/')
        
    nueva_desc = request.form.get('descripcion')
    mi_id = session['usuario_id'] 
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('INSERT INTO tareas (descripcion, usuario_id) VALUES (%s, %s)', (nueva_desc, mi_id))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    
    # ¡Gritamos por el radio que hay una tarea nueva!
    socketio.emit('actualizacion_tareas', {'mensaje': '¡Alguien agregó una tarea!'})
    
    return redirect('/tareas')

@app.route('/eliminar_tarea/<int:id>')
def eliminar_tarea(id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('DELETE FROM tareas WHERE id = %s', (id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    
    # ¡Gritamos por el radio que se borró una tarea!
    socketio.emit('actualizacion_tareas', {'mensaje': '¡Alguien eliminó una tarea!'})
    
    return redirect('/tareas')

@app.route('/completar_tarea/<int:id>')
def completar_tarea(id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("UPDATE tareas SET estado = 'Completada' WHERE id = %s", (id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    
    # ¡Gritamos por el radio que se completó una tarea!
    socketio.emit('actualizacion_tareas', {'mensaje': '¡Alguien completó una tarea!'})
    
    return redirect('/tareas')

if __name__ == '__main__':
    # Arrancamos con el motor de Sockets en lugar del normal
    socketio.run(app, debug=True)