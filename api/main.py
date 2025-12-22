print("STARTING API")
print("Current directory:", os.getcwd())
print("Python path:", sys.path)

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import time
import logging
import sqlite3
from datetime import datetime

# Add parent directory to path
print("[DEBUG] Starting API initialization...")
print(f"[DEBUG] Working directory: {os.getcwd()}")
print(f"[DEBUG] __file__: {__file__}")

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"[DEBUG] Project root: {project_root}")

if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"[DEBUG] sys.path: {sys.path[:3]}")

print("[DEBUG] Attempting to import HybridSearchEngine...")
try:
    from models.hybrid_search_engine import HybridSearchEngine
    print("[DEBUG]  Successfully imported HybridSearchEngine")
except Exception as e:
    print(f"[DEBUG]  Failed to import: {e}")
    import traceback
    traceback.print_exc()
    raise

# ============================================================================
# LOGGING SETUP
# ============================================================================

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP FOR QUERY LOGGING
# ============================================================================

def init_db():
    """Initialize SQLite database for query logging"""
    conn = sqlite3.connect('logs/queries.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized")

init_db()

def log_query(query, num_results, response_time, cached, latency, use_reranker):
    """Log query to database"""
    try:
        conn = sqlite3.connect('logs/queries.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO queries (
                timestamp, query, num_results, response_time, cached,
                embedding_time, dense_time, bm25_time, fusion_time, reranker_time,
                use_reranker
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            query,
            num_results,
            response_time,
            cached,
            latency.get('embedding', 0),
            latency.get('dense', 0),
            latency.get('bm25', 0),
            latency.get('fusion', 0),
            latency.get('reranker', 0),
            use_reranker
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log query: {e}")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Product Recommendation API",
    description="Hybrid search with BM25 + Dense vectors + BGE Reranker",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
logger.info("Loading search engine...")
engine = HybridSearchEngine()
logger.info("API ready!")

# In-memory metrics
metrics = {
    "total_searches": 0,
    "total_time": 0.0,
    "cache_hits": 0
}

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    return {
        "name": "Product Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Main search",
            "/health": "Health check",
            "/stats": "API statistics",
            "/cache-stats": "Cache info"
        }
    }

@app.get("/health")
def health():
    try:
        info = engine.qdrant.get_collection(engine.collection_name)
        logger.info("Health check: OK")
        return {
            "status": "healthy",
            "qdrant": "connected",
            "total_products": info.points_count,
            "models": "loaded"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/stats")
def get_stats():
    """API statistics"""
    avg_time = metrics["total_time"] / metrics["total_searches"] if metrics["total_searches"] > 0 else 0
    cache_rate = metrics["cache_hits"] / metrics["total_searches"] if metrics["total_searches"] > 0 else 0
    
    return {
        "total_searches": metrics["total_searches"],
        "avg_response_time": round(avg_time, 3),
        "cache_hits": metrics["cache_hits"],
        "cache_hit_rate": round(cache_rate, 3)
    }

@app.get("/cache-stats")
def cache_stats():
    return engine.get_cache_stats()

@app.get("/search")
def search(
    query: str = Query(..., min_length=2),
    top_k: int = Query(3, ge=1, le=10),
    use_reranker: bool = Query(True)
):
    logger.info(f"Search: '{query}' | top_k={top_k} | reranker={use_reranker}")
    
    overall_start = time.time()
    latency = {}
    
    try:
        cache_key = f"{query}_{20}_{0.65}"
        was_cached = cache_key in engine._hybrid_cache
        
        if was_cached:
            metrics["cache_hits"] += 1
        
        # Track components
        emb_start = time.time()
        _ = engine.get_embedding(query)
        latency['embedding'] = time.time() - emb_start
        
        dense_start = time.time()
        _ = engine.dense_search(query, 50)
        latency['dense'] = time.time() - dense_start
        
        bm25_start = time.time()
        _ = engine.bm25_search(query, 50)
        latency['bm25'] = time.time() - bm25_start
        
        fusion_start = time.time()
        candidates = engine.hybrid_search(query, top_k=20, alpha=0.65)
        latency['fusion'] = time.time() - fusion_start
        
        if use_reranker:
            rerank_start = time.time()
            results = engine.rerank(query, candidates, top_k=top_k)
            latency['reranker'] = time.time() - rerank_start
        else:
            results = candidates[:top_k]
            latency['reranker'] = 0
        
        elapsed = time.time() - overall_start
        
        # Update metrics
        metrics["total_searches"] += 1
        metrics["total_time"] += elapsed
        
        # Log to database
        log_query(query, len(results), elapsed, was_cached, latency, use_reranker)
        
        logger.info(f"Search completed in {elapsed:.3f}s")
        
        return {
            "query": query,
            "num_results": len(results),
            "response_time": round(elapsed, 3),
            "cached": was_cached,
            "latency_breakdown_ms": {k: round(v * 1000, 1) for k, v in latency.items()},
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
