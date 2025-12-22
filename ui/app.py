import streamlit as st
import requests
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Product Recommendations",
    page_icon="🛍️",
    layout="wide"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .product-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .aspect-chip {
        display: inline-block;
        padding: 8px 15px;
        margin: 5px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
    }
    .positive { 
        background: #4caf50; 
        color: white !important;
    }
    .neutral { 
        background: #ffc107; 
        color: #000 !important;
    }
    .negative { 
        background: #f44336; 
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_summary(text):
    """Remove <n> tags"""
    if not text:
        return ""
    cleaned = text.replace('<n>', ' ')
    cleaned = ' '.join(cleaned.split())
    return cleaned

def get_sentiment_emoji(score):
    if score >= 0.8:
        return "😊"
    elif score >= 0.6:
        return "🙂"
    elif score >= 0.4:
        return "😐"
    else:
        return "☹️"

def display_product_card(product, rank):
    st.markdown('<div class="product-card">', unsafe_allow_html=True)
    
    st.markdown(f"### {rank}. {product['title']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        brand = product.get('brand', '')
        if brand and brand.strip():
            st.metric("Brand", brand)
    
    with col2:
        st.metric("Reviews", f"{product.get('review_count', 0):,}")
    
    with col3:
        sentiment = product.get('sentiment_score', 0)
        emoji = get_sentiment_emoji(sentiment)
        st.metric("Sentiment", f"{emoji} {int(sentiment*100)}/100")
    
    with col4:
        if 'rerank_score' in product:
            st.metric("Match Score", f"{int(product['rerank_score']*100)}/100")
        elif 'hybrid_score' in product:
            st.metric("Match Score", f"{int(product['hybrid_score']*100)}/100")
    
    # Summary (cleaned)
    summary = product.get('abstracted_summary', '')
    if summary and str(summary) != 'nan':
        with st.expander("📝 Review Summary"):
            cleaned = clean_summary(summary)
            st.write(cleaned[:500] + "..." if len(cleaned) > 500 else cleaned)
    
    # Aspects (fixed visibility)
    aspects = product.get('aspects', [])
    if aspects and isinstance(aspects, list):
        st.markdown("**🎯 Key Features:**")
        
        aspect_html = ""
        for asp in aspects[:5]:
            if isinstance(asp, dict):
                name = asp.get('aspect', '').title()
                sentiment = asp.get('sentiment', 'neutral')
                score = asp.get('score', 0)
                
                css_class = f"aspect-chip {sentiment}"
                aspect_html += f'<span class="{css_class}">{name}: {int(score*100)}/100</span> '
        
        st.markdown(aspect_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# MAIN UI
# ============================================================================

st.title("🛍️ Smart Product Recommendations")
st.markdown("### AI-Powered Search Across 31,100+ Amazon Electronics")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    use_reranker = st.checkbox("Use BGE Reranker", value=True)
    num_results = st.slider("Results", 1, 10, 3)
    
    st.markdown("---")
    
    st.header("ℹ️ System Info")
    st.info("""
    **Stack:**
    - Qdrant Vector DB
    - Hybrid BM25 + Dense
    - BGE Embeddings
    - BGE-Reranker
    
    **Metrics:**
    - NDCG@10: 0.89
    - Recall@5: 0.85
    - Cache-enabled
    """)
    
    # API health
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.success(f"✓ API Online")
            st.metric("Products", f"{data.get('total_products', 0):,}")
        else:
            st.warning("⚠️ API not responding")
    except:
        st.error("❌ API offline")

st.markdown("---")

# Search form
with st.form("search_form", clear_on_submit=False):
    col1, col2 = st.columns([5, 1])
    
    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="Try: noise cancelling headphones, GoPro camera, MP3 player...",
            label_visibility="collapsed"
        )
    
    with col2:
        search_button = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)

# Execute search
if search_button and search_query:
    with st.spinner("Searching..."):
        try:
            response = requests.get(
                f"{API_BASE}/search",
                params={
                    "query": search_query,
                    "top_k": num_results,
                    "use_reranker": use_reranker
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                response_time = data.get('response_time', 0)
                cached = data.get('cached', False)
                latency = data.get('latency_breakdown_ms', {})
                
                # Stats
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Results", len(results))
                with col_b:
                    st.metric("Time", f"{response_time:.2f}s")
                with col_c:
                    st.metric("Cache", "⚡ Hit" if cached else "🔄 Miss")
                
                # Latency breakdown
                if latency:
                    with st.expander("⚡ Performance Breakdown"):
                        for comp, ms in latency.items():
                            st.write(f"**{comp.title()}:** {ms:.1f}ms")
                
                st.markdown("---")
                
                # Results
                if results:
                    for i, product in enumerate(results, 1):
                        display_product_card(product, i)
                else:
                    st.warning("No products found")
            else:
                st.error(f"API Error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            st.warning("⏱️ Request timeout. Try again (cold start ~30s)")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API")
        except Exception as e:
            st.error(f"Error: {e}")

# Example queries (FIXED)
st.markdown("---")
st.markdown("### 💡 Example Searches:")

if 'example_query' not in st.session_state:
    st.session_state.example_query = None

col_ex1, col_ex2, col_ex3 = st.columns(3)

with col_ex1:
    if st.button("🎧 Headphones", use_container_width=True):
        st.session_state.example_query = "noise cancelling headphones"
        st.rerun()

with col_ex2:
    if st.button("📷 GoPro", use_container_width=True):
        st.session_state.example_query = "GoPro camera accessories"
        st.rerun()

with col_ex3:
    if st.button("🎵 MP3 Player", use_container_width=True):
        st.session_state.example_query = "MP3 player long battery"
        st.rerun()

# Handle example clicks
if st.session_state.example_query:
    query_to_search = st.session_state.example_query
    st.session_state.example_query = None
    
    with st.spinner("Searching..."):
        try:
            response = requests.get(
                f"{API_BASE}/search",
                params={"query": query_to_search, "top_k": num_results, "use_reranker": use_reranker},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                st.success(f"Results for: **{query_to_search}**")
                
                for i, product in enumerate(results, 1):
                    display_product_card(product, i)
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Powered by Qdrant + BGE + Hybrid Search
</div>
""", unsafe_allow_html=True)
