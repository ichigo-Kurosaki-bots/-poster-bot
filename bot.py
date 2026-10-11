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
        "and I will generate the 16:9 widescreen poster layout for you!"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

def add_title_overlay(image_bytes, title_text):
    """Downloads backdrop, ensures 16:9 landscape ratio, and adds stylized title overlay."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Force strict 16:9 widescreen ratio
    target_width = 1280
    target_height = 720
    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_size = int(height * 0.08)
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    try:
        bbox = draw.textbbox((0, 0), title_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width, text_height = draw.textsize(title_text, font=font)

    x = (width - text_width) / 2
    y = height - text_height - int(height * 0.12)

    # Draw text outline/shadow for readability
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

def get_watch_provider_link(item_id, media_type):
    """Fetches watch provider link (e.g. Prime Video / Netflix) from TMDb."""
    endpoint = "movie" if media_type == "movie" else "tv"
    watch_url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
    try:
        res = requests.get(watch_url).json()
        results = res.get("results", {})
        for country in ["IN", "US", "GB"]:
            if country in results and "link" in results[country]:
                return "ᴘʀɪᴍᴇ ᴠɪᴅᴇᴏ ᴘᴏsᴛᴇʀ", results[country]["link"]
        if results:
            first_country = list(results.keys())[0]
            if "link" in results[first_country]:
                return "sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋ", results[first_country]["link"]
    except Exception:
        pass
    return None, None

@bot.message_handler(func=lambda message: True)
def search_poster(message):
    query = message.text.strip()
    
    if query.startswith("/p "):
        query = query[3:].strip()
    elif query.startswith("/poster "):
        query = query[8:].strip()

    status_msg = bot.reply_to(message, f"🔍 <i>Searching 16:9 poster layout for:</i> <code>{query}</code>...", parse_mode="HTML")
    
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
            valid_items = [i for i in results if i.get("backdrop_path")]
            if not valid_items:
                bot.edit_message_text("❌ 16:9 landscape banner not available for this title.", message.chat.id, status_msg.message_id)
                return

            item = valid_items[0]
            title = item.get("title") or item.get("name") or "Unknown Title"
            item_id = item.get("id")
            media_type = item.get("media_type", "movie")
            
            release_date = item.get("release_date") or item.get("first_air_date") or ""
            year = release_date.split("-")[0] if release_date else "N/A"
            
            backdrop_path = item.get("backdrop_path")
            poster_path = item.get("poster_path")
            
            backdrop_url_original = f"https://image.tmdb.org/t/p/original{backdrop_path}"
            portrait_url_original = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else backdrop_url_original
            
            # Fetch OTT / Watch Provider link
            provider_label, provider_link = get_watch_provider_link(item_id, media_type)
            
            # Fetch background image bytes
            img_response = requests.get(backdrop_url_original)
            if img_response.status_code == 200:
                processed_image = add_title_overlay(img_response.content, title)
                
                # Styled caption using small caps formatting
                caption_lines = [
                    "<b>ᴍᴏʜᴀᴍᴍᴇᴅ ᴘᴏsᴛᴇʀ ʙᴏᴛ</b>\n"
                ]
                
                if provider_link:
                    caption_lines.append(f"<b>{provider_label}:</b> {provider_link}\n")
                
                caption_lines.append(f"<b>ᴘᴏʀᴛʀᴀɪᴛ:</b> <a href=\"{portrait_url_original}\">ᴄʟɪᴄᴋ ʜᴇʀᴇ</a>\n")
                caption_lines.append(f"<b>ᴄᴏᴠᴇʀ:</b> <a href=\"{backdrop_url_original}\">ᴄʟɪᴄᴋ ʜᴇʀᴇ</a>\n")
                caption_lines.append(f"<b>{title} ({year})</b>")
                
                caption = "\n".join(caption_lines)
                
                # Inline Buttons: Aero Unity button and Open Image button side-by-side
                markup = telebot.types.InlineKeyboardMarkup()
                aero_button = telebot.types.InlineKeyboardButton(text="• ᴀᴇʀᴏ ᴜɴɪᴛʏ •", url="https://t.me/Aero_Unity")
                open_image_button = telebot.types.InlineKeyboardButton(text="ᴏᴘᴇɴ ɪᴍᴀɢᴇ ↗", url=backdrop_url_original)
                markup.row(aero_button, open_image_button)
                
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.send_photo(
                    chat_id=message.chat.id,
                    photo=processed_image,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                bot.edit_message_text("❌ Failed to download background image.", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("❌ Content not found! Please check your spelling or try another title.", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"⚠️ An error occurred: {str(e)}", message.chat.id, status_msg.message_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=port)
