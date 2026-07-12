import os
import zipfile
from PIL import Image

def process_images():
    zip_path = r'c:\Users\91636\Downloads\images.zip'
    output_dir = r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\extracted_pngs'
    os.makedirs(output_dir, exist_ok=True)
    
    # Mapping of webp name inside zip to standard LaTeX filenames
    name_map = {
        '01.webp': 'rf_feature_importance.png',
        '02.webp': 'pca_cluster_structure.png',
        '03.webp': 'elbow_plot.png',
        '04.webp': 'centroid_heatmap.png',
        '05.webp': 'rf_attack_results.png',
        '06.webp': 'cnn_training_curves.png',
        '07.webp': 'cluster_visualization.png'
    }
    
    # Extract and convert
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            filename = file_info.filename
            if filename in name_map:
                new_name = name_map[filename]
                new_path = os.path.join(output_dir, new_name)
                
                # Extract to memory and save as PNG
                with zip_ref.open(filename) as source_file:
                    with Image.open(source_file) as img:
                        img.save(new_path, 'PNG')
                        print(f"Converted: {filename} -> {new_name}")
                        
    # Package into a new zip file in Downloads
    out_zip_path = r'c:\Users\91636\Downloads\converted_images.zip'
    with zipfile.ZipFile(out_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        for file in os.listdir(output_dir):
            if file.endswith('.png'):
                file_path = os.path.join(output_dir, file)
                zip_out.write(file_path, file)
                
    print(f"\nAll images packaged into: {out_zip_path}")

if __name__ == '__main__':
    process_images()
