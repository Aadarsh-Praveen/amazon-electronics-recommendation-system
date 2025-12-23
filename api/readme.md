# 🔧 Product Recommendation API

FastAPI-based REST API for hybrid product search with BGE reranker.

---

## 🚀 Quick Start

### **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
export GCS_BUCKET_NAME="your-bucket"

# Download cache files (BM25 index, mappings)
cd ..
python scripts/download_cache.py

# Run API
cd api
uvicorn main:app --reload --port 8000
```

**Access:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📡 API Endpoints

### **GET /** 
Root endpoint - API information

**Response:**
```json
{
  "name": "Product Recommendation API",
  "version": "1.0.0",
  "endpoints": {
    "/search": "Main search",
    "/health": "Health check",
    "/stats": "API statistics",
    "/cache-stats": "Cache info"
  }
}
```

---

### **GET /health**
Health check and system status

**Response:**
```json
{
  "status": "healthy",
  "qdrant": "connected",
  "total_products": 31100,
  "models": "loaded"
}
```

---

### **GET /search**
Search for products using hybrid retrieval

**Query Parameters:**
- `query` (string, required): Search query (min 2 chars)
- `top_k` (integer, optional, default=3): Number of results (1-10)
- `use_reranker` (boolean, optional, default=true): Enable BGE reranker

**Example Request:**
```bash
curl "http://localhost:8000/search?query=wireless%20headphones&top_k=5&use_reranker=true"
```

**Response:**
```json
{
  "query": "wireless headphones",
  "num_results": 5,
  "response_time": 0.545,
  "cached": false,
  "latency_breakdown_ms": {
    "embedding": 45.2,
    "dense": 120.5,
    "bm25": 85.3,
    "fusion": 15.1,
    "reranker": 278.9
  },
  "results": [
    {
      "product_id": "B00HMRDKO2",
      "title": "Mpow Bluetooth Headphones Over Ear",
      "brand": "Mpow",
      "price": 29.99,
      "avg_rating": 4.4,
      "review_count": 1247,
      "sentiment_score": 0.82,
      "abstracted_summary": "Comfortable wireless headphones with good sound quality...",
      "aspects": [
        {"aspect": "sound_quality", "sentiment": "positive", "score": 0.85},
        {"aspect": "battery_life", "sentiment": "positive", "score": 0.78},
        {"aspect": "comfort", "sentiment": "positive", "score": 0.88}
      ],
      "hybrid_score": 0.89,
      "rerank_score": 0.92,
      "rank": 1
    }
  ]
}
```

---

### **GET /stats**
API usage statistics

**Response:**
```json
{
  "total_searches": 1234,
  "avg_response_time": 0.543,
  "cache_hits": 789,
  "cache_hit_rate": 0.64
}
```

---

### **GET /cache-stats**
Cache layer statistics

**Response:**
```json
{
  "embedding_cache": 150,
  "dense_cache": 200,
  "bm25_cache": 180,
  "hybrid_cache": 175
}
```

---

## 🔧 Architecture

```
Request
   ↓
FastAPI Router
   ↓
HybridSearchEngine
   ↓
┌────────────┬─────────────┬──────────┐
│ Embedding  │ Dense Search│   BM25   │
│   Cache    │    Cache    │  Cache   │
└────────────┴─────────────┴──────────┘
   ↓
Hybrid Fusion (α=0.65)
   ↓
BGE Reranker (optional)
   ↓
JSON Response
```

---

## 📊 Performance

### **Latency Components**

| Component | Avg Time | Cached |
|-----------|----------|--------|
| Embedding | 45ms | ✅ Yes |
| Dense Search | 120ms | ✅ Yes |
| BM25 Search | 85ms | ✅ Yes |
| Fusion | 15ms | ✅ Yes |
| Reranker | 280ms | ❌ No |
| **Total (uncached)** | ~545ms | - |
| **Total (cached)** | ~50ms | - |

### **Cache Hit Rates**
- Production average: **65-75%**
- Speedup with cache: **10-15x**

---

## 🗄️ Database Schema

### **Query Logging (SQLite)**

```sql
CREATE TABLE queries (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    query TEXT,
    num_results INTEGER,
    response_time REAL,
    cached BOOLEAN,
    embedding_time REAL,
    dense_time REAL,
    bm25_time REAL,
    fusion_time REAL,
    reranker_time REAL,
    use_reranker BOOLEAN
);
```

Location: `logs/queries.db`

---

## 🔐 Environment Variables

### **Required**

```bash
QDRANT_URL           # Qdrant cluster URL
QDRANT_API_KEY       # Qdrant API key
GCS_BUCKET_NAME      # Google Cloud Storage bucket for cache files
```

### **Optional**

```bash
PORT                 # API port (default: 8080)
LOG_LEVEL           # Logging level (default: INFO)
```

---

## 🧪 Testing

### **Manual Testing**

```bash
# Health check
curl http://localhost:8000/health

# Search
curl "http://localhost:8000/search?query=bluetooth%20speaker&top_k=3"

# Stats
curl http://localhost:8000/stats
```

### **Load Testing**

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 "http://localhost:8000/search?query=headphones&top_k=3"
```

---

## 📈 Monitoring

Logs are written to:
- **Console**: Real-time logging
- **File**: `logs/api.log`
- **Database**: `logs/queries.db`

View logs:
```bash
tail -f logs/api.log
```

Query database:
```bash
sqlite3 logs/queries.db "SELECT * FROM queries ORDER BY timestamp DESC LIMIT 10;"
```

---

## 🐛 Troubleshooting

### **Issue: "Cache files not found"**

**Solution:**
```bash
python scripts/download_cache.py
```

### **Issue: "Qdrant connection failed"**

**Check:**
- QDRANT_URL is correct
- QDRANT_API_KEY is valid
- Firewall allows outbound HTTPS

### **Issue: "Models failed to load"**

**For VM deployment:**
- Models download on first run (takes 2-3 minutes)
- Check internet connectivity

**For Cloud Run:**
- Models must be pre-cached in Docker image

---

## 📚 Dependencies

See `requirements.txt` for full list. Key dependencies:

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **qdrant-client** - Vector database client
- **fastembed** - BGE embeddings
- **sentence-transformers** - BGE reranker
- **rank-bm25** - BM25 keyword search
- **polars** - Fast dataframes

---

## 🔗 Related Documentation

- [Main README](../README.md)
- [Deployment Guide](../docs/deployment_guide.md)
- [Architecture](../docs/architecture.md)