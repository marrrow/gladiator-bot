import uuid  
import os
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from telegram import Bot, Update

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
socketio = SocketIO(app, cors_allowed_origins="*")

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN')
bot = Bot(TELEGRAM_TOKEN)

# In-memory storage (replace with DB later)
active_duels = {}
users = {}

class Duel:
    def __init__(self, duel_id):
        self.id = duel_id
        self.players = {}
        self.winner = None

@app.route('/')
def home():
    return "Gladiator Bot Running 🛡️⚔️"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    if update.message and '/start' in update.message.text:
        duel_id = str(uuid.uuid4())
        active_duels[duel_id] = Duel(duel_id)
        # Replace YOUR_RENDER_URL with your actual domain
        bot.send_message(
            chat_id=update.message.chat_id,
            text=f"⚔️ Join duel: https://your-domain.com/arena?id={duel_id}"
        )
    return 'OK'

@app.route('/arena')
def arena():
    return render_template('arena.html')

@socketio.on('connect')
def handle_connect(data):
    duel_id = data['duel_id']
    user_id = data['user_id']
    
    if duel_id not in active_duels:
        return
    
    active_duels[duel_id].players[user_id] = {'health': 100, 'stamina': 100}
    socketio.emit('update', active_duels[duel_id].players, room=duel_id)

@socketio.on('attack')
def handle_attack(data):
    duel_id = data['duel_id']
    attacker_id = data['user_id']
    
    duel = active_duels.get(duel_id)
    if not duel:
        return
    
    for player_id in duel.players:
        if player_id != attacker_id:
            duel.players[player_id]['health'] -= 10
            if duel.players[player_id]['health'] <= 0:
                duel.winner = attacker_id
                users[attacker_id] = users.get(attacker_id, 0) + 1
                socketio.emit('winner', {'winner': attacker_id}, room=duel_id)
    
    socketio.emit('update', duel.players, room=duel_id)

if __name__ == '__main__':
    socketio.run(app)