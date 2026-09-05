import json
import os
import random
from threading import Thread
import discord
from dotenv import load_dotenv
from flask import Flask

# --- Tiny web server to keep Render Web Service happy ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is online and running 24/7!'


def run_web():
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


def keep_alive():
  t = Thread(target=run_web)
  t.start()


# --------------------------------------------------------

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

DATA_FILE = 'streaks.json'

# ... (keep all your existing load_data, save_data, and command code here) ...

if __name__ == '__main__':
  keep_alive()  # Starts the web server in the background
  client.run(TOKEN)  # Starts your Discord bot
