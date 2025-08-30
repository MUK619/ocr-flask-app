import os
import platform
import shutil
from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# -----------------------------
# Auto-detect Tesseract path
# -----------------------------
if platform.system() == "Windows":
    # Windows local path (update if yours is different)
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    # Linux/Render auto-detect
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# -----------------------------
# Flask setup
# -----------------------------
app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# File validation
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file uploaded")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            try:
                if filename.lower().endswith(".pdf"):
                    pages = convert_from_path(file_path, 300)
                    text_list = [pytesseract.image_to_string(page) for page in pages]
                    extracted_text = "\n".join(text_list)
                else:
                    img = Image.open(file_path)
                    extracted_text = pytesseract.image_to_string(img)
            except Exception as e:
                extracted_text = f"OCR failed: {str(e)}"

    return render_template("index.html", extracted_text=extracted_text)

# -----------------------------
# Run locally
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
