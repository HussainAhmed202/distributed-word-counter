import os
import sys
from collections import Counter

import nltk
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

from client import load_text, preprocess_text, process_chunk, split_text

nltk.download("stopwords")
nltk.download("punkt_tab")

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():

    # # Configuration
    # # slave_servers = [
    # #     ("172.31.35.88", 18861),
    # #     ("172.31.35.148", 18862),
    # #     ("172.31.39.162", 18863),
    # # ]

    slave_servers = [
        (os.getenv("SLAVE1_IP"), int(os.getenv("SLAVE1_PORT"))),
        (os.getenv("SLAVE2_IP"), int(os.getenv("SLAVE2_PORT"))),
        (os.getenv("SLAVE3_IP"), int(os.getenv("SLAVE3_PORT"))),
    ]

    # print(slave_servers)

    # ports = [18861, 18862, 18863]
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

    text = preprocess_text(text)

    # Split text into chunks
    chunks = split_text(text, len(slave_servers))

    print(f"Split text into {len(chunks)} chunks")

    # # Connect and send tasks
    # results = [process_chunk(port, chunk) for port, chunk in zip(ports, chunks)]

    # # Connect and send tasks
    # results: list[dict] = []
    # for port, chunk in zip(ports, chunks):
    #     try:
    #         word_counts = process_chunk(port, chunk)
    #         if word_counts:
    #             results.append(word_counts)
    #             print(f"Successfully processed chunk on port {port}")
    #         else:
    #             print(f"No results from slave on port {port}")
    #     except Exception as e:
    #         print(f"Failed to process on port {port}: {e}")

    # Connect and send tasks
    results: list[dict] = []
    for (host, port), chunk in zip(slave_servers, chunks):
        try:
            word_counts = process_chunk(host, port, chunk)
            if word_counts:
                results.append(word_counts)
                print(f"Successfully processed chunk on port {port}")
            else:
                print(f"No results from slave on port {port}")
        except Exception as e:
            print(f"Failed to process on port {port}: {e}")

    # Combine results
    if not results:
        print("Error: No results collected from any slaves.")
        sys.exit(1)

    # aggregate result
    final_counts = Counter()
    for r in results:
        final_counts.update(r)

    print("\nTop 10 most common words:")
    print("-" * 30)
    # for word, count in results.most_common(10):
    #     print(f"{word}: {count}")

    for word, count in final_counts.most_common(10):
        print(f"{word}: {count}")

    # Send all words
    words = [[word, count] for word, count in final_counts.items()]
    return jsonify({"words": words})


if __name__ == "__main__":
    app.run(debug=True)
