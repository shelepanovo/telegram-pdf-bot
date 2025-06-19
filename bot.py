import os
import logging
import pdfkit
import shutil
import zipfile
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Логирование (полезно для Render)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Получаем токен из переменных окружения
TG_TOKEN = os.environ.get("TG_TOKEN")

# Папка для wkhtmltopdf (если локально или в репозитории)
WKHTMLTOPDF_PATH = './wkhtmltopdf/wkhtmltopdf'

# Проверим, существует ли wkhtmltopdf и сделаем исполняемым
if os.path.isfile(WKHTMLTOPDF_PATH):
    os.chmod(WKHTMLTOPDF_PATH, 0o755)

# PDFKit конфигурация
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# Папка для загрузки файлов
UPLOAD_DIR = "uploads"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Отправь HTML файлы, затем команду /convert")


async def handle_html(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_dir = os.path.join(UPLOAD_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    file = update.message.document
    file_path = os.path.join(user_dir, file.file_name)

    await file.get_file().download_to_drive(file_path)
    await update.message.reply_text(f"✅ Файл получен: {file.file_name}")


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_dir = os.path.join(UPLOAD_DIR, user_id)

    if not os.path.isdir(user_dir):
        await update.message.reply_text("❌ Нет HTML файлов.")
        return

    pdf_dir = os.path.join(user_dir, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)

    errors = []

    for filename in os.listdir(user_dir):
        if filename.endswith(".html"):
            html_path = os.path.join(user_dir, filename)
            pdf_path = os.path.join(pdf_dir, filename.replace(".html", ".pdf"))
            try:
                pdfkit.from_file(html_path, pdf_path, configuration=config)
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

    # Создание ZIP
    zip_path = os.path.join(user_dir, "converted.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in os.listdir(pdf_dir):
            file_path = os.path.join(pdf_dir, filename)
            zipf.write(file_path, arcname=filename)

    # Отправка архива
    await update.message.reply_document(InputFile(zip_path))

    if errors:
        error_text = "\n".join(errors)
        await update.message.reply_text(f"⚠️ Ошибки:\n{error_text}")

    # Очистка
    shutil.rmtree(user_dir)


def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(MessageHandler(filters.Document.FileExtension("html"), handle_html))

    app.run_polling()


if __name__ == "__main__":
    main()
