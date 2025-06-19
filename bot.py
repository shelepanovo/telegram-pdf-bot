
import os
import logging
import shutil
import tempfile
import zipfile

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import pdfkit

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TG_TOKEN")

user_files = {}

def convert_html_to_pdf(html_path, pdf_path):
    try:
        pdfkit.from_file(html_path, pdf_path, configuration=pdfkit.configuration(wkhtmltopdf='./wkhtmltopdf/wkhtmltopdf'))
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при конвертации {html_path}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Отправьте HTML-файлы, затем команду /convert")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
    for doc in update.message.document:
        file = await context.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
            await file.download_to_drive(f.name)
            user_files[user_id].append(f.name)
    await update.message.reply_text("✅ Файлы получены. Теперь отправьте /convert")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("⚠️ Нет загруженных HTML-файлов.")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_paths = []
        for i, html_path in enumerate(user_files[user_id]):
            pdf_path = os.path.join(temp_dir, f"{i+1}.pdf")
            if convert_html_to_pdf(html_path, pdf_path):
                pdf_paths.append(pdf_path)

        zip_path = os.path.join(temp_dir, "converted.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pdf in pdf_paths:
                zipf.write(pdf, os.path.basename(pdf))

        await update.message.reply_document(InputFile(zip_path))
        user_files[user_id] = []

def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/html"), handle_files))
    app.run_polling()

if __name__ == "__main__":
    main()
