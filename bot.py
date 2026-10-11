import os
import telebot
import requests
from flask import Flask
import threading

# Use your provided OMDb API key
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OMDB_API_KEY = "1e5af9d3"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "OMDb Poster Bot is running 24/7!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Welcome to OMDb Poster Bot!**\n\n"
        "Send me any movie or series name, and I will fetch its poster and direct link for you!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def search_poster(message):
    query = message.text.strip()
    status_msg = bot.reply_to(message, f"🔍 *Searching poster for:* `{query}`...", parse_mode="Markdown")
    
    # Fetch data from OMDb API
    url = f"http://www.omdbapi.com/?t={requests.utils.quote(query)}&apikey={OMDB_API_KEY}"
    response = requests.get(url).json()

    if response.get("Response") == "True":
        title = response.get("Title")
        year = response.get("Year")
        rating = response.get("imdbRating")
        genre = response.get("Genre")
        poster_url = response.get("Poster")

        if poster_url and poster_url != "N/A":
            caption = (
                f"🎬 **{title}** ({year})\n"
                f"⭐ **IMDb:** {rating} | 🎭 **Genre:** {genre}\n\n"
                f"🔗 **[Click Here to Open Full Poster Image]({poster_url})**"
            )
            
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.send_photo(
                chat_id=message.chat.id,
                photo=poster_url,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("❌ Poster not available for this title.", message.chat.id, status_msg.message_id)
    else:
        bot.edit_message_text("❌ Movie or series not found! Please check your spelling.", message.chat.id, status_msg.message_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Run Telegram bot polling in a background thread
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    # Run Flask server for Render 24/7 uptime
    app.run(host="0.0.0.0", port=port)
