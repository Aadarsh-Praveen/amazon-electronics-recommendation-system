import polars as pl
import pickle
import os

print("Creating product_id to numeric ID mapping")

# Load your dataset
df = pl.read_csv("output_with_aspects_LATEST.csv")

# Create mapping (same order as uploaded)
product_id_to_idx = {}
for idx, row in enumerate(df.iter_rows(named=True)):
    product_id_to_idx[str(row['product_id'])] = idx

# Save
os.makedirs("cache", exist_ok=True)
with open("cache/product_id_mapping.pkl", "wb") as f:
    pickle.dump(product_id_to_idx, f)

print(f"Created mapping for {len(product_id_to_idx):,} products")
print(f"Saved to: cache/product_id_mapping.pkl")