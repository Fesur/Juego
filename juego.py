import tkinter as tk
import random
import time
import requests
from tkinter import simpledialog, messagebox

# URL del servidor
SERVER_URL = 'http://127.0.0.1:5000'

# Lista de colores y sus nombres
colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange']
color_names = ['Red', 'Green', 'Blue', 'Yellow', 'Purple', 'Orange']

# Solicitar el nombre del jugador
root = tk.Tk()
root.withdraw()  # Ocultar la ventana principal temporalmente
player_name = simpledialog.askstring("Nombre del Jugador", "Por favor, ingresa tu nombre:")
root.deiconify()  # Mostrar la ventana principal nuevamente

# Variables para almacenar el estado del juego
try:
    game_state = requests.get(f'{SERVER_URL}/get_state', params={'player_name': player_name}).json()
except requests.exceptions.ConnectionError:
    print("Error: No se pudo conectar al servidor. Asegúrate de que el servidor esté en ejecución.")
    game_state = {
        'correct_clicks': 0,
        'incorrect_clicks': 0,
        'lives': 3,
        'color_hits': {color: 0 for color in colors}
    }

# Variable global para los intentos totales
total_attempts = 0

# Variables para el temporizador de clics
last_click_time = time.time()

# Función para actualizar el color y el nombre mostrados
def update_color():
    global current_color, current_name
    current_color = random.choice(colors)
    current_name = random.choice(color_names)
    color_label.config(text=current_name, fg=current_color)

# Función para manejar el clic izquierdo (correcto)
def left_click(event):
    global game_state, last_click_time
    if current_color.lower() == current_name.lower():
        result_label.config(text="Correcto!", fg="green")
        game_state['correct_clicks'] += 1
        game_state['color_hits'][current_color] += 1
    else:
        result_label.config(text="Incorrecto!", fg="red")
        game_state['incorrect_clicks'] += 1
        game_state['lives'] = max(0, game_state['lives'] - 1)  # Asegurarse de que las vidas no sean negativas
        if game_state['lives'] == 0:
            end_game()
            return
    update_color()
    update_server_state()
    update_labels()
    update_click_timer()

# Función para manejar el clic derecho (incorrecto)
def right_click(event):
    global game_state, last_click_time
    if current_color.lower() != current_name.lower():
        result_label.config(text="Correcto!", fg="green")
        game_state['correct_clicks'] += 1
        game_state['color_hits'][current_color] += 1
    else:
        result_label.config(text="Incorrecto!", fg="red")
        game_state['incorrect_clicks'] += 1
        game_state['lives'] = max(0, game_state['lives'] - 1)  # Asegurarse de que las vidas no sean negativas
        if game_state['lives'] == 0:
            end_game()
            return
    update_color()
    update_server_state()
    update_labels()
    update_click_timer()

# Función para actualizar el estado del juego en el servidor
def update_server_state():
    global game_state
    try:
        requests.post(f'{SERVER_URL}/update_state', json={'player_name': player_name, 'game_state': game_state})
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al servidor para actualizar el estado.")

# Función para actualizar las etiquetas del juego
def update_labels():
    correct_clicks_label.config(text=f"Clics correctos: {game_state['correct_clicks']}")
    incorrect_clicks_label.config(text=f"Clics incorrectos: {game_state['incorrect_clicks']}")
    lives_label.config(text=f"Vidas restantes: {game_state['lives']}")
    attempts_label.config(text=f"Intentos totales: {total_attempts}")
    for color, count in game_state['color_hits'].items():
        color_hit_labels[color].config(text=f"{color.capitalize()}: {count}")

# Función para actualizar el temporizador de clics
def update_click_timer():
    global last_click_time
    current_time = time.time()
    time_diff = current_time - last_click_time
    click_timer_label.config(text=f"Tiempo entre clics: {time_diff:.2f} s")
    last_click_time = current_time

# Función para mostrar la ventana de diálogo al terminar el juego
def show_end_game_dialog():
    response = messagebox.askquestion("Juego Terminado", "¿Quieres reiniciar el juego?", icon='warning')
    if response == 'yes':
        reset_game()
    else:
        root.quit()

# Función para terminar el juego
def end_game():
    global total_attempts
    result_label.config(text="Juego Terminado", fg="black")
    root.unbind("<Button-1>")
    root.unbind("<Button-3>")
    total_attempts += 1  # Incrementar intentos totales solo al terminar el juego
    update_server_state()
    show_end_game_dialog()

# Función para reiniciar el juego
def reset_game():
    global game_state, total_attempts
    try:
        requests.post(f'{SERVER_URL}/reset_game', json={'player_name': player_name})
        game_state = requests.get(f'{SERVER_URL}/get_state', params={'player_name': player_name}).json()
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar al servidor para reiniciar el juego.")
        game_state = {
            'correct_clicks': 0,
            'incorrect_clicks': 0,
            'lives': 3,
            'color_hits': {color: 0 for color in colors}
        }
    game_state['lives'] = 3  # Reiniciar las vidas a su valor inicial
    update_color()
    update_labels()
    root.bind("<Button-1>", left_click)
    root.bind("<Button-3>", right_click)

# Configuración de la interfaz gráfica
root = tk.Tk()
root.title(f"Juego de Colores - Jugador: {player_name}")

color_label = tk.Label(root, text="", font=("Helvetica", 32))
color_label.pack(pady=20)

result_label = tk.Label(root, text="", font=("Helvetica", 24))
result_label.pack(pady=20)

correct_clicks_label = tk.Label(root, text="Clics correctos: 0", font=("Helvetica", 16))
correct_clicks_label.pack(pady=10)

incorrect_clicks_label = tk.Label(root, text="Clics incorrectos: 0", font=("Helvetica", 16))
incorrect_clicks_label.pack(pady=10)

click_timer_label = tk.Label(root, text="Tiempo entre clics: 0.00 s", font=("Helvetica", 16))
click_timer_label.pack(pady=10)

lives_label = tk.Label(root, text=f"Vidas restantes: {game_state['lives']}", font=("Helvetica", 16))
lives_label.pack(pady=10)

attempts_label = tk.Label(root, text="Intentos totales: 0", font=("Helvetica", 16))
attempts_label.pack(pady=10)

# Crear y colocar las etiquetas para los aciertos por color
color_hit_labels = {}
for color in colors:
    label = tk.Label(root, text=f"{color.capitalize()}: 0", font=("Helvetica", 16))
    label.pack(pady=5)
    color_hit_labels[color] = label

# Vincular los clics izquierdo y derecho a las funciones correspondientes
root.bind("<Button-1>", left_click)
root.bind("<Button-3>", right_click)

# Iniciar el juego
update_color()

# Ejecutar el bucle principal de la ventana
root.mainloop()