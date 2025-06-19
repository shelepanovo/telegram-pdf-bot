import os
import logging
import tempfile
import shutil
import zipfile
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import pdfkit
from PyPDF2 import PdfMerger

TG_TOKEN = os.getenv("TG_TOKEN")
WKHTMLTOPDF_PATH = os.getenv("WKHTMLTOPDF_PATH", "./wkhtmltopdf/wkhtmltopdf")
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

logging.basicConfig(level=logging.INFO)

BASE_TMP_DIR = tempfile.gettempdir()

def get_user_dir(user_id: int):
    path = os.path.join(BASE_TMP_DIR, f"user_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Отправь HTML или PDF файл.\n"
        "📄 /convert — конвертировать HTML → PDF\n"
        "📎 /merge — объединить все PDF → ZIP"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    user_dir = get_user_dir(update.effective_user.id)
    file_ext = os.path.splitext(doc.file_name)[-1].lower()

    file_path = os.path.join(user_dir, doc.file_name)
    file_obj = await doc.get_file()
    await file_obj.download_to_drive(custom_path=file_path)

    if file_ext == ".html":
        await update.message.reply_text(f"✅ HTML сохранён: {doc.file_name}")
    elif file_ext == ".pdf":
        await update.message.reply_text(f"✅ PDF сохранён: {doc.file_name}")
    else:
        os.remove(file_path)
        await update.message.reply_text("⚠️ Поддерживаются только .html и .pdf")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dir = get_user_dir(update.effective_user.id)
    html_files = [f for f in os.listdir(user_dir) if f.lower().endswith(".html")]

    if not html_files:
        await update.message.reply_text("❌ Нет HTML файлов для конвертации.")
        return

    zip_path = os.path.join(user_dir, "converted_html.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for html_file in html_files:
            html_path = os.path.join(user_dir, html_file)
            pdf_name = os.path.splitext(html_file)[0] + ".pdf"
            pdf_path = os.path.join(user_dir, pdf_name)
            try:
                pdfkit.from_file(html_path, pdf_path, configuration=config)
                zipf.write(pdf_path, arcname=pdf_name)
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка в {html_file}: {e}")

    await update.message.reply_document(InputFile(zip_path, filename="converted_html.zip"))
    shutil.rmtree(user_dir)

async def merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_dir = get_user_dir(update.effective_user.id)
    pdf_files = sorted(f for f in os.listdir(user_dir) if f.lower().endswith(".pdf"))

    if not pdf_files:
        await update.message.reply_text("❌ Нет PDF файлов для объединения.")
        return

    merged_path = os.path.join(user_dir, "merged.pdf")
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(os.path.join(user_dir, pdf))
    merger.write(merged_path)
    merger.close()

    zip_path = os.path.join(user_dir, "merged_pdf.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(merged_path, arcname="merged.pdf")

    await update.message.reply_document(InputFile(zip_path, filename="merged_pdf.zip"))
    shutil.rmtree(user_dir)

def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("merge", merge))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
