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
  app.run(
      host='0.0.0.0',
      port=int(os.environ.get('PORT', 8080)),
      debug=False,
      use_reloader=False,
  )


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


def default_data():
  return {
      'fortnite': {'streak': 0, 'best': 0, 'wins': 0, 'losses': 0},
      'dbd': {'streak': 0, 'best': 0, 'wins': 0, 'losses': 0},
  }


def load_data():
  if not os.path.exists(DATA_FILE):
    return default_data()

  try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
      data = json.load(f)
  except (json.JSONDecodeError, OSError):
    data = default_data()

  for game in ['fortnite', 'dbd']:
    if not isinstance(data.get(game), dict):
      data[game] = {}
    data[game].setdefault('streak', 0)
    data[game].setdefault('best', 0)
    data[game].setdefault('wins', 0)
    data[game].setdefault('losses', 0)

  return data


def save_data(data):
  try:
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
      json.dump(data, f, indent=4)
  except OSError as exc:
    print(f'Could not save {DATA_FILE}: {exc}')


# --- Verification System UI Components ---
verification_codes = {}


class VerifyModal(discord.ui.Modal, title='Account Verification'):
  code_input = discord.ui.TextInput(
      label='Enter Verification Code',
      placeholder='Type the 4-digit code sent to your DMs',
      min_length=4,
      max_length=4,
  )

  async def on_submit(self, interaction: discord.Interaction):
    user_id = interaction.user.id
    entered_code = self.code_input.value.strip()

    if (
        user_id not in verification_codes
        or verification_codes[user_id] != entered_code
    ):
      await interaction.response.send_message(
          '❌ **Incorrect Code:** Please click "Generate Code" first and check'
          ' your DMs.',
          ephemeral=True,
      )
      return

    if interaction.guild is None:
      await interaction.response.send_message(
          '❌ Verification can only be completed inside a server.',
          ephemeral=True,
      )
      return

    role = discord.utils.get(interaction.guild.roles, name='Verified')
    if not role:
      await interaction.response.send_message(
          "❌ **Setup Error:** The 'Verified' role does not exist on this"
          ' server. Ask an admin to create it!',
          ephemeral=True,
      )
      return

    try:
      await interaction.user.add_roles(role)
      del verification_codes[user_id]
      await interaction.response.send_message(
          '✅ **Success!** You have been verified and given the **Verified**'
          ' role.',
          ephemeral=True,
      )
    except discord.Forbidden:
      await interaction.response.send_message(
          '❌ **Permission Error:** I cannot assign roles. Make sure my bot'
          ' role is placed *above* the Verified role in server settings.',
          ephemeral=True,
      )


class VerifyView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label='Generate Code',
      style=discord.ButtonStyle.primary,
      custom_id='gen_code_btn',
  )
  async def generate_code(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    code = str(random.randint(1000, 9999))
    verification_codes[interaction.user.id] = code

    try:
      await interaction.user.send(
          f'🔐 Your Discord verification code is: **{code}**\nReturn to the'
          ' server and click **Verify** to enter it.'
      )
      await interaction.response.send_message(
          '📬 I have sent your verification code via **Direct Message (DM)**!',
          ephemeral=True,
      )
    except discord.Forbidden:
      await interaction.response.send_message(
          '❌ **DM Blocked:** I could not send you a DM. Please enable DMs from'
          ' server members in your privacy settings and try again.',
          ephemeral=True,
      )

  @discord.ui.button(
      label='Verify',
      style=discord.ButtonStyle.success,
      custom_id='verify_modal_btn',
  )
  async def verify_button(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(VerifyModal())


view_registered = False


@client.event
async def on_ready():
  global view_registered

  # Persistent views only need to be registered once per process.
  if not view_registered:
    client.add_view(VerifyView())
    view_registered = True

  print(f'Success! Logged in as {client.user} (ID: {client.user.id})')


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
        name='🛠️ System & Admin',
        value=(
            '`!ping` — Checks bot latency\n'
            '`!say <msg>` — Broadcasts a message (Admin Only)\n'
            '`!linksetup` — Posts the verification panel (Admin Only)\n'
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

  # 7. Admin-Only Say Command
  elif msg == '!say' or msg.startswith('!say '):
    if not message.author.guild_permissions.administrator:
      await message.channel.send(
          '❌ **Access Denied:** You must be a server administrator to use this'
          ' command!'
      )
      return

    parts = message.content.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
      await message.channel.send(
          '❌ **Usage Error:** Please provide text! Example: `!say Hello'
          ' everyone!`'
      )
      return

    text_to_say = parts[1]

    try:
      await message.delete()
    except discord.Forbidden:
      pass

    await message.channel.send(text_to_say)

  # 8. Setup Verification Panel (Admin Only)
  elif msg == '!linksetup':
    if not message.author.guild_permissions.administrator:
      await message.channel.send(
          '❌ **Access Denied:** You must be an administrator to post the'
          ' verification panel.'
      )
      return

    try:
      await message.delete()
    except discord.Forbidden:
      pass

    embed = discord.Embed(
        title='🛡️ Server Verification',
        description=(
            'Welcome! To gain access to the rest of the server, you must'
            ' complete verification.\n\n'
            '**Step 1:** Click **Generate Code** to receive a code in your'
            ' DMs.\n**Step 2:** Click **Verify** and enter your 4-digit code.'
        ),
        color=discord.Color.blue(),
    )
    embed.set_footer(
        text='Make sure your direct messages are open for this server!'
    )

    await message.channel.send(embed=embed, view=VerifyView())


if __name__ == '__main__':
  keep_alive()
  client.run(TOKEN)
