import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import requests
import os
from datetime import datetime
import json

st.set_page_config(
    page_title="System Monitoring",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# CONFIG
# ============================================================================

# Get API base from secrets or environment
try:
    API_BASE = st.secrets["API_BASE"]
except:
    API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=30)
def load_queries(limit=1000):
    """Load recent queries from API"""
    try:
        r = requests.get(f"{API_BASE}/query-logs?limit={limit}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            
            if data.get('logs'):
                df = pd.DataFrame(data['logs'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_api_stats():
    try:
        r = requests.get(f"{API_BASE}/stats", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=60)
def get_cache_stats():
    try:
        r = requests.get(f"{API_BASE}/cache-stats", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=60)
def get_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.json() if r.status_code == 200 else {"status": "offline"}
    except:
        return {"status": "offline"}

# ============================================================================
# HEADER
# ============================================================================

st.title("📊 System Monitoring Dashboard")
st.markdown("### Real-Time Performance & Analytics")

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh (30s)", value=False):
    import time
    time.sleep(30)
    st.rerun()

st.sidebar.markdown(f"**Last updated:** {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.markdown(f"**API Endpoint:** {API_BASE}")

if st.sidebar.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["🏥 Health", "📈 Performance", "🔍 Queries", "🎯 Evaluation"])

# ============================================================================
# TAB 1: SYSTEM HEALTH
# ============================================================================

with tab1:
    st.header("System Health & Status")
    
    health = get_health()
    api_stats = get_api_stats()
    cache_stats = get_cache_stats()
    
    # Status cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if health.get('status') == 'healthy':
            st.success("✅ API: Healthy")
        else:
            st.error("❌ API: Offline")
    
    with col2:
        if health.get('qdrant') == 'connected':
            st.success("✅ Qdrant: Connected")
        else:
            st.warning("⚠️ Qdrant: Disconnected")
    
    with col3:
        st.metric("Products", f"{health.get('total_products', 0):,}")
    
    with col4:
        if health.get('models') == 'loaded':
            st.success("✅ Models: Ready")
        else:
            st.warning("⚠️ Models: Loading")
    
    st.markdown("---")
    
    # Cache stats
    st.subheader("Cache Status")
    
    if cache_stats:
        cache_col1, cache_col2, cache_col3, cache_col4 = st.columns(4)
        
        with cache_col1:
            st.metric("Embedding Cache", cache_stats.get('embedding_cache', 0))
        with cache_col2:
            st.metric("Dense Cache", cache_stats.get('dense_cache', 0))
        with cache_col3:
            st.metric("BM25 Cache", cache_stats.get('bm25_cache', 0))
        with cache_col4:
            st.metric("Hybrid Cache", cache_stats.get('hybrid_cache', 0))
    
    # API metrics
    st.markdown("---")
    st.subheader("API Statistics")
    
    if api_stats:
        api_col1, api_col2, api_col3 = st.columns(3)
        
        with api_col1:
            st.metric("Total Searches", api_stats.get('total_searches', 0))
        with api_col2:
            st.metric("Avg Response", f"{api_stats.get('avg_response_time', 0):.3f}s")
        with api_col3:
            cache_rate = api_stats.get('cache_hit_rate', 0)
            st.metric("Cache Hit Rate", f"{cache_rate*100:.1f}%")

# ============================================================================
# TAB 2: PERFORMANCE
# ============================================================================

with tab2:
    st.header("Performance Analytics")
    
    df = load_queries()
    
    if not df.empty:
        # Response time trend
        st.subheader("Response Time Over Time")
        
        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['response_time'],
            mode='lines+markers',
            name='Response Time',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))
        fig_timeline.update_layout(
            xaxis_title="Time",
            yaxis_title="Response Time (seconds)",
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        st.markdown("---")
        
        # Latency breakdown
        st.subheader("Latency Breakdown")
        
        perf_col1, perf_col2 = st.columns(2)
        
        with perf_col1:
            # Pie chart
            avg_latency = {
                'Embedding': df['embedding_time'].mean(),
                'Dense Search': df['dense_time'].mean(),
                'BM25': df['bm25_time'].mean(),
                'Fusion': df['fusion_time'].mean(),
                'Reranker': df['reranker_time'].mean()
            }
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(avg_latency.keys()),
                values=[v*1000 for v in avg_latency.values()],
                hole=0.4,
                textinfo='label+percent'
            )])
            fig_pie.update_layout(title="Time Distribution (%)", height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with perf_col2:
            # Bar chart
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=list(avg_latency.keys()),
                    y=[v*1000 for v in avg_latency.values()],
                    marker_color=['#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']
                )
            ])
            fig_bar.update_layout(
                title="Average Latency (ms)",
                yaxis_title="Milliseconds",
                height=400
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Cache performance
        st.markdown("---")
        st.subheader("Cache Performance")
        
        # Convert to boolean if needed
        df['cached'] = df['cached'].astype(bool)
        
        cached = df[df['cached'] == True]
        uncached = df[df['cached'] == False]
        
        cache_perf_col1, cache_perf_col2, cache_perf_col3 = st.columns(3)
        
        with cache_perf_col1:
            st.metric("Cached Queries", len(cached))
        
        with cache_perf_col2:
            avg_cached = cached['response_time'].mean() if not cached.empty else 0
            st.metric("Cached Avg Time", f"{avg_cached:.3f}s")
        
        with cache_perf_col3:
            avg_uncached = uncached['response_time'].mean() if not uncached.empty else 0
            st.metric("Uncached Avg Time", f"{avg_uncached:.3f}s")
        
        if not cached.empty and not uncached.empty and avg_cached > 0:
            speedup = avg_uncached / avg_cached
            st.success(f"⚡ **Cache provides {speedup:.1f}× speedup**")
    
    else:
        st.info("📊 No performance data yet. Make some searches in the UI!")
        st.markdown("**Your API endpoint:**")
        st.code(f"{API_BASE}/search?query=headphones&top_k=3")

# ============================================================================
# TAB 3: QUERY ANALYTICS
# ============================================================================

with tab3:
    st.header("Query Analytics")
    
    df = load_queries()
    
    if not df.empty:
        # Query volume
        st.subheader("Query Volume")
        
        df['hour'] = df['timestamp'].dt.floor('H')
        hourly = df.groupby('hour').size().reset_index(name='count')
        
        fig_volume = go.Figure(data=[
            go.Bar(
                x=hourly['hour'],
                y=hourly['count'],
                marker_color='#3498db'
            )
        ])
        fig_volume.update_layout(
            title="Queries per Hour",
            xaxis_title="Hour",
            yaxis_title="Number of Queries",
            height=350
        )
        st.plotly_chart(fig_volume, use_container_width=True)
        
        st.markdown("---")
        
        # Top queries
        query_col1, query_col2 = st.columns(2)
        
        with query_col1:
            st.subheader("🔥 Most Popular Queries")
            
            top_queries = df['query'].value_counts().head(10)
            
            for i, (query, count) in enumerate(top_queries.items(), 1):
                st.write(f"**{i}.** {query} — {count} searches")
        
        with query_col2:
            st.subheader("🐌 Slowest Queries")
            
            slowest = df.nlargest(10, 'response_time')[['query', 'response_time']]
            
            for idx, row in slowest.iterrows():
                st.write(f"**{row['query']}** — {row['response_time']:.2f}s")
        
        st.markdown("---")
        
        # Recent queries
        st.subheader("🕐 Recent Searches")
        
        recent = df.head(20)[['timestamp', 'query', 'num_results', 'response_time', 'cached']].copy()
        recent['timestamp'] = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        recent['cached'] = recent['cached'].astype(bool).map({True: '⚡', False: '🔄'})
        recent.columns = ['Time', 'Query', 'Results', 'Response (s)', 'Cache']
        
        st.dataframe(recent, use_container_width=True, hide_index=True)
    
    else:
        st.info("📊 No query data yet. Make some searches in the UI!")

# ============================================================================
# TAB 4: EVALUATION
# ============================================================================

with tab4:
    st.header("🎯 Evaluation Metrics")
    
    # Use static evaluation data (always available)
    st.markdown("""
    **Offline Evaluation Results** (10 test queries)
    """)
    
    # Static metrics
    avg_metrics = {
        'Recall@5': 0.803,
        'Recall@10': 1.0,
        'Precision@5': 0.620,
        'MRR': 0.833,
        'NDCG@10': 0.854
    }
    
    # Metrics display
    st.subheader("Overall Performance")
    
    eval_col1, eval_col2, eval_col3, eval_col4, eval_col5 = st.columns(5)
    
    with eval_col1:
        st.metric("Recall@5", f"{avg_metrics['Recall@5']:.3f}")
    with eval_col2:
        st.metric("Recall@10", f"{avg_metrics['Recall@10']:.3f}")
    with eval_col3:
        st.metric("Precision@5", f"{avg_metrics['Precision@5']:.3f}")
    with eval_col4:
        st.metric("MRR", f"{avg_metrics['MRR']:.3f}")
    with eval_col5:
        st.metric("NDCG@10", f"{avg_metrics['NDCG@10']:.3f}")
    
    st.markdown("---")
    
    # Bar chart
    st.subheader("Metrics Visualization")
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(avg_metrics.keys()),
            y=list(avg_metrics.values()),
            marker_color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'],
            text=[f"{v:.3f}" for v in avg_metrics.values()],
            textposition='outside'
        )
    ])
    fig.update_layout(
        title="Evaluation Metrics (Higher is Better)",
        yaxis_range=[0, 1.1],
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Per-query performance (static data)
    st.subheader("Per-Query Performance")
    
    per_query_data = [
        {'Query': 'noise cancelling headphones', 'Recall@5': 1.000, 'Precision@5': 1.000, 'MRR': 1.000, 'NDCG@10': 1.000},
        {'Query': 'wireless bluetooth earbuds', 'Recall@5': 1.000, 'Precision@5': 0.600, 'MRR': 1.000, 'NDCG@10': 0.853},
        {'Query': 'GoPro camera accessories', 'Recall@5': 1.000, 'Precision@5': 1.000, 'MRR': 1.000, 'NDCG@10': 1.000},
        {'Query': 'digital camera with zoom', 'Recall@5': 1.000, 'Precision@5': 1.000, 'MRR': 1.000, 'NDCG@10': 1.000},
        {'Query': 'MP3 player long battery', 'Recall@5': 1.000, 'Precision@5': 0.200, 'MRR': 0.500, 'NDCG@10': 0.631},
        {'Query': 'USB cable iPhone', 'Recall@5': 0.500, 'Precision@5': 0.400, 'MRR': 0.500, 'NDCG@10': 0.711},
        {'Query': 'phone camera lens', 'Recall@5': 0.600, 'Precision@5': 0.600, 'MRR': 1.000, 'NDCG@10': 0.874},
        {'Query': 'tablet case', 'Recall@5': 0.600, 'Precision@5': 0.600, 'MRR': 1.000, 'NDCG@10': 0.918},
        {'Query': 'sound quality earphones', 'Recall@5': 0.333, 'Precision@5': 0.200, 'MRR': 0.333, 'NDCG@10': 0.558},
        {'Query': 'budget headphones', 'Recall@5': 1.000, 'Precision@5': 0.600, 'MRR': 1.000, 'NDCG@10': 1.000}
    ]
    
    df_queries = pd.DataFrame(per_query_data)
    
    # Color code cells without matplotlib
    def color_cells(val):
        if val >= 0.8:
            # Darker green background with dark text
            return 'background-color: #90ee90; color: #000000; font-weight: bold'
        elif val >= 0.6:
            # Light orange background with dark text
            return 'background-color: #ffd700; color: #000000; font-weight: bold'
        else:
            # Light red background with dark text
            return 'background-color: #ffcccb; color: #000000; font-weight: bold'
    
    # Apply styling to numeric columns only
    styled_df = df_queries.style.applymap(
        color_cells, 
        subset=['Recall@5', 'Precision@5', 'MRR', 'NDCG@10']
    )
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    st.info("""
    **Metrics Explanation:**
    - **Recall@5**: Percentage of relevant items found in top 5 results
    - **Recall@10**: Percentage of relevant items found in top 10 results
    - **Precision@5**: Percentage of top 5 results that are relevant
    - **MRR**: Mean Reciprocal Rank - measures how quickly relevant items appear
    - **NDCG@10**: Normalized Discounted Cumulative Gain - overall ranking quality
    
    🟢 Green (≥0.8) = Excellent | 🟡 Yellow (0.6-0.8) = Good | 🔴 Red (<0.6) = Needs Improvement
    """)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("📊 Dashboard Info")
    
    st.markdown("---")
    
    st.subheader("Quick Stats")
    
    df = load_queries()
    if not df.empty:
        st.metric("Total Queries", len(df))
        st.metric("Avg Response", f"{df['response_time'].mean():.2f}s")
        cached_pct = (df['cached'].astype(bool).sum() / len(df)) * 100
        st.metric("Cache Rate", f"{cached_pct:.0f}%")
    else:
        st.info("No query data yet")
    
    st.markdown("---")
    
    st.info("""
    **Dashboard Features:**
    - ✅ Real-time health monitoring
    - ✅ Performance analytics
    - ✅ Query tracking
    - ✅ Cache statistics
    - ✅ Evaluation metrics
    
    **Data Source:**
    - API endpoint for live data
    - Static data for evaluation
    """)