from flask import Flask, request, jsonify
import os
import time
import random

app = Flask(__name__)

SAVE_DIR = "captured_images"
os.makedirs(SAVE_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # Save image with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"plant_{timestamp}.jpg"
        filepath = os.path.join(SAVE_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(request.data)

        print(f"[INFO] Image saved: {filepath}")

        # ===== Dummy ML Model =====
        severity_score = random.randint(0, 100)  # Fake severity 0–100
        print(f"Infection severity: {severity_score}%")

        return jsonify({
            "status": "success",
            "file": filename,
            "severity": severity_score
        }), 200

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
