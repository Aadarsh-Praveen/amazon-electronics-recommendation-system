import os
import time
os.system("pip install -r /opt/ml/processing/input/requirements/requirements.txt --quiet")

import torch
import boto3
import argparse
import threading
import polars as pl
import shutil
from accelerate import Accelerator
from transformers import PegasusTokenizer, PegasusForConditionalGeneration



# FAST TRIM + CHUNK FUNCTIONS

def trim_text(text: str, max_chars: int = 3500) -> str:
    if text is None:
        return ""
    return text[:max_chars]


def chunk_text(text: str, tokenizer, max_tokens: int = 300):
    words = text.split()
    chunks, current = [], []

    for w in words:
        current.append(w)
        encoded = tokenizer(" ".join(current), truncation=False,
                            return_tensors="pt")["input_ids"].shape[1]

        if encoded >= max_tokens:
            chunks.append(" ".join(current[:-1]))
            current = [w]

    if current:
        chunks.append(" ".join(current))

    return chunks



# CONFIG

INPUT_FILE = "/opt/ml/processing/input/product_grouped.csv"
OUTPUT_DIR = "/opt/ml/processing/output/"
BUCKET = "amazon-electronics-dataset"

CHECKPOINT_PREFIX = "s3://amazon-electronics-dataset/checkpoint_files/"

CHECKPOINT_RATE = 100    # save every 100 products
END_PRODUCT = 30700      # stop here

BATCH_SIZE = 40
CHUNK_BATCH_SIZE = 12

os.environ["TOKENIZERS_PARALLELISM"] = "true"
torch.backends.cudnn.benchmark = True



# ASYNC CHECKPOINT UPLOADER

def save_checkpoint_async(df_slice, checkpoint_num, bucket, prefix):
    filename = f"checkpoint_file_{checkpoint_num}.csv"
    local_path = f"/tmp/{filename}"

    df_slice.write_csv(local_path)
    key = prefix.replace(f"s3://{bucket}/", "") + filename

    def upload():
        boto3.client("s3").upload_file(local_path, bucket, key)

    threading.Thread(target=upload).start()
    print(f"[Checkpoint] Queued upload → s3://{bucket}/{key}")



# MULTI-GPU SUMMARIZATION

def summarize_chunks_in_batches(chunks, tokenizer, model, device):
    if not chunks:
        return ""

    summaries = []

    for i in range(0, len(chunks), CHUNK_BATCH_SIZE):
        batch = chunks[i:i + CHUNK_BATCH_SIZE]

        encoded = tokenizer(
            batch,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                encoded["input_ids"],
                num_beams=3,
                max_length=128,
                min_length=32,
                early_stopping=True
            )

        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        summaries.extend(decoded)

    return " ".join(summaries)



# MAIN PIPELINE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top_k", type=int, default=30700)   # limit to 30700
    args = parser.parse_args()
    TOP_K = args.top_k

    accelerator = Accelerator()
    device = accelerator.device

    # LOAD DATASET
    
    print("LOADING DATASET")
    df_grouped = pl.read_csv(INPUT_FILE)
    df_top = df_grouped.sort("review_count", descending=True).head(TOP_K)

    # LOAD PEGASUS MODEL
    
    print("LOADING PEGASUS MODEL FROM LOCAL DIRECTORY")

    MODEL_DIR = "/opt/ml/processing/pegasus_model"

    CACHE_PATH = "/root/.cache/huggingface"
    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        print("Cleared HuggingFace cache")

    tokenizer = PegasusTokenizer.from_pretrained(MODEL_DIR)

    model = PegasusForConditionalGeneration.from_pretrained(
        MODEL_DIR,
        torch_dtype=torch.float16
    )

    # Force clean generation config
    model.config.num_beams = 3
    model.generation_config.num_beams = 3
    model.generation_config.length_penalty = 0.8

    print("GEN CONFIG:", model.generation_config.to_dict())

    model = accelerator.prepare(model)
    print("Pegasus loaded on device:", device)

    # MAIN LOOP — STOP AT EXACTLY 30,700
    

    batch_products = []
    results = []
    checkpoint_num = 1
    start_time = time.time()

    for idx, row in enumerate(df_top.iter_rows(named=True), start=1):

        if idx > END_PRODUCT:
            print(f"Reached END_PRODUCT={END_PRODUCT}. Stopping.")
            break

        batch_products.append(row)

        if len(batch_products) == BATCH_SIZE:

            texts = [trim_text(p["all_reviews"]) for p in batch_products]
            product_ids = [p["product_id"] for p in batch_products]
            review_counts = [p["review_count"] for p in batch_products]

            batch_summaries = []

            for text in texts:
                chunks = chunk_text(text, tokenizer)
                summary = summarize_chunks_in_batches(
                    chunks, tokenizer, model, device
                )
                batch_summaries.append(summary)

            # Append results
            for pid, rev, summ in zip(product_ids, review_counts, batch_summaries):
                results.append({
                    "product_id": pid,
                    "abstracted_summary": summ,
                    "review_count": rev
                })

            batch_products = []

            # Save checkpoint every 100 products
            if idx % CHECKPOINT_RATE == 0:
                batch_df = pl.DataFrame(results)
                save_checkpoint_async(batch_df, checkpoint_num, BUCKET, CHECKPOINT_PREFIX)
                checkpoint_num += 1
                results = []
                print(f"[Checkpoint] Saved at product {idx}")

            # Log ETA (fixed)
            if idx % 1000 == 0:
                elapsed = time.time() - start_time
                speed = idx / elapsed   # products per second
                remaining = END_PRODUCT - idx
                eta_hours = (remaining / speed) / 3600
                print(f"[Progress] {idx}/{END_PRODUCT} | ETA: {eta_hours:.2f} hrs")

    # FINAL BATCH SAVE
    
    if results:
        batch_df = pl.DataFrame(results)
        save_checkpoint_async(batch_df, checkpoint_num, BUCKET, CHECKPOINT_PREFIX)
        print(f"[Checkpoint] Final batch saved.")

    print("PROCESS COMPLETE")


if __name__ == "__main__":
    main()
