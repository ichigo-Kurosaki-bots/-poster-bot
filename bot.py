import os
import io
import telebot
import requests
from flask import Flask
import threading
from PIL import Image, ImageDraw, ImageFont

# Load credentials from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Mohammed Poster Bot is running 24/7!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>Welcome to Universal Poster Bot!</b>\n\n"
        "Send me any title (Movies, Series, Anime, K-Dramas, etc.), "
        "and I will generate the poster layout for you!"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

def add_title_overlay(image_bytes, title_text):
    """Adds a stylized title overlay to the bottom center of the image."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    # Load default linux font or fallback to default
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_size = int(height * 0.08)
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    # Calculate text dimensions
    try:
        bbox = draw.textbbox((0, 0), title_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width, text_height = draw.textsize(title_text, font=font)

    x = (width - text_width) / 2
    y = height - text_height - int(height * 0.1)

    # Draw text outline/shadow for high visibility
    outline_range = 3
    for adj_x in range(-outline_range, outline_range + 1):
        for adj_y in range(-outline_range, outline_range + 1):
            draw.text((x + adj_x, y + adj_y), title_text, font=font, fill="black")

    # Draw main text in white
    draw.text((x, y), title_text, font=font, fill="white")

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output

@bot.message_handler(func=lambda message: True)
def search_poster(message):
    query = message.text.strip()
    
    # Remove leading command if user types /p or /poster
    if query.startswith("/p "):
        query = query[3:].strip()
    elif query.startswith("/poster "):
        query = query[8:].strip()

    status_msg = bot.reply_to(message, f"🔍 <i>Searching poster layout for:</i> <code>{query}</code>...", parse_mode="HTML")
    
    if not TMDB_API_KEY:
        bot.edit_message_text("⚠️ <b>Error:</b> <code>TMDB_API_KEY</code> is missing in Render environment variables!", message.chat.id, status_msg.message_id, parse_mode="HTML")
        return

    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}"
    
    try:
        res = requests.get(url)
        if res.status_code != 200:
            bot.edit_message_text(f"⚠️ <b>TMDb API Error ({res.status_code}):</b> Check your API Key.", message.chat.id, status_msg.message_id, parse_mode="HTML")
            return

        response = res.json()
        results = response.get("results", [])

        if results:
            item = next((i for i in results if i.get("backdrop_path")), results[0])
            title = item.get("title") or item.get("name") or "Unknown Title"
            release_date = item.get("release_date") or item.get("first_air_date") or ""
            year = release_date.split("-")[0] if release_date else "N/A"
            
            backdrop_path = item.get("backdrop_path")
            poster_path = item.get("poster_path")
            
            if backdrop_path:
                backdrop_url_original = f"https://image.tmdb.org/t/p/original{backdrop_path}"
                portrait_url_original = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else backdrop_url_original
                
                # Fetch image bytes
                img_response = requests.get(backdrop_url_original)
                if img_response.status_code == 200:
                    processed_image = add_title_overlay(img_response.content, title)
                    
                    # Formatted text matching your screenshot
                    user_name = message.from_user.first_name if message.from_user else "User"
                    caption = (
                        f"<b>Mohammed Poster Bot</b>  <i>Admin</i>\n\n"
                        f"<b>Portrait:</b> <a href=\"{portrait_url_original}\">Click Here</a>\n\n"
                        f"<b>Cover:</b> <a href=\"{backdrop_url_original}\">Click Here</a>\n\n"
                        f"<b>{title} ({year})</b>"
                    )
                    
                    # Updates button at the bottom
                    markup = telebot.types.InlineKeyboardMarkup()
                    updates_button = telebot.types.InlineKeyboardButton(text="• ᴀᴇʀᴏ ᴜɴɪᴛʏ •", url="https://t.me/Aero_Unity")
                    markup.add(updates_button)
                    
                    bot.delete_message(message.chat.id, status_msg.message_id)
                    bot.send_photo(
                        chat_id=message.chat.id,
                        photo=processed_image,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                else:
                    bot.edit_message_text("❌ Failed to download backdrop image.", message.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text("❌ Landscape banner not available for this title.", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Content not found! Please check your spelling or try another title.", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"⚠️ An error occurred: {str(e)}", message.chat.id, status_msg.message_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=port)
