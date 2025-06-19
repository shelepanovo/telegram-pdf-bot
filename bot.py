import os
import logging
import tempfile
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pdfkit
from PyPDF2 import PdfMerger

TG_TOKEN = os.getenv("TG_TOKEN")
WKHTMLTOPDF_PATH = os.getenv("WKHTMLTOPDF_PATH", "./wkhtmltopdf/wkhtmltopdf")
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Отправь HTML или PDF. Команды:\n/convert — HTML → PDF\n/merge — Объединить PDF")

html_files = []
pdf_files = []

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    file_ext = os.path.splitext(doc.file_name)[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        file_path = tmp.name
        await doc.get_file().download_to_drive(file_path)

        if file_ext == ".html":
            html_files.append(file_path)
            await update.message.reply_text(f"✅ HTML получен: {doc.file_name}")
        elif file_ext == ".pdf":
            pdf_files.append(file_path)
            await update.message.reply_text(f"✅ PDF получен: {doc.file_name}")
        else:
            await update.message.reply_text("⚠️ Только .html и .pdf поддерживаются.")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not html_files:
        await update.message.reply_text("❌ Нет HTML файлов.")
        return
    converted = []
    for html in html_files:
        pdf_path = html.replace(".html", ".pdf")
        try:
            pdfkit.from_file(html, pdf_path, configuration=config)
            converted.append(pdf_path)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    for pdf in converted:
        await update.message.reply_document(InputFile(pdf))
    html_files.clear()

async def merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not pdf_files:
        await update.message.reply_text("❌ Нет PDF файлов.")
        return
    merger = PdfMerger()
    for f in pdf_files:
        merger.append(f)
    merged_path = tempfile.mktemp(suffix=".pdf")
    merger.write(merged_path)
    merger.close()
    await update.message.reply_document(InputFile(merged_path))
    pdf_files.clear()

def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("merge", merge))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
