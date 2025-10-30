import cv2
import time
from ultralytics import YOLO

# Load your custom-trained YOLOv8 model
model = YOLO(r'C:\Users\9c23o\Plant Infection Level Detection ML model Using YOLOV8\best.pt')

# Open the webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Starting live analysis. Press 'q' to quit.")

# --- Variables for Counting and Time-based Updates ---
last_update_time = time.time()
update_interval = 5  # Update every 5 seconds
healthy_count = 0
infected_count = 0
healthy_percentage = 0  # Initialize percentage variables
infected_percentage = 0 # Initialize percentage variables

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run object detection on the frame. verbose=False hides unnecessary output.
    results = model(frame, stream=True, verbose=False)

    # Reset counts for the current frame
    current_healthy = 0
    current_infected = 0

    # Process detections
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            confidence = box.conf[0].cpu().numpy()
            class_id = int(box.cls[0].cpu().numpy())
            class_name = model.names[class_id]
            
            # --- CRITICAL FIX: Correct the class names to match your dataset ---
            if class_name == 'Healthy_leaves':
                current_healthy += 1
                color = (0, 255, 0)
            elif class_name == 'Infected_leaves':
                current_infected += 1
                color = (0, 0, 255)
            else: # Handle the 'background' class if your model has it
                color = (128, 128, 128) # Gray color for background
            
            # Draw the bounding box and label
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f'{class_name}: {confidence:.2f}'
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # --- Update Counts and Display Percentage Every 5 Seconds ---
    if time.time() - last_update_time >= update_interval:
        total_plants = current_healthy + current_infected
        if total_plants > 0:
            healthy_percentage = (current_healthy / total_plants) * 100
            infected_percentage = (current_infected / total_plants) * 100
        else:
            healthy_percentage = 0
            infected_percentage = 0
        
        healthy_count = current_healthy
        infected_count = current_infected
        
        last_update_time = time.time()

    # Display the counts and percentages on the frame
    cv2.putText(frame, f"Healthy: {healthy_count} ({healthy_percentage:.1f}%)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"Infected: {infected_count} ({infected_percentage:.1f}%)", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # Show the frame
    cv2.imshow('Live Plant Disease Detection', frame)
    
    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()