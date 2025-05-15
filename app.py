import os
from collections import Counter

from flask import Flask, jsonify, render_template, request
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

from client import load_text, process_chunk, split_text  # your backend logic

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")  # this serves index.html from templates/


@app.route("/process", methods=["POST"])
def process_file():
    text = ""

    # Check if file was uploaded
    if "file" in request.files and request.files["file"].filename != "":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        if filename.endswith(".pdf"):
            try:
                reader = PdfReader(filepath)
                text = " ".join(
                    [
                        page.extract_text()
                        for page in reader.pages
                        if page.extract_text()
                    ]
                )
            except Exception as e:
                return jsonify({"error": f"PDF parsing failed: {str(e)}"}), 400
        elif filename.endswith(".txt"):
            text = load_text(filepath)
        else:
            return jsonify({"error": "Unsupported file type."}), 400

    elif "text" in request.form and request.form["text"].strip():
        text = request.form["text"]
    else:
        return jsonify({"error": "No valid input provided."}), 400

    ports = [18861, 18862, 18863]
    chunks = split_text(text, len(ports))
    results = [process_chunk(port, chunk) for port, chunk in zip(ports, chunks)]

    final_counts = Counter()
    for r in results:
        final_counts.update(r)

    # Send all words, not just top 10
    words = [[word, count] for word, count in final_counts.items()]
    return jsonify({"words": words})


if __name__ == "__main__":
    app.run(debug=True)
