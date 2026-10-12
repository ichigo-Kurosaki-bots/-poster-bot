import os
import io
import re
import html
import telebot
import requests
from flask import Flask, send_file, request
import threading
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import database

# Load credentials from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

# Official Group link for the restriction button
POSTER_GROUP_URL = os.environ.get("POSTER_GROUP_URL", "https://t.me/+VXY_za8DNjQzYmVl")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

session = requests.Session()

# Persistent directory cache for processed images so web links never expire with an Internal Server Error
CACHE_DIR = "poster_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# YOUR OWNER ID
OWNER_ID = 7284759394

# Custom Image URLs
START_IMAGE_URL = "https://telegra.ph/file/2ab528ba65c23832cdcf6-4ff26f1b433ef961eb.jpg"
ABOUT_IMAGE_URL = "https://graph.org/file/283e03b08d8306b8d85af-8436c3be9697b2374c.jpg"
FSUB_IMAGE_URL  = "https://graph.org/file/faf795187aa693e1024a4-746b376c8dcc889d4f.jpg"

# Initialize SQLite tables
database.init_db()

@app.route('/')
def home():
    return "mohammed poster bot is running 24/7!"

@app.route('/poster/<item_id>')
def serve_poster(item_id):
    """Flask route to reliably serve the cached poster image file."""
    file_path = os.path.join(CACHE_DIR, f"{item_id}.jpg")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')
    return "poster not found or expired.", 404

def is_user_member(user_id):
    channels = database.get_fsub_channels()
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
    channels = database.get_fsub_channels()
    markup = telebot.types.InlineKeyboardMarkup()
    for channel in channels:
        channel_name = channel.replace("@", "")
        markup.add(telebot.types.InlineKeyboardButton(text=f"• join {channel}", url=f"https://t.me/{channel_name}"))
    
    markup.add(telebot.types.InlineKeyboardButton(text="🔄 check subscription", callback_data="check_fsub"))
    
    fsub_text = (
        "⚠️ <b>access denied!</b>\n\n"
        "you must join our update channels below to use this bot.\n"
        "after joining, click <b>check subscription</b> to continue."
    )
    try:
        bot.send_photo(chat_id, FSUB_IMAGE_URL, caption=fsub_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, fsub_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "user"
    database.add_user(user_id, first_name)
    
    if database.is_banned(user_id):
        bot.reply_to(message, "❌ <b>you are banned from using this bot.</b>", parse_mode="HTML")
        return
    
    if not is_user_member(user_id):
        send_fsub_prompt(message.chat.id)
        return

    welcome_text = (
        "👋 <b>welcome to universal poster bot!</b>\n\n"
        "send me any title (movies, series, anime, k-dramas, etc.), "
        "and i will generate the 16:9 widescreen poster layout for you!"
    )
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    about_btn = telebot.types.InlineKeyboardButton(text="• about •", callback_data="btn_about")
    updates_btn = telebot.types.InlineKeyboardButton(text="• updates •", url="https://t.me/Aero_Unity")
    owner_btn = telebot.types.InlineKeyboardButton(text="• owner •", url="https://t.me/Mr_Mohammed_29")
    
    markup.row(about_btn, updates_btn)
    markup.row(owner_btn)
    
    try:
        bot.send_photo(message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

# --- Command: Owner-Only PM Search Toggle ---
@bot.message_handler(commands=['pmsearch'])
def toggle_pm_search(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ <b>access denied:</b> owner command only.", parse_mode="HTML")
        return

    args = message.text.strip().split()
    if len(args) > 1:
        action = args[1].lower()
        if action in ['on', 'enable', 'true', '1']:
            database.set_global_pm_search(True)
            bot.reply_to(message, "✅ <b>pm search enabled for users!</b>", parse_mode="HTML")
        elif action in ['off', 'disable', 'false', '0']:
            database.set_global_pm_search(False)
            bot.reply_to(message, "🔒 <b>pm search disabled for users!</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, "⚠️ usage: <code>/pmsearch on</code> or <code>/pmsearch off</code>", parse_mode="HTML")
    else:
        status = database.get_global_pm_search()
        status_str = "🟢 <b>on</b>" if status else "🔴 <b>off</b>"
        bot.reply_to(message, f"ℹ️ <b>pm search status:</b> {status_str}", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if database.is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ you are banned from using this bot.", show_alert=True)
        return
    
    if call.data == "check_fsub":
        if is_user_member(user_id):
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            
            welcome_text = (
                "✅ <b>Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇssғᴜʟ</b>\n\n"
                "<b>Wᴇʟᴄᴏᴍᴇ Bᴀᴄᴋ 𝗌𝖾𝗇𝖽 𝗆𝖾 𝖺𝗇𝗒 𝗍𝗂𝗍𝗅𝖾 (𝗆𝗈𝗏𝗂𝖾𝗌, 𝗌𝖾𝗋𝗂𝖾𝗌, 𝖺𝗇𝗂𝗆𝖾, 𝗄-𝖽𝗋𝖺𝗆𝖺𝗌, 𝖾𝗍𝖼.), "
                "to 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝗍𝗁𝖾 𝗉𝗈𝗌𝗍𝖾𝗋 𝗅𝖺𝗒𝗈𝗎𝗍 𝖿𝗈𝗋 𝗒𝗈𝗎</b>"
            )
            markup = telebot.types.InlineKeyboardMarkup(row_width=2)
            about_btn = telebot.types.InlineKeyboardButton(text="• about •", callback_data="btn_about")
            updates_btn = telebot.types.InlineKeyboardButton(text="• updates •", url="https://t.me/Aero_Unity")
            owner_btn = telebot.types.InlineKeyboardButton(text="• owner •", url="https://t.me/Mr_Mohammed_29")
            markup.row(about_btn, updates_btn)
            markup.row(owner_btn)
            
            bot.send_photo(call.message.chat.id, START_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ you haven't joined all channels yet!", show_alert=True)
            
    elif call.data == "btn_about":
        about_text = (
            "⍟───[ <b>ᴍʏ ᴅᴇᴛᴀɪʟꜱ</b> ]───⍟\n\n"
            "‣ <b>ᴍʏ ɴᴀᴍᴇ : poster bot</b>\n"
            "‣ <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href=\"https://t.me/Mr_Mohammed_29\"><b>mohammed</b></a></b>\n"
            "‣ <b>ʟɪʙʀᴀʀʏ : pyrogram / telebot </b>\n"
            "‣ <b>ʟᴀɴɢᴜᴀɢᴇ : python 3 </b>\n"
            "‣ <b>ʙᴏᴛ sᴇʀᴠᴇʀ : <a href=\"https://t.me/Aero_Unity\"><b>aero unity</b></a></b>\n"
            "‣ <b>ʙᴜɪʟᴅ sᴛᴀᴛᴜs : ᴠ3.9.1 [sᴛᴀʙʟᴇ] </b>"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        home_btn = telebot.types.InlineKeyboardButton(text="🏠 home", callback_data="btn_home")
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
            "👋 <b>Wᴇʟᴄᴏᴍᴇ Tᴏ Uɴɪᴠᴇʀsᴀʟ Pᴏsᴛᴇʀ Bᴏᴛ!</b>\n\n"
            "<b>𝗌𝖾𝗇𝖽 𝗆𝖾 𝖺𝗇𝗒 𝗍𝗂𝗍𝗅𝖾 (𝗆𝗈𝗏𝗂𝖾𝗌, 𝗌𝖾𝗋𝗂𝖾𝗌, 𝖺𝗇𝗂𝗆𝖾, 𝗄-𝖽𝗋𝖺𝗆𝖺𝗌, 𝖾𝗍𝖼.),"
            "𝖺𝗇𝖽 𝗂 𝗐𝗂𝗅𝗅 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝗍𝗁𝖾 𝗉𝗈𝗌𝗍𝖾𝗋 𝗅𝖺𝗒𝗈𝗎𝗍 𝖿𝗈𝗋 𝗒𝗈𝗎!</b>"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        about_btn = telebot.types.InlineKeyboardButton(text="• Aʙᴏᴜᴛ •", callback_data="btn_about")
        updates_btn = telebot.types.InlineKeyboardButton(text="• Uᴘᴅᴀᴛᴇs •", url="https://t.me/Aero_Unity")
        owner_btn = telebot.types.InlineKeyboardButton(text="• Oᴡɴᴇʀ •", url="https://t.me/Mr_Mohammed_29")
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

# --- Admin-Only Commands --- #
@bot.message_handler(commands=['stats'])
def bot_stats(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "<b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ </b>", parse_mode="HTML")
        return
    
    users = database.get_all_users()
    total_users = len(users)
    
    user_list_str = ""
    for idx, (uid, fname) in enumerate(users[:25], 1):
        safe_fname = html.escape(fname or "user")
        user_list_str += f"{idx}. {safe_fname} (<code>{uid}</code>)\n"
    
    if total_users > 25:
        user_list_str += f"\n<i>...and {total_users - 25} more users.</i>"

    stats_msg = (
        f"📊 <b>𝖡𝗈𝗍 𝖲𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝗌:</b>\n\n"
        f"<b>ᴛᴏᴛᴀʟ ᴜsᴇʀs:</b> <code>{total_users}</code>\n\n"
        f"<b>ᴜsᴇʀs ʟɪsᴛs:</b>\n{user_list_str if user_list_str else 'no users yet.'}"
    )
    bot.reply_to(message, stats_msg, parse_mode="HTML")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ</b>", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        try:
            target_id = int(args[1].strip())
            database.ban_user(target_id)
            bot.reply_to(message, f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʙᴀɴɴᴇᴅ ᴀ ᴜsᴇʀ ɪᴅ : <code>{target_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(message, "‼️ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ", parse_mode="HTML")
    else:
        bot.reply_to(message, " <code>/ban user_id</code>", parse_mode="HTML")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ</b>", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        try:
            target_id = int(args[1].strip())
            database.unban_user(target_id)
            bot.reply_to(message, f"✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴜɴʙᴀɴɴᴇᴅ ᴜsᴇʀ ɪᴅ : <code>{target_id}</code>", parse_mode="HTML")
        except ValueError:
            bot.reply_to(message, "‼️ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.", parse_mode="HTML")
    else:
        bot.reply_to(message, "<code>/unban user_id</code>", parse_mode="HTML")

@bot.message_handler(commands=['banlist'])
def list_banned_users(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ</b>", parse_mode="HTML")
        return
    banned_ids = database.get_banned_users()
    if banned_ids:
        banned_str = "\n".join([f"• <code>{uid}</code> •" for uid in banned_ids])
        bot.reply_to(message, f"🚫 <b>ʙᴀɴɴᴇᴅ ᴜsᴇʀs ʟɪsᴛ:</b>\n\n{banned_str}", parse_mode="HTML")
    else:
        bot.reply_to(message, "‼️ ɴᴏ ʙᴀɴɴᴇᴅ ᴜsᴇʀs ꜰᴏᴜɴᴅ.", parse_mode="HTML")

@bot.message_handler(commands=['addforcesub'])
def add_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ </b>", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        current_channels = database.get_fsub_channels()
        if channel not in current_channels:
            database.add_fsub_channel(channel)
            bot.reply_to(message, f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴀᴅᴅᴇᴅ <code>{channel}</code> ᴛᴏ ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʟɪsᴛ.</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"‼️ ᴄʜᴀɴɴᴇʟ <code>{channel}</code> ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜᴇ ʟɪsᴛ.", parse_mode="HTML")
    else:
        bot.reply_to(message, "<code>/addforcesub @channelusername</code>", parse_mode="HTML")

@bot.message_handler(commands=['removeforce'])
def remove_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ</b>", parse_mode="HTML")
        return
    args = message.text.split()
    if len(args) > 1:
        channel = args[1].strip()
        current_channels = database.get_fsub_channels()
        if channel in current_channels:
            database.remove_fsub_channel(channel)
            bot.reply_to(message, f"<b>✅️ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ <code>{channel}</code> ꜰʀᴏᴍ ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʟɪsᴛ</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, f"‼️ ᴄʜᴀɴɴᴇʟ<code>{channel}</code> ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ʟɪsᴛ.", parse_mode="HTML")
    else:
        bot.reply_to(message, " <code>/removeforce @channelusername</code>", parse_mode="HTML")

@bot.message_handler(commands=['fsublist'])
def list_force_sub(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, " <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ: ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ sᴇɴᴘᴀɪ </b>", parse_mode="HTML")
        return
    channels = database.get_fsub_channels()
    if channels:
        channels_str = "\n".join([f"• <code>{ch}</code> •" for ch in channels])
        bot.reply_to(message, f" <b>ꜰᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴄʜᴀɴɴᴇʟs ʟɪsᴛ:</b>\n\n{channels_str}", parse_mode="HTML")
    else:
        bot.reply_to(message, "‼️<b>ɴᴏ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ sᴇᴛ.</b>", parse_mode="HTML")

# --- Helper: Fetch Official Title Logo PNG from TMDb ---
def get_tmdb_logo_url(item_id, media_type):
    endpoint = "movie" if media_type == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{endpoint}/{item_id}/images?api_key={TMDB_API_KEY}"
    try:
        res = session.get(url, timeout=4).json()
        logos = res.get("logos", [])
        if logos:
            en_logos = [l for l in logos if l.get("iso_639_1") == "en"]
            selected_logo = en_logos[0] if en_logos else logos[0]
            return f"https://image.tmdb.org/t/p/original{selected_logo['file_path']}"
    except Exception:
        pass
    return None

# --- Poster Generation Logic (Proper Aspect-Ratio Handling) ---
def add_title_overlay(image_bytes, title_text, logo_url=None):
    orig_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    target_width, target_height = 1280, 720
    
    # If image is tall/vertical portrait (aspect ratio < 1.33)
    if orig_img.width / orig_img.height < 1.33:
        bg = orig_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(15))
        
        portrait = orig_img.copy()
        portrait.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        
        x_offset = (target_width - portrait.width) // 2
        y_offset = (target_height - portrait.height) // 2
        bg.paste(portrait, (x_offset, y_offset), portrait if portrait.mode == 'RGBA' else None)
        image = bg
    else:
        image = orig_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    logo_applied = False
    if logo_url:
        try:
            logo_res = session.get(logo_url, timeout=5)
            if logo_res.status_code == 200:
                logo_img = Image.open(io.BytesIO(logo_res.content)).convert("RGBA")
                max_logo_w = int(target_width * 0.6)
                max_logo_h = int(target_height * 0.3)
                logo_img.thumbnail((max_logo_w, max_logo_h), Image.Resampling.LANCZOS)
                logo_w, logo_h = logo_img.size
                x = int((target_width - logo_w) / 2)
                y = int(target_height - logo_h - (target_height * 0.08))
                image.paste(logo_img, (x, y), logo_img)
                logo_applied = True
        except Exception:
            pass

    if not logo_applied:
        rgb_image = image.convert("RGB")
        draw = ImageDraw.Draw(rgb_image)
        width, height = rgb_image.size
        
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
            font = ImageFont.truetype(font_path, int(height * 0.10))
        except:
            font = ImageFont.load_default()

        words = title_text.split()
        if len(words) > 3:
            mid = len(words) // 2
            title_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            title_lines = [title_text]

        line_heights, line_widths = [], []
        for line in title_lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except:
                w, h = draw.textsize(line, font=font)
            line_widths.append(w)
            line_heights.append(h)

        total_text_height = sum(line_heights) + (len(title_lines) - 1) * 10
        y = height - total_text_height - int(height * 0.10)

        for i, line in enumerate(title_lines):
            x = (width - line_widths[i]) / 2
            for adj_x in range(-3, 4):
                for adj_y in range(-3, 4):
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
    first_name = message.from_user.first_name or "user"
    database.add_user(user_id, first_name)

    if database.is_banned(user_id):
        return

    if not is_user_member(user_id):
        send_fsub_prompt(message.chat.id)
        return

    # Check Global PM Search restriction if query is sent in Private Chat (Allows Owner regardless)
    if message.chat.type == "private" and user_id != OWNER_ID:
        pm_enabled = database.get_global_pm_search()
        if not pm_enabled:
            access_denied_text = (
                "🔒 <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b>\n\n"
                "<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀ ᴀᴜᴛʜᴏʀɪsᴇᴅ ᴜsᴇʀ.\n\n"
                "ᴘʟᴇᴀsᴇ ᴜsᴇ ᴛʜɪs ʙᴏᴛ ɪɴ ᴏᴜʀ ᴘᴏsᴛᴇʀ ɢʀᴏᴜᴘ.</b>"
            )
            markup = telebot.types.InlineKeyboardMarkup()
            group_btn = telebot.types.InlineKeyboardButton(text="• ᴊᴏɪɴ ᴘᴏsᴛᴇʀ ɢʀᴏᴜᴘ •", url=POSTER_GROUP_URL)
            markup.add(group_btn)
            bot.reply_to(message, access_denied_text, parse_mode="HTML", reply_markup=markup)
            return

    raw_query = message.text.strip()
    if raw_query.startswith("/p "):
        raw_query = raw_query[3:].strip()
    elif raw_query.startswith("/poster "):
        raw_query = raw_query[8:].strip()

    # --- Season Detection (e.g., Reacher S01 or Season 2) ---
    season_number = None
    clean_query = raw_query
    season_match = re.search(r'(?i)\b(?:s|season)\s*0*(\d+)\b', raw_query)
    if season_match:
        season_number = int(season_match.group(1))
        clean_query = re.sub(r'(?i)\b(?:s|season)\s*0*\d+\b', '', raw_query).strip()

    status_msg = bot.reply_to(message, f"<b><i>searching <code>{html.escape(raw_query)}</code>...</i></b>", parse_mode="HTML")
    
    if not TMDB_API_KEY:
        bot.edit_message_text("⚠️ <b>𝖾𝗋𝗋𝗈𝗋:</b> <code>tmdb_api_key</code> 𝗂𝗌 𝗆𝗂𝗌𝗌𝗂𝗇𝗀!.", message.chat.id, status_msg.message_id, parse_mode="HTML")
        return

    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={requests.utils.quote(clean_query)}"
    
    try:
        res = session.get(url, timeout=5)
        if res.status_code != 200:
            bot.edit_message_text(f"⚠️ <b>𝗍𝗆𝖽𝖻 𝖺𝗉𝗂 𝖾𝗋𝗋𝗈𝗋 ({res.status_code})</b>", message.chat.id, status_msg.message_id, parse_mode="HTML")
            return

        response = res.json()
        results = response.get("results", [])

        if not results:
            tv_url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={requests.utils.quote(clean_query)}"
            tv_res = session.get(tv_url, timeout=5)
            if tv_res.status_code == 200:
                results = tv_res.json().get("results", [])
                for r in results:
                    r["media_type"] = "tv"

        if results:
            valid_items = [i for i in results if i.get("backdrop_path") or i.get("poster_path")]
            if not valid_items:
                bot.edit_message_text("‼️ ɪᴍᴀɢᴇ ʙᴀɴɴᴇʀ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ꜰᴏʀ ᴛʜɪs ᴛɪᴛʟᴇ.", message.chat.id, status_msg.message_id)
                return

            item = valid_items[0]
            title = item.get("title") or item.get("name") or "unknown title"
            item_id = str(item.get("id"))
            media_type = item.get("media_type", "movie")
            
            release_date = item.get("release_date") or item.get("first_air_date") or ""
            year = release_date.split("-")[0] if release_date else "n/a"
            
            backdrop_path = item.get("backdrop_path")
            poster_path = item.get("poster_path")

            # --- Handle Seasons --- #
            if season_number and media_type == "tv":
                season_url = f"https://api.themoviedb.org/3/tv/{item_id}/season/{season_number}?api_key={TMDB_API_KEY}"
                season_res = session.get(season_url, timeout=5)
                if season_res.status_code == 200:
                    season_data = season_res.json()
                    if season_data.get("poster_path"):
                        poster_path = season_data.get("poster_path")
                    title = f"{title} season {season_number}"
                
                # Fetch season-specific backdrop images from TMDb season images endpoint
                season_img_url = f"https://api.themoviedb.org/3/tv/{item_id}/season/{season_number}/images?api_key={TMDB_API_KEY}"
                season_img_res = session.get(season_img_url, timeout=4)
                if season_img_res.status_code == 200:
                    s_data = season_img_res.json()
                    s_backdrops = s_data.get("backdrops", [])
                    if s_backdrops and s_backdrops[0].get("file_path"):
                        backdrop_path = s_backdrops[0].get("file_path")

            backdrop_url_original = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else f"https://image.tmdb.org/t/p/original{poster_path}"
            portrait_url_original = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else backdrop_url_original
            
            logo_url = get_tmdb_logo_url(item_id, media_type)
            
            img_response = session.get(backdrop_url_original, timeout=8)
            if img_response.status_code == 200:
                processed_image_io = add_title_overlay(img_response.content, title, logo_url)
                
                # Unique cache key per season so different seasons never overwrite each other
                cache_key = f"{item_id}_s{season_number}" if season_number else item_id
                file_path = os.path.join(CACHE_DIR, f"{cache_key}.jpg")
                with open(file_path, "wb") as f:
                    f.write(processed_image_io.getvalue())
                
                app_url = os.environ.get("RENDER_EXTERNAL_URL") or request.host_url.rstrip('/')
                titled_poster_url = f"{app_url}/poster/{cache_key}"
                
                safe_title = html.escape(title)
                
                caption_lines = [
                    "<b>ᴍᴏʜᴀᴍᴍᴇᴅ ᴘᴏsᴛᴇʀ ʙᴏᴛ</b>\n",
                    f"<b>ᴘᴏʀᴛʀᴀɪᴛ :</b> <a href=\"{portrait_url_original}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n",
                    f"<b>ᴄᴏᴠᴇʀ :</b> <a href=\"{titled_poster_url}\"><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n",
                    f"<b>ᴛɪᴛʟᴇ : {safe_title} ({year})</b>"
                ]
                
                caption = "\n".join(caption_lines)
                
                markup = telebot.types.InlineKeyboardMarkup()
                aero_button = telebot.types.InlineKeyboardButton(text="• ᴀᴇʀᴏ ᴜɴɪᴛʏ •", url="https://t.me/Aero_Unity")
                open_image_button = telebot.types.InlineKeyboardButton(text="• ᴏᴘᴇɴ ɪᴍᴀɢᴇ •", url=titled_poster_url)
                markup.row(aero_button, open_image_button)
                
                try:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                except Exception:
                    pass
                
                bot.send_photo(
                    chat_id=message.chat.id,
                    photo=backdrop_url_original,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                bot.edit_message_text("‼️ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ʙᴀᴄᴋɢʀᴏᴜɴᴅ ɪᴍᴀɢᴇ.", message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text("ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴘᴇʟʟɪɴɢ.", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        try:
            bot.edit_message_text(f"⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ: {html.escape(str(e))}", message.chat.id, status_msg.message_id, parse_mode="HTML")
        except Exception:
            pass
            
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    try:
        bot.remove_webhook()
    except Exception:
        pass
        
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=port)
