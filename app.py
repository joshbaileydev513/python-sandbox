import discord
import os
import openai
import yt_dlp as youtube_dl
import asyncio

# Set up your OpenAI API key (from environment variable or hardcoded)
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # This is required to listen for member join events

# Create the bot client
client = discord.Client(intents=intents)

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

# Function to handle personality-based responses
def check_identity(message_content):
    identity_prompts = [
        "who are you", 
        "what is your name", 
        "what are you", 
        "tell me about yourself"
    ]
    
    for prompt in identity_prompts:
        if prompt in message_content.lower():
            return "I am josh-bot, the all-inclusive Discord bot giving a glimpse into the mind of Human Josh, my fleshy overlord!"
    
    return None

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
        
        # Disconnect after music stops
        await voice_client.disconnect()

    except Exception as e:
        print(f"Error playing music: {e}")
        if voice_client:
            await voice_client.disconnect()

# Event that triggers when the bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Event to welcome new members
@client.event
async def on_member_join(member):
    # Find the channel where the bot should send the welcome message
    channel = discord.utils.get(member.guild.text_channels, name='general')  # Replace 'general' with your channel

    if channel:
        # Send a custom welcome message to the new member
        await channel.send(f"Welcome to the thunderdome, {member.mention}, you stupid SOB!")

# Event that triggers when a message is sent in the server
@client.event
async def on_message(message):
    # Prevent the bot from responding to itself
    if message.author == client.user:
        return

    # Check if the message asks about the bot's identity
    identity_response = check_identity(message.content)
    if identity_response:
        await message.channel.send(identity_response)
        return

    # Command to play LoFi music in the voice channel
    if message.content.startswith('!playmusic'):
        voice_channel = discord.utils.get(message.guild.voice_channels, name='General')  # Adjust 'general' to your voice channel's name
        
        if voice_channel:
            await message.channel.send("Joining voice channel and playing LoFi music...")
            # LoFi stream URL from YouTube
            await play_music(voice_channel, 'https://www.youtube.com/watch?v=jfKfPfyJRdk')
        else:
            await message.channel.send("General voice channel not found.")

    # Process all other messages through GPT-4
    else:
        user_message = message.content  # Extract the entire message

        # Send a typing indicator while processing
        async with message.channel.typing():
            gpt_response = await get_chatgpt_response(user_message)
        
        # Send the response back to the Discord channel
        await message.channel.send(gpt_response)

# Run the bot
token = os.getenv('DISCORD_BOT_TOKEN')  # Make sure your bot token is set here
client.run(token)
