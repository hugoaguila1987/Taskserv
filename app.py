from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
# Esta llave secreta es obligatoria para que Flask encripte las sesiones de los usuarios
app.secret_key = 'llave_super_secreta_de_taskserv' 

# --- CONFIGURACIÓN DE POSTGRESQL ---
# Aquí pondremos las llaves de acceso cuando instalemos tu base de datos
DB_HOST = "localhost" 
DB_NAME = "taskserv_db"
DB_USER = "postgres"
DB_PASS = "root"

def obtener_conexion():
    # Nos conectamos al servidor de Postgres con las credenciales
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
        
        # 1. Creamos la tabla de USUARIOS (Postgres usa SERIAL en lugar de AUTOINCREMENT)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nombre_usuario TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # 2. Creamos la tabla de TAREAS usando SERIAL también
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
    password = request.form.get('password') 
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        # Usamos %s en lugar de ? para inyectar datos seguros en Postgres
        cursor.execute('INSERT INTO usuarios (nombre_usuario, password) VALUES (%s, %s)', (nombre, password))
        conexion.commit()
    except psycopg2.IntegrityError:
        # Si el usuario ya existe, cancelamos la transacción para que no marque error fatal
        conexion.rollback() 
    
    cursor.close()
    conexion.close()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    nombre = request.form.get('nombre_usuario')
    password = request.form.get('password')
    
    conexion = obtener_conexion()
    # RealDictCursor hace que los resultados se lean igual que en SQLite para no tener que cambiar el HTML
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    
    # Buscamos si existe alguien con ese usuario y contraseña
    cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s AND password = %s', (nombre, password))
    usuario = cursor.fetchone()
    
    cursor.close()
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
    # ¡SEGURIDAD! Si alguien intenta entrar aquí sin iniciar sesión, lo regresamos al inicio
    if 'usuario_id' not in session:
        return redirect('/')
        
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    
    # Le pedimos SOLO las tareas del usuario actual, ordenadas por su ID
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
    mi_id = session['usuario_id'] # Sacamos quién es el usuario de la memoria
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Guardamos la tarea y le pegamos la etiqueta de quién es el dueño
    cursor.execute('INSERT INTO tareas (descripcion, usuario_id) VALUES (%s, %s)', (nueva_desc, mi_id))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    return redirect('/tareas')

@app.route('/eliminar_tarea/<int:id>')
def eliminar_tarea(id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Le decimos a Postgres que borre la tarea que tenga este ID exacto
    cursor.execute('DELETE FROM tareas WHERE id = %s', (id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    return redirect('/tareas')

@app.route('/completar_tarea/<int:id>')
def completar_tarea(id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Le decimos a Postgres que actualice el estado a "Completada"
    cursor.execute("UPDATE tareas SET estado = 'Completada' WHERE id = %s", (id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    return redirect('/tareas')

if __name__ == '__main__':
    app.run(debug=True)