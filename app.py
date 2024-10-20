import discord
import os
import openai
import yt_dlp as youtube_dl
import asyncio
from discord import app_commands
from discord.ext import commands

# Set up your OpenAI API key (from environment variable or hardcoded)
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # This is required to listen for member join events

# Create a bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize voice_client globally
voice_client = None

# Function to get a response from GPT using the new API (>= v1.0.0)
async def get_chatgpt_response(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# YouTube DL options
youtube_dl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
}

# Function to join the voice channel and play music from YouTube
async def play_music(voice_channel, url):
    global voice_client  # Declare voice_client as global
    try:
        # Join the voice channel
        voice_client = await voice_channel.connect()
        
        # Use youtube_dl to extract audio source
        with youtube_dl.YoutubeDL(youtube_dl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']
            audio_source = await discord.FFmpegOpusAudio.from_probe(url2)
        
        # Play the audio
        voice_client.play(audio_source, after=lambda e: print("Music ended:", e))
        
        # Keep playing indefinitely until the user stops the bot
        while voice_client.is_playing():
            await asyncio.sleep(1)
        
        return voice_client  # Return the voice client to stop the music later
    except Exception as e:
        print(f"Error playing music: {e}")
        return None

# Function to stop music and disconnect
async def stop_music(voice_client):
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()  # Stop the currently playing music
        await voice_client.disconnect()

# Slash command to play LoFi music and send a chill message
@bot.tree.command(name="chill", description="Play LoFi music and send a chill message")
async def chill(interaction: discord.Interaction):
    voice_channel = discord.utils.get(interaction.guild.voice_channels, name='General')
    if voice_channel:
        await interaction.response.send_message("Joining voice channel and playing LoFi music...")
        
        # Play the music as a background task
        asyncio.create_task(play_music(voice_channel, 'https://www.youtube.com/watch?v=jfKfPfyJRdk'))

        # Send a chill message to the general channel
        channel = discord.utils.get(interaction.guild.text_channels, name='general')
        if channel:
            await channel.send(f"Thanks {interaction.user.mention} for taking the conscious effort to have a chill day 🍁")
    else:
        await interaction.response.send_message("General voice channel not found.")

# Slash command to play LoFi music without the chill message
@bot.tree.command(name="play", description="Play LoFi music in the voice channel")
async def play(interaction: discord.Interaction):
    voice_channel = discord.utils.get(interaction.guild.voice_channels, name='General')
    if voice_channel:
        await interaction.response.send_message("Joining voice channel and playing LoFi music...")
        # Play the music as a background task
        asyncio.create_task(play_music(voice_channel, 'https://www.youtube.com/watch?v=jfKfPfyJRdk'))
    else:
        await interaction.response.send_message("General voice channel not found.")

# Slash command to stop music and disconnect
@bot.tree.command(name="stop", description="Stop music and disconnect from the voice channel")
async def stop(interaction: discord.Interaction):
    global voice_client
    if voice_client and voice_client.is_connected():
        await stop_music(voice_client)
        await interaction.response.send_message("Stopping the music and disconnecting...")
    else:
        await interaction.response.send_message("Not connected to a voice channel.")

# Slash command to show help
@bot.tree.command(name="help", description="Show the available commands")
async def help_command(interaction: discord.Interaction):
    help_message = (
        "**Here are the available commands:**\n"
        "`/play` - Play LoFi music in the voice channel.\n"
        "`/chill` - Play LoFi music and send a chill message.\n"
        "`/stop` - Stop the music and disconnect the bot.\n"
        "`/help` - Show this list of commands."
    )
    await interaction.response.send_message(help_message)

# Event that triggers when the bot is ready
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()  # Sync commands with Discord
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Event to welcome new members
@bot.event
async def on_member_join(member):
    # Find the channel where the bot should send the welcome message
    channel = discord.utils.get(member.guild.text_channels, name='general')  # Replace 'general' with your channel
    if channel:
        # Send a custom welcome message to the new member
        await channel.send(f"Welcome to the thunderdome, {member.mention}, you stupid SOB!")

# Run the bot
token = os.getenv('DISCORD_BOT_TOKEN')  # Make sure your bot token is set here
bot.run(token)
