import os
import shutil
from sklearn.model_selection import train_test_split
import xml.etree.ElementTree as ET
from PIL import Image

def convert_pascal_to_yolo(xml_dir, img_dir, output_dir, classes):
    # This is a helper function to convert annotations
    # ( ... function implementation as provided in a previous response ... )
    pass  # Placeholder, as the full function is long

def split_and_prepare_dataset(data_dir, classes_list, split_ratio=0.8):
    """Splits dataset into training and validation sets and converts annotations."""
    images_dir = os.path.join(data_dir, 'images')
    annotations_dir = os.path.join(data_dir, 'annotations')
    
    # Create new directories for the split dataset
    os.makedirs(os.path.join(data_dir, 'images', 'train'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'images', 'val'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'labels', 'train'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'labels', 'val'), exist_ok=True)
    
    image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png'))]
    xml_files = [f for f in os.listdir(annotations_dir) if f.endswith('.xml')]

    # Split the dataset
    train_images, val_images, train_xmls, val_xmls = train_test_split(
        image_files, xml_files, test_size=1-split_ratio, random_state=42
    )

    # Move files to the new directories
    for img_file, xml_file in zip(train_images, train_xmls):
        shutil.move(os.path.join(images_dir, img_file), os.path.join(data_dir, 'images', 'train'))
        shutil.move(os.path.join(annotations_dir, xml_file), os.path.join(data_dir, 'labels_temp', 'train'))

    for img_file, xml_file in zip(val_images, val_xmls):
        shutil.move(os.path.join(images_dir, img_file), os.path.join(data_dir, 'images', 'val'))
        shutil.move(os.path.join(annotations_dir, xml_file), os.path.join(data_dir, 'labels_temp', 'val'))

    # Convert annotations
    convert_pascal_to_yolo(os.path.join(data_dir, 'labels_temp', 'train'), 
                           os.path.join(data_dir, 'images', 'train'), 
                           os.path.join(data_dir, 'labels', 'train'), classes_list)
    convert_pascal_to_yolo(os.path.join(data_dir, 'labels_temp', 'val'), 
                           os.path.join(data_dir, 'images', 'val'), 
                           os.path.join(data_dir, 'labels', 'val'), classes_list)

if __name__ == '__main__':
    data_directory = r"C:\Users\9c23o\Plant Infection Level Detection Website\Real_Dataset"
    my_classes = ['Healthy_Plant', 'Infected_Plant']
    
    split_and_prepare_dataset(data_directory, my_classes)