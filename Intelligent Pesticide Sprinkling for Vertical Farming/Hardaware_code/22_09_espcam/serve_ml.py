from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os
import time
import cv2
import base64
import numpy as np
from ultralytics import YOLO

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "smart_pesticide_db"

# Ensure directories exist
UPLOAD_FOLDER = "uploads"
ANALYSIS_FOLDER = "analysis_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ANALYSIS_FOLDER, exist_ok=True)

# Load the YOLOv8 model once when the application starts
try:
    MODEL_PATH = r'C:\Users\9c23o\Plant Infection Level Detection ML model Using YOLOV8\best.pt'
    model = YOLO(MODEL_PATH)
    print("YOLO model loaded successfully.")
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    model = None

# Initialize MongoDB
try:
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    analysis_collection = db["analysis_data"]
    print("MongoDB connected successfully.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    client = None


# --- API Endpoints ---

@app.route("/", methods=["GET"])
def home():
    """A simple endpoint to confirm the server is running."""
    if client:
        return "Smart Pesticide System Backend is running and connected to MongoDB!", 200
    else:
        return "Smart Pesticide System Backend is running but not connected to MongoDB.", 500

@app.route("/   ", methods=["POST"])
def analyze_image_from_esp32():
    
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    if model is None:
        return jsonify({"error": "ML model not loaded."}), 500

    try:
       # Save image with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"plant_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        print(f"[INFO] Image saved: {filepath}")

        # Decode image properly
        np_arr = np.frombuffer(request.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Save image
        cv2.imwrite(filepath, frame)

        # Run object detection on the frame
        results = model(frame, verbose=False)

        # Process detections to get current counts
        current_healthy = 0
        current_infected = 0
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0].cpu().numpy())
                class_name = model.names[class_id]
                if class_name == 'Healthy_leaves':
                    current_healthy += 1
                elif class_name == 'Infected_leaves':
                    current_infected += 1
        
        # Calculate infection percentage
        total_leaves = current_healthy + current_infected
        infected_percentage = (current_infected / total_leaves) * 100 if total_leaves > 0 else 0
        
        # Create a document to be saved
        analysis_document = {
            "healthy_count": current_healthy,
            "infected_count": current_infected,
            "infected_percentage": float(f"{infected_percentage:.2f}"),
            "timestamp": datetime.utcnow()
        }

        # Save the analysis data to the MongoDB collection
        analysis_collection.insert_one(analysis_document)
        print(f"Analysis data received and saved: Healthy={current_healthy}, Infected={current_infected}.")

        # Return a simple JSON response with only the infection percentage
        return jsonify({
            "infected_percentage": float(f"{infected_percentage:.2f}")
        }), 200

    except Exception as e:
        print(f"Error processing analysis data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/analysis/latest", methods=["GET"])
def get_latest_analysis():
    """Fetches the most recent analysis data from MongoDB for the frontend."""
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    try:
        latest_analysis = analysis_collection.find_one(sort=[('timestamp', -1)])
        if latest_analysis:
            latest_analysis["_id"] = str(latest_analysis["_id"])
            latest_analysis["timestamp"] = latest_analysis["timestamp"].isoformat() + "Z"
            return jsonify(latest_analysis), 200
        else:
            return jsonify({"message": "No analysis data found."}), 404
    except Exception as e:
        print(f"Error fetching latest analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/analysis/history", methods=["GET"])
def get_analysis_history():
    """Fetches the most recent 10 analysis records from MongoDB for the frontend."""
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    try:
        history = analysis_collection.find().sort("timestamp", -1).limit(10)
        history_list = []
        for doc in history:
            doc["_id"] = str(doc["_id"])
            doc["timestamp"] = doc["timestamp"].isoformat() + "Z"
            history_list.append(doc)
        
        return jsonify({"analyses": history_list}), 200
    except Exception as e:
        print(f"Error fetching analysis history: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
