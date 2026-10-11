import os
import io
import sqlite3
import telebot
import requests
from flask import Flask, send_file, request
import threading
from PIL import Image, ImageDraw, ImageFont

# Load credentials from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

session = requests.Session()

# Temporary in-memory cache for processed 16:9 images to serve via Flask web route
PROCESSED_IMAGES_CACHE = {}

# YOUR OWNER ID
OWNER_ID = 7284759394

# Custom Image URLs
START_IMAGE_URL = "https://telegra.ph/file/2ab528ba65c23832cdcf6-4ff26f1b433ef961eb.jpg"
ABOUT_IMAGE_URL = "https://graph.org/file/283e03b08d8306b8d85af-8436c3be9697b2374c.jpg"
FSUB_IMAGE_URL  = "https://graph.org/file/faf795187aa693e1024a4-746b376c8dcc889d4f.jpg"

# --- Database Initialization (Persistent across redeploys) ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fsub_channels (
            channel TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user_to_db(user_id, first_name):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_all_users():
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, first_name FROM users")
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception:
        return []

def is_user_banned(user_id):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        banned = cursor.fetchone() is not None
        conn.close()
        return banned
    except Exception:
        return False

def ban_user_db(user_id):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def unban_user_db(user_id):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_banned_users():
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM banned_users")
        banned = [row[0] for row in cursor.fetchall()]
        conn.close()
        return banned
    except Exception:
        return []

def get_fsub_channels():
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT channel FROM fsub_channels")
        channels = [row[0] for row in cursor.fetchall()]
        conn.close()
        return channels
    except Exception:
        return []

def add_fsub_channel_db(channel):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO fsub_channels (channel) VALUES (?)", (channel,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def remove_fsub_channel_db(channel):
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fsub_channels WHERE channel = ?", (channel,))
        conn.commit()
        conn.close()
    except Exception:
        pass

@app.route('/')
def home():
    return "Mohammed Poster Bot is running 24/7!"

@app.route('/poster/<item_id>')
def serve_poster(item_id):
    """Flask route to serve the generated 16:9 poster with official logo overlay."""
    if item_id in PROCESSED_IMAGES_CACHE:
        img_io = PROCESSED_IMAGES_CACHE[item_id]
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    return "Poster not found or expired.", 404

def is_user_member(user_id):
    channels = get_fsub_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            pass
    return True

def send_fsub_prompt(chat_id):
    channels = get_fsub_channels()
    markup = telebot.types.InlineKeyboardMarkup()
    for channel in channels:
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
    first_name = message.from_user.first_name or "User"
    add_user_to_db(user_id, first_name)
    
    if is_user_banned(user_id):
        bot.reply_to(message, "❌ <b>You are banned from using this bot.</b>", parse_mode="HTML")
        return
    
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
    
    markup.row(about_btn, updates_btn)
    markup.row(owner_btn)
    
    try:
        bot.send_photo(message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ You are banned from using this bot.", show_alert=True)
        return
    
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

# --- Admin-Only Commands ---
@bot.message_handler(commands=['stats'])
def bot_stats(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    
    users = get_all_users()
    total_users = len(users)
    
    user_list_str = ""
    for idx, (uid, fname) in enumerate(users[:25], 1):
        user_list_str += f"{idx}. {fname} (<code>{uid}</code>)\n"
    
    if total_users > 25:
        user_list_str += f"\n<i>...and {total_users - 25} more users.</i>"

    stats_msg = (
        f"📊 <b>Bot Statistics:</b>\n\n"
        f"👥 Total Unique Users: <code>{total_users}</code>\n\n"
        f"<b>User List:</b>\n{user_list_str if user_list_str else 'No users yet.'}"
    )
    bot.reply_to(message, stats_msg, parse_mode="HTML")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        try:
            target_id = int(args[1].strip())
            ban_user_db(target_id)
            bot.reply_to(message, f"✅ Successfully banned user ID: <code>{target_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(message, "⚠️ Invalid User ID format. Use numeric ID.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/ban USER_ID`", parse_mode="HTML")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        try:
            target_id = int(args[1].strip())
            unban_user_db(target_id)
            bot.reply_to(message, f"✅ Successfully unbanned user ID: <code>{target_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(message, "⚠️ Invalid User ID format. Use numeric ID.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/unban USER_ID`", parse_mode="HTML")

@bot.message_handler(commands=['banlist'])
def list_banned_users(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    banned_ids = get_banned_users()
    if banned_ids:
        banned_str = "\n".join([f"• <code>{uid}</code>" for uid in banned_ids])
        bot.reply_to(message, f"🚫 <b>Banned Users List:</b>\n\n{banned_str}", parse_mode="HTML")
    else:
        bot.reply_to(message, "ℹ️ No banned users.", parse_mode="HTML")

@bot.message_handler(commands=['addforcesub'])
def add_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        current_channels = get_fsub_channels()
        if channel not in current_channels:
            add_fsub_channel_db(channel)
            bot.reply_to(message, f"✅ Successfully added <code>{channel}</code> to Force Subscription list.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"⚠️ Channel <code>{channel}</code> is already in the list.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/addforcesub @ChannelUsername`", parse_mode="HTML")

@bot.message_handler(commands=['removeforce'])
def remove_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        current_channels = get_fsub_channels()
        if channel in current_channels:
            remove_fsub_channel_db(channel)
            bot.reply_to(message, f"✅ Successfully removed <code>{channel}</code> from Force Subscription list.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ Channel <code>{channel}</code> not found in list.", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ Usage: `/removeforce @ChannelUsername`", parse_mode="HTML")

@bot.message_handler(commands=['fsublist'])
def list_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the bot owner only.", parse_mode="HTML")
        return
    channels = get_fsub_channels()
    if channels:
        channels_str = "\n".join([f"• <code>{ch}</code>" for ch in channels])
        bot.reply_to(message, f"📢 <b>Force Subscription Channels:</b>\n\n{channels_str}", parse_mode="HTML")
    else:
        bot.reply_to(message, "ℹ️ No Force Subscription channels are currently set.", parse_mode="HTML")

# --- Helper: Fetch Official Title Logo PNG from TMDb ---
def get_tmdb_logo_url(item_id, media_type):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/images?api_key={TMDB_API_KEY}"
    try:
        res = session.get(url, timeout=4).json()
        logos = res.get("logos", [])
        if logos:
            # Prefer English logos if available
            en_logos = [l for l in logos if l.get("iso_639_1") == "en"]
            selected_logo = en_logos[0] if en_logos else logos[0]
            return f"https://image.tmdb.org/t/p/original{selected_logo['file_path']}"
    except Exception:
        pass
    return None

# --- Poster Generation Logic (Overlay Official Logo PNG or Serif Fallback) ---
def add_title_overlay(image_bytes, title_text, logo_url=None):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    target_width = 1280
    target_height = 720
    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    logo_applied = False
    
    # Attempt to paste official PNG logo if available
    if logo_url:
        try:
            logo_res = session.get(logo_url, timeout=5)
            if logo_res.status_code == 200:
                logo_img = Image.open(io.BytesIO(logo_res.content)).convert("RGBA")
                
                # Resize logo appropriately (max width 60%, max height 30% of canvas)
                max_logo_w = int(target_width * 0.6)
                max_logo_h = int(target_height * 0.3)
                logo_img.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
                
                logo_w, logo_h = logo_img.size
                x = int((target_width - logo_w) / 2)
                y = int(target_height - logo_h - (target_height * 0.08))
                
                # Paste transparent PNG logo onto 16:9 canvas
                image.paste(logo_img, (x, y), logo_img)
                logo_applied = True
        except Exception:
            pass

    # Fallback to Serif typography if official logo is missing
    if not logo_applied:
        rgb_image = image.convert("RGB")
        draw = ImageDraw.Draw(rgb_image)
        width, height = rgb_image.size
        
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
            font_size = int(height * 0.10)
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        words = title_text.split()
        if len(words) > 3:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            title_lines = [line1, line2]
        else:
            title_lines = [title_text]

        line_heights = []
        line_widths = []
        for line in title_lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except:
                w, h = draw.textsize(line, font=font)
            line_widths.append(w)
            line_heights.append(h)

        total_text_height = sum(line_heights) + (len(title_lines) - 1) * 10
        y = height - total_text_height - int(height * 0.10)

        for i, line in enumerate(title_lines):
            x = (width - line_widths[i]) / 2
            outline_range = 3
            for adj_x in range(-outline_range, outline_range + 1):
                for adj_y in range(-outline_range, outline_range + 1):
                    draw.text((x + adj_x, y + adj_y), line, font=font, fill="black")

            draw.text((x, y), line, font=font, fill="white")
            y += line_heights[i] + 10
        image = rgb_image

    output = io.BytesIO()
    image.convert("RGB").save(output, format="JPEG", quality=92)
    output.seek(0)
    return output

@bot.message_handler(func=lambda message: True)
def search_poster(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    add_user_to_db(user_id, first_name)

    if is_user_banned(user_id):
        return

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
            item_id = str(item.get("id"))
            media_type = item.get("media_type", "movie")
            
            release_date = item.get("release_date") or item.get("first_air_date") or ""
            year = release_date.split("-")[0] if release_date else "N/A"
            
            backdrop_path = item.get("backdrop_path")
            poster_path = item.get("poster_path")
            
            backdrop_url_original = f"https://image.tmdb.org/t/p/original{backdrop_path}"
            portrait_url_original = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else backdrop_url_original
            
            # Fetch official title logo PNG
            logo_url = get_tmdb_logo_url(item_id, media_type)
            
            img_response = session.get(backdrop_url_original, timeout=8)
            if img_response.status_code == 200:
                # Generate 16:9 widescreen poster with official logo overlay
                processed_image = add_title_overlay(img_response.content, title, logo_url)
                
                PROCESSED_IMAGES_CACHE[item_id] = processed_image
                
                app_url = os.environ.get("RENDER_EXTERNAL_URL") or request.host_url.rstrip('/')
                titled_poster_url = f"{app_url}/poster/{item_id}"
                
                caption_lines = [
                    "<b>ᴍᴏʜᴀᴍᴍᴇᴅ ᴘᴏsᴛᴇʀ ʙᴏᴛ</b>\n",
                    f"<b>ᴘᴏʀᴛʀᴀɪᴛ :</b> <a href=\"{portrait_url_original}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n",
                    f"<b>ᴄᴏᴠᴇʀ :</b> <a href=\"{titled_poster_url}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n",
                    f"<b>ᴛɪᴛʟᴇ : {title} ({year})</b>"
                ]
                
                caption = "\n".join(caption_lines)
                
                markup = telebot.types.InlineKeyboardMarkup()
                aero_button = telebot.types.InlineKeyboardButton(text="• ᴀᴇʀᴏ ᴜɴɪᴛʏ •", url="https://t.me/Aero_Unity")
                open_image_button = telebot.types.InlineKeyboardButton(text="ᴏᴘᴇɴ ɪᴍᴀɢᴇ ↗", url=titled_poster_url)
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
