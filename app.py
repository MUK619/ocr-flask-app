import os
import platform
from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# ------------------------
# Auto-detect Tesseract path based on OS
# ------------------------
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# ------------------------
# Flask app setup
# ------------------------
app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------
# File validation
# ------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------
# Routes
# ------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file uploaded")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                if filename.lower().endswith(".pdf"):
                    pages = convert_from_path(filepath)
                    extracted_text = ""
                    for page in pages:
                        extracted_text += pytesseract.image_to_string(page) + "\n"
                else:
                    img = Image.open(filepath)
                    extracted_text = pytesseract.image_to_string(img)

            except Exception as e:
                extracted_text = f"OCR failed: {str(e)}"

    return render_template("index.html", extracted_text=extracted_text)


if __name__ == "__main__":
    app.run(debug=True)
