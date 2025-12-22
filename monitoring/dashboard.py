import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import json

st.set_page_config(
    page_title="System Monitoring",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# CONFIG
# ============================================================================

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
DB_PATH = "logs/queries.db"

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=30)
def load_queries(limit=1000):
    """Load recent queries"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM queries ORDER BY timestamp DESC LIMIT {limit}", conn)
        conn.close()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
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
        return r.json() if r.status_code == 200 else {}
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

if st.sidebar.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["🏥 Health", "📈 Performance", "🔍 Queries", "📊 Evaluation"])

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
            st.success("✓ API: Healthy")
        else:
            st.error("✗ API: Offline")
    
    with col2:
        if health.get('qdrant') == 'connected':
            st.success("✓ Qdrant: Connected")
        else:
            st.warning("⚠️ Qdrant: Disconnected")
    
    with col3:
        st.metric("Products", f"{health.get('total_products', 0):,}")
    
    with col4:
        if health.get('models') == 'loaded':
            st.success("✓ Models: Ready")
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
        
        if not cached.empty and not uncached.empty:
            speedup = avg_uncached / avg_cached
            st.success(f"⚡ **Cache provides {speedup:.1f}× speedup**")
    
    else:
        st.info("No performance data yet. Make some searches!")

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
            
            for idx, (query, time_val) in slowest[['query', 'response_time']].iterrows():
                st.write(f"**{query}** — {time_val:.2f}s")
        
        st.markdown("---")
        
        # Recent queries
        st.subheader("Recent Searches")
        
        recent = df.head(20)[['timestamp', 'query', 'num_results', 'response_time', 'cached']].copy()
        recent['timestamp'] = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        recent['cached'] = recent['cached'].map({True: '⚡', False: '🔄'})
        recent.columns = ['Time', 'Query', 'Results', 'Response (s)', 'Cache']
        
        st.dataframe(recent, use_container_width=True, hide_index=True)
    
    else:
        st.info("No query data yet")

# ============================================================================
# TAB 4: EVALUATION
# ============================================================================

with tab4:
    st.header("Evaluation Metrics")
    
    try:
        with open("evaluation_results.json", "r") as f:
            eval_data = json.load(f)
        
        avg_metrics = eval_data.get('average_metrics', {})
        
        # Metrics display
        st.subheader("Overall Performance")
        
        eval_col1, eval_col2, eval_col3, eval_col4, eval_col5 = st.columns(5)
        
        with eval_col1:
            st.metric("Recall@5", f"{avg_metrics.get('Recall@5', 0):.3f}")
        with eval_col2:
            st.metric("Recall@10", f"{avg_metrics.get('Recall@10', 0):.3f}")
        with eval_col3:
            st.metric("Precision@5", f"{avg_metrics.get('Precision@5', 0):.3f}")
        with eval_col4:
            st.metric("MRR", f"{avg_metrics.get('MRR', 0):.3f}")
        with eval_col5:
            st.metric("NDCG@10", f"{avg_metrics.get('NDCG@10', 0):.3f}")
        
        st.markdown("---")
        
        # Bar chart
        st.subheader("Metrics Visualization")
        
        metrics_df = pd.DataFrame({
            'Metric': list(avg_metrics.keys()),
            'Score': list(avg_metrics.values())
        })
        
        fig = go.Figure(data=[
            go.Bar(
                x=metrics_df['Metric'],
                y=metrics_df['Score'],
                marker_color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'],
                text=metrics_df['Score'].round(3),
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
        
        # Per-query performance
        st.subheader("Per-Query Performance")
        
        per_query = eval_data.get('per_query', [])
        
        if per_query:
            query_data = []
            for item in per_query:
                query_data.append({
                    'Query': item['query'],
                    'Recall@5': round(item['metrics']['Recall@5'], 3),
                    'Precision@5': round(item['metrics']['Precision@5'], 3),
                    'MRR': round(item['metrics']['MRR'], 3),
                    'NDCG@10': round(item['metrics']['NDCG@10'], 3)
                })
            
            df_queries = pd.DataFrame(query_data)
            
            st.dataframe(
                df_queries.style.background_gradient(
                    cmap='RdYlGn',
                    subset=['Recall@5', 'Precision@5', 'MRR', 'NDCG@10']
                ),
                use_container_width=True,
                hide_index=True
            )
    
    except FileNotFoundError:
        st.warning("📁 No evaluation results found")
        st.info("Run evaluation:\n```bash\npython Testing/evaluate_system.py\n```")
    except Exception as e:
        st.error(f"Error: {e}")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("Dashboard Controls")
    
    st.markdown("---")
    
    st.subheader("Quick Stats")
    
    df = load_queries()
    if not df.empty:
        st.metric("Total Queries", len(df))
        st.metric("Avg Response", f"{df['response_time'].mean():.2f}s")
        st.metric("Cache Rate", f"{(df['cached'].sum() / len(df))*100:.0f}%")
    
    st.markdown("---")
    
    st.info("""
    **Features:**
    - Real-time metrics
    - Latency tracking
    - Query analytics
    - Cache monitoring
    - Evaluation results
    """)
