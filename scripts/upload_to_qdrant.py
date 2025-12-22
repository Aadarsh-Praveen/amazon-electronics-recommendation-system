import polars as pl
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding
from tqdm import tqdm
import json
import os
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("UPLOADING DATA TO QDRANT CLOUD")
print("="*80)

# Initialize Qdrant client
print("\nConnecting to Qdrant Cloud")
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
print("Connected to Qdrant")

# Load embedder
print("\nLoading embedding model")
embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
print("Embedding model loaded (384 dims)")

# Load dataset
print("\nLoading dataset")
df = pl.read_csv("output_with_aspects_LATEST.csv")
print(f"Loaded {df.height:,} products")

# Create or recreate collection
collection_name = "amazon-products"

print(f"\nCreating collection '{collection_name}' ")
try:
    qdrant.delete_collection(collection_name)
    print("Deleted existing collection")
except:
    print("No existing collection to delete")

qdrant.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=384,  # bge-small-en-v1.5 dimension
        distance=Distance.COSINE
    )
)
print(f"Collection '{collection_name}' created")


# Upload in batches
batch_size = 200
total_batches = (df.height + batch_size - 1) // batch_size

print(f"\nUploading {total_batches} batches")


def safe_float(x, default=0.0):
    try:
        if x is None or x == "" or x != x:  # handles None, "", NaN
            return default
        return float(x)
    except:
        return default

def safe_int(x, default=0):
    try:
        if x is None or x == "" or x != x:
            return default
        return int(float(x))
    except:
        return default
    
for batch_num in tqdm(range(total_batches), desc="Uploading batches"):
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, df.height)
    
    batch = df[start_idx:end_idx]
    
    # Prepare texts
    texts = []
    for row in batch.iter_rows(named=True):
        title = str(row.get('title', ''))
        summary = str(row.get('abstracted_summary', ''))
        desc = str(row.get('description', ''))
        
        text = f"{title} {summary} {desc}".strip()
        
        # Ensure non-empty
        if len(text) < 10:
            text = title or "Product"
        
        texts.append(text[:2000])
    
    # Generate embeddings
    embeddings = list(embedder.embed(texts))
    
    # Create points
    points = []
    for i, row in enumerate(batch.iter_rows(named=True)):
        # create numeric ID for Qdrant (required!)
        point_id = start_idx + i 

        # Parse aspects
        try:
            aspects = json.loads(row.get("aspect_extracted", "[]"))
            if not isinstance(aspects, list):
                aspects = []
        except:
            aspects = []
        
        # Create point
        points.append(
            PointStruct(
                id=point_id,  
                vector=embeddings[i].tolist(),
                payload={
                    "product_id": str(row['product_id']),  
                    "title": str(row.get('title', ''))[:300],
                    "brand": str(row.get('brand', ''))[:100],
                    "categories": str(row.get('categories', ''))[:300],
                    "avg_rating": safe_float(row.get('avg_rating', 0)),
                    "review_count": safe_int(row.get('review_count', 0)),
                    "sentiment_score": safe_float(row.get('sentiment_score', 0)),
                    "price": safe_float(row.get('price', 0) or 0),
                    "abstracted_summary": str(row.get('abstracted_summary', ''))[:1000],
                    "description": str(row.get('description', ''))[:1000],
                    "aspects": aspects[:5],
                }
            )
        )
    
    # Upload batch
    qdrant.upsert(collection_name=collection_name, points=points)

print("\nUpload complete!")

# Verify
collection_info = qdrant.get_collection(collection_name)
print("VERIFICATION")
print(f"Total vectors uploaded: {collection_info.points_count:,}")
print(f"Vector dimension: {collection_info.config.params.vectors.size}")
print(f"Distance metric: {collection_info.config.params.vectors.distance}")
print(f"{df.height:,} products uploaded to Qdrant Cloud")
print("SUCCESS!")
