# -*- coding: utf-8 -*-
import uuid  
import os
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler  # Added

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
socketio = SocketIO(app, cors_allowed_origins="*")

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'YOUR_NEW_TOKEN')  # Replace with new token
bot = Bot(TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None)  # Added

# In-memory storage
active_duels = {}
users = {}

class Duel:
    def __init__(self, duel_id):
        self.id = duel_id
        self.players = {}
        self.winner = None

def start_command(update, context):  # Added
    duel_id = str(uuid.uuid4())
    active_duels[duel_id] = Duel(duel_id)
    update.message.reply_text(
        f"⚔️ Join duel: https://gladiator-bot.onrender.com/arena?id={duel_id}"
    )

dispatcher.add_handler(CommandHandler('start', start_command))  # Added

@app.route('/')
def home():
    return "Gladiator Bot Running 🛡️⚔️"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)  # Added
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