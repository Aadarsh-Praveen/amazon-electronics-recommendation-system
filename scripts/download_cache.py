import os
import gdown

CACHE_DIR = "cache"

# Google Drive file IDs
FILES = {
    "bm25_index.pkl": {
        "id": "1hw-aaLdyike4WlfWjSoiPZB9eIfBNPkO",
        "min_size_mb": 50  # BM25 should be large
    },
    "product_id_mapping.pkl": {
        "id": "1TtHq0GBPTEx2k0iSxRf0YHDP_4sOAa2c",
        "min_size_mb": 0.1  # Mapping can be small (100KB+)
    }
}

def verify_file(filepath, min_size_mb=0.1):
    """Verify downloaded file is valid"""
    if not os.path.exists(filepath):
        return False
    
    # Check file size
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    
    # For very small files, check if it's HTML error page
    if file_size_mb < 0.001:  # Less than 1KB
        print(f"File too small ({file_size_mb:.4f}MB), likely download error")
        return False
    
    if file_size_mb < min_size_mb:
        # Check if it's an HTML error page
        with open(filepath, 'rb') as f:
            first_bytes = f.read(100)
            if b'<html' in first_bytes.lower() or b'<!doctype' in first_bytes.lower():
                print(f"File is HTML error page, not a pickle file")
                return False
    
    # Try to open as pickle
    try:
        import pickle
        with open(filepath, 'rb') as f:
            pickle.load(f)
        return True
    except Exception as e:
        print(f"File verification failed: {e}")
        return False

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    print("Downloading cache files from Google Drive using gdown\n")
    
    for filename, config in FILES.items():
        file_id = config["id"]
        min_size = config["min_size_mb"]
        destination = os.path.join(CACHE_DIR, filename)
        
        # Check if file exists and is valid
        if os.path.exists(destination):
            print(f"Checking existing {filename}...")
            if verify_file(destination, min_size):
                file_size = os.path.getsize(destination) / (1024 * 1024)
                print(f"✓ {filename} already exists and is valid ({file_size:.2f}MB), skipping\n")
                continue
            else:
                print(f"Existing {filename} is corrupted, re-downloading")
                os.remove(destination)
        
        # Download from Google Drive
        print(f"Downloading {filename}")
        url = f"https://drive.google.com/uc?id={file_id}"
        
        try:
            # gdown handles large files and virus scan warnings automatically
            gdown.download(url, destination, quiet=False, fuzzy=True)
            
            # Verify the downloaded file
            if verify_file(destination, min_size):
                file_size = os.path.getsize(destination) / (1024 * 1024)
                print(f"✓ {filename} downloaded and verified successfully ({file_size:.2f}MB)\n")
            else:
                print(f"✗ {filename} download failed - file is corrupted")
                if os.path.exists(destination):
                    os.remove(destination)
                print("\nTROUBLESHOOTING:")
                print(f"   1. Make sure the file is shared publicly on Google Drive")
                print(f"   2. Check the file ID: {file_id}")
                print(f"   3. Try downloading manually: https://drive.google.com/file/d/{file_id}/view")
                return False
                
        except Exception as e:
            print(f"✗ Error downloading {filename}: {e}\n")
            if os.path.exists(destination):
                os.remove(destination)
            return False
    
    print("All cache files ready!")
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)