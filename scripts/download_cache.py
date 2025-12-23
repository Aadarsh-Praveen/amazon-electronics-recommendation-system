import os
from google.cloud import storage

CACHE_DIR = "cache"

# Google Cloud Storage configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "amazon-cache-bucket")
GCS_FILES = ["bm25_index.pkl", "product_id_mapping.pkl"]

def download_from_gcs():
    """Download cache files from Google Cloud Storage"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    print(f"Downloading cache files from GCS bucket: {GCS_BUCKET_NAME}\n")
    
    try:
        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        for filename in GCS_FILES:
            destination = os.path.join(CACHE_DIR, filename)
            
            # Check if file exists locally
            if os.path.exists(destination):
                file_size = os.path.getsize(destination) / (1024 * 1024)
                print(f"{filename} already exists ({file_size:.2f}MB), skipping\n")
                continue
            
            # Download from GCS
            print(f"Downloading {filename}...")
            blob = bucket.blob(f"cache/{filename}")
            blob.download_to_filename(destination)
            
            file_size = os.path.getsize(destination) / (1024 * 1024)
            print(f"{filename} downloaded successfully ({file_size:.2f}MB)\n")
        
        print("All cache files ready!")
        return True
        
    except Exception as e:
        print(f"Error downloading from GCS: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = download_from_gcs()
    sys.exit(0 if success else 1)