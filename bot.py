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
user_stats = {}
yt_cache = {}
search_history = {}

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= /start KOMANDASI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # User statistikasini yangilash
    if user_id not in user_stats:
        user_stats[user_id] = {
            'name': user.first_name,
            'downloads': 0,
            'searches': 0,
            'first_seen': update.message.date
        }
    
    welcome_text = f"""
🎵 **Salom {user.first_name}!** {"" if user.id != ADMIN_ID else "👑"}

🤖 **Kuchli Musiqa Botiga xush kelibsiz!**

🌟 **Premium Xususiyatlar:**

🔍 **Aqlli Qidiruv** - YouTube dan eng yaxshi natijalar
📱 **Instagram Video** - Videodan musiqa aniqlash + MP3
🎥 **YouTube Link** - To'g'ridan-to'g'ri MP3 yuklash
🎤 **Ovozli Xabar** - Shazam bilan musiqa aniqlash
📊 **Statistika** - Shaxsiy faollik statistikasi
⚡ **Tezkor** - Parallel yuklash va konvertatsiya
🎨 **Sifatli** - 320kbps MP3 sifati

📌 **Qo'llanma:**
• Qo'shiq nomi yozing (*Masalan: "Shape of You"*)
• Instagram video link yuboring
• YouTube link yuboring
• Ovozli xabar yuboring

👑 **Admin: @Rustamov_v1**
🆘 **Yordam: /help**
    """
    
    keyboard = [
        [InlineKeyboardButton("📚 Batafsil Qo'llanma", callback_data="help")],
        [InlineKeyboardButton("🎵 Mashhur Qo'shiqlar", callback_data="popular")],
        [InlineKeyboardButton("📊 Mening Statistikam", callback_data="mystats")],
        [InlineKeyboardButton("⚡ Tez Sozlamalar", callback_data="quick")]
    ]
    
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ================= /help KOMANDASI =================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎵 **Batafsil Qo'llanma:**

📥 **1. Qo'shiq Qidirish**
   *Istalgan qo'shiq nomini yozing*
   ⁃ `Shape of You`
   ⁃ `Xamdam Sobirov Sen Aysan`
   ⁃ `Oʻzbekiston qoʻshigʻi`

📱 **2. Instagram Video**
   *Instagram video linkini yuboring*
   ⁃ Men videoni yuklab olaman
   ⁃ Musiqani Shazam bilan aniqlayman
   ⁃ MP3 formatida yuklab beraman

🎥 **3. YouTube Link**
   *YouTube video yoki shorts linki*
   ⁃ To'g'ridan MP3 yuklash
   ⁃ 320kbps yuqori sifat
   ⁃ ID3 taglar bilan

🎤 **4. Ovozli Xabar**
   *Musiqani ovozli xabar sifatida yuboring*
   ⁃ Shazam texnologiyasi
   ⁃ 95% aniqlik darajasi
   ⁃ Avtomatik qidiruv

⚡ **Qo'shimcha Imkoniyatlar:**
   📊 Shaxsiy statistika
   🔍 Search history
   ⭐ Sevimlilar ro'yxati
   🎯 Aqlli takliflar

👑 **Admin: @Rustamov_v1**
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ================= YOUTUBE QIDIRUV + PAGINATION =================
async def search_youtube(update: Update, query: str, page=0):
    """Kuchli YouTube qidiruv"""
    user_id = update.effective_user.id
    user_stats[user_id]['searches'] += 1
    
    # Search history ga qo'shish
    if user_id not in search_history:
        search_history[user_id] = []
    search_history[user_id].append(query)
    
    search_url = f"ytsearch10:{query}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            all_entries = info.get('entries', [])
            
            if not all_entries:
                await update.message.reply_text("❌ Hech narsa topilmadi. Boshqa so'z yoki ijrochi nomini yozib ko'ring.")
                return None

            # Pagination
            per_page = 5
            start_idx = page * per_page
            end_idx = start_idx + per_page
            entries = all_entries[start_idx:end_idx]
            
            if not entries:
                await update.message.reply_text("❌ Sahifa mavjud emas.")
                return None

            # Keyboard yaratish
            keyboard = []
            for idx, entry in enumerate(entries, start=start_idx+1):
                title = entry.get('title', 'Nomaʼlum')[:45]
                duration = entry.get('duration', 0)
                views = entry.get('view_count', 0)
                
                # Formatlash
                duration_str = f" ⏱{duration//60}:{duration%60:02d}" if duration else ""
                views_str = f" 👁{views//1000}k" if views > 1000 else ""
                
                yt_cache[str(idx)] = entry['webpage_url']
                button_text = f"{idx}. {title}{duration_str}{views_str}"
                button = InlineKeyboardButton(button_text, callback_data=f"download_{idx}")
                keyboard.append([button])

            # Navigation tugmalari
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"search_prev_{page}_{query}"))
            if end_idx < len(all_entries):
                nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"search_next_{page}_{query}"))
            if nav_buttons:
                keyboard.append(nav_buttons)

            # Qo'shimcha tugmalar
            keyboard.append([
                InlineKeyboardButton("🔍 Boshqa qidiruv", callback_data="new_search"),
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = f"""
🔍 **Qidiruv natijalari:** '{query}'
📄 **Sahifa:** {page + 1}
🎯 **Topildi:** {len(all_entries)} ta natija

📋 Quyidagi treklardan birini tanlang:
            """
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            
            return entries

    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        await update.message.reply_text("❌ Qidiruvda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        return None

# ================= YOUTUBE YUKLASH =================
async def download_youtube_audio(update: Update, video_url: str):
    """Yuqori sifatli MP3 yuklash"""
    user_id = update.effective_user.id
    temp_files = []
    
    try:
        # Yuklanayotganini bildirish
        progress_msg = None
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text("""
⏳ **Yuklanmoqda...**

📥 Video yuklanmoqda...
🔄 MP3 ga konvert qilinmoqda...
⚡ Tezlashtirilmoqda...

⏰ *Qisqa kutishingizni so'raymiz...*
            """, parse_mode='Markdown')
        else:
            progress_msg = await update.message.reply_text("⏳ Yuklanmoqda...")

        # YouTube DL sozlamalari
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'http_chunk_size': 10485760,  # 10MB chunks for faster download
        }

        # Yuklab olish
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = filename.rsplit('.', 1)[0] + '.mp3'
            temp_files.extend([filename, mp3_filename])

        # Statistikani yangilash
        user_stats[user_id]['downloads'] += 1

        # Telegramga yuborish
        title = info.get('title', 'Audio')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Nomaʼlum')
        
        caption = f"""
🎵 **{title}**

👤 **Ijrochi:** {uploader}
⏱ **Davomiylik:** {duration//60}:{duration%60:02d}
📊 **Sifat:** 320kbps MP3
👤 **Yuklagan:** {update.effective_user.first_name}

✅ @MusicMasterBot tomonidan yuklandi
        """
        
        # Audio faylni yuborish
        with open(mp3_filename, 'rb') as audio_file:
            audio_message = await update.effective_chat.send_audio(
                audio=audio_file,
                caption=caption,
                title=title[:64],
                performer=uploader[:64],
                duration=duration,
                parse_mode='Markdown'
            )

        # Muvaffaqiyatli xabar
        success_text = f"""
✅ **Muvaffaqiyatli Yuklandi!**

🎵 **{title}**
👤 **{uploader}**

📊 **Sizning statistikangiz:**
• Yuklab olishlar: {user_stats[user_id]['downloads']}
• Qidiruvlar: {user_stats[user_id]['searches']}

🔍 **Yana qo'shiq qidirish uchun nomini yozing!**
        """
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(success_text, parse_mode='Markdown')
        elif progress_msg:
            await progress_msg.edit_text(success_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Download error: {e}")
        error_text = """
❌ **Yuklab olishda xatolik yuz berdi**

Sabablari:
• Video mavjud emas
• Internet aloqasi muammosi
• Video bloklangan

🔄 Iltimos, qayta urinib ko'ring yoki boshqa video tanlang.
        """
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(error_text, parse_mode='Markdown')
        elif progress_msg:
            await progress_msg.edit_text(error_text, parse_mode='Markdown')

    finally:
        # Vaqtincha fayllarni tozalash
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"File cleanup error: {e}")

# ================= INSTAGRAM VIDEO =================
async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Instagram videoni mukammal qayta ishlash"""
    user_id = update.effective_user.id
    temp_files = []
    
    try:
        # Boshlash xabari
        progress_msg = await update.message.reply_text("""
📥 **Instagram Video Yuklanmoqda...**

⏳ Video yuklanmoqda...
🎵 Audio ajratilmoqda...
🔍 Musiqa aniqlanmoqda...

*Bu bir daqiqa davomishi mumkin...*
        """, parse_mode='Markdown')

        # Video yuklash
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'temp/insta_%(id)s.%(ext)s',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            temp_files.append(video_path)

        await progress_msg.edit_text("""
✅ **Video Yuklandi!**

🎥 Video tahlil qilinmoqda...
🎵 Musiqa aniqlanmoqda...
⚡ Shazam ishlayapti...
        """, parse_mode='Markdown')

        # Audio konvert qilish
        audio_path = f"temp/insta_audio_{user_id}.mp3"
        audio = AudioSegment.from_file(video_path)
        audio.export(audio_path, format="mp3", bitrate="320k")
        temp_files.append(audio_path)

        # Musiqani aniqlash
        await progress_msg.edit_text("""
🎵 **Musiqa Aniqlanmoqda...**

🔊 Audio tahlil qilinmoqda...
🎶 Shazam bazasi tekshirilmoqda...
⭐ Natijalar qidirilmoqda...
        """, parse_mode='Markdown')
        
        shazam = Shazam()
        result = await shazam.recognize_song(audio_path)

        if result and 'track' in result:
            track = result['track']
            title = track.get('title', 'Nomaʼlum')
            artist = track.get('subtitle', 'Nomaʼlum')
            music_name = f"{title} - {artist}"
            
            # Aniqlangan musiqa haqida ma'lumot
            genius_text = f"""
🎶 **MUSIQA ANIQLANDI!**

📀 **Nomi:** {title}
👤 **Ijrochi:** {artist}
🎼 **Janr:** {track.get('genres', {}).get('primary', 'Nomaʼlum')}
📅 **Yil:** {track.get('releasedate', 'Nomaʼlum')}

🔍 **YouTube dan qidirilmoqda...**
            """
            
            await progress_msg.edit_text(genius_text, parse_mode='Markdown')
            
            # YouTube dan qidirish
            await search_youtube(update, music_name)
            
        else:
            await progress_msg.edit_text("""
❌ **Musiqa Aniqlanmadi**

Sabablari:
• Musiqa juda qisqa
• Ovoz sifati past
• Shazam bazasida yo'q

🔄 Boshqa video yuborib ko'ring.
            """, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Instagram error: {e}")
        error_text = f"""
❌ **Instagram Xatosi**

Tafsilot: {str(e)}

🔄 Iltimos, quyidagilarni tekshiring:
• Link to'g'ri ligi
• Video mavjudligi
• Internet aloqasi
        """
        try:
            await progress_msg.edit_text(error_text, parse_mode='Markdown')
        except:
            await update.message.reply_text(error_text, parse_mode='Markdown')

    finally:
        # Fayllarni tozalash
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

# ================= OVOZLI XABAR =================
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ovozli xabarni aniqlash"""
    user_id = update.effective_user.id
    temp_files = []
    
    try:
        progress_msg = await update.message.reply_text("""
🎤 **Ovozli Xabar Tahlil Qilinmoqda...**

🔊 Audio yuklanmoqda...
🎵 Format konvert qilinmoqda...
🔍 Shazam ishlayapti...

*10-30 soniya davomishi mumkin...*
        """, parse_mode='Markdown')

        # Ovozli xabarni yuklash
        voice_file = await update.message.voice.get_file()
        voice_path = f"temp/voice_{user_id}_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(voice_path)
        temp_files.append(voice_path)

        # MP3 ga konvert qilish
        mp3_path = voice_path.replace('.ogg', '.mp3')
        audio = AudioSegment.from_file(voice_path)
        audio.export(mp3_path, format="mp3", bitrate="192k")
        temp_files.append(mp3_path)

        # Shazam bilan aniqlash
        await progress_msg.edit_text("""
✅ **Audio Tayyor!**

🎶 Shazam aniqlayapti...
🔊 Audio tahlil qilinmoqda...
⭐ Natijalar solishtirilmoqda...
        """, parse_mode='Markdown')
        
        shazam = Shazam()
        result = await shazam.recognize_song(mp3_path)

        if result and 'track' in result:
            track = result['track']
            title = track.get('title', 'Nomaʼlum')
            artist = track.get('subtitle', 'Nomaʼlum')
            music_name = f"{title} - {artist}"
            
            await progress_msg.edit_text(f"""
🎶 **MUSIQA TOPILDI!**

📀 **Nomi:** {title}
👤 **Ijrochi:** {artist}
🎼 **Janr:** {track.get('genres', {}).get('primary', 'Nomaʼlum')}
📅 **Yil:** {track.get('releasedate', 'Nomaʼlum')}

🔍 **YouTube dan qidirilmoqda...**
            """, parse_mode='Markdown')
            
            await search_youtube(update, music_name)
            
        else:
            await progress_msg.edit_text("""
❌ **Musiqa Topilmadi**

Sabablari:
• Musiqa aniq emas
• Ovoz sifati past  
• Qo'shiq juda qisqa
• Shazam bazasida yo'q

🔄 Boshqa ovozli xabar yuboring.
            """, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Voice error: {e}")
        await progress_msg.edit_text(f"❌ Xatolik: {str(e)}")

    finally:
        # Fayllarni tozalash
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kuchli callback handler"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("download_"):
        video_id = data.split("_")[1]
        video_url = yt_cache.get(video_id)
        
        if video_url:
            await download_youtube_audio(update, video_url)
        else:
            await query.edit_message_text("❌ Video topilmadi. Qayta urinib ko'ring.")
    
    elif data.startswith("search_"):
        # Pagination handler
        parts = data.split("_")
        action = parts[1]  # prev yoki next
        page = int(parts[2])
        search_query = "_".join(parts[3:])
        
        if action == "prev":
            new_page = max(0, page - 1)
        else:  # next
            new_page = page + 1
            
        await search_youtube(update, search_query, new_page)
        await query.message.delete()
    
    elif data == "help":
        await help_command(update, context)
        await query.message.delete()
    
    elif data == "popular":
        popular_songs = [
            "🎵 Shape of You - Ed Sheeran",
            "💫 Blinding Lights - The Weeknd", 
            "🐵 Dance Monkey - Tones and I",
            "🔥 Believer - Imagine Dragons",
            "❤️ Sen Aysan - Xamdam Sobirov",
            "🌟 Despacito - Luis Fonsi",
            "🎸 Bohemian Rhapsody - Queen",
            "💿 Thriller - Michael Jackson"
        ]
        
        text = "🎵 **Mashhur Qo'shiqlar Ro'yxati:**\n\n" + "\n".join(popular_songs)
        text += "\n\n🔍 *Istalgan qo'shiq nomini yozing!*"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif data == "mystats":
        stats = user_stats.get(user_id, {'downloads': 0, 'searches': 0})
        stats_text = f"""
📊 **Shaxsiy Statistika**

👤 **Foydalanuvchi:** {query.from_user.first_name}
📥 **Yuklab olishlar:** {stats['downloads']} ta
🔍 **Qidiruvlar:** {stats['searches']} ta
⭐ **Faollik darajasi:** {'🟢 Yuqori' if stats['downloads'] > 5 else '🟡 Oʻrta' if stats['downloads'] > 0 else '🔴 Yangi'}

🎯 **So'ngi qidiruvlar:**
{chr(10).join([f'• {q}' for q in search_history.get(user_id, ['Hali qidiruv yoʻq'])[-3:]])}

🚀 **Davom eting!**
        """
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    elif data == "admin" and user_id == ADMIN_ID:
        total_users = len(user_stats)
        total_downloads = sum([stats['downloads'] for stats in user_stats.values()])
        total_searches = sum([stats['searches'] for stats in user_stats.values()])
        
        admin_text = f"""
👑 **Admin Panel**

📈 **Umumiy Statistika:**
• 👥 Foydalanuvchilar: {total_users}
• 📥 Yuklab olishlar: {total_downloads}
• 🔍 Qidiruvlar: {total_searches}

⚙️ **Sozlamalar:**
• Bot faol
• Yuklash limiti: Cheksiz
• Sifat: 320kbps

🔧 **Admin Amallari:**
• /broadcast - Xabar yuborish
• /stats - Batafsil statistika
        """
        await query.edit_message_text(admin_text, parse_mode='Markdown')
    
    elif data in ["new_search", "main_menu", "quick"]:
        await start(update, context)
        await query.message.delete()

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
        await update.message.reply_text(f"🔍 **'{text}'** qidirilmoqda...", parse_mode='Markdown')
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
    application.add_handler(CommandHandler("stats", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Botni ishga tushirish
    print("""
🤖 **Kuchli Musiqa Boti Ishga Tushdi!**
🎵 Version: 2.0 Premium
⚡ Features: YouTube, Instagram, Shazam
👑 Admin: @Rustamov_v1
🚀 Ready to rock!
    """)
    application.run_polling()

if __name__ == "__main__":
    main()
    
    
