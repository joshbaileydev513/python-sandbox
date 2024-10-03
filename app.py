import discord
import os
import openai

# Set up your OpenAI API key (from environment variable or hardcoded)
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define intents for the bot
intents = discord.Intents.default()
intents.message_content = True

# Create the bot client
client = discord.Client(intents=intents)

# Function to get a response from GPT using the new API (>= v1.0.0)
async def get_chatgpt_response(prompt):
    try:
        # Use the correct method for OpenAI >= v1.0.0
        response = openai.chat.completions.create(
            model="gpt-4",  # Or use "gpt-4" if you have access
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150  # Adjust as necessary
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Event that triggers when the bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Event that triggers when a message is sent in the server
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Respond to the keyword "Yo"
    if message.content.startswith('Yo'):
        user_message = message.content[len('Yo '):]  # Extract the part after "Yo"

        # Send a typing indicator while processing
        async with message.channel.typing():
            gpt_response = await get_chatgpt_response(user_message)
        
        # Send the response back to the Discord channel
        await message.channel.send(gpt_response)

# Run the bot
token = os.getenv('DISCORD_BOT_TOKEN')  # Make sure your bot token is set here
client.run(token)
