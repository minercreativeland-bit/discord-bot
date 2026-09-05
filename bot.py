import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('MTU0NTYzNjEyNzA5NDg2NTkzMA.Gpdnu4.zu6sXmsCwyr94CCZ0OIkpSaSlK9HW8ZQTY2cNY')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Success! Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == '!ping':
        await message.channel.send('Pong!')

client.run(TOKEN)