# Day 2 — OCR Flask App
# Features: Drag-and-drop upload, language select, optional OpenCV enhance, safer handling

import os, time
from datetime import timedelta
from flask import Flask, render_template, request, send_file, url_for, flash, redirect
from werkzeug.utils import secure_filename

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

try:
    import cv2, numpy as np
    _has_cv2 = True
except Exception:
    _has_cv2 = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTS = {"png","jpg","jpeg","tif","tiff","bmp","gif","pdf"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="templates")
app.secret_key = "replace-me"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.permanent_session_lifetime = timedelta(days=1)

def allowed_file(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXTS

def enhance_cv(pil_img):
    if not _has_cv2: return pil_img
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thr = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY,31,15)
    den = cv2.medianBlur(thr,3)
    den = cv2.resize(den,None,fx=1.5,fy=1.5,interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(den)

def ocr_pil(pil, lang, enhance):
    if enhance and _has_cv2:
        try: return pytesseract.image_to_string(enhance_cv(pil), lang=lang)
        except Exception: return pytesseract.image_to_string(pil, lang=lang)
    return pytesseract.image_to_string(pil, lang=lang)

@app.route("/", methods=["GET","POST"])
def index():
    extracted_text, download_link, error = None,None,None
    if request.method=="POST":
        lang = request.form.get("lang","eng")
        enhance = bool(request.form.get("enhance"))
        file = request.files.get("file")
        if not file or file.filename.strip()=="":
            error="Please choose a file."; return render_template("index.html", error=error)
        if not allowed_file(file.filename):
            error="Unsupported file type."; return render_template("index.html", error=error)
        safe = secure_filename(file.filename); up_path=os.path.join(UPLOAD_FOLDER,safe)
        file.save(up_path)
        try:
            parts=[]
            if safe.lower().endswith(".pdf"):
                pages=convert_from_path(up_path,dpi=300)
                for i,page in enumerate(pages,1):
                    parts.append(f"--- Page {i} ---\n{ocr_pil(page,lang,enhance)}\n")
            else:
                parts.append(ocr_pil(Image.open(up_path),lang,enhance))
            text="\n".join(parts).strip() or "[No text detected]"
            stamp=time.strftime("%Y%m%d_%H%M%S")
            out_name=f"{os.path.splitext(safe)[0]}_{stamp}.txt"
            out_path=os.path.join(OUTPUT_FOLDER,out_name)
            with open(out_path,"w",encoding="utf-8") as f: f.write(text)
            extracted_text=text; download_link=url_for("download_file", filename=out_name)
        except Exception as e:
            error=f"Processing failed: {e}"
    return render_template("index.html", extracted_text=extracted_text, download_link=download_link, error=error)

@app.route("/download/<path:filename>")
def download_file(filename):
    path=os.path.join(OUTPUT_FOLDER,filename)
    if not os.path.isfile(path): return redirect(url_for("index"))
    return send_file(path, as_attachment=True)

if __name__=="__main__": app.run(debug=True)
