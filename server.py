from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import mysql.connector
import pandas as pd

app = Flask(__name__)
socketio = SocketIO(app)

# Conectar a la base de datos MySQL
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",  # Reemplaza con tu host de MySQL
        user="nuevo_usuario",  # Reemplaza con tu usuario de MySQL
        password="",  # Reemplaza con tu contraseña de MySQL
        database="game"  # Reemplaza con el nombre de tu base de datos
    )
    return conn

# Crear las tablas si no existen
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_state (
            player_id INT,
            correct_clicks INT,
            incorrect_clicks INT,
            lives INT,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS color_hits (
            player_id INT,
            color VARCHAR(50),
            hits INT,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            player_id INT,
            correct_clicks INT,
            incorrect_clicks INT,
            total_attempts INT,
            lives INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS color_hits_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            player_id INT,
            color VARCHAR(50),
            hits INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')
    conn.commit()
    conn.close()

# Inicializar la base de datos
init_db()

@app.route('/get_state', methods=['GET'])
def get_state():
    player_name = request.args.get('player_name')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener el ID del jugador
    cursor.execute('SELECT id FROM players WHERE name = %s', (player_name,))
    player = cursor.fetchone()
    if not player:
        # Si el jugador no existe, crearlo
        cursor.execute('INSERT INTO players (name) VALUES (%s)', (player_name,))
        conn.commit()
        cursor.execute('SELECT id FROM players WHERE name = %s', (player_name,))
        player = cursor.fetchone()
        # Inicializar el estado del juego para el nuevo jugador
        cursor.execute('''
            INSERT INTO game_state (player_id, correct_clicks, incorrect_clicks, lives)
            VALUES (%s, 0, 0, 3)
        ''', (player['id'],))
        colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange']
        for color in colors:
            cursor.execute('INSERT INTO color_hits (player_id, color, hits) VALUES (%s, %s, 0)', (player['id'], color))
        conn.commit()
    
    # Obtener el estado del juego
    cursor.execute('SELECT * FROM game_state WHERE player_id = %s', (player['id'],))
    game_state = cursor.fetchone()
    cursor.execute('SELECT * FROM color_hits WHERE player_id = %s', (player['id'],))
    color_hits = cursor.fetchall()
    conn.close()
    return jsonify({
        'correct_clicks': game_state['correct_clicks'],
        'incorrect_clicks': game_state['incorrect_clicks'],
        'lives': game_state['lives'],
        'color_hits': {row['color']: row['hits'] for row in color_hits}
    })

@app.route('/update_state', methods=['POST'])
def update_state():
    data = request.json
    player_name = data['player_name']
    game_state = data['game_state']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener el ID del jugador
    cursor.execute('SELECT id FROM players WHERE name = %s', (player_name,))
    player = cursor.fetchone()
    
    # Actualizar el estado del juego
    cursor.execute('''
        UPDATE game_state
        SET correct_clicks = %s, incorrect_clicks = %s, lives = %s
        WHERE player_id = %s
    ''', (game_state['correct_clicks'], game_state['incorrect_clicks'], game_state['lives'], player['id']))
    for color, hits in game_state['color_hits'].items():
        cursor.execute('UPDATE color_hits SET hits = %s WHERE player_id = %s AND color = %s', (hits, player['id'], color))
    conn.commit()
    conn.close()
    socketio.emit('update', data)
    return jsonify({'status': 'success'})

@app.route('/reset_game', methods=['POST'])
def reset_game():
    data = request.json
    player_name = data['player_name']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener el ID del jugador
    cursor.execute('SELECT id FROM players WHERE name = %s', (player_name,))
    player = cursor.fetchone()
    
    # Guardar el estado actual en la tabla de historial
    cursor.execute('SELECT * FROM game_state WHERE player_id = %s', (player['id'],))
    game_state = cursor.fetchone()
    cursor.execute('''
        INSERT INTO game_history (player_id, correct_clicks, incorrect_clicks, total_attempts, lives)
        VALUES (%s, %s, %s, %s, %s)
    ''', (player['id'], game_state['correct_clicks'], game_state['incorrect_clicks'], total_attempts, game_state['lives']))
    
    cursor.execute('SELECT * FROM color_hits WHERE player_id = %s', (player['id'],))
    color_hits = cursor.fetchall()
    for row in color_hits:
        cursor.execute('''
            INSERT INTO color_hits_history (player_id, color, hits)
            VALUES (%s, %s, %s)
        ''', (player['id'], row['color'], row['hits']))
    
    # Reiniciar el estado del juego
    cursor.execute('''
        UPDATE game_state
        SET correct_clicks = 0, incorrect_clicks = 0, lives = 3
        WHERE player_id = %s
    ''', (player['id'],))
    cursor.execute('UPDATE color_hits SET hits = 0 WHERE player_id = %s', (player['id'],))
    conn.commit()
    conn.close()
    socketio.emit('reset')
    return jsonify({'status': 'success'})

# Ruta para el dashboard
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM game_history')
    game_history = cursor.fetchall()
    cursor.execute('SELECT * FROM color_hits_history')
    color_hits_history = cursor.fetchall()
    conn.close()
    
    game_history_df = pd.DataFrame(game_history)
    color_hits_history_df = pd.DataFrame(color_hits_history)
    
    # Convertir los datos a JSON para pasarlos al frontend
    game_history_json = game_history_df.to_json(orient='records')
    color_hits_history_json = color_hits_history_df.to_json(orient='records')
    
    return render_template('dashboard.html', game_history=game_history_json, color_hits_history=color_hits_history_json)

if __name__ == '__main__':
    socketio.run(app, debug=True)