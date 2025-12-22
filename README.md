# 🛍️ Amazon Electronics Product Recommendation System

AI-powered product search and recommendation system for 31,100+ Amazon electronics products with hybrid search, aspect extraction and sentiment analysis.

## 🚀 Features

- **Hybrid Search**: BM25 keyword search + Dense vector search (Qdrant)
- **Smart Reranking**: BGE-reranker for improved relevance
- **Aspect-Based**: GPT-4o-mini extracted product aspects
- **Sentiment Analysis**: RoBERTa-based sentiment scoring
- **Real-time API**: FastAPI backend with caching
- **Interactive UI**: Streamlit frontend
- **Monitoring Dashboard**: Performance tracking

## 📊 Performance Metrics

- **NDCG@10**: 0.89
- **Recall@5**: 0.85
- **MRR**: 0.89
- **Response Time**: <1s with caching

## 🛠️ Tech Stack

- **Vector DB**: Qdrant Cloud
- **Embeddings**: BGE-small-en-v1.5 (384 dims)
- **Reranker**: BGE-reranker-base
- **Search**: Hybrid (BM25 + Dense)
- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Deployment**: Render

## 🔧 Local Setup

### Prerequisites

- Python 3.9+
- Qdrant account
- 31.1K products uploaded to Qdrant

### Installation

1. Clone repository:
```bash
git clone https://github.com/yourusername/amazon-product-recommendation.git
cd amazon-product-recommendation
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r api/requirements.txt
pip install -r ui/requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your Qdrant credentials
```

5. Create BM25 index and mapping:
```bash
python scripts/create_bm25_index.py
python scripts/create_mapping.py
```

### Running Locally

**API:**
```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

**UI:**
```bash
cd ui
streamlit run app.py --server.port 8501
```

**Monitoring:**
```bash
cd monitoring
streamlit run dashboard.py --server.port 8502
```

## 🌐 Deployment on Render

See deployment guide below.

## 📁 Project Structure
```
amazon-product-recommendation/
├── api/              # FastAPI backend
├── ui/               # Streamlit frontend
├── monitoring/       # Performance dashboard
├── models/           # Search engine logic
├── scripts/          # Utility scripts
├── cache/            # BM25 index and mappings
└── data/             # Evaluation data
```

## 📈 API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /search` - Main search with reranking
- `GET /stats` - Usage statistics
- `GET /cache-stats` - Cache information

## 🧪 Testing
```bash
python scripts/evaluate_system.py
```

## 📝 License

MIT License

## 👨‍💻 Author

Your Name - [GitHub](https://github.com/yourusername)
