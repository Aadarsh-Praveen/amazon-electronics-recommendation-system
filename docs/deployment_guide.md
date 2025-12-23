# 🚀 Deployment Guide

Complete guide for deploying the Amazon Electronics Recommendation System.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Option 1: Google Cloud VM (Recommended)](#option-1-google-cloud-vm-recommended)
- [Option 2: Streamlit Cloud (UI Only)](#option-2-streamlit-cloud-ui-only)
- [Option 3: Google Cloud Run](#option-3-google-cloud-run)
- [Cost Comparison](#cost-comparison)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🎯 Overview

### **Deployment Options**

| Option | API | UI | Reranker | Cost/Month | Complexity |
|--------|-----|----|---------| -----------|------------|
| **VM + Streamlit** | VM | Streamlit Cloud | ✅ Yes | $25 (FREE 12mo) | Medium |
| **Cloud Run + Streamlit** | Cloud Run | Streamlit Cloud | ❌ No | $3-5 | Low |
| **All Local** | Local | Local | ✅ Yes | $0 | Very Low |

**Recommended:** Option 1 (VM + Streamlit Cloud)

---

## 📦 Prerequisites

### **Required**

1. **Google Cloud Account**
   - Free trial: $300 credits (69 days)
   - Billing enabled

2. **Qdrant Cloud Account**
   - Free tier: 1GB cluster
   - Sign up: https://cloud.qdrant.io/

3. **GitHub Account** (for Streamlit Cloud)

4. **Tools Installed**
   - Google Cloud SDK (`gcloud`)
   - Git
   - Python 3.10+

### **Optional**

- AWS Account (for SageMaker processing)
- Docker (for local testing)

---

## 🖥️ OPTION 1: Google Cloud VM (Recommended)

**Best for:** Production deployment with full reranker functionality

### **Step 1: Create VM**

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Create e2-medium VM (2 vCPU, 4GB RAM)
gcloud compute instances create product-recommendation-vm \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --boot-disk-size=30GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server

# Create firewall rule
gcloud compute firewall-rules create allow-http-8080 \
    --allow tcp:8080 \
    --target-tags http-server \
    --description="Allow HTTP on port 8080"
```

**Cost:** ~$25/month (FREE for 12 months with $300 credits)

---

### **Step 2: Upload Code**

```bash
# Upload project (excluding cache/logs)
gcloud compute scp --recurse --zone=us-central1-a \
    --exclude="cache/" \
    --exclude="logs/" \
    --exclude="__pycache__/" \
    --exclude="notebooks/" \
    /path/to/amazon-electronics-recommendation-system \
    product-recommendation-vm:~/app
```

---

### **Step 3: Setup VM**

```bash
# SSH into VM
gcloud compute ssh product-recommendation-vm --zone=us-central1-a

# Update system
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git

# Navigate to app
cd ~/app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r api/requirements.txt

# Set environment variables
export QDRANT_URL="https://YOUR_CLUSTER.qdrant.io"
export QDRANT_API_KEY="YOUR_API_KEY"
export GCS_BUCKET_NAME="amazon-cache-bucket"

# Download cache files from GCS
python scripts/download_cache.py

# Verify cache
ls -lh cache/
# Should show: bm25_index.pkl (122MB), product_id_mapping.pkl (486KB)
```

---

### **Step 4: Test API**

```bash
# On VM - start API
cd ~/app
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

**From your local machine:**

```bash
# Get VM external IP
EXTERNAL_IP=$(gcloud compute instances describe product-recommendation-vm \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# Test
curl "http://$EXTERNAL_IP:8080/health"
curl "http://$EXTERNAL_IP:8080/search?query=headphones&top_k=3"
```

---

### **Step 5: Create Systemd Service (Run Forever)**

```bash
# On VM, create service file
sudo nano /etc/systemd/system/product-api.service
```

**Paste this** (replace `YOUR_USERNAME` with your actual username):

```ini
[Unit]
Description=Product Recommendation API
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/app
Environment="PATH=/home/YOUR_USERNAME/app/venv/bin"
Environment="QDRANT_URL=https://YOUR_CLUSTER.qdrant.io"
Environment="QDRANT_API_KEY=YOUR_API_KEY"
Environment="GCS_BUCKET_NAME=amazon-cache-bucket"
ExecStart=/home/YOUR_USERNAME/app/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable product-api
sudo systemctl start product-api
sudo systemctl status product-api
```

---

### **Step 6: Deploy UI to Streamlit Cloud**

1. **Push code to GitHub** (if not already done)

2. **Go to** https://share.streamlit.io/

3. **Click "New app"**

4. **Configure:**
   - Repository: `YOUR_USERNAME/amazon-electronics-recommendation-system`
   - Branch: `main`
   - Main file path: `ui/app.py`

5. **Add secrets** (Advanced settings):
   ```toml
   API_BASE = "http://YOUR_VM_IP:8080"
   ```

6. **Click "Deploy"**

**Result:** Your UI is live at `https://YOUR_APP.streamlit.app` 🎉

---

## ☁️ OPTION 2: Streamlit Cloud (UI Only)

**Best for:** Quick demo without backend setup

### **Simplified Streamlit App**

Create `streamlit_app.py`:

```python
import streamlit as st
from qdrant_client import QdrantClient
from fastembed import TextEmbedding

st.title("🛍️ Amazon Product Search")

@st.cache_resource
def init_qdrant():
    return QdrantClient(
        url=st.secrets["QDRANT_URL"],
        api_key=st.secrets["QDRANT_API_KEY"]
    )

@st.cache_resource
def init_embedder():
    return TextEmbedding("BAAI/bge-small-en-v1.5")

qdrant = init_qdrant()
embedder = init_embedder()

query = st.text_input("Search products:")

if st.button("Search") and query:
    vector = list(embedder.embed([query]))[0]
    results = qdrant.query_points(
        collection_name="amazon-products",
        query=vector.tolist(),
        limit=10
    )
    
    for r in results.points:
        st.write(f"**{r.payload['title']}**")
        st.write(f"Rating: {r.payload['avg_rating']}/5")
```

**Deploy:**
1. Push to GitHub
2. Deploy on Streamlit Cloud
3. Add secrets: `QDRANT_URL`, `QDRANT_API_KEY`

**Limitations:**
- ❌ No BM25 (semantic search only)
- ❌ No reranker (RAM limits)
- ❌ No caching
- ✅ 100% FREE

---

## ☁️ OPTION 3: Google Cloud Run

**Best for:** Serverless deployment without reranker

### **Why No Reranker?**

Cloud Run containers can't download HuggingFace models during startup due to:
- Health check timeouts (10 min max)
- Rate limiting from shared IPs
- Ephemeral filesystem restrictions

**Solution:** Deploy without reranker (NDCG drops from 0.854 to ~0.78)

---

### **Deployment Steps**

```bash
# Build Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/product-api --dockerfile Dockerfile.api .

# Deploy to Cloud Run
gcloud run deploy product-recommendation-api \
    --image gcr.io/YOUR_PROJECT/product-api \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 600 \
    --set-env-vars QDRANT_URL=YOUR_URL,QDRANT_API_KEY=YOUR_KEY,GCS_BUCKET_NAME=YOUR_BUCKET
```

**See:** `deployment/google-cloud/README.md` for complete setup

---

## 💰 Cost Comparison

### **Monthly Costs**

| Component | VM Setup | Cloud Run Setup | Local Only |
|-----------|----------|-----------------|------------|
| **API (VM)** | $25 | - | $0 |
| **API (Cloud Run)** | - | $3-5 | - |
| **UI (Streamlit Cloud)** | $0 | $0 | $0 |
| **Qdrant Cloud** | $25 | $25 | $25 |
| **GCS Storage** | $0.01 | $0.01 | - |
| **Total** | **$50** | **$28-30** | **$25** |

**With GCP Free Trial:**
- VM setup: **$0 for 12 months** ✅
- After 12 months: $50/month

---

## 🔧 VM Management

### **Start/Stop VM** (Save Money)

```bash
# Stop VM (costs ~$1/mo for storage only)
gcloud compute instances stop product-recommendation-vm --zone=us-central1-a

# Start VM
gcloud compute instances start product-recommendation-vm --zone=us-central1-a

# Service auto-starts on boot!
```

---

### **View Logs**

```bash
# View service logs
gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
    --command="sudo journalctl -u product-api -f"

# View last 100 lines
gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
    --command="sudo journalctl -u product-api -n 100"
```

---

### **Restart Service**

```bash
gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
    --command="sudo systemctl restart product-api"
```

---

### **Update Code**

```bash
# Upload new code
gcloud compute scp --recurse --zone=us-central1-a \
    /path/to/updated/code \
    product-recommendation-vm:~/app

# Restart service
gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
    --command="sudo systemctl restart product-api"
```

---

### **Delete VM** (Cleanup)

```bash
# Delete VM completely
gcloud compute instances delete product-recommendation-vm --zone=us-central1-a

# Delete firewall rule
gcloud compute firewall-rules delete allow-http-8080
```

---

## 🔐 Security Best Practices

### **1. Use HTTPS**

Set up SSL with Let's Encrypt (for production):

```bash
# Install Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/product-api

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

### **2. Add API Authentication**

In `api/main.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return key

@app.get("/search", dependencies=[Depends(verify_api_key)])
def search(...):
    ...
```

---

### **3. Restrict CORS**

```python
# In main.py, change from:
allow_origins=["*"]

# To:
allow_origins=["https://your-app.streamlit.app"]
```

---

## 📊 Monitoring Setup

### **1. Enable Cloud Monitoring**

```bash
gcloud services enable monitoring.googleapis.com

# Install monitoring agent on VM
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

---

### **2. Set Up Alerts**

```bash
# Create alert for high CPU
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="High CPU Alert" \
    --condition-display-name="CPU > 80%" \
    --condition-threshold-value=0.8
```

---

### **3. View Metrics**

Visit: https://console.cloud.google.com/monitoring

---

## 🧪 Testing Deployment

### **Smoke Tests**

```bash
# 1. Health check
curl http://YOUR_VM_IP:8080/health

# Expected: {"status":"healthy",...}

# 2. Search test
curl "http://YOUR_VM_IP:8080/search?query=test&top_k=1"

# Expected: JSON with results

# 3. Stats check
curl http://YOUR_VM_IP:8080/stats

# Expected: {"total_searches":N,...}
```

---

### **Load Testing**

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Run 100 requests, 10 concurrent
ab -n 100 -c 10 "http://YOUR_VM_IP:8080/search?query=headphones&top_k=3"

# Check results:
# - Requests per second
# - Mean response time
# - Failed requests (should be 0)
```

---

## 🔄 CI/CD Setup (Optional)

### **GitHub Actions Workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VM

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup gcloud
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Upload code to VM
      run: |
        gcloud compute scp --recurse --zone=us-central1-a \
          --exclude="cache/" --exclude="logs/" \
          . product-recommendation-vm:~/app
    
    - name: Restart service
      run: |
        gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
          --command="sudo systemctl restart product-api"
```

---

## 🐛 Troubleshooting

### **Issue: VM won't start**

```bash
# Check VM status
gcloud compute instances describe product-recommendation-vm --zone=us-central1-a

# View serial console output
gcloud compute instances get-serial-port-output product-recommendation-vm --zone=us-central1-a
```

---

### **Issue: API not accessible**

**Check firewall:**
```bash
gcloud compute firewall-rules list | grep 8080
```

**Check service status:**
```bash
gcloud compute ssh product-recommendation-vm --zone=us-central1-a \
    --command="sudo systemctl status product-api"
```

---

### **Issue: Out of memory**

**Solution 1:** Upgrade VM
```bash
# Stop VM
gcloud compute instances stop product-recommendation-vm --zone=us-central1-a

# Change machine type
gcloud compute instances set-machine-type product-recommendation-vm \
    --zone=us-central1-a \
    --machine-type=e2-standard-2

# Start VM
gcloud compute instances start product-recommendation-vm --zone=us-central1-a
```

**Solution 2:** Reduce cache size

In `hybrid_search_engine.py`:
```python
self.max_cache_size = 500  # Reduced from 1000
```

---

### **Issue: Slow startup**

**Cause:** Models downloading from HuggingFace on first run

**Solution:** Wait 2-3 minutes on first startup. Subsequent starts will be fast (<10s).

---

## 📈 Scaling Guide

### **Vertical Scaling** (Single VM)

```bash
# Upgrade to e2-standard-4 (4 vCPU, 16GB RAM)
gcloud compute instances set-machine-type product-recommendation-vm \
    --zone=us-central1-a \
    --machine-type=e2-standard-4
```

**Cost:** ~$60/month

---

### **Horizontal Scaling** (Multiple VMs + Load Balancer)

```bash
# Create instance template
gcloud compute instance-templates create product-api-template \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server \
    --metadata=startup-script-url=gs://YOUR_BUCKET/startup.sh

# Create instance group
gcloud compute instance-groups managed create product-api-group \
    --base-instance-name=product-api \
    --size=3 \
    --template=product-api-template \
    --zone=us-central1-a

# Create load balancer
gcloud compute backend-services create product-api-backend \
    --protocol=HTTP \
    --port-name=http \
    --global
```

**Cost:** ~$75/month (3 VMs)

---

## 🔒 Production Hardening

### **1. Use Custom Domain**

```bash
# Reserve static IP
gcloud compute addresses create product-api-ip --region=us-central1

# Get IP
gcloud compute addresses describe product-api-ip --region=us-central1

# Point your domain's A record to this IP
# Then configure Nginx with SSL
```

---

### **2. Set Up Monitoring**

```bash
# Install Cloud Monitoring agent
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

---

### **3. Enable Backup**

```bash
# Create disk snapshot schedule
gcloud compute resource-policies create snapshot-schedule daily-backup \
    --region=us-central1 \
    --max-retention-days=7 \
    --on-source-disk-delete=keep-auto-snapshots \
    --daily-schedule \
    --start-time=03:00

# Attach to VM disk
gcloud compute disks add-resource-policies product-recommendation-vm \
    --resource-policies=daily-backup \
    --zone=us-central1-a
```

---

## 📊 Performance Tuning

### **1. Increase Cache Size**

```python
# In hybrid_search_engine.py
self.max_cache_size = 2000  # Increased from 1000
```

---

### **2. Optimize Qdrant Query**

```python
# Add search parameters
results = self.qdrant.query_points(
    collection_name=self.collection_name,
    query=vector.tolist(),
    limit=top_k,
    search_params={"hnsw_ef": 128, "exact": False}  # Faster approximate search
)
```

---

### **3. Enable HTTP/2**

In systemd service, change `ExecStart`:
```ini
ExecStart=/home/YOUR_USERNAME/app/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8080 --http h11
```

---

## 🔗 Next Steps

After deployment:

1. ✅ Test all endpoints
2. ✅ Monitor logs for errors
3. ✅ Set up alerts
4. ✅ Create backups
5. ✅ Document your specific configuration
6. ✅ Share your app URL!

---

## 📚 Additional Resources

- [Google Cloud VM Documentation](https://cloud.google.com/compute/docs)
- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Qdrant Cloud Guide](https://qdrant.tech/documentation/cloud/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)