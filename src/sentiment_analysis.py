import polars as pl
import torch
import boto3
import threading
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F


# LOAD SENTIMENT MODEL
def load_sentiment_model(model_name="cardiffnlp/twitter-roberta-base-sentiment"):
    """
    Load RoBERTa sentiment model (3 classes: Negative, Neutral, Positive)
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device)

    return tokenizer, model, device


# RUN SENTIMENT ON A SINGLE TEXT
def get_sentiment(tokenizer, model, device, text: str):
    """
    Returns: sentiment_label, sentiment_score
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return "neutral", 0.0

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]

    labels = ["negative", "neutral", "positive"]
    idx = probs.argmax().item()

    return labels[idx], float(probs[idx])


# SAVE CHECKPOINT TO S3
def save_sentiment_checkpoint(df_slice, num, bucket, prefix):
    filename = f"sentiment_checkpoint_{num}.csv"
    local_path = f"/tmp/{filename}"
    df_slice.write_csv(local_path)

    key = prefix.replace(f"s3://{bucket}/", "") + filename

    def upload_async():
        boto3.client("s3").upload_file(local_path, bucket, key)

    thread = threading.Thread(target=upload_async)
    thread.start()

    print(f"[Checkpoint] Uploaded → s3://{bucket}/{key}")


# MERGE SENTIMENT CHECKPOINTS
def merge_sentiment_checkpoints(bucket, prefix, output_path):
    s3 = boto3.client("s3")
    prefix_key = prefix.replace(f"s3://{bucket}/", "")

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix_key)

    files = [obj["Key"] for obj in response.get("Contents", [])
             if obj["Key"].endswith(".csv")]

    dfs = []
    for f in files:
        obj = s3.get_object(Bucket=bucket, Key=f)
        dfs.append(pl.read_csv(obj["Body"]))

    merged = pl.concat(dfs)

    local_final = "/tmp/sentiment_scores_only.csv"
    merged.write_csv(local_final)

    s3.upload_file(local_final, bucket, output_path.replace(f"s3://{bucket}/", ""))

    print("[Final Merge] Created sentiment_scores_only.csv")
    return merged


# MERGE SENTIMENT BACK TO FULL SUMMARY DATASET
def merge_sentiment_with_summary(df_full, df_sent):
    df_final = df_full.join(df_sent, on="product_id", how="left")
    return df_final
