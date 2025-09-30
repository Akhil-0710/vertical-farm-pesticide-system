# vertical-farm-pesticide-system

# Intelligent Pesticide Sprinkling for Vertical Farming 🌱🤖

An end-to-end IoT + Computer Vision system that **detects crop infections and sprays pesticide precisely** in a vertical farming setup.  
Built for **Smart India Hackathon 2025**.

---

## 🚀 Features
- ESP32-CAM module for real-time plant imaging
- YOLO-based infection severity detection on local Flask server
- Automated **capture → inference → spray** loop
- Pulley-based carriage for vertical traversal
- Controlled pesticide pump for dose-based spraying
- Easy to retrofit onto indoor vertical farms

---

## 📦 Project Structure
```text
vertical-farm-pesticide-system/
├─ esp32-cam/         # camera firmware
├─ esp32-control/     # motor + pump firmware
├─ backend/           # Flask API & ML inference
├─ hardware/          # wiring, components, mechanical notes
├─ docs/              # diagrams & extended documentation
└─ demo/              # photos, video links, slides
