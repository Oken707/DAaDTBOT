import os
import tempfile
import logging
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import asyncio

# === 🔑 ТВОЙ ТОКЕН ===
TOKEN = "8339659211:AAGHwPsA03pVKiNTMD6sLokeNt4csmImsi0"

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# === НАСТРОЙКИ YT-DLP ===
YTDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "retries": 3,
}

# === Проверка Instagram ссылки ===
def is_instagram_url(text: str) -> bool:
    return "instagram.com" in text or "instagr.am" in text

# === Проверка YouTube ссылки ===
def is_youtube_url(text: str) -> bool:
    return "youtube.com" in text or "youtu.be" in text

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу скачать видео из Instagram и YouTube.\n\n"
        "📎 Отправь ссылку — и выбери формат загрузки."
    )

# === Когда пользователь отправляет ссылку ===
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if not (is_instagram_url(text) or is_youtube_url(text)):
        await update.message.reply_text("❌ Это не ссылка Instagram или YouTube.")
        return

    context.user_data["url"] = text

    keyboard = [
        [
            InlineKeyboardButton("🎬 Видео (MP4)", callback_data="format_video"),
            InlineKeyboardButton("🎧 Аудио (MP3)", callback_data="format_audio"),
        ]
    ]
    await update.message.reply_text("Выбери формат загрузки 👇", reply_markup=InlineKeyboardMarkup(keyboard))

# === Обработка кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    if not url:
        await query.edit_message_text("⚠️ Ошибка: не найдена ссылка. Отправь её заново.")
        return

    format_type = query.data.split("_")[1]
    await query.edit_message_text("⏳ Загружаю, подожди немного...")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            opts = YTDL_OPTS.copy()
            if format_type == "video":
                opts.update({
                    "format": "mp4[ext=mp4]/best",
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s")
                })
            else:
                opts.update({
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })

            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                await query.edit_message_text("❌ Не удалось скачать файл.")
                return

            # === Проверка размера файла ===
            file_size = os.path.getsize(filename)

            if file_size > 2 * 1024 * 1024 * 1024:  # > 2 ГБ
                await query.message.reply_text(
                    f"⚠️ Файл слишком большой для Telegram "
                    f"({round(file_size / 1024 / 1024, 1)} МБ).\n\n"
                    f"📥 Скачай напрямую по ссылке:\n{url}"
                )
            else:
                with open(filename, "rb") as f:
                    # === вариант 5: если видео > 50 МБ, отправляем как документ ===
                    if format_type == "video":
                        if file_size > 50 * 1024 * 1024:
                            await query.message.reply_document(
                                f,
                                caption="🎬 Видео скачано успешно!\n👉 @yuklabolibyubor_bot",
                                read_timeout=600,
                                write_timeout=600,
                            )
                        else:
                            await query.message.reply_video(
                                f,
                                caption="🎬 Видео скачано успешно!\n👉 @Yuklabolibyubor_bot",
                                read_timeout=600,
                                write_timeout=600,
                            )
                    else:
                        await query.message.reply_audio(
                            f,
                            caption="🎧 Аудио скачано успешно!\n👉 @Yuklabolibyubor_bot",
                            read_timeout=600,
                            write_timeout=600,
                        )

                await query.message.reply_text("✅ Готово! Спасибо, что пользуешься ботом 😊")

        except Exception as e:
            log.exception("Ошибка при загрузке")
            await query.edit_message_text(f"⚠️ Ошибка при скачивании: {e}")

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()

# === Запуск под Windows ===
if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
