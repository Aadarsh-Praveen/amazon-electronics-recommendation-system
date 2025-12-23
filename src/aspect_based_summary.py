from openai import OpenAI
import polars as pl
from tqdm import tqdm
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_WORKERS = 10
CACHE_DIR = "aspect_cache"
CHECKPOINT_INTERVAL = 500
OUTPUT_DIR = "outputs"
REQUEST_DELAY = 0.05 

# JSON SCHEMA
ASPECT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "aspect_output",
        "schema": {
            "type": "object",
            "properties": {
                "aspects": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "aspect": {"type": "string"},
                            "sentiment": {"type": "string"},
                            "score": {"type": "number"}
                        },
                        "required": ["aspect", "sentiment", "score"]
                    }
                }
            },
            "required": ["aspects"]
        }
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ensure_directories():
    """Create necessary directories if they don't exist"""
    Path(CACHE_DIR).mkdir(exist_ok=True)
    Path(OUTPUT_DIR).mkdir(exist_ok=True)


def get_cache_path(product_id):
    """Get cache file path for a product"""
    return Path(CACHE_DIR) / f"{product_id}.json"


def load_from_cache(product_id):
    """Load aspects from cache if available"""
    cache_file = get_cache_path(product_id)
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def save_to_cache(product_id, aspects):
    """Save aspects to cache"""
    cache_file = get_cache_path(product_id)
    try:
        with open(cache_file, 'w') as f:
            json.dump(aspects, f)
    except Exception as e:
        print(f"Warning: Could not cache {product_id}: {e}")


def get_timestamp():
    """Get formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def validate_aspect(aspect):
    """Ensure sentiment and score are consistent"""
    sentiment = aspect["sentiment"].lower()
    score = aspect["score"]
    
    # Fix inconsistencies between sentiment label and score
    if sentiment == "negative":
        if score > 0.45:
            # If labeled negative but score is high, invert it
            aspect["score"] = max(0.1, min(0.45, 1.0 - score))
    elif sentiment == "positive":
        if score < 0.65:
            # If labeled positive but score is low, adjust it
            aspect["score"] = max(0.65, score)
    elif sentiment == "neutral":
        if score < 0.45 or score > 0.65:
            # Force neutral scores to be in neutral range
            aspect["score"] = 0.5
    
    # Ensure score is in valid range 0.0 to 1.0
    aspect["score"] = max(0.0, min(1.0, aspect["score"]))
    
    return aspect


# ============================================================================
# ASPECT EXTRACTION
# ============================================================================

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def extract_aspects(summary):
    """Extract aspects from summary using OpenAI API"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format=ASPECT_SCHEMA,
        messages=[
            {
                "role": "user",
                "content": f"""Extract 3-5 key product aspects (features) from this review summary.

For each aspect, provide:
1. aspect: Feature name (e.g., "battery life", "sound quality", "build quality")
2. sentiment: Must be exactly "positive", "neutral", or "negative"
3. score: Sentiment intensity from 0.0 to 1.0 where:
   - 0.0 = Extremely negative
   - 0.2 = Very negative
   - 0.4 = Somewhat negative
   - 0.5 = Neutral
   - 0.6 = Somewhat positive
   - 0.8 = Very positive
   - 1.0 = Extremely positive

CRITICAL RULE: Score MUST align with sentiment label:
- If sentiment is "negative", score must be between 0.0 and 0.45
- If sentiment is "neutral", score must be between 0.45 and 0.65
- If sentiment is "positive", score must be between 0.65 and 1.0

Review summary:
{summary}"""
            }
        ],
        max_tokens=350,
        temperature=0
    )
    
    structured = json.loads(response.choices[0].message.content)
    
    # Validate and fix any inconsistencies
    aspects = structured["aspects"]
    validated_aspects = [validate_aspect(asp) for asp in aspects]
    
    return validated_aspects


def process_single_product(row):
    """Process a single product row (to be used in parallel)"""
    product_id = row["product_id"]
    summary = row.get("abstracted_summary", "")
    
    # Check cache first
    cached_aspects = load_from_cache(product_id)
    if cached_aspects is not None:
        return {
            "product_id": product_id,
            "aspect_extracted": json.dumps(cached_aspects),
            "processing_status": "cached"
        }
    
    # Handle empty/null summaries
    if summary is None or summary == "" or str(summary).lower() == "nan":
        result = {
            "product_id": product_id,
            "aspect_extracted": "[]",
            "processing_status": "empty_summary"
        }
        save_to_cache(product_id, [])
        return result
    
    # Extract aspects
    try:
        aspects = extract_aspects(summary)
        result = {
            "product_id": product_id,
            "aspect_extracted": json.dumps(aspects),
            "processing_status": "success"
        }
        save_to_cache(product_id, aspects)
        return result
        
    except Exception as e:
        print(f"\nError processing {product_id}: {str(e)[:100]}")
        result = {
            "product_id": product_id,
            "aspect_extracted": "[]",
            "processing_status": f"error: {str(e)[:50]}"
        }
        save_to_cache(product_id, [])
        return result


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("=" * 80)
    print("ASPECT EXTRACTION WITH PARALLEL PROCESSING")
    print("=" * 80)
    
    # Create necessary directories
    ensure_directories()
    
    # Load data
    print("\nLoading input data...")
    input_file = "final_merged_metadata_summary_sentiment.csv"
    
    try:
        df_original = pl.read_csv(input_file)
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    print(f"Loaded {df_original.height:,} products")
    print(f"Columns: {', '.join(df_original.columns)}")
    
    # Check for required columns
    if "product_id" not in df_original.columns:
        print("Error: 'product_id' column not found in dataset!")
        return
    
    if "abstracted_summary" not in df_original.columns:
        print("Error: 'abstracted_summary' column not found in dataset!")
        return
    
    null_count = df_original.select(pl.col('abstracted_summary').null_count()).item()
    print(f"Null summaries: {null_count:,}")
    
    # Optional: Filter for high-quality products
    print("\nFiltering options...")
    print("   Tip: Filter to high-quality products to save time and money")
    print("   Uncomment filtering code if needed")
    
    # Uncomment these lines to filter (RECOMMENDED)
    # df_original = df_original.filter(
    #     (pl.col("review_count") >= 50) &
    #     (pl.col("abstracted_summary").str.lengths() >= 100)
    # )
    # print(f"After filtering: {df_original.height:,} products")
    
    # Test run on 2 products first
    print("\n" + "=" * 80)
    print("TESTING ON 2 PRODUCTS FIRST")
    print("=" * 80)
    
    df_test = df_original.head(2)
    
    for row in df_test.iter_rows(named=True):
        pid = row["product_id"]
        summary = row.get("abstracted_summary", "")
        
        print(f"\nPRODUCT: {pid}")
        print(f"SUMMARY: {str(summary)[:200]}...")
        
        if summary and str(summary).lower() != "nan":
            try:
                aspects = extract_aspects(summary)
                print(f"EXTRACTED {len(aspects)} ASPECTS:")
                for asp in aspects:
                    print(f"   - {asp['aspect']}: {asp['sentiment']} (score: {asp['score']})")
            except Exception as e:
                print(f"ERROR: {e}")
        else:
            print("Empty summary, skipping")
    
    # Ask user to continue
    print("\n" + "=" * 80)
    response = input("\nTest successful! Continue with full processing? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Processing cancelled.")
        return
    
    # Full processing with parallel execution
    print("\n" + "=" * 80)
    print("STARTING PARALLEL PROCESSING")
    print("=" * 80)
    print(f"Workers: {MAX_WORKERS}")
    print(f"Total products: {df_original.height:,}")
    print(f"Cache directory: {CACHE_DIR}/")
    print(f"Estimated time: {(df_original.height / MAX_WORKERS / 20):.1f} - {(df_original.height / MAX_WORKERS / 10):.1f} minutes")
    
    # Check how many are already cached
    cached_count = sum(1 for row in df_original.iter_rows(named=True) 
                       if load_from_cache(row["product_id"]) is not None)
    if cached_count > 0:
        print(f"Found {cached_count:,} cached products (will skip)")
        remaining = df_original.height - cached_count
        print(f"Remaining to process: {remaining:,}")
        print(f"Adjusted time: {(remaining / MAX_WORKERS / 20):.1f} - {(remaining / MAX_WORKERS / 10):.1f} minutes")
    
    print()
    
    start_time = time.time()
    aspect_results = []
    processed_count = 0
    cached_used_count = 0
    error_count = 0
    
    # Process all products in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all jobs
        futures = {
            executor.submit(process_single_product, row): row
            for row in df_original.iter_rows(named=True)
        }
        
        # Collect results with progress bar
        with tqdm(total=len(futures), desc="Processing", unit="product", ncols=100) as pbar:
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    aspect_results.append(result)
                    
                    # Update counters
                    if result["processing_status"] == "cached":
                        cached_used_count += 1
                    elif result["processing_status"] == "success":
                        processed_count += 1
                    else:
                        error_count += 1
                    
                    # Update progress bar description
                    pbar.set_postfix({
                        'new': processed_count,
                        'cached': cached_used_count,
                        'errors': error_count
                    })
                    pbar.update(1)
                    
                    # Save checkpoint periodically
                    if (i + 1) % CHECKPOINT_INTERVAL == 0:
                        checkpoint_df = pl.DataFrame(aspect_results)
                        checkpoint_file = f"checkpoint_{i+1}.csv"
                        checkpoint_df.write_csv(checkpoint_file)
                        tqdm.write(f"Checkpoint saved: {checkpoint_file}")
                        
                except Exception as e:
                    tqdm.write(f"Future failed: {e}")
                    error_count += 1
                    pbar.update(1)
    
    elapsed_time = time.time() - start_time
    
    # Create results DataFrame
    print("\nCreating results DataFrame...")
    df_aspects = pl.DataFrame(aspect_results)
    
    # Calculate statistics
    print("\n" + "=" * 80)
    print("PROCESSING STATISTICS")
    print("=" * 80)
    
    status_counts = df_aspects.group_by("processing_status").count().sort("count", descending=True)
    print(status_counts)
    
    print(f"\nTotal time: {elapsed_time/60:.2f} minutes ({elapsed_time:.1f} seconds)")
    print(f"Average speed: {elapsed_time/df_original.height:.2f} seconds per product")
    print(f"Estimated cost: ${(processed_count * 0.000112):.2f}")
    print(f"Successfully processed: {processed_count:,}")
    print(f"Loaded from cache: {cached_used_count:,}")
    print(f"Errors: {error_count:,}")
    
    # Merge with original DataFrame
    print("\n" + "=" * 80)
    print("MERGING WITH ORIGINAL DATASET")
    print("=" * 80)
    
    # Keep only product_id and aspect_extracted for merging
    df_aspects_clean = df_aspects.select(["product_id", "aspect_extracted"])
    
    # Join back to original DataFrame
    print("Joining aspect data with original data...")
    df_final = df_original.join(df_aspects_clean, on="product_id", how="left")
    
    print(f"Merged dataset shape: {df_final.height:,} rows x {df_final.width} columns")
    print(f"Final columns: {', '.join(df_final.columns)}")
    
    # Show sample output
    print("\n" + "=" * 80)
    print("SAMPLE OUTPUT (First 3 Products)")
    print("=" * 80)
    
    sample_cols = ["product_id"]
    if "abstracted_summary" in df_final.columns:
        sample_cols.append("abstracted_summary")
    sample_cols.append("aspect_extracted")
    
    for row in df_final.select(sample_cols).head(3).iter_rows(named=True):
        print(f"\nProduct: {row['product_id']}")
        if "abstracted_summary" in row:
            summary = str(row.get('abstracted_summary', ''))[:150]
            print(f"Summary: {summary}...")
        
        aspects_str = row.get('aspect_extracted', '[]')
        if aspects_str and aspects_str != '[]':
            try:
                aspects = json.loads(aspects_str)
                print(f"Aspects ({len(aspects)}):")
                for asp in aspects:
                    print(f"   - {asp['aspect']}: {asp['sentiment']} (score: {asp['score']})")
            except:
                print(f"Aspects: {aspects_str}")
        else:
            print("Aspects: None extracted")
    
    # Save final merged dataset
    timestamp = get_timestamp()
    output_file = f"{OUTPUT_DIR}/final_dataset_with_aspects_{timestamp}.csv"
    
    print("\n" + "=" * 80)
    print("SAVING FINAL OUTPUT")
    print("=" * 80)
    print(f"Saving to: {output_file}")
    
    df_final.write_csv(output_file)
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"File saved successfully!")
    print(f"File size: {file_size:.2f} MB")
    
    # Also save a backup in current directory
    backup_file = "output_with_aspects_LATEST.csv"
    df_final.write_csv(backup_file)
    print(f"Backup saved: {backup_file}")
    
    # Clean up checkpoint files (optional)
    print("\nCleaning up checkpoint files...")
    checkpoint_files = list(Path(".").glob("checkpoint_*.csv"))
    if checkpoint_files:
        response = input(f"Found {len(checkpoint_files)} checkpoint files. Delete them? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            for cf in checkpoint_files:
                cf.unlink()
            print(f"Deleted {len(checkpoint_files)} checkpoint files")
        else:
            print("Kept checkpoint files")
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"Main output: {output_file}")
    print(f"Backup: {backup_file}")
    print(f"Cache directory: {CACHE_DIR}/ ({len(list(Path(CACHE_DIR).glob('*.json'))):,} files)")
    print(f"\nDataset statistics:")
    print(f"   Total products: {df_final.height:,}")
    print(f"   Total columns: {df_final.width}")
    print(f"   Products with aspects: {df_final.filter(pl.col('aspect_extracted') != '[]').height:,}")
    print(f"   Products without aspects: {df_final.filter(pl.col('aspect_extracted') == '[]').height:,}")
    
    print("\nNext steps:")
    print("   1. Load the output file: pl.read_csv('output_with_aspects_LATEST.csv')")
    print("   2. Parse aspect_extracted column using json.loads()")
    print("   3. Use aspects for product recommendations!")
    
    print("\nAll done! Happy analyzing!")


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        print("Progress has been cached - you can resume by running again")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()