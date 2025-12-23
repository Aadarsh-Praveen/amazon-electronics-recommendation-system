# 📊 System Monitoring Dashboard

Real-time analytics and performance monitoring for the recommendation system.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API endpoint
export API_BASE="http://localhost:8000"

# Run dashboard
streamlit run dashboard.py
```

Visit: http://localhost:8502

---

## 📈 Dashboard Tabs

### **Tab 1: System Health**

**Displays:**
- ✅ API status (healthy/offline)
- ✅ Qdrant connection status
- ✅ Total products indexed
- ✅ Model loading status
- ✅ Cache statistics (embedding, dense, BM25, hybrid)
- ✅ API metrics (total searches, avg response time, cache hit rate)

---

### **Tab 2: Performance Analytics**

**Charts:**
1. **Response Time Timeline**
   - Line chart showing response time over time
   - Identifies performance degradation

2. **Latency Breakdown**
   - Pie chart: Time distribution across components
   - Bar chart: Average latency per component

3. **Cache Performance**
   - Cached vs uncached query comparison
   - Speedup factor calculation

**Metrics Tracked:**
- Embedding time
- Dense search time
- BM25 search time
- Fusion time
- Reranker time

---

### **Tab 3: Query Analytics**

**Visualizations:**
1. **Query Volume**
   - Bar chart: Queries per hour
   - Identifies peak usage times

2. **Top Queries**
   - Most popular search terms
   - Frequency counts

3. **Slowest Queries**
   - Queries with highest latency
   - Performance bottleneck identification

4. **Recent Searches**
   - Table of last 20 queries
   - Timestamps, results count, response time, cache status

---

### **Tab 4: Evaluation Metrics**

**Displays:**
- Overall system performance (NDCG, Recall, Precision, MRR)
- Bar chart visualization
- Per-query performance breakdown
- Color-coded heatmap

**Metrics:**
- **Recall@5**: 0.803
- **Recall@10**: 1.000
- **Precision@5**: 0.620
- **MRR**: 0.833
- **NDCG@10**: 0.854

---

## 🔄 Auto-Refresh

Enable auto-refresh in sidebar:
- Refreshes every 30 seconds
- Shows last updated timestamp
- Manual refresh button available

---

## 💾 Data Sources

### **SQLite Database**
- Location: `../logs/queries.db`
- Contains all query logs with detailed metrics

### **API Endpoints**
- `/health` - System status
- `/stats` - Aggregate statistics
- `/cache-stats` - Cache information

### **Evaluation File**
- Location: `../evaluation_results.json`
- Contains offline evaluation metrics

---

## 📊 Metrics Explained

### **NDCG@10** (Normalized Discounted Cumulative Gain)
- Measures ranking quality
- Accounts for position of relevant items
- Range: 0-1 (higher is better)

### **Recall@K**
- Fraction of relevant items retrieved in top K
- Range: 0-1 (higher is better)

### **Precision@K**
- Fraction of top K results that are relevant
- Range: 0-1 (higher is better)

### **MRR** (Mean Reciprocal Rank)
- Average of reciprocal ranks of first relevant item
- Range: 0-1 (higher is better)

---

## 🎨 Customization

### **Update Refresh Rate**

In `dashboard.py`:

```python
# Change from 30s to 60s
if st.sidebar.checkbox("Auto-refresh (60s)", value=False):
    import time
    time.sleep(60)
    st.rerun()
```

### **Modify Chart Colors**

```python
# Update color schemes
marker_color=['#YOUR_COLOR1', '#YOUR_COLOR2', ...]
```

---

## 🐛 Troubleshooting

### **Issue: "No data available"**

**Solution:** 
- Make some searches in the main UI first
- Database is created on first API query

### **Issue: "Cannot connect to API"**

**Solution:**
- Check `API_BASE` is correct
- Verify API is running: `curl $API_BASE/health`

### **Issue: "Evaluation metrics not found"**

**Solution:**
```bash
cd ../scripts
python evaluate_system.py
```

---

## 📚 Dependencies

- **streamlit** - Dashboard framework
- **plotly** - Interactive charts
- **pandas** - Data manipulation
- **requests** - API client

---

## 🔗 Related

- [API Documentation](../api/README.md)
- [Main README](../README.md)