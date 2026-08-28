"""
CUAD Dataset Downloader
-----------------------------------------------
Downloads the Contract Understanding Atticus Dataset (CUAD) 
directly from the official Zenodo archive and extracts 5 text samples.
"""

import os
import urllib.request
import zipfile
import shutil

def download_sample_contracts(output_dir="data/sample_contracts", num_samples=5):
    # 1. Prepare directories
    os.makedirs(output_dir, exist_ok=True)
    
    # Official Zenodo URL for CUAD v1
    url = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"
    zip_path = "CUAD_v1.zip"
    extract_path = "temp_cuad"
    
    print("Downloading CUAD dataset...")
    # 2. Download the zip file
    urllib.request.urlretrieve(url, zip_path)
    
    print("Download complete. Extracting files...")
    # 3. Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
        
    # The raw text files are located in this specific subfolder
    source_dir = os.path.join(extract_path, "CUAD_v1", "full_contract_txt")
    
    # 4. Get all .txt files
    all_files = [f for f in os.listdir(source_dir) if f.endswith('.txt')]
    
    print(f"Found {len(all_files)} total contracts. Copying {num_samples} samples...")
    
    # 5. Move the requested number of samples to our project folder
    for i in range(min(num_samples, len(all_files))):
        filename = all_files[i]
        src_path = os.path.join(source_dir, filename)
        dst_path = os.path.join(output_dir, filename)
        
        # Copy file to our data folder
        shutil.copy2(src_path, dst_path)
        print(f" -> Saved: {dst_path}")
        
    # 6. Clean up the zip and temp extraction folder so we don't waste storage
    print("Cleaning up temporary files...")
    os.remove(zip_path)
    shutil.rmtree(extract_path)
    
    print("Data download complete! Your test data is ready.")

if __name__ == "__main__":
    download_sample_contracts()