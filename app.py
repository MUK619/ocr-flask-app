# app.py — Ready-to-use Flask OCR (Images + PDFs) for local & Render
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_file, url_for, redirect
from werkzeug.utils import secure_filename

import cv2
import numpy as np
from pdf2image import convert_from_path, PDFInfoNotInstalledError, PDFPageCountError
import pytesseract
import shutil

# ----------------------------- Flask setup -----------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "gif", "pdf"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["OUTPUT_FOLDER"] = str(OUTPUT_DIR)

# ------------------------ Tesseract configuration ----------------------
# Prefer an environment variable (works on Render & Linux). Fallback to Windows default.
tess_env = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
if tess_env:
    pytesseract.pytesseract.tesseract_cmd = tess_env
else:
    win_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.exists(win_default):
        pytesseract.pytesseract.tesseract_cmd = win_default
# (Otherwise rely on PATH.)

# Poppler path (Windows only). On Render/Linux, poppler-utils is on PATH via render.yaml.
POPPLER_PATH = os.getenv("POPPLER_PATH", None)

# --------------------------- Helper functions --------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

def pil_to_cv2(pil_img):
    """Convert PIL.Image to OpenCV BGR ndarray."""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def preprocess_for_ocr(cv_img: np.ndarray) -> np.ndarray:
    """Light, robust preprocessing for OCR: grayscale -> denoise -> threshold -> de-speckle."""
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    denoised = cv2.medianBlur(th, 3)
    # Slight upscale helps OCR on small text
    denoised = cv2.resize(denoised, None, fx=1.25, fy=1.25, interpolation=cv2.INTER_CUBIC)
    return denoised

def ocr_cv_image(cv_img: np.ndarray, lang: str = "eng") -> str:
    processed = preprocess_for_ocr(cv_img)
    config = "--oem 3 --psm 6"
    return pytesseract.image_to_string(processed, lang=lang, config=config)

# ------------------------------- Routes --------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None
    download_link = None
    error = None

    if request.method == "POST":
        if "file" not in request.files:
            error = "No file part in the request."
            return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)

        f = request.files["file"]
        if f.filename.strip() == "":
            error = "No file selected."
            return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)

        if not allowed_file(f.filename):
            error = "Unsupported file type. Please upload an image or PDF."
            return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)

        safe_name = secure_filename(f.filename)
        upload_path = UPLOAD_DIR / safe_name
        f.save(str(upload_path))

        pieces = []

        try:
            if safe_name.lower().endswith(".pdf"):
                if POPPLER_PATH:
                    pages = convert_from_path(str(upload_path), dpi=300, poppler_path=POPPLER_PATH)
                else:
                    pages = convert_from_path(str(upload_path), dpi=300)

                for i, page in enumerate(pages, start=1):
                    cv_img = pil_to_cv2(page)
                    text = ocr_cv_image(cv_img)
                    pieces.append(f"--- Page {i} ---\n{text.strip()}")
            else:
                img = cv2.imread(str(upload_path))
                if img is None:
                    error = "Could not read the image file."
                    return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)
                pieces.append(ocr_cv_image(img).strip())

        except PDFInfoNotInstalledError:
            error = ("Poppler is not installed or not found.\n"
                     "• On Windows: install Poppler and set POPPLER_PATH to its 'bin' folder.\n"
                     "• On Render: ensure 'poppler-utils' is listed in render.yaml.")
        except PDFPageCountError:
            error = "Could not read pages from this PDF."
        except Exception as e:
            error = f"Error during processing: {e}"

        if error is None:
            text = "\n\n".join([p for p in pieces if p]).strip() or "(No text detected.)"
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            base = Path(safe_name).stem
            out_name = f"{base}_{ts}.txt"
            out_path = OUTPUT_DIR / out_name
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(text)
            extracted_text = text
            download_link = url_for("download_file", filename=out_name)

    return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)

@app.route("/download/<path:filename>")
def download_file(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "File not found.", 404
    return send_file(path, as_attachment=True, download_name=path.name)

@app.get("/healthz")
def healthz():
    return "ok", 200

# ------------------------------ Entrypoint ------------------------------
if __name__ == "__main__":
    # For local testing; on Render, gunicorn runs this module
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
