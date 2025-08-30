import os, time, platform, shutil
from datetime import timedelta
from flask import Flask, render_template, request, send_file, url_for, flash, redirect
from werkzeug.utils import secure_filename

import pytesseract
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
from PIL import Image

# Detect OS and set correct Tesseract path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

try:
    import cv2, numpy as np
    _has_cv2 = True
except Exception:
    _has_cv2 = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif", "pdf"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="templates")
app.secret_key = "replace-me"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file uploaded")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file and file.filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                if filename.lower().endswith(".pdf"):
                    images = convert_from_path(filepath)
                else:
                    images = [Image.open(filepath)]

                extracted_texts = []
                for img in images:
                    extracted_texts.append(pytesseract.image_to_string(img))

                text = "\n".join(extracted_texts)

                output_file = os.path.join(OUTPUT_FOLDER, filename + ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(text)

                return send_file(output_file, as_attachment=True)

            except Exception as e:
                flash(f"Processing failed: {str(e)}")
                return redirect(request.url)

    return render_template("index.html", extracted_text=text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
