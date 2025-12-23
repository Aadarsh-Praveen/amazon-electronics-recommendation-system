# 🏗️ System Architecture

Complete technical architecture of the Amazon Electronics Recommendation System.

---

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Streamlit UI │  │  Monitoring  │  │  Direct API  │       │
│  │   (Cloud)    │  │  Dashboard   │  │    Calls     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────|─────────────────┼────────--─────┘
          │                 |                 │
          └───────────────────-───────────────┘
                            │
                    ┌───────▼────────┐
                    │  FastAPI Layer │
                    │  (Port 8080)   │
                    └───────┬────────┘
                            │
          ┌─────────────────┼───────────────┐
          │                 │               │
    ┌─────▼─────┐    ┌─────-▼────┐    ┌─────▼─────┐
    │  Logging  │    │   Cache   │    │  Search   │
    │  (SQLite) │    │  (Memory) │    │  Engine   │
    └───────────┘    └───────────┘    └─────┬─────┘
                                            │
                        ┌───────────────────┼──────────────────-┐
                        │                   │                   │
                  ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
                  │   BM25    │      │   Dense     │     │  Qdrant     │
                  │  (Local)  │      │ Embeddings  │     │  (Cloud)    │
                  │  Keyword  │      │   (BGE)     │     │  Vector DB  │
                  └─────┬─────┘      └──────┬──────┘     └──────┬──────┘
                        │                   │                   │
                        └───────────────────┴───────────────────┘
                                            │
                                    ┌───────▼────────┐
                                    │ Hybrid Fusion  │
                                    │   (α=0.65)     │
                                    └───────┬────────┘
                                            │
                                    ┌───────▼────────┐
                                    │ BGE Reranker   │
                                    │ (CrossEncoder) │
                                    └───────┬────────┘
                                            │
                                     Ranked Results
```

---

## 🔍 Search Pipeline (Detailed)

### **Phase 1: Query Processing**

```python
User Query: "noise cancelling headphones"
    ↓
Text Preprocessing (lowercase, tokenize)
    ↓
Embedding Generation (BGE-small-en-v1.5, 384 dims)
    ↓
Cache Check (embedding cache)
```

---

### **Phase 2: Dual Retrieval**

**Path A: Dense Search**
```
Query Vector (384d)
    ↓
Qdrant Vector Search (cosine similarity)
    ↓
Top 50 candidates
    ↓
Normalized scores (0-1)
```

**Path B: BM25 Search**
```
Query Tokens ["noise", "cancelling", "headphones"]
    ↓
BM25 Scoring (local index)
    ↓
Top 50 candidates
    ↓
Normalized scores (0-1)
```

---

### **Phase 3: Hybrid Fusion**

```python
For each product_id:
    hybrid_score = α * dense_score + (1-α) * bm25_score
    
Where α = 0.65 (tuned parameter)
```

**Why Hybrid?**
- Dense search: Semantic understanding
- BM25: Exact keyword matching
- Fusion: Best of both worlds

**Performance:**
- Dense alone: NDCG@10 = 0.72
- BM25 alone: NDCG@10 = 0.68
- **Hybrid**: NDCG@10 = 0.78

---

### **Phase 4: Reranking (Optional)**

```
Top 20 hybrid candidates
    ↓
BGE Cross-Encoder (BAAI/bge-reranker-base)
    ↓
Query-document pair scoring
    ↓
Combined Score:
    final = 0.70 * rerank_score 
          + 0.20 * sentiment_score 
          + 0.10 * popularity_score
    ↓
Top K results
```

**Performance Impact:**
- Hybrid alone: NDCG@10 = 0.78
- **With reranker**: NDCG@10 = 0.854 (+9.5%)

---

## 🗄️ Data Storage Architecture

### **Vector Database (Qdrant Cloud)**

**Schema:**
```python
{
    "id": 12345,  # Numeric ID
    "vector": [0.234, -0.123, ...],  # 384 dimensions
    "payload": {
        "product_id": "B00ABC123",
        "title": "Product Title",
        "brand": "Brand Name",
        "price": 49.99,
        "avg_rating": 4.5,
        "review_count": 1247,
        "sentiment_score": 0.85,
        "abstracted_summary": "Summary text...",
        "aspects": [
            {"aspect": "sound_quality", "sentiment": "positive", "score": 0.88}
        ]
    }
}
```

**Collection:** `amazon-products`  
**Vectors:** 31,100  
**Dimension:** 384  
**Distance:** Cosine  

---

### **BM25 Index (Local Cache)**

**Structure:**
```python
{
    "bm25": BM25Okapi object,
    "corpus": [
        ["token1", "token2", ...],  # Product 1
        ["token3", "token4", ...]   # Product 2
    ],
    "product_ids": ["B00ABC123", "B00DEF456", ...]
}
```

**File:** `cache/bm25_index.pkl` (122 MB)  
**Location:** Google Cloud Storage → Downloaded to local cache  

---

### **Product ID Mapping (Local Cache)**

**Purpose:** Map string product IDs → numeric Qdrant IDs

```python
{
    "B00ABC123": 0,
    "B00DEF456": 1,
    "B00GHI789": 2,
    ...
}
```

**File:** `cache/product_id_mapping.pkl` (486 KB)  
**Location:** Google Cloud Storage  

---

## 🔄 Caching Strategy

### **Multi-Level Cache**

```
Request
    ↓
┌──────────────────────────┐
│  L1: Embedding Cache     │  ← 1000 entries
│  (query → vector)        │
└────────┬─────────────────┘
         │ Miss
    ┌────▼─────────────────┐
    │  L2: Dense Cache     │  ← 1000 entries
    │  (query → results)   │
    └────────┬─────────────┘
             │ Miss
        ┌────▼─────────────┐
        │  L3: BM25 Cache  │  ← 1000 entries
        │  (query → scores)│
        └────────┬─────────┘
                 │ Miss
            ┌────▼──────────┐
            │ L4: Hybrid    │  ← 1000 entries
            │ (final cache) │
            └───────────────┘
```

**Cache Eviction:** LRU (Least Recently Used)  
**Max Size:** 1000 entries per layer  

---

## 🧠 ML Models Architecture

### **1. BGE Embeddings (FastEmbed)**

**Model:** `BAAI/bge-small-en-v1.5`  
**Size:** 320 MB  
**Dimension:** 384  
**Input:** Text (up to 512 tokens)  
**Output:** Dense vector  

**Usage:**
```python
from fastembed import TextEmbedding

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
vector = list(embedder.embed(["your query"]))[0]
```

---

### **2. BGE Reranker (Sentence Transformers)**

**Model:** `BAAI/bge-reranker-base`  
**Size:** 420 MB  
**Architecture:** Cross-encoder (query-document pairs)  
**Input:** [query, document] pairs  
**Output:** Relevance score (0-1)  

**Usage:**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-base", max_length=512)
scores = reranker.predict([
    ["query", "document 1"],
    ["query", "document 2"]
])
```

---

### **3. Pegasus Summarization**

**Model:** `google/pegasus-cnn_dailymail`  
**Size:** 568 MB  
**Architecture:** Transformer encoder-decoder  
**Input:** Long review text (up to 512 tokens per chunk)  
**Output:** Abstractive summary  

**Strategy:**
1. Chunk long text into 300-token segments
2. Summarize each chunk (max 128 tokens)
3. Concatenate chunk summaries

---

### **4. RoBERTa Sentiment**

**Model:** `cardiffnlp/twitter-roberta-base-sentiment`  
**Size:** 499 MB  
**Classes:** Negative, Neutral, Positive  
**Input:** Summary text  
**Output:** Sentiment label + confidence score  

---

## 🔐 Security Architecture

### **API Security**

```
Request
    ↓
CORS Middleware (allow all origins - development)
    ↓
Input Validation (Pydantic)
    ↓
Rate Limiting (future)
    ↓
Handler
```

**Recommendations for Production:**
- Add API key authentication
- Implement rate limiting
- Restrict CORS origins
- Use HTTPS (SSL/TLS)

---

### **Secret Management**

**Development:**
- `.env` files (not committed)

**Production (VM):**
- Environment variables in systemd service
- Or use Google Secret Manager

**Streamlit Cloud:**
- Streamlit Secrets (TOML format)

---

## 📈 Scalability

### **Current Capacity**
- **Products:** 31,100
- **Concurrent users:** ~10-20 (VM)
- **Queries/second:** ~2-3

### **Scaling Options**

**Horizontal Scaling:**
```
Load Balancer
    ↓
┌────────┬────────┬────────┐
│ VM 1   │ VM 2   │ VM 3   │
└───┬────┴────┬───┴────┬───┘
    │         │        │
    └─────────┴────────┘
              │
      Qdrant Cloud
```

**Vertical Scaling:**
- Upgrade VM: e2-medium → e2-standard-4
- Add more memory/CPU

---

## 🔄 Data Flow

### **Indexing Pipeline**

```
Raw Reviews (6.7M)
    ↓
Preprocessing (clean, filter)
    ↓
Grouping (by product_id)
    ↓
Summarization (Pegasus + SageMaker)
    ↓
Sentiment Analysis (RoBERTa)
    ↓
Aspect Extraction (Zero-shot NLI)
    ↓
Metadata Merge
    ↓
Embedding Generation (BGE)
    ↓
Upload to Qdrant + Create BM25 Index
    ↓
Ready for Search
```

**Total Time:** ~20-24 hours (one-time)

---

### **Query Pipeline**

```
User Query
    ↓
API Request (FastAPI)
    ↓
Check Cache (4 levels)
    ↓ (miss)
Parallel Retrieval
    ├─ BM25 Search (local)
    └─ Dense Search (Qdrant)
    ↓
Hybrid Fusion
    ↓
Retrieve Full Payloads (Qdrant)
    ↓
Reranking (BGE Cross-Encoder)
    ↓
Return Top-K Results
    ↓
Cache Results
    ↓
JSON Response
```

**Total Latency:** 50ms (cached) - 3s (uncached with reranker)

---

## 🧩 Component Interactions

### **HybridSearchEngine Class**

**Responsibilities:**
- Manage Qdrant connection
- Load BM25 index
- Generate embeddings
- Coordinate retrieval
- Apply reranking
- Maintain caches

**Key Methods:**
```python
get_embedding(query)          # Generate/cache embeddings
dense_search(query, top_k)    # Qdrant vector search
bm25_search(query, top_k)     # Local BM25 search
hybrid_search(query, top_k, α) # Fuse results
rerank(query, results, top_k) # CrossEncoder reranking
search(query, top_k, use_reranker) # Main entry point
```

---

## 💾 Storage Architecture

### **Cloud Storage (GCS)**

```
gs://amazon-cache-bucket/
└── cache/
    ├── bm25_index.pkl         (122 MB)
    └── product_id_mapping.pkl (486 KB)
```

**Access Pattern:**
- Download on VM startup
- Cache locally for fast access

---

### **Vector Database (Qdrant Cloud)**

**Configuration:**
- Cluster: 1GB memory
- Collection: `amazon-products`
- Vectors: 31,100
- Dimension: 384
- Distance: Cosine

**Query Performance:**
- Average latency: 120ms
- 95th percentile: 200ms

---

### **Local Storage (VM)**

```
~/app/
├── cache/
│   ├── bm25_index.pkl    (downloaded from GCS)
│   └── product_id_mapping.pkl
└── logs/
    ├── api.log           (rotating, 10MB max)
    └── queries.db        (SQLite, query history)
```

---

## 🔄 Deployment Architectures

### **Option 1: VM + Streamlit Cloud** (Current)

```
┌──────────────────┐
│ Streamlit Cloud  │ (FREE)
│   (UI Only)      │
└────────┬─────────┘
         │ HTTP
    ┌────▼──────────────┐
    │ Google Cloud VM   │ ($25/mo, FREE with credits)
    │ (API + Models)    │
    │ e2-medium         │
    │ 2 vCPU, 4GB RAM   │
    └────────┬──────────┘
             │ gRPC
        ┌────▼─────┐
        │  Qdrant  │ ($25/mo)
        │  Cloud   │
        └──────────┘
```

**Total Cost:** $50/month (FREE for 12 months with GCP credits)

---

### **Option 2: All Cloud Run** (No Reranker)

```
┌──────────────────┐
│  Cloud Run UI    │ (Serverless, $0-2/mo)
└────────┬─────────┘
         │
    ┌────▼──────────────┐
    │  Cloud Run API    │ (Serverless, $3-5/mo)
    │  (No Reranker)    │
    └────────┬──────────┘
             │
        ┌────▼─────┐
        │  Qdrant  │ ($25/mo)
        └──────────┘
```

**Total Cost:** $28-32/month  
**Limitation:** No reranker (NDCG drops to ~0.78)

---

## 🧪 Model Performance Comparison

### **Retrieval Methods**

| Method | NDCG@10 | Latency | Complexity |
|--------|---------|---------|------------|
| **Dense only** | 0.720 | 150ms | Low |
| **BM25 only** | 0.680 | 90ms | Very Low |
| **Hybrid (α=0.65)** | 0.780 | 250ms | Medium |
| **Hybrid + Reranker** | 0.854 | 550ms | High |

### **Alpha (α) Tuning**

Hybrid fusion weight tested:

| α | Dense Weight | BM25 Weight | NDCG@10 |
|---|--------------|-------------|---------|
| 0.5 | 50% | 50% | 0.761 |
| 0.6 | 60% | 40% | 0.774 |
| **0.65** | **65%** | **35%** | **0.780** |
| 0.7 | 70% | 30% | 0.776 |
| 0.8 | 80% | 20% | 0.751 |

**Optimal:** α = 0.65 (slightly favor semantic search)

---

## 🎯 Design Decisions

### **Why Hybrid Search?**

**Dense Search Strengths:**
- ✅ Semantic understanding
- ✅ Handles synonyms
- ✅ Cross-lingual potential

**Dense Search Weaknesses:**
- ❌ Misses exact keywords
- ❌ Slower indexing
- ❌ Requires GPU for large-scale

**BM25 Strengths:**
- ✅ Fast keyword matching
- ✅ No training required
- ✅ Interpretable scores

**BM25 Weaknesses:**
- ❌ No semantic understanding
- ❌ Fails on paraphrases
- ❌ Vocabulary mismatch issues

**Hybrid Solution:** Combine both! 🎯

---

### **Why BGE Models?**

**Alternatives Considered:**
- Sentence-BERT
- MPNet
- E5 embeddings

**BGE Chosen Because:**
- ✅ SOTA performance on MTEB benchmark
- ✅ Small model size (320MB vs 1.2GB for large models)
- ✅ Fast inference
- ✅ Optimized for retrieval tasks

---

### **Why Qdrant?**

**Alternatives:**
- Pinecone (more expensive)
- Weaviate (complex setup)
- Milvus (self-hosted only)
- FAISS (no cloud option)

**Qdrant Chosen Because:**
- ✅ Generous free tier
- ✅ Managed cloud service
- ✅ Fast (gRPC protocol)
- ✅ Payload filtering
- ✅ Python-native

---

## 🔬 Technical Optimizations

### **1. Batch Embedding**

```python
# Instead of:
for query in queries:
    embed(query)

# Do:
embeddings = list(embedder.embed(queries))  # Batch processing
```

**Speedup:** 3-5x

---

### **2. Async Checkpoint Uploads**

```python
def save_checkpoint_async():
    threading.Thread(target=upload_to_s3).start()
```

**Benefit:** Don't block processing while uploading

---

### **3. Lazy Loading**

```python
@st.cache_resource
def load_model():
    return HybridSearchEngine()
```

**Benefit:** Load once, reuse across requests

---

### **4. Early Stopping in Reranker**

Only rerank top 20 hybrid candidates (not all 50)

**Speedup:** 2.5x faster reranking

---

## 📊 Resource Requirements

### **Development (Local)**
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 500MB (code + cache)
- **CPU:** 2 cores minimum

### **Production (VM)**
- **RAM:** 4GB (e2-medium)
- **Storage:** 30GB disk
- **CPU:** 2 vCPUs
- **Network:** 1 Gbps

### **Production (Cloud Run)**
- **RAM:** 4GB
- **CPU:** 2 vCPUs
- **Timeout:** 600s
- **Concurrency:** 80 requests/instance

---

## 🔮 Future Improvements

### **Performance**
- [ ] Add GPU support for reranker
- [ ] Implement query result caching in Redis
- [ ] Use ONNX runtime for faster inference
- [ ] Quantize models (float16 → int8)

### **Features**
- [ ] Personalized recommendations
- [ ] Filtering by price, brand, rating
- [ ] "More like this" feature
- [ ] User preference learning

### **Scalability**
- [ ] Kubernetes deployment
- [ ] Horizontal pod autoscaling
- [ ] Database sharding
- [ ] CDN for static assets

---

## 🔗 References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [BGE Models](https://github.com/FlagOpen/FlagEmbedding)
- [BM25 Paper](https://en.wikipedia.org/wiki/Okapi_BM25)