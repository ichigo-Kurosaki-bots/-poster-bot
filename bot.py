import os
import telebot
import requests
from flask import Flask
import threading

# Load credentials from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") # Add this in Render settings

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Universal 16:9 Poster Bot is running 24/7!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Welcome to Universal 16:9 Banner & Poster Bot!**\n\n"
        "Send me any title (Movies, K-Dramas, C-Dramas, J-Dramas, Anime, Series, etc.), "
        "and I will fetch its 16:9 widescreen landscape thumbnail with a direct link!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def search_poster(message):
    query = message.text.strip()
    status_msg = bot.reply_to(message, f"🔍 *Searching 16:9 landscape banner for:* `{query}`...", parse_mode="Markdown")
    
    # TMDb Multi-Search endpoint covers global movies, TV shows, Asian dramas, and anime
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}"
    response = requests.get(url).json()
    results = response.get("results", [])

    if results:
        item = results[0]
        title = item.get("title") or item.get("name") or "Unknown Title"
        media_type = item.get("media_type", "unknown").upper()
        backdrop_path = item.get("backdrop_path") # This provides the 16:9 landscape image
        
        if backdrop_path:
            # 16:9 widescreen image URLs
            image_url_high = f"https://image.tmdb.org/t/p/w1280{backdrop_path}"
            image_url_original = f"https://image.tmdb.org/t/p/original{backdrop_path}"
            
            caption = (
                f"🎬 **{title}**\n"
                f"📺 **Type:** {media_type}\n"
                f"📐 *16:9 Widescreen Thumbnail*\n\n"
                f"🔗 **[Click Here to Open Full Image Link]({image_url_original})**"
            )
            
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.send_photo(
                chat_id=message.chat.id,
                photo=image_url_high,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("❌ 16:9 landscape banner not available for this title.", message.chat.id, status_msg.message_id)
    else:
        bot.edit_message_text("❌ Content not found! Please check your spelling or try another title.", message.chat.id, status_msg.message_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Run Telegram bot polling in a background thread
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    # Run Flask server for Render 24/7 uptime
    app.run(host="0.0.0.0", port=port)
