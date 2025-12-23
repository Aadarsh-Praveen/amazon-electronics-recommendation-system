# 📡 API Reference

Complete API documentation for the Product Recommendation System.

---

## 🌐 Base URL

```
Development:  http://localhost:8000
Production:   http://YOUR_VM_IP:8080
Cloud Run:    https://your-api.run.app
```

---

## 📋 Endpoints

### **GET /**

Root endpoint providing API information.

**URL:** `/`

**Parameters:** None

**Response:** `200 OK`

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

**Example:**
```bash
curl http://localhost:8000/
```

---

### **GET /health**

Health check endpoint for monitoring system status.

**URL:** `/health`

**Parameters:** None

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "qdrant": "connected",
  "total_products": 31100,
  "models": "loaded"
}
```

**Possible Status Values:**
- `healthy` - All systems operational
- `unhealthy` - One or more components failed

**Example:**
```bash
curl http://localhost:8000/health
```

**Use Case:** Load balancer health checks, monitoring

---

### **GET /search**

Main search endpoint using hybrid retrieval with optional reranking.

**URL:** `/search`

**Parameters:**

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `query` | string | ✅ Yes | - | min 2 chars | Search query |
| `top_k` | integer | ❌ No | 3 | 1-10 | Number of results |
| `use_reranker` | boolean | ❌ No | true | - | Enable BGE reranker |

**Response:** `200 OK`

```json
{
  "query": "wireless headphones",
  "num_results": 3,
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
      "abstracted_summary": "Comfortable wireless headphones with excellent sound quality for the price. Great battery life lasting up to 20 hours. Some users report Bluetooth connectivity issues.",
      "aspects": [
        {
          "aspect": "sound_quality",
          "sentiment": "positive",
          "score": 0.85
        },
        {
          "aspect": "battery_life",
          "sentiment": "positive",
          "score": 0.88
        },
        {
          "aspect": "comfort",
          "sentiment": "positive",
          "score": 0.78
        },
        {
          "aspect": "bluetooth_connectivity",
          "sentiment": "neutral",
          "score": 0.45
        },
        {
          "aspect": "durability",
          "sentiment": "positive",
          "score": 0.72
        }
      ],
      "hybrid_score": 0.89,
      "rerank_score": 0.92,
      "rank": 1
    },
    {
      "product_id": "B01NAJGGA2",
      "title": "Cowin E7 Active Noise Cancelling Headphones",
      "brand": "Cowin",
      "price": 69.99,
      "avg_rating": 4.3,
      "review_count": 3421,
      "sentiment_score": 0.79,
      "abstracted_summary": "Premium noise cancelling headphones with deep bass and comfortable fit...",
      "aspects": [...],
      "hybrid_score": 0.87,
      "rerank_score": 0.89,
      "rank": 2
    },
    {
      "product_id": "B00NG57H4S",
      "title": "Sony MDRZX110NC Noise Cancelling Headphones",
      "brand": "Sony",
      "price": 49.99,
      "avg_rating": 4.1,
      "review_count": 2847,
      "sentiment_score": 0.81,
      "abstracted_summary": "Affordable Sony noise cancelling headphones with decent sound quality...",
      "aspects": [...],
      "hybrid_score": 0.85,
      "rerank_score": 0.87,
      "rank": 3
    }
  ]
}
```

**Examples:**

```bash
# Basic search
curl "http://localhost:8000/search?query=headphones&top_k=3"

# Search with more results
curl "http://localhost:8000/search?query=bluetooth%20speaker&top_k=10"

# Search without reranker (faster)
curl "http://localhost:8000/search?query=camera&top_k=5&use_reranker=false"

# Complex query
curl "http://localhost:8000/search?query=noise%20cancelling%20headphones%20with%20long%20battery&top_k=5&use_reranker=true"
```

**Error Responses:**

**400 Bad Request** - Invalid parameters
```json
{
  "detail": "Query must be at least 2 characters"
}
```

**500 Internal Server Error** - Server error
```json
{
  "detail": "Search failed: Connection to Qdrant failed"
}
```

---

### **GET /stats**

API usage statistics.

**URL:** `/stats`

**Parameters:** None

**Response:** `200 OK`

```json
{
  "total_searches": 1234,
  "avg_response_time": 0.543,
  "cache_hits": 789,
  "cache_hit_rate": 0.639
}
```

**Field Descriptions:**
- `total_searches` - Total queries since API startup
- `avg_response_time` - Average response time in seconds
- `cache_hits` - Number of cached query results
- `cache_hit_rate` - Percentage of queries served from cache (0-1)

**Example:**
```bash
curl http://localhost:8000/stats
```

---

### **GET /cache-stats**

Detailed cache layer statistics.

**URL:** `/cache-stats`

**Parameters:** None

**Response:** `200 OK`

```json
{
  "embedding_cache": 150,
  "dense_cache": 200,
  "bm25_cache": 180,
  "hybrid_cache": 175
}
```

**Field Descriptions:**
- `embedding_cache` - Cached query embeddings
- `dense_cache` - Cached dense search results
- `bm25_cache` - Cached BM25 scores
- `hybrid_cache` - Cached hybrid fusion results

**Example:**
```bash
curl http://localhost:8000/cache-stats
```

---

## 📊 Response Objects

### **SearchResult**

```typescript
{
  "product_id": string,           // Unique product identifier
  "title": string,                // Product title
  "brand": string,                // Brand name
  "price": number,                // Price in USD
  "avg_rating": number,           // Average rating (0-5)
  "review_count": number,         // Total number of reviews
  "sentiment_score": number,      // Sentiment score (0-1)
  "abstracted_summary": string,   // Generated summary of reviews
  "aspects": Aspect[],            // Array of aspect ratings
  "hybrid_score": number,         // Hybrid retrieval score
  "rerank_score": number,         // Reranker score (if enabled)
  "rank": number                  // Position in results (1-N)
}
```

---

### **Aspect**

```typescript
{
  "aspect": string,      // Aspect name (e.g., "sound_quality")
  "sentiment": string,   // "positive", "neutral", or "negative"
  "score": number        // Confidence score (0-1)
}
```

**Common Aspects:**
- `sound_quality`
- `battery_life`
- `comfort`
- `durability`
- `value_for_money`
- `noise_cancellation`
- `bluetooth_connectivity`
- `build_quality`
- `ease_of_use`
- `design`

---

## ⚡ Performance Metrics

### **Response Time Breakdown**

Typical uncached query:

```
Total: 545ms
├─ Embedding:  45ms  (8%)
├─ Dense:      120ms (22%)
├─ BM25:       85ms  (16%)
├─ Fusion:     15ms  (3%)
└─ Reranker:   280ms (51%)
```

Typical cached query:
```
Total: 50ms (cached hybrid result + reranking)
```

---

### **Throughput**

| Scenario | Queries/Second | Avg Latency |
|----------|----------------|-------------|
| **All cached** | ~20 | 50ms |
| **50% cached** | ~5 | 300ms |
| **No cache** | ~2 | 550ms |
| **No reranker** | ~8 | 180ms |

---

## 🔧 Configuration

### **Environment Variables**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QDRANT_URL` | ✅ Yes | - | Qdrant cluster URL |
| `QDRANT_API_KEY` | ✅ Yes | - | Qdrant API key |
| `GCS_BUCKET_NAME` | ✅ Yes | - | GCS bucket for cache |
| `PORT` | ❌ No | 8080 | API port |
| `LOG_LEVEL` | ❌ No | INFO | Logging level |

---

### **Search Algorithm Parameters**

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `alpha` (α) | 0.65 | 0-1 | Dense vs BM25 weight |
| `dense_top_k` | 50 | 10-100 | Dense retrieval candidates |
| `bm25_top_k` | 50 | 10-100 | BM25 retrieval candidates |
| `rerank_candidates` | 20 | 5-50 | Candidates to rerank |
| `max_cache_size` | 1000 | 100-5000 | Cache capacity |

**Tuning:**
- Higher α → favor semantic search
- Lower α → favor keyword matching
- More candidates → better recall, slower response

---

## 🔐 Authentication (Future)

### **API Key Authentication** (Planned)

```bash
curl -H "X-API-Key: your-secret-key" \
  "http://localhost:8000/search?query=headphones"
```

### **Rate Limiting** (Planned)

```
10 requests/second per IP
1000 requests/day per API key
```

---

## 📝 Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | - |
| `400` | Bad Request | Invalid parameters, query too short |
| `404` | Not Found | Invalid endpoint |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Server Error | Qdrant connection failed, model error |
| `503` | Service Unavailable | System overloaded |

---

## 🧪 Testing Examples

### **Python (requests)**

```python
import requests

API_BASE = "http://localhost:8000"

# Health check
r = requests.get(f"{API_BASE}/health")
print(r.json())

# Search
r = requests.get(f"{API_BASE}/search", params={
    "query": "wireless earbuds",
    "top_k": 5,
    "use_reranker": True
})
results = r.json()
```

---

### **JavaScript (fetch)**

```javascript
const API_BASE = "http://localhost:8000";

// Search
fetch(`${API_BASE}/search?query=headphones&top_k=3`)
  .then(res => res.json())
  .then(data => console.log(data.results));
```

---

### **cURL Examples**

```bash
# URL-encoded query (spaces → %20)
curl "http://localhost:8000/search?query=noise%20cancelling%20headphones&top_k=5"

# With authentication (future)
curl -H "X-API-Key: your-key" \
  "http://localhost:8000/search?query=camera"

# JSON output prettified
curl "http://localhost:8000/search?query=headphones" | jq .
```

---

## 📊 Webhook Support (Future)

### **POST /webhook/search**

Async search with callback URL:

```bash
curl -X POST http://localhost:8000/webhook/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "headphones",
    "top_k": 10,
    "callback_url": "https://your-app.com/webhook"
  }'
```

---

## 🔗 Interactive Documentation

### **Swagger UI**

Visit: http://YOUR_VM_IP:8080/docs

- Try API endpoints directly in browser
- View request/response schemas
- Generate code samples

### **ReDoc**

Visit: http://YOUR_VM_IP:8080/redoc

- Clean, readable documentation
- Downloadable OpenAPI spec
- Search functionality

---

## 📚 SDK Examples (Future)

### **Python SDK**

```python
from product_search import ProductSearchClient

client = ProductSearchClient(
    api_base="http://YOUR_VM_IP:8080",
    api_key="your-key"
)

results = client.search(
    query="wireless headphones",
    top_k=5,
    use_reranker=True
)

for product in results:
    print(f"{product.rank}. {product.title} - {product.rerank_score:.2f}")
```

---

## 🔧 Rate Limiting (Future)

**Planned Limits:**
- 10 requests/second per IP
- 1000 requests/day per API key
- Burst: 20 requests

**Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1640995200
```

---

## 📈 Performance SLA

### **Uptime**
- Target: 99.5% (VM deployment)
- Monitored via Cloud Monitoring

### **Latency**
- P50: <300ms
- P95: <1000ms
- P99: <3000ms

### **Accuracy**
- NDCG@10: >0.80
- Recall@10: >0.95

---

## 🔗 Related Documentation

- [Architecture](architecture.md)
- [Deployment Guide](deployment_guide.md)
- [Evaluation Metrics](evaluation_metrics.md)