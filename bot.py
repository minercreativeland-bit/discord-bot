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


def load_data():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
      data = json.load(f)
      for game in ['fortnite', 'dbd']:
        if game not in data:
          data[game] = {'streak': 0, 'best': 0, 'wins': 0, 'losses': 0}
        else:
          data[game].setdefault('streak', 0)
          data[game].setdefault('best', 0)
          data[game].setdefault('wins', 0)
          data[game].setdefault('losses', 0)
      return data
  return {
      'fortnite': {'streak': 0, 'best': 0, 'wins': 0, 'losses': 0},
      'dbd': {'streak': 0, 'best': 0, 'wins': 0, 'losses': 0},
  }


def save_data(data):
  with open(DATA_FILE, 'w') as f:
    json.dump(data, f, indent=4)


@client.event
async def on_ready():
  print(f'Success! Logged in as {client.user}')


@client.event
async def on_message(message):
  if message.author == client.user:
    return

  msg = message.content.lower()
  data = load_data()

  # 1. Ping Command
  if msg == '!ping':
    latency = round(client.latency * 1000)
    embed = discord.Embed(
        title='🏓 Pong!',
        description=f'Gateway latency: **{latency}ms**',
        color=discord.Color.green(),
    )
    await message.channel.send(embed=embed)

  # 2. Command Directory (!cmds / !help)
  elif msg in ['!cmds', '!help']:
    embed = discord.Embed(
        title='🤖 Bot Command Directory',
        description='Here are all the available commands you can use:',
        color=discord.Color.teal(),
    )
    embed.add_field(
        name='🎮 Gaming & Streaks',
        value=(
            '`!drop` — Picks a random Fortnite landing zone\n'
            '`!streak` — Views the live competitive dashboard\n'
            '`!win fn` or `!win dbd` — Logs a win/escape\n'
            '`!loss fn` or `!loss dbd` — Resets a streak'
        ),
        inline=False,
    )
    embed.add_field(
        name='🛠️ System',
        value=(
            '`!ping` — Checks bot latency\n'
            '`!cmds` — Displays this command list'
        ),
        inline=False,
    )
    embed.set_footer(text='Example: !win fn')
    await message.channel.send(embed=embed)

  # 3. Fortnite Drop Picker
  elif msg == '!drop':
    locations = [
        'Tilted Towers',
        'Pleasant Park',
        'Retail Row',
        'Salty Springs',
        'Mega City',
        'Restored Reels',
        'Grim Gate',
        'Nitrodome',
    ]
    chosen_spot = random.choice(locations)
    embed = discord.Embed(
        title='🎮 Tactical Drop Coordinator',
        description=f'Recommended Landing Zone:\n### 🎯 **{chosen_spot}**',
        color=discord.Color.blue(),
    )
    embed.set_footer(text='May the odds be ever in your favor.')
    await message.channel.send(embed=embed)

  # 4. Professional Streak Dashboard
  elif msg in ['!streak', '!streaks']:
    fn = data['fortnite']
    dbd = data['dbd']

    embed = discord.Embed(
        title='📊 Competitive Performance Dashboard',
        description='Live tracking metrics for current gaming sessions.',
        color=discord.Color.gold(),
    )
    embed.add_field(
        name='🎮 Fortnite',
        value=(
            f"• Current Streak: **{fn['streak']}**\n• Personal Best:"
            f" **{fn['best']}**\n• Total Wins: **{fn['wins']}**"
        ),
        inline=False,
    )
    embed.add_field(
        name='🔪 Dead by Daylight',
        value=(
            f"• Current Streak: **{dbd['streak']}**\n• Personal Best:"
            f" **{dbd['best']}**\n• Total Escapes: **{dbd['wins']}**"
        ),
        inline=False,
    )
    embed.set_footer(text=f'Requested by {message.author.name}')
    await message.channel.send(embed=embed)

  # 5. Log a Win
  elif msg == '!win' or msg.startswith('!win '):
    parts = msg.split(' ')
    if len(parts) < 2:
      await message.channel.send(
          '❌ **Usage Error:** Please specify the game! Example: `!win fn` or'
          ' `!win dbd`'
      )
      return

    game = parts[1]
    if game in ['fn', 'fortnite']:
      data['fortnite']['streak'] += 1
      data['fortnite']['wins'] += 1
      if data['fortnite']['streak'] > data['fortnite']['best']:
        data['fortnite']['best'] = data['fortnite']['streak']
      save_data(data)

      embed = discord.Embed(
          title='🏆 Victory Logged: Fortnite',
          description=(
              f"Current Streak: **{data['fortnite']['streak']}** 🔥"
              f" (Personal Best: {data['fortnite']['best']})"
          ),
          color=discord.Color.from_rgb(0, 255, 128),
      )
      await message.channel.send(embed=embed)

    elif game in ['dbd', 'deadbydaylight']:
      data['dbd']['streak'] += 1
      data['dbd']['wins'] += 1
      if data['dbd']['streak'] > data['dbd']['best']:
        data['dbd']['best'] = data['dbd']['streak']
      save_data(data)

      embed = discord.Embed(
          title='🔪 Escape Logged: Dead by Daylight',
          description=(
              f"Current Streak: **{data['dbd']['streak']}** 🔥 (Personal Best:"
              f" {data['dbd']['best']})"
          ),
          color=discord.Color.purple(),
      )
      await message.channel.send(embed=embed)
    else:
      await message.channel.send(
          "❌ Unknown game. Use `fn` for Fortnite or `dbd` for Dead by Daylight."
      )

  # 6. Log a Loss / Reset Streak
  elif msg in ['!loss', '!reset'] or msg.startswith('!loss ') or msg.startswith('!reset '):
    parts = msg.split(' ')
    if len(parts) < 2:
      await message.channel.send(
          '❌ **Usage Error:** Please specify the game! Example: `!loss fn` or'
          ' `!loss dbd`'
      )
      return

    game = parts[1]
    if game in ['fn', 'fortnite']:
      old_streak = data['fortnite']['streak']
      data['fortnite']['streak'] = 0
      save_data(data)

      embed = discord.Embed(
          title='💀 Streak Terminated: Fortnite',
          description=(
              f'Previous active streak of **{old_streak}** has been reset to 0.'
          ),
          color=discord.Color.red(),
      )
      await message.channel.send(embed=embed)

    elif game in ['dbd', 'deadbydaylight']:
      old_streak = data['dbd']['streak']
      data['dbd']['streak'] = 0
      save_data(data)

      embed = discord.Embed(
          title='💀 Streak Terminated: Dead by Daylight',
          description=(
              f'Previous active streak of **{old_streak}** has been reset to 0.'
          ),
          color=discord.Color.red(),
      )
      await message.channel.send(embed=embed)
    else:
      await message.channel.send(
          "❌ Unknown game. Use `fn` for Fortnite or `dbd` for Dead by Daylight."
      )


if __name__ == '__main__':
  keep_alive()
  client.run(TOKEN)
