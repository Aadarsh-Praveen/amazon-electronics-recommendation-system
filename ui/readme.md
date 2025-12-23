# 🎨 Product Search UI

Streamlit-based web interface for product recommendations.

---

## 🚀 Quick Start

### **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Set API endpoint
export API_BASE="http://localhost:8000"

# Run UI
streamlit run app.py
```

Visit: http://localhost:8501

---

## ☁️ Deploy to Streamlit Cloud

### **Step 1: Push to GitHub**

Ensure your code is in a GitHub repository.

### **Step 2: Deploy on Streamlit Cloud**

1. Go to https://share.streamlit.io/
2. Click **"New app"**
3. Select your repository
4. **Main file path:** `ui/app.py`
5. Click **"Advanced settings"**
6. Add secret:
   ```toml
   API_BASE = "http://YOUR_VM_IP:8080"
   ```
7. Click **"Deploy"**

### **Step 3: Access Your App**

Your app will be available at: `https://YOUR_APP.streamlit.app`

---

## 🎨 Features

### **Search Interface**
- Real-time product search
- Customizable result count (1-10)
- Toggle BGE reranker on/off

### **Product Cards**
- Product title and brand
- Review count and sentiment score
- Match score (hybrid or rerank)
- Review summary (expandable)
- Aspect-based ratings

### **Performance Metrics**
- Response time tracking
- Cache hit/miss indicator
- Latency breakdown

### **Example Searches**
- One-click example queries
- Pre-configured searches for testing

---

## ⚙️ Configuration

### **Environment Variables**

```bash
API_BASE     # API endpoint URL (required)
```

### **UI Settings**

Users can customize via sidebar:
- **Use BGE Reranker**: Toggle reranker on/off
- **Results**: Number of products to display (1-10)

---

## 🎨 Customization

### **Styling**

Custom CSS is defined in `app.py`:
- Product cards with gradient borders
- Aspect chips (color-coded by sentiment)
- Responsive layout

### **Modify Colors**

Edit the CSS section in `app.py`:

```python
st.markdown("""
<style>
    .product-card {
        border-left: 4px solid #YOUR_COLOR;
    }
    .positive { background: #YOUR_GREEN; }
    .negative { background: #YOUR_RED; }
</style>
""", unsafe_allow_html=True)
```

---

## 📊 Components

### **Search Form**
- Text input for queries
- Search button
- Example query buttons

### **Results Display**
- Product cards with metadata
- Expandable review summaries
- Aspect-based ratings (chips)

### **Sidebar**
- Settings panel
- System information
- API health status

---

## 🐛 Troubleshooting

### **Issue: "Cannot connect to API"**

**Solutions:**
1. Check `API_BASE` is correct
2. Verify API is running: `curl $API_BASE/health`
3. Check firewall allows HTTP traffic

### **Issue: "API timeout"**

**Solutions:**
1. Increase timeout in Streamlit config
2. Check API performance
3. Verify network connectivity

### **Issue: "Cached results"**

**Note:** The API caches results for faster responses. To force fresh results, modify your query slightly or clear API cache.

---

## 📚 Dependencies

See `requirements.txt`:

- **streamlit** - Web framework
- **requests** - HTTP client
- **plotly** - Visualizations (for monitoring)

---

## 🔗 Related

- [API Documentation](../api/README.md)
- [Deployment Guide](../docs/deployment_guide.md)
- [Main README](../README.md)