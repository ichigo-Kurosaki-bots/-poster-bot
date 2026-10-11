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

session = requests.Session()

USERS_DB = set()
FORCE_SUB_CHANNELS = [] # e.g. ["@Aero_Unity"]

# Custom Image URLs
START_IMAGE_URL = "https://telegra.ph/file/2ab528ba65c23832cdcf6-4ff26f1b433ef961eb.jpg"
ABOUT_IMAGE_URL = "https://graph.org/file/283e03b08d8306b8d85af-8436c3be9697b2374c.jpg"
FSUB_IMAGE_URL  = "https://graph.org/file/faf795187aa693e1024a4-746b376c8dcc889d4f.jpg"

@app.route('/')
def home():
    return "Mohammed Poster Bot is running 24/7!"

def is_user_member(user_id):
    if not FORCE_SUB_CHANNELS:
        return True
    for channel in FORCE_SUB_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            pass
    return True

def send_fsub_prompt(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    for channel in FORCE_SUB_CHANNELS:
        channel_name = channel.replace("@", "")
        markup.add(telebot.types.InlineKeyboardButton(text=f"• Join {channel}", url=f"https://t.me/{channel_name}"))
    
    markup.add(telebot.types.InlineKeyboardButton(text="🔄 Check Subscription", callback_data="check_fsub"))
    
    fsub_text = (
        "⚠️ <b>Access Denied!</b>\n\n"
        "You must join our update channels below to use this bot.\n"
        "After joining, click <b>Check Subscription</b> to continue."
    )
    try:
        bot.send_photo(chat_id, FSUB_IMAGE_URL, caption=fsub_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, fsub_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    USERS_DB.add(user_id)
    
    if not is_user_member(user_id):
        send_fsub_prompt(message.chat.id)
        return

    welcome_text = (
        "👋 <b>Welcome to Universal Poster Bot!</b>\n\n"
        "Send me any title (Movies, Series, Anime, K-Dramas, etc.), "
        "and I will generate the 16:9 widescreen poster layout for you!"
    )
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    about_btn = telebot.types.InlineKeyboardButton(text="• About •", callback_data="btn_about")
    updates_btn = telebot.types.InlineKeyboardButton(text="• Updates •", url="https://t.me/Aero_Unity")
    owner_btn = telebot.types.InlineKeyboardButton(text="• Owner •", url="https://t.me/Mr_Mohammed_29")
    
    # Layout: About | Updates on top row, Owner on bottom row
    markup.row(about_btn, updates_btn)
    markup.row(owner_btn)
    
    try:
        bot.send_photo(message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "check_fsub":
        if is_user_member(user_id):
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            
            welcome_text = (
                "✅ <b>Verification Successful!</b>\n\n"
                "👋 Welcome back! Send me any title (Movies, Series, Anime, K-Dramas, etc.) "
                "to generate your 16:9 widescreen poster."
            )
            markup = telebot.types.InlineKeyboardMarkup(row_width=2)
            about_btn = telebot.types.InlineKeyboardButton(text="• About •", callback_data="btn_about")
            updates_btn = telebot.types.InlineKeyboardButton(text="• Updates •", url="https://t.me/Aero_Unity")
            owner_btn = telebot.types.InlineKeyboardButton(text="• Owner •", url="https://t.me/Mr_Mohammed_29")
            markup.row(about_btn, updates_btn)
            markup.row(owner_btn)
            
            bot.send_photo(call.message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet!", show_alert=True)
            
    elif call.data == "btn_about":
        about_text = (
            "⍟───[ <b>ᴍʏ ᴅᴇᴛᴀɪʟꜱ</b> ]───⍟\n\n"
            "‣ <b>ᴍʏ ɴᴀᴍᴇ : Poster Bot</b>\n"
            "‣ <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href=\"https://t.me/Mr_Mohammed_29\"><b>Mohammed</b></a></b>\n"
            "‣ <b>ʟɪʙʀᴀʀʏ : ᴘʏʀᴏɢʀᴀᴍ / ᴛᴇʟᴇʙᴏᴛ </b>\n"
            "‣ <b>ʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ 3 </b>\n"
            "‣ <b>ʙᴏᴛ sᴇʀᴠᴇʀ : <a href=\"https://t.me/Aero_Unity\"><b>Aero Unity</b></a></b>\n"
            "‣ <b>ʙᴜɪʟᴅ sᴛᴀᴛᴜs : ᴠ3.9.1 [sᴛᴀʙʟᴇ] </b>"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        home_btn = telebot.types.InlineKeyboardButton(text="🏠 Home", callback_data="btn_home")
        markup.add(home_btn)
        
        try:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=telebot.types.InputMediaPhoto(ABOUT_IMAGE_URL, caption=about_text, parse_mode="HTML"),
                reply_markup=markup
            )
        except Exception:
            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=about_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception:
                bot.send_photo(call.message.chat.id, ABOUT_IMAGE_URL, caption=about_text, parse_mode="HTML", reply_markup=markup)

    elif call.data == "btn_home":
        welcome_text = (
            "👋 <b>Welcome to Universal Poster Bot!</b>\n\n"
            "Send me any title (Movies, Series, Anime, K-Dramas, etc.), "
            "and I will generate the 16:9 widescreen poster layout for you!"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        about_btn = telebot.types.InlineKeyboardButton(text="• About •", callback_data="btn_about")
        updates_btn = telebot.types.InlineKeyboardButton(text="• Updates •", url="https://t.me/Aero_Unity")
        owner_btn = telebot.types.InlineKeyboardButton(text="• Owner •", url="https://t.me/Mr_Mohammed_29")
        markup.row(about_btn, updates_btn)
        markup.row(owner_btn)
        
        try:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=telebot.types.InputMediaPhoto(START_IMAGE_URL, caption=welcome_text, parse_mode="HTML"),
                reply_markup=markup
            )
        except Exception:
            try:
                bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception:
                bot.send_photo(call.message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)

# --- Admin Force Sub & Stats Commands ---
@bot.message_handler(commands=['stats'])
def bot_stats(message):
    total_users = len(USERS_DB)
    bot.reply_to(message, f"📊 <b>Bot Statistics:</b>\n\n👥 Total Unique Users: <code>{total_users}</code>", parse_mode="HTML")

@bot.message_handler(commands=['addforcesub'])
def add_force_sub(message):
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        if channel not in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.append(channel)
            bot.reply_to(message, f"✅ Successfully added <code>{channel}</code> to Force Subscription list.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"⚠️ Channel <code>{channel}</code> is already in the list.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/addforcesub @ChannelUsername`", parse_mode="HTML")

@bot.message_handler(commands=['removeforce'])
def remove_force_sub(message):
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        if channel in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.remove(channel)
            bot.reply_to(message, f"✅ Successfully removed <code>{channel}</code> from Force Subscription list.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ Channel <code>{channel}</code> not found in list.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/removeforce @ChannelUsername`", parse_mode="HTML")

@bot.message_handler(commands=['fsublist'])
def list_force_sub(message):
    if FORCE_SUB_CHANNELS:
        channels_str = "\n".join([f"• <code>{ch}</code>" for ch in FORCE_SUB_CHANNELS])
        bot.reply_to(message, f"📢 <b>Force Subscription Channels:</b>\n\n{channels_str}", parse_mode="HTML")
    else:
        bot.reply_to(message, "ℹ️ No Force Subscription channels are currently set.", parse_mode="HTML")

# --- Poster Generation Logic ---
def add_title_overlay(image_bytes, title_text):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
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

    outline_range = 3
    for adj_x in range(-outline_range, outline_range + 1):
        for adj_y in range(-outline_range, outline_range + 1):
            draw.text((x + adj_x, y + adj_y), title_text, font=font, fill="black")

    draw.text((x, y), title_text, font=font, fill="white")

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=90)
    output.seek(0)
    return output

def get_watch_provider_link(item_id, media_type):
    endpoint = "movie" if media_type == "movie" else "tv"
    watch_url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/watch/providers?api_key={TMDB_API_KEY}"
    try:
        res = session.get(watch_url, timeout=5).json()
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
    user_id = message.from_user.id
    USERS_DB.add(user_id)

    if not is_user_member(user_id):
        send_fsub_prompt(message.chat.id)
        return

    query = message.text.strip()
    if query.startswith("/p "):
        query = query[3:].strip()
    elif query.startswith("/poster "):
        query = query[8:].strip()

    status_msg = bot.reply_to(message, f"<b><i>Searching <code>{query}</code>...</i></b>", parse_mode="HTML")
    
    if not TMDB_API_KEY:
        bot.edit_message_text("⚠️ <b>Error:</b> <code>TMDB_API_KEY</code> is missing in Render environment variables!", message.chat.id, status_msg.message_id, parse_mode="HTML")
        return

    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(query)}"
    
    try:
        res = session.get(url, timeout=5)
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
            
            provider_label, provider_link = get_watch_provider_link(item_id, media_type)
            
            img_response = session.get(backdrop_url_original, timeout=8)
            if img_response.status_code == 200:
                processed_image = add_title_overlay(img_response.content, title)
                
                caption_lines = [
                    "<b>ᴍᴏʜᴀᴍᴍᴇᴅ ᴘᴏsᴛᴇʀ ʙᴏᴛ</b>\n"
                ]
                
                if provider_link:
                    caption_lines.append(f"<b>{provider_label}:</b> <a href=\"{provider_link}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n")
                
                caption_lines.append(f"<b>ᴘᴏʀᴛʀᴀɪᴛ:</b> <a href=\"{portrait_url_original}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n")
                caption_lines.append(f"<b>ᴄᴏᴠᴇʀ:</b> <a href=\"{backdrop_url_original}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n")
                caption_lines.append(f"<b>{title} ({year})</b>")
                
                caption = "\n".join(caption_lines)
                
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
