
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
    await update.message.reply_text("📎 Отправьте HTML-файлы, затем команду /convert")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
    for doc in update.message.document:
        file = await context.bot.get_file(doc.file_id)
        temp_dir = tempfile.mkdtemp()
        html_path = os.path.join(temp_dir, doc.file_name)
        await file.download_to_drive(html_path)
        user_files[user_id].append(html_path)
    await update.message.reply_text("✅ Файлы получены. Теперь отправьте /convert")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("❌ Нет HTML файлов.")
        return

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "converted_pdfs.zip")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for html_path in user_files[user_id]:
            base = os.path.basename(html_path)
            name, _ = os.path.splitext(base)
            pdf_path = os.path.join(temp_dir, f"{name}.pdf")
            if convert_html_to_pdf(html_path, pdf_path):
                zipf.write(pdf_path, arcname=f"{name}.pdf")
    
    await update.message.reply_document(InputFile(zip_path))
    shutil.rmtree(temp_dir)
    user_files[user_id] = []

def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/html"), handle_files))
    app.run_polling()

if __name__ == "__main__":
    main()
