from flask import Flask, render_template, request, redirect, url_for, send_file
import pytesseract
import shutil
import os
from pdf2image import convert_from_path
from PIL import Image
import uuid

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

# ✅ Auto-detect tesseract path (works on Render & Windows)
tess = shutil.which("tesseract")
if tess:
    pytesseract.pytesseract.tesseract_cmd = tess
else:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect(url_for("index"))

    file = request.files["file"]

    if file.filename == "":
        return redirect(url_for("index"))

    # Save uploaded file
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    output_text = ""

    # If PDF → convert each page to image and OCR
    if file.filename.lower().endswith(".pdf"):
        pages = convert_from_path(filepath)
        for page in pages:
            text = pytesseract.image_to_string(page)
            output_text += text + "\n"

    # If image (jpg, png, etc.)
    else:
        image = Image.open(filepath)
        output_text = pytesseract.image_to_string(image)

    # Save extracted text
    output_filename = f"{uuid.uuid4().hex}.txt"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
