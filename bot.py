import os
import logging
import asyncio
import yt_dlp
from pydub import AudioSegment
from shazamio import Shazam
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= SOZLAMALAR =================
TELEGRAM_TOKEN = "8172860090:AAESHIwiNU2n9vgtBVxKthIoQcvRzlHZSNw"
ADMIN_ID = 7800649803

# Cache va ma'lumotlar
yt_cache = {}

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= /start KOMANDASI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🎵 **Salom {user.first_name}!**

🤖 **Musiqa Qidirish Botiga xush kelibsiz!**

📌 **Meni quyidagilar uchun ishlatishingiz mumkin:**

🔍 **Qo'shiq nomi yozish** - YouTube dan qidirish
📱 **Instagram video link** - Videodan musiqa aniqlash  
🎥 **YouTube link** - To'g'ridan-to'g'ri MP3 yuklash

⚡ **Tez va sifatli musiqa yuklab beraman!**

📞 **Aloqa: @Rustamov_v1**
    """
    
    keyboard = [
        [InlineKeyboardButton("📚 Qo'llanma", callback_data="help")],
        [InlineKeyboardButton("🎵 Mashhur qo'shiqlar", callback_data="popular")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ================= /help KOMANDASI =================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎵 **Qo'llanma:**

1. **Qo'shiq qidirish** - Istalgan qo'shiq nomini yozing
   *Masalan: "Shape of You"*

2. **Instagram video** - Instagram video linkini yuboring
   *Men videodagi musiqani aniqlab, MP3 yuklab beraman*

3. **YouTube link** - YouTube video linkini yuboring
   *To'g'ridan-to'g'ri MP3 formatida yuklab oling*

📞 **Qo'llab-quvvatlash: @Rustamov_v1**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ================= YOUTUBE QIDIRUV =================
async def search_youtube(update: Update, query: str):
    """YouTube dan musiqa qidirish"""
    search_url = f"ytsearch5:{query}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])[:5]
            
            if not entries:
                await update.message.reply_text("❌ Hech narsa topilmadi. Boshqa so'z yozib ko'ring.")
                return

            # Keyboard yaratish
            keyboard = []
            for idx, entry in enumerate(entries, 1):
                title = entry.get('title', 'Nomaʼlum')[:45]
                yt_cache[str(idx)] = entry['webpage_url']
                button = InlineKeyboardButton(
                    f"{idx}. {title}", 
                    callback_data=f"download_{idx}"
                )
                keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = f"🔍 **Qidiruv natijalari:** '{query}'\n\n📋 Quyidagi treklardan birini tanlang:"
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        await update.message.reply_text("❌ Qidiruvda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# ================= YOUTUBE YUKLASH =================
async def download_youtube_audio(update: Update, video_url: str):
    """YouTube videoni MP3 ga yuklash"""
    try:
        # Yuklanayotganini bildirish
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text("⏳ Yuklanmoqda...")
        else:
            await update.message.reply_text("⏳ Yuklanmoqda...")

        # YouTube DL sozlamalari
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'temp_audio.%(ext)s',
            'quiet': True,
        }

        # Yuklab olish
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)

        # MP3 ga konvert qilish
        audio = AudioSegment.from_file(filename)
        mp3_filename = "song.mp3"
        audio.export(mp3_filename, format="mp3")

        # Telegramga yuborish
        caption = f"🎵 **{info.get('title', 'Audio')}**\n\n✅ @SongFinderBot"
        
        with open(mp3_filename, 'rb') as audio_file:
            await update.effective_chat.send_audio(
                audio=audio_file,
                caption=caption,
                title=info.get('title', 'Audio')[:30],
                performer=info.get('uploader', 'Unknown'),
                parse_mode='Markdown'
            )

        # Muvaffaqiyatli xabar
        success_text = f"✅ **{info.get('title', 'Audio')}**\n\n🎧 Muvaffaqiyatli yuklab olindi!"
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(success_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Download error: {e}")
        error_text = "❌ Yuklab olishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

    finally:
        # Vaqtincha fayllarni tozalash
        for file_path in [filename, mp3_filename]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

# ================= INSTAGRAM VIDEO =================
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Instagram videoni qayta ishlash"""
    try:
        await update.message.reply_text("📥 Instagram videosi yuklanmoqda...")

        # Video yuklash
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'temp_insta.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

        # Audio konvert qilish
        audio_path = "temp_audio.mp3"
        audio = AudioSegment.from_file(video_path)
        audio.export(audio_path, format="mp3")

        # Musiqani aniqlash
        await update.message.reply_text("🎵 Musiqani aniqlayman...")
        shazam = Shazam()
        result = await shazam.recognize_song(audio_path)

        if result and 'track' in result:
            track = result['track']
            title = track.get('title', 'Nomaʼlum')
            artist = track.get('subtitle', 'Nomaʼlum')
            music_name = f"{title} - {artist}"
            
            await update.message.reply_text(
                f"🎶 **Aniqlangan musiqa:**\n\n"
                f"📀 **Nomi:** {title}\n"
                f"👤 **Ijrochi:** {artist}\n\n"
                f"🔍 YouTube dan qidirilmoqda..."
            )
            
            # YouTube dan qidirish
            await search_youtube(update, music_name)
            
        else:
            await update.message.reply_text("❌ Musiqani aniqlab bo'lmadi. Boshqa video yuboring.")

    except Exception as e:
        logger.error(f"Instagram error: {e}")
        await update.message.reply_text("❌ Instagram videoni qayta ishlashda xatolik.")

    finally:
        # Fayllarni tozalash
        for file_path in [video_path, audio_path]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalarni boshqarish"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("download_"):
        video_id = data.split("_")[1]
        video_url = yt_cache.get(video_id)
        
        if video_url:
            await download_youtube_audio(update, video_url)
        else:
            await query.edit_message_text("❌ Video topilmadi. Qayta urinib ko'ring.")
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "popular":
        popular_songs = [
            "Shape of You - Ed Sheeran",
            "Blinding Lights - The Weeknd", 
            "Dance Monkey - Tones and I",
            "Believer - Imagine Dragons",
            "Sen Aysan - Xamdam Sobirov"
        ]
        
        text = "🎵 **Mashhur qo'shiqlar:**\n\n" + "\n".join([f"• {song}" for song in popular_songs])
        text += "\n\n🔍 Istalgan qo'shiq nomini yozing!"
        await query.edit_message_text(text, parse_mode='Markdown')

# ================= ASOSIY HANDLER =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asosiy xabarlarni boshqarish"""
    text = update.message.text.strip()
    
    if not text:
        return
    
    # Instagram link
    if "instagram.com" in text:
        await handle_instagram(update, context, text)
    
    # YouTube link
    elif "youtube.com" in text or "youtu.be" in text:
        await download_youtube_audio(update, text)
    
    # Matnli qidiruv
    else:
        await update.message.reply_text(f"🔍 '{text}' qidirilmoqda...")
        await search_youtube(update, text)

# ================= BOTNI ISHGA TUSHIRISH =================
def main():
    """Botni ishga tushirish"""
    # Papkalarni yaratish
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    # Botni yaratish
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Handlerni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Botni ishga tushirish
    print("🎵 Musiqa Boti ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
