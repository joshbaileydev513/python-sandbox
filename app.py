import discord
import os

# Define the intents (what your bot should be able to listen for)
intents = discord.Intents.default()  # This enables the default intents
intents.message_content = True  # You need to explicitly allow access to message content

# Create a client instance that represents the bot
client = discord.Client(intents=intents)

# Define an event that will trigger when the bot has connected to Discord
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Define an event that will trigger when a message is sent in the chat
@client.event
async def on_message(message):
    # Make sure the bot does not reply to itself
    if message.author == client.user:
        return

    # Example of bot responding to a specific message
    if message.content.startswith('!hello'):
        await message.channel.send('Hello!')

# Run the bot using the token
token = os.getenv('DISCORD_BOT_TOKEN')  # You'll set this in your environment variables
client.run(token)
