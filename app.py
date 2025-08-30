import os
import platform
from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# ✅ Auto-detect Tesseract path based on OS
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Flask app setup
app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# File validation
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
            file.save(filepath)

            try:
                text = ""
                if file.filename.lower().endswith(".pdf"):
                    images = convert_from_path(filepath)
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(image)
                        text += f"\n--- Page {i+1} ---\n{page_text}\n"
                else:
                    image = Image.open(filepath)
                    text = pytesseract.image_to_string(image)

                extracted_text = text.strip() if text.strip() else "⚠️ No text detected."

            except Exception as e:
                extracted_text = f"OCR failed: {e}"

    return render_template("index.html", extracted_text=extracted_text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
