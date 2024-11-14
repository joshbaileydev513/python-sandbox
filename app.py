import discord
import os
import openai
import yt_dlp as youtube_dl
import asyncio
import requests
import json
import datetime
import re        # Added if using regular expressions
from discord import app_commands
from discord.ext import commands

# Set up your OpenAI API key (from environment variable or hardcoded)
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # This is required to listen for member join events
intents.guilds = True  # Required for application commands (slash commands)
intents.messages = True 

# Create a bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store user session data for league information
user_league_info = {}

# Initialize voice_client globally
voice_client = None

# Function to get a response from GPT using the new API (>= v1.0.0)
async def get_chatgpt_response(prompt):
    print(f"Attempting to get ChatGPT response for prompt: {prompt}")
    try:
        if not openai.api_key:
            print("Error: OpenAI API key is not set")
            return "Error: OpenAI API key is not configured."
        
        print("Making API call to OpenAI...")
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        print("Successfully received response from OpenAI")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in get_chatgpt_response: {str(e)}")
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

# Slash command for users to input their league info
@bot.tree.command(name="leagueinfo", description="Set your ESPN Fantasy Football league info")
async def set_league_info(interaction: discord.Interaction, league_id: str, swid: str, espn_s2: str):
    user_id = interaction.user.id
    try:
        # Validate SWID format (should be a GUID enclosed in curly braces)
        if not re.match(r'^\{[A-F0-9\-]{36}\}$', swid, re.IGNORECASE):
            await interaction.response.send_message("Invalid SWID format. It should be in the format `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`.")
            return

        # Optionally validate espn_s2 if you have a regex pattern

        # Store user data
        user_league_info[user_id] = {
            "league_id": league_id,
            "swid": swid,
            "espn_s2": espn_s2
        }
        await interaction.response.send_message(f"Your league info has been set for league_id: {league_id}")
    except Exception as e:
        print(f"Error storing league info: {str(e)}")
        await interaction.response.send_message("An error occurred while setting your league info. Please try again.")

# Helper function to check if user has provided league info
def has_league_info(user_id):
    return user_id in user_league_info

def build_espn_url(league_id, season_id=None, historical=False):
    base_url = "https://fantasy.espn.com/apis/v3/games/ffl/"
    if historical:
        url = f"{base_url}leagueHistory/{league_id}"
        params = {
            'view': [
                'mLiveScoring', 'mMatchupScore', 'mRoster', 'mSettings',
                'mStandings', 'mStatus', 'mTeam', 'modular', 'mNav'
            ],
            'seasonId': season_id
        }
    else:
        if not season_id:
            season_id = datetime.datetime.now().year  # Use the current season
        url = f"{base_url}seasons/{season_id}/segments/0/leagues/{league_id}"
        params = {
            'view': ['mMatchupScore', 'mTeam', 'mSettings']
        }
    return url, params

# Command to get current ranks
@bot.tree.command(name="currentranks", description="Get current league power rankings")
async def current_ranks(interaction: discord.Interaction):
    user_id = interaction.user.id

    if not has_league_info(user_id):
        await interaction.response.send_message("Please set your league info using `/leagueinfo` first.")
        return

    league_info = user_league_info[user_id]
    league_id = league_info["league_id"]
    swid = league_info["swid"]
    espn_s2 = league_info["espn_s2"]

    # Define the current season
    season_id = datetime.datetime.now().year

    url, params = build_espn_url(league_id, season_id)

    cookies = {"SWID": swid, "espn_s2": espn_s2}

    try:
        response = requests.get(url, params={'view': params['view']}, cookies=cookies)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        teams = data.get('teams')
        if not teams:
            await interaction.response.send_message("Could not retrieve teams from the league data.")
            return

        # Sort teams by their overall rank
        teams.sort(key=lambda x: x['rankCalculatedFinal'])

        message = "Current League Power Rankings:\n"
        for idx, team in enumerate(teams, start=1):
            team_name = team['location'] + " " + team['nickname']
            message += f"{idx}. {team_name}\n"

        await interaction.response.send_message(message)
    except requests.exceptions.HTTPError as http_err:
        await interaction.response.send_message(f"HTTP error occurred: {str(http_err)}")
    except json.JSONDecodeError:
        await interaction.response.send_message("Error decoding the response from ESPN API.")
    except Exception as e:
        await interaction.response.send_message(f"An unexpected error occurred: {str(e)}")

# Command to get historical power ranks
@bot.tree.command(name="historicalranks", description="Get historical ESPN Fantasy Power Rankings")
async def historical_ranks(interaction: discord.Interaction, season_id: int = None):
    user_id = interaction.user.id

    if not has_league_info(user_id):
        await interaction.response.send_message("Please set your league info using `/leagueinfo` first.")
        return

    league_info = user_league_info[user_id]
    league_id = league_info["league_id"]
    swid = league_info["swid"]
    espn_s2 = league_info["espn_s2"]

    # Use the specified season or default to the previous year
    if season_id is None:
        season_id = datetime.datetime.now().year - 1

    url, params = build_espn_url(league_id, season_id, historical=True)

    cookies = {"SWID": swid, "espn_s2": espn_s2}

    try:
        response = requests.get(url, params={'view': params['view'], 'seasonId': season_id}, cookies=cookies)
        response.raise_for_status()

        data = response.json()
        if not data:
            await interaction.response.send_message(f"No data returned for the {season_id} season.")
            return

        league_data = data[0]  # Since leagueHistory returns a list
        teams = league_data.get('teams')
        if not teams:
            await interaction.response.send_message("Could not retrieve teams from the league data.")
            return

        # Sort teams by their final rank
        teams.sort(key=lambda x: x.get('rankCalculatedFinal', 0))

        message = f"Historical League Power Rankings for {season_id}:\n"
        for team in teams:
            rank = team.get('rankCalculatedFinal', 'N/A')
            team_name = team['location'] + " " + team['nickname']
            message += f"{rank}. {team_name}\n"

        await interaction.response.send_message(message)
    except requests.exceptions.HTTPError as http_err:
        await interaction.response.send_message(f"HTTP error occurred: {str(http_err)}")
    except json.JSONDecodeError:
        await interaction.response.send_message("Error decoding the response from ESPN API.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        await interaction.response.send_message("An unexpected error occurred while processing your request.")

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
        "`/stop` - Stop the music and disconnect from the voice channel\n"
        "`/leagueinfo` - Set your ESPN Fantasy Football league info\n"
        "`/currentranks` - Get current ESPN league power rankings.\n"
        "`/historicalranks` - Get historical ESPN Fantasy Power Rankings\n"
        "`/help` - Show this list of commands."
    )
    await interaction.response.send_message(help_message)

# Event that triggers when the bot is ready
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user} (ID: {bot.user.id})')
    print(f"OpenAI API Key status: {'Set' if openai.api_key else 'Not Set'}")
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

# Add this event handler for messages
@bot.event
async def on_message(message):
    try:
        # Ignore messages from the bot itself
        if message.author == bot.user:
            return

        # Process commands first (important to keep slash commands working)
        await bot.process_commands(message)

        # Debug logging
        print(f"Message received: {message.content}")
        print(f"Message author: {message.author}")

        # Respond to all messages (no mention required)
        if message.content:
            async with message.channel.typing():
                print("Getting ChatGPT response...")
                response = await get_chatgpt_response(message.content)
                print(f"ChatGPT response received: {response}")
                await message.reply(response)

    except Exception as e:
        print(f"Error in on_message: {str(e)}")
        await message.channel.send(f"An error occurred while processing your message: {str(e)}")

# Run the bot
token = os.getenv('DISCORD_BOT_TOKEN')  # Make sure your bot token is set here
bot.run(token)
