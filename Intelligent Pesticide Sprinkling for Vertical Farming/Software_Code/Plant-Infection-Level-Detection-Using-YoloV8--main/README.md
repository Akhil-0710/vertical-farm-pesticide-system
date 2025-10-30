1. Download the Code 📥
Go to the GitHub repository page.
Click the green Code button and select Download ZIP.
Extract the contents of the ZIP file to a folder on your computer.

2. Install Python Libraries 🐍
Open a terminal or Command Prompt in your project folder.
Install all the necessary libraries using pip:

pip install ultralytics opencv-python torch Pillow scikit-learn


3. Prepare the Dataset 📂
Place your images and annotations in the Real_Dataset folder.
Run the splitting script to organize your data for the model:

python split_dataset.py

4. Train the Model 🧠
Ensure your data.yaml file is correctly configured.
Run the training script to create your custom model (best.pt):

python train.py

5. Run Live Prediction 📸
Open the Live_Prediction.py file.
Make sure the model path points to the new best.pt file in the runs directory.
Run the prediction script and view the results on your webcam:

python Live_Prediction.py
