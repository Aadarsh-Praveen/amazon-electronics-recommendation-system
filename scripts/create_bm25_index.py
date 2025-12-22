import polars as pl
from rank_bm25 import BM25Okapi
import pickle
import os
from tqdm import tqdm

print("CREATING BM25 KEYWORD INDEX")

# Load dataset
print("\nLoading dataset")
df = pl.read_csv("output_with_aspects_LATEST.csv")
print(f"Loaded {df.height:,} products")

# Prepare corpus for BM25
print("\nTokenizing corpus for BM25")
corpus = []
product_ids = []

for row in tqdm(df.iter_rows(named=True), total=df.height, desc="Processing products"):
    # Combine text fields
    title = str(row.get('title', ''))
    summary = str(row.get('abstracted_summary', ''))
    description = str(row.get('description', ''))
    
    text = f"{title} {summary} {description}"
    
    # Tokenize (simple word splitting)
    tokens = text.lower().split()
    
    corpus.append(tokens)
    product_ids.append(str(row['product_id']))

# Build BM25 index
print("\nBuilding BM25 index")
bm25 = BM25Okapi(corpus)

# Create cache directory
os.makedirs("cache", exist_ok=True)

# Save index
print("\nSaving BM25 index")
with open("cache/bm25_index.pkl", "wb") as f:
    pickle.dump({
        'bm25': bm25,
        'corpus': corpus,
        'product_ids': product_ids
    }, f)

file_size = os.path.getsize('cache/bm25_index.pkl') / 1024 / 1024

print("BM25 INDEX CREATED!")
print(f"Indexed {len(corpus):,} products")
print(f"Saved to: cache/bm25_index.pkl")
print(f"File size: {file_size:.1f}MB")
