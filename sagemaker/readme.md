# 🚀 AWS SageMaker Processing Jobs

GPU-accelerated abstractive summarization using Pegasus on AWS SageMaker.

---

## 📋 Overview

This folder contains scripts for running large-scale text summarization on AWS SageMaker Processing Jobs.

**Task:** Summarize 31,100 products (6.7M reviews) using Pegasus transformer  
**Hardware:** `ml.g5.12xlarge` (4x NVIDIA A10G GPUs, 48GB VRAM each)  
**Runtime:** ~12-15 hours  
**Cost:** ~$80-100 per run  

---

## 🎯 What It Does

1. **Loads grouped reviews** from S3 (`product_grouped.csv`)
2. **Downloads Pegasus model** from S3
3. **Chunks long reviews** into digestible pieces (300 tokens)
4. **Summarizes in batches** using multi-GPU parallelism
5. **Saves checkpoints** every 100 products to S3
6. **Stops at 30,700 products** (configurable)

---

## 🏗️ Architecture

```
S3 Inputs
    ↓
┌─────────────────────────────────┐
│  SageMaker Processing Instance  │
│  ml.g5.12xlarge (4x A10G GPUs)  │
│                                 │
│  ┌─────────────────────────┐    │
│  │ Pegasus Model           │    │
│  │ (google/pegasus-cnn)    │    │
│  └─────────────────────────┘    │
│           ↓                     │
│  Multi-GPU Batch Processing     │
│  (Accelerate framework)         │
│           ↓                     │
│  Checkpoint every 100 products  │
└─────────────────────────────────┘
    ↓
S3 Outputs (checkpoints)
```

---

## 📁 Files

### **`run_processing.py`**
Main processing script that:
- Loads dataset and model
- Chunks reviews intelligently
- Runs multi-GPU summarization
- Saves checkpoints asynchronously

### **`requirements.txt`**
Python dependencies for SageMaker container

---

## 🚀 Running a Processing Job

### **From Jupyter Notebook** (Recommended)

See `notebooks/run_processing_job.ipynb`:

```python
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput
from sagemaker import get_execution_role

role = get_execution_role()

processor = ScriptProcessor(
    image_uri="763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310",
    command=["python3"],
    instance_type="ml.g5.12xlarge",
    instance_count=1,
    role=role
)

processor.run(
    code="sagemaker/run_processing.py",
    inputs=[
        ProcessingInput(
            source="s3://amazon-electronics-dataset/grouping_dataset/product_grouped.csv",
            destination="/opt/ml/processing/input"
        ),
        ProcessingInput(
            source="sagemaker/requirements.txt",
            destination="/opt/ml/processing/input/requirements"
        ),
        ProcessingInput(
            source="s3://amazon-electronics-dataset/pegasus_model/",
            destination="/opt/ml/processing/pegasus_model"
        )
    ],
    outputs=[
        ProcessingOutput(
            source="/opt/ml/processing/output",
            destination="s3://amazon-electronics-dataset/summarized_dataset/"
        )
    ],
    arguments=["--top_k", "30700"]
)
```

---

## ⚙️ Configuration

### **Key Parameters**

```python
# In run_processing.py

BATCH_SIZE = 40              # Products per batch
CHUNK_BATCH_SIZE = 12        # Chunks processed together
CHECKPOINT_RATE = 100        # Save every N products
END_PRODUCT = 30700          # Stop at this product
MAX_TOKENS = 300             # Tokens per chunk
```

### **Pegasus Generation Config**

```python
num_beams = 3
max_length = 128
min_length = 32
length_penalty = 0.8
early_stopping = True
```

---

## 📊 Performance

### **Processing Speed**
- **~150-200 products/hour** (4 GPUs)
- **~12-15 hours** for 31,100 products
- **Checkpoint every 5-8 minutes**

### **Resource Utilization**
- **GPU Memory**: ~35-40GB per GPU
- **CPU**: 48 vCPUs
- **RAM**: 192GB
- **Storage**: 30GB

---

## 💾 Checkpoints

### **Why Checkpoints?**
- Resume from failure
- Monitor progress
- Incremental backups

### **Checkpoint Structure**

Each checkpoint contains:
```csv
product_id,abstracted_summary,review_count
B00ABC123,"Summary text here...",42
```

Saved to: `s3://BUCKET/checkpoint_files/checkpoint_file_N.csv`

### **Merge Checkpoints**

After processing completes:

```python
# See notebooks/03_merge_checkpoints.ipynb
import polars as pl
import boto3

# List all checkpoints
s3 = boto3.client("s3")
files = s3.list_objects_v2(Bucket=BUCKET, Prefix="checkpoint_files/")

# Read and concatenate
dfs = [pl.read_csv(s3.get_object(Bucket=BUCKET, Key=f["Key"])["Body"]) 
       for f in files["Contents"]]
merged = pl.concat(dfs)

# Save
merged.write_csv("merged_summaries.csv")
```

---

## 💰 Cost Estimation

### **Instance Pricing**
- `ml.g5.12xlarge`: **$7.09/hour**
- 15 hours runtime: **~$106**

### **Storage**
- S3 storage (1GB checkpoints): **$0.02/month**

### **Total Cost Per Run**
- **One-time summarization**: ~$106
- **Storage**: Negligible

---

## 🔧 Customization

### **Use Different Model**

Replace Pegasus with T5 or BART:

```python
from transformers import T5Tokenizer, T5ForConditionalGeneration

tokenizer = T5Tokenizer.from_pretrained("t5-base")
model = T5ForConditionalGeneration.from_pretrained("t5-base")
```

### **Adjust Chunk Size**

```python
def chunk_text(text: str, tokenizer, max_tokens: int = 500):  # Changed from 300
    # ... rest of code
```

### **Change Batch Size**

```python
BATCH_SIZE = 60  # Process more products per batch (requires more VRAM)
```

---

## 📝 Notes

- **First run takes longer** (~20 min) - downloading model
- **Subsequent runs** use cached model
- **Monitor CloudWatch logs** for progress
- **Checkpoints save asynchronously** - don't block processing

---

## 🔗 Related

- [Notebooks](../notebooks/)
- [Main README](../README.md)