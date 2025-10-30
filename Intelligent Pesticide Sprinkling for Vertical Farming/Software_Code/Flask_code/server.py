from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timezone
import os
import cv2
import numpy as np
from ultralytics import YOLO
import base64

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "smart_pesticide_db"

# Ensure directories exist
ANALYSIS_FOLDER = "analysis_images"
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
    return "Smart Pesticide System Backend is running!", 200

@app.route("/api/test", methods=["GET"])
def test_api():
    """Test endpoint to check API connectivity."""
    return jsonify({
        "status": "API is working",
        "mongodb_connected": client is not None,
        "model_loaded": model is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_folder": ANALYSIS_FOLDER,
        "analysis_folder_exists": os.path.exists(ANALYSIS_FOLDER)
    }), 200

@app.route("/api/analysis/image", methods=["POST"])
def analyze_image_from_esp32():
    print("[DEBUG] Received image analysis request")
    
    if client is None:
        print("[ERROR] Backend not connected to MongoDB")
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    if model is None:
        print("[ERROR] ML model not loaded")
        return jsonify({"error": "ML model not loaded."}), 500

    try:
        if not request.data:
            print("[ERROR] No image data received")
            return jsonify({"error": "No image data received."}), 400
        
        print(f"[DEBUG] Received image data size: {len(request.data)} bytes")
        
        # Decode image from raw request data
        np_arr = np.frombuffer(request.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            print("[ERROR] Failed to decode image")
            return jsonify({"error": "Failed to decode image. Ensure it is a valid JPEG."}), 400

        print(f"[DEBUG] Image decoded successfully. Shape: {frame.shape}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        # Run object detection on the frame and get the annotated result
        print("[DEBUG] Running YOLO detection...")
        results = model(frame, verbose=False)
        annotated_frame = results[0].plot()

        # Save the annotated image to the analysis_images folder
        annotated_filename = f"annotated_plant_{timestamp_str}.jpg"
        annotated_filepath = os.path.join(ANALYSIS_FOLDER, annotated_filename)
        
        success = cv2.imwrite(annotated_filepath, annotated_frame)
        if success:
            print(f"[INFO] Annotated image saved: {annotated_filepath}")
        else:
            print(f"[ERROR] Failed to save annotated image: {annotated_filepath}")
            return jsonify({"error": "Failed to save annotated image"}), 500
        
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
        
        print(f"[DEBUG] Detection results - Healthy: {current_healthy}, Infected: {current_infected}")
        
        # Calculate infection percentage
        total_leaves = current_healthy + current_infected
        infected_percentage = (current_infected / total_leaves) * 100 if total_leaves > 0 else 0
        
        # Create a document to be saved
        analysis_document = {
            "healthy_count": current_healthy,
            "infected_count": current_infected,
            "infected_percentage": float(f"{infected_percentage:.2f}"),
            "timestamp": datetime.now(timezone.utc),
            "image_filename": annotated_filename
        }

        # Save the analysis data to the MongoDB collection
        result = analysis_collection.insert_one(analysis_document)
        print(f"[INFO] Analysis data saved with ID: {result.inserted_id}")

        # Return a simple JSON response
        return jsonify({
            #"message": "Image analyzed and data saved.",
            #"healthy_count": current_healthy,
            #"infected_count": current_infected,
            "infected_percentage": infected_percentage,
            #"timestamp": analysis_document["timestamp"].isoformat(),
            #"image_url": f"/api/images/{annotated_filename}",
            #"image_filename": annotated_filename,
            #"image_path": annotated_filepath
        }), 200

    except Exception as e:
        print(f"[ERROR] Error processing analysis data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/analysis/latest", methods=["GET"])
def get_latest_analysis():
    """Fetches the most recent analysis data and the corresponding annotated image filename."""
    print("[DEBUG] Fetching latest analysis...")
    
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    try:
        latest_analysis = analysis_collection.find_one(sort=[('timestamp', -1)])
        if latest_analysis:
            print(f"[DEBUG] Found latest analysis: {latest_analysis}")
            
            latest_analysis["_id"] = str(latest_analysis["_id"])
            latest_analysis["timestamp"] = latest_analysis["timestamp"].isoformat()
            
            image_filename = latest_analysis.get("image_filename")
            if image_filename:
                # Check if the image file actually exists
                image_path = os.path.join(ANALYSIS_FOLDER, image_filename)
                if os.path.exists(image_path):
                    latest_analysis['image_url'] = f'/api/images/{image_filename}'
                    print(f"[DEBUG] Image file exists: {image_path}")
                else:
                    latest_analysis['image_url'] = None
                    print(f"[WARNING] Image file not found: {image_path}")
            else:
                latest_analysis['image_url'] = None
                print("[WARNING] No image filename in latest analysis")
            
            return jsonify(latest_analysis), 200
        else:
            print("[DEBUG] No analysis data found in database")
            return jsonify({"message": "No analysis data found."}), 404
    except Exception as e:
        print(f"[ERROR] Error fetching latest analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/images/<path:filename>', methods=["GET"])
def serve_image(filename):
    """Endpoint to serve images from the analysis_images folder."""
    print(f"[DEBUG] Serving image request for: {filename}")
    
    try:
        # Add security check to prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            print(f"[ERROR] Invalid filename: {filename}")
            return jsonify({"error": "Invalid filename"}), 400
            
        image_path = os.path.join(ANALYSIS_FOLDER, filename)
        print(f"[DEBUG] Looking for image at: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"[ERROR] Image not found: {image_path}")
            # List available files for debugging
            try:
                files = os.listdir(ANALYSIS_FOLDER)
                print(f"[DEBUG] Available files in {ANALYSIS_FOLDER}: {files}")
            except:
                print(f"[DEBUG] Could not list files in {ANALYSIS_FOLDER}")
            return jsonify({"error": "Image not found"}), 404
        
        print(f"[DEBUG] Serving image: {image_path}")
        return send_from_directory(ANALYSIS_FOLDER, filename, as_attachment=False)
        
    except Exception as e:
        print(f"[ERROR] Error serving image {filename}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/analysis/history", methods=["GET"])
def get_analysis_history2():
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
    
def get_analysis_history():
    """Fetches the most recent analysis records from MongoDB for the frontend."""
    print("[DEBUG] Fetching analysis history...")
    
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    try:
        # Get limit parameter from query string, default to 10
        limit = request.args.get('limit', 10, type=int)
        
        history = analysis_collection.find().sort("timestamp", -1).limit(limit)
        history_list = []
        for doc in history:
            doc["_id"] = str(doc["_id"])
            doc["timestamp"] = doc["timestamp"].isoformat()
            
            image_filename = doc.get("image_filename")
            if image_filename:
                # Check if the image file actually exists
                image_path = os.path.join(ANALYSIS_FOLDER, image_filename)
                if os.path.exists(image_path):
                    doc['image_url'] = f'/api/images/{image_filename}'
                else:
                    doc['image_url'] = None
            else:
                doc['image_url'] = None

            history_list.append(doc)
        
        print(f"[DEBUG] Returning {len(history_list)} analysis records")
        return jsonify({"analyses": history_list}), 200
        
    except Exception as e:
        print(f"[ERROR] Error fetching analysis history: {e}")
        return jsonify({"error": str(e)}), 500

# Add a test endpoint to create dummy data for testing
@app.route("/api/test-data", methods=["POST"])
def create_test_data():
    """Create test analysis data with a dummy image for testing."""
    if client is None:
        return jsonify({"error": "Backend not connected to MongoDB."}), 500
    
    try:
        # Create a dummy image (simple colored rectangle)
        dummy_image = np.zeros((300, 400, 3), dtype=np.uint8)
        dummy_image[:, :] = [0, 255, 0]  # Green color
        cv2.putText(dummy_image, 'TEST IMAGE', (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)
        
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        test_filename = f"test_image_{timestamp_str}.jpg"
        test_filepath = os.path.join(ANALYSIS_FOLDER, test_filename)
        
        success = cv2.imwrite(test_filepath, dummy_image)
        if not success:
            return jsonify({"error": "Failed to create test image"}), 500
        
        # Create test analysis document
        test_document = {
            "healthy_count": 5,
            "infected_count": 2,
            "infected_percentage": 28.57,
            "timestamp": datetime.now(timezone.utc),
            "image_filename": test_filename
        }
        
        result = analysis_collection.insert_one(test_document)
        
        return jsonify({
            "message": "Test data created successfully",
            "id": str(result.inserted_id),
            "image_url": f"/api/images/{test_filename}",
            "image_path": test_filepath
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Error creating test data: {e}")
        return jsonify({"error": str(e)}), 500

# List all available images
@app.route("/api/images", methods=["GET"])
def list_images():
    """List all available images in the analysis folder."""
    try:
        files = os.listdir(ANALYSIS_FOLDER)
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        
        return jsonify({
            "folder": ANALYSIS_FOLDER,
            "total_files": len(files),
            "image_files": image_files,
            "all_files": files
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Error listing images: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"[INFO] Starting Flask server...")
    print(f"[INFO] Analysis folder: {ANALYSIS_FOLDER}")
    print(f"[INFO] Analysis folder exists: {os.path.exists(ANALYSIS_FOLDER)}")
    
    # Enable debug mode for development
    app.run(host="0.0.0.0", port=5000, debug=True)