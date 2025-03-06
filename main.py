import discord
from discord.ext import commands
from discord import app_commands
import openai
import pdfplumber
import os

# Load API Keys from .env (or replace with your actual token)
from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Configure bot with command tree for slash commands
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # Use this to register slash commands

@bot.event
async def on_ready():
    await tree.sync()  # Sync slash commands
    print(f'✅ Logged in as {bot.user}')

@tree.command(name="resume_reword", description="Upload your resume as a PDF and get AI-powered feedback.")
async def resume_reword(interaction: discord.Interaction, attachment: discord.Attachment, level: str):
    """Handles PDF uploads, extracts resume text, and provides feedback."""
    if not attachment.filename.endswith(".pdf"):
        await interaction.response.send_message("⚠️ Please upload a valid PDF file.", ephemeral=True)
        return

    await interaction.response.send_message("📄 Processing your resume... ⏳", ephemeral=True)

    # Save the file temporarily
    file_path = f"./{attachment.filename}"
    await attachment.save(file_path)

    # Extract text
    resume_text = extract_resume_text(file_path)

    if not resume_text:
        await interaction.followup.send("⚠️ Could not extract text from your resume. Ensure it's a readable PDF.", ephemeral=True)
        return

    # Remove temp file
    os.remove(file_path)

    # Generate GPT-4 prompt
    prompt = f"""
    Provide a detailed review of the following resume for a {level} software engineering position.
    Focus on clarity, structure, impact, readability, and areas of improvement.
    Suggest how to enhance descriptions, highlight key achievements, and improve formatting.
    Then, rewrite key sections to be more compelling and professional.

    Resume Content:
    {resume_text}

    Resume Feedback and Suggested Improvements:
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    feedback_text = response.choices[0].message.content

    # Split feedback into smaller messages if it exceeds Discord's limit
    def split_message(text, max_length=1990):
        """Splits a message into chunks while ensuring Markdown formatting works."""
        chunks = []
        while len(text) > max_length:
            split_index = text.rfind("\n", 0, max_length)
            if split_index == -1:
                split_index = max_length
            chunks.append(text[:split_index])
            text = text[split_index:].strip()
        chunks.append(text)
        return chunks
    
    feedback_chunks = split_message(feedback_text)
    for chunk in feedback_chunks:
        await interaction.followup.send(f"📄 **Resume Feedback:**\n```{chunk}```", ephemeral=False)

def extract_resume_text(pdf_path):
    """Extracts text from a PDF resume."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text.strip()

bot.run(DISCORD_TOKEN)
