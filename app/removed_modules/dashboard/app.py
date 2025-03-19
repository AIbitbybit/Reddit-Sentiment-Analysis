"""
Streamlit dashboard for visualizing sentiment analysis results.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from reddit_sentiment_analysis.config import (
    BUSINESS_ASPECTS,
    DASHBOARD_DESCRIPTION,
    DASHBOARD_TITLE,
    DEFAULT_SUBREDDITS,
)
from reddit_sentiment_analysis.data_collection.collector import DataCollector
from reddit_sentiment_analysis.preprocessing.text_processor import TextProcessor
from reddit_sentiment_analysis.storage.vector_store import SentimentVectorStore
from reddit_sentiment_analysis.workflows.sentiment_workflow import (
    run_sentiment_workflow,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize vector store
vector_store = SentimentVectorStore()

# Set page config
st.set_page_config(
    page_title=DASHBOARD_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dashboard title
st.title(DASHBOARD_TITLE)
st.markdown(DASHBOARD_DESCRIPTION)

# Sidebar
st.sidebar.title("Controls")

# Settings link in sidebar
st.sidebar.header("Application Settings")
st.sidebar.info(
    "To configure API keys, email settings, and other options, please use the Settings tab in the main GUI. "
    "You can access it by running the monitoring GUI with `python run_app.py`."
)

# Data collection section in sidebar
st.sidebar.header("Data Collection")
with st.sidebar.expander("Collect New Data", expanded=False):
    subreddit_options = DEFAULT_SUBREDDITS + ["all"]
    selected_subreddits = st.multiselect(
        "Select subreddits",
        options=subreddit_options,
        default=["business", "smallbusiness"],
    )

    time_filter = st.selectbox(
        "Time filter",
        options=["hour", "day", "week", "month", "year", "all"],
        index=2,  # Default to "week"
    )

    post_limit = st.slider(
        "Maximum posts per subreddit", min_value=5, max_value=100, value=20, step=5
    )

    filter_business = st.checkbox("Filter for business content", value=True)

    if st.button("Collect and Analyze Data"):
        with st.spinner("Collecting data from Reddit..."):
            try:
                # Create data collector
                collector = DataCollector(output_dir="data/raw")

                # Collect data
                posts = collector.collect_data(
                    subreddits=selected_subreddits,
                    time_filter=time_filter,
                    limit=post_limit,
                    filter_business=filter_business,
                )

                st.success(f"Collected {len(posts)} posts from Reddit")

                # Preprocess data
                text_processor = TextProcessor()
                processed_posts = text_processor.preprocess_posts(posts)

                # Analyze sentiment
                with st.spinner("Analyzing sentiment..."):
                    results = []
                    for post in processed_posts:
                        # Run async function in sync context
                        result = asyncio.run(run_sentiment_workflow(post))
                        results.append(result)

                    # Store results
                    doc_ids = vector_store.add_results(results)

                    st.success(f"Analyzed and stored {len(results)} posts")
            except Exception as e:
                st.error(f"Error collecting and analyzing data: {str(e)}")
                logger.error(f"Error in data collection: {str(e)}")

# Search section in sidebar
st.sidebar.header("Search")
with st.sidebar.expander("Search Results", expanded=False):
    search_query = st.text_input("Search query")
    sentiment_filter = st.selectbox(
        "Filter by sentiment",
        options=["All", "Positive", "Negative", "Neutral"],
        index=0,
    )

    if st.button("Search"):
        with st.spinner("Searching..."):
            try:
                # Prepare filter
                filter_metadata = None
                if sentiment_filter != "All":
                    filter_metadata = {"overall_sentiment": sentiment_filter.lower()}

                # Search vector store
                search_results = vector_store.search(
                    query=search_query, filter_metadata=filter_metadata, limit=20
                )

                if search_results:
                    st.session_state.search_results = search_results
                    st.success(f"Found {len(search_results)} results")
                else:
                    st.warning("No results found")
            except Exception as e:
                st.error(f"Error searching: {str(e)}")
                logger.error(f"Error in search: {str(e)}")

# Main content
tab1, tab2, tab3 = st.tabs(["Overview", "Sentiment Analysis", "Aspect Analysis"])

with tab1:
    st.header("Sentiment Overview")

    # Get sentiment distribution
    sentiment_counts = vector_store.get_sentiment_distribution()

    if sum(sentiment_counts.values()) > 0:
        # Create sentiment distribution chart
        fig = px.pie(
            names=list(sentiment_counts.keys()),
            values=list(sentiment_counts.values()),
            title="Sentiment Distribution",
            color=list(sentiment_counts.keys()),
            color_discrete_map={
                "positive": "#4CAF50",
                "negative": "#F44336",
                "neutral": "#9E9E9E",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        # Create sentiment counts table
        sentiment_df = pd.DataFrame(
            {
                "Sentiment": list(sentiment_counts.keys()),
                "Count": list(sentiment_counts.values()),
            }
        )
        st.dataframe(sentiment_df, use_container_width=True)
    else:
        st.info("No sentiment data available. Please collect and analyze data first.")

    # Recent results
    st.subheader("Recent Analysis Results")

    # Get positive and negative results
    positive_results = vector_store.filter_by_sentiment("positive", limit=5)
    negative_results = vector_store.filter_by_sentiment("negative", limit=5)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Top Positive Mentions")
        if positive_results:
            for result in positive_results:
                with st.expander(
                    f"{result['metadata'].get('subreddit', 'Unknown')} - {result['id']}"
                ):
                    st.markdown(
                        f"**Sentiment:** {result['metadata'].get('overall_sentiment', 'Unknown')}"
                    )
                    st.markdown(
                        f"**Confidence:** {result['metadata'].get('overall_confidence', 0):.2f}"
                    )
                    st.markdown(f"**Document:**\n{result['document']}")
        else:
            st.info("No positive results available")

    with col2:
        st.markdown("### Top Negative Mentions")
        if negative_results:
            for result in negative_results:
                with st.expander(
                    f"{result['metadata'].get('subreddit', 'Unknown')} - {result['id']}"
                ):
                    st.markdown(
                        f"**Sentiment:** {result['metadata'].get('overall_sentiment', 'Unknown')}"
                    )
                    st.markdown(
                        f"**Confidence:** {result['metadata'].get('overall_confidence', 0):.2f}"
                    )
                    st.markdown(f"**Document:**\n{result['document']}")
        else:
            st.info("No negative results available")

with tab2:
    st.header("Sentiment Analysis Details")

    # Get all results for analysis
    all_results = []
    for sentiment in ["positive", "negative", "neutral"]:
        sentiment_results = vector_store.filter_by_sentiment(sentiment, limit=100)
        all_results.extend(sentiment_results)

    if all_results:
        # Create dataframe
        results_data = []
        for result in all_results:
            results_data.append(
                {
                    "id": result["id"],
                    "subreddit": result["metadata"].get("subreddit", "Unknown"),
                    "sentiment": result["metadata"].get("overall_sentiment", "Unknown"),
                    "confidence": result["metadata"].get("overall_confidence", 0),
                    "has_comments": result["metadata"].get("has_comments", False),
                    "comment_count": result["metadata"].get("comment_count", 0),
                }
            )

        results_df = pd.DataFrame(results_data)

        # Sentiment by subreddit
        if "subreddit" in results_df.columns:
            st.subheader("Sentiment by Subreddit")

            # Group by subreddit and sentiment
            subreddit_sentiment = (
                results_df.groupby(["subreddit", "sentiment"])
                .size()
                .reset_index(name="count")
            )

            # Create grouped bar chart
            fig = px.bar(
                subreddit_sentiment,
                x="subreddit",
                y="count",
                color="sentiment",
                title="Sentiment Distribution by Subreddit",
                color_discrete_map={
                    "positive": "#4CAF50",
                    "negative": "#F44336",
                    "neutral": "#9E9E9E",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        # Confidence distribution
        if "confidence" in results_df.columns:
            st.subheader("Confidence Distribution")

            fig = px.histogram(
                results_df,
                x="confidence",
                color="sentiment",
                nbins=20,
                title="Confidence Score Distribution",
                color_discrete_map={
                    "positive": "#4CAF50",
                    "negative": "#F44336",
                    "neutral": "#9E9E9E",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        # Raw data table
        st.subheader("Raw Data")
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No sentiment data available. Please collect and analyze data first.")

with tab3:
    st.header("Aspect-Based Sentiment Analysis")

    # Get all results for aspect analysis
    all_results = []
    for sentiment in ["positive", "negative", "neutral"]:
        sentiment_results = vector_store.filter_by_sentiment(sentiment, limit=100)
        all_results.extend(sentiment_results)

    if all_results:
        # Extract aspect sentiments from documents
        aspect_data = []

        for result in all_results:
            document = result["document"]

            # Extract aspect sentiments from document text
            lines = document.split("\n")
            aspect_section_started = False

            for line in lines:
                if line.startswith("Aspect Sentiments:"):
                    aspect_section_started = True
                    continue

                if aspect_section_started and ":" in line:
                    try:
                        aspect_part = line.split(":", 1)[0].strip()
                        sentiment_part = line.split(":", 1)[1].split("-")[0].strip()

                        aspect_data.append(
                            {
                                "post_id": result["id"],
                                "subreddit": result["metadata"].get(
                                    "subreddit", "Unknown"
                                ),
                                "aspect": aspect_part,
                                "sentiment": sentiment_part,
                            }
                        )
                    except:
                        pass

        if aspect_data:
            aspect_df = pd.DataFrame(aspect_data)

            # Aspect sentiment distribution
            st.subheader("Aspect Sentiment Distribution")

            # Group by aspect and sentiment
            aspect_sentiment = (
                aspect_df.groupby(["aspect", "sentiment"])
                .size()
                .reset_index(name="count")
            )

            # Create grouped bar chart
            fig = px.bar(
                aspect_sentiment,
                x="aspect",
                y="count",
                color="sentiment",
                title="Sentiment Distribution by Business Aspect",
                color_discrete_map={
                    "positive": "#4CAF50",
                    "negative": "#F44336",
                    "neutral": "#9E9E9E",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

            # Aspect sentiment heatmap
            st.subheader("Aspect Sentiment Heatmap")

            # Pivot table for heatmap
            heatmap_data = aspect_df.pivot_table(
                index="aspect",
                columns="sentiment",
                values="post_id",
                aggfunc="count",
                fill_value=0,
            )

            # Create heatmap
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Sentiment", y="Aspect", color="Count"),
                x=heatmap_data.columns,
                y=heatmap_data.index,
                color_continuous_scale="RdYlGn",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Raw aspect data
            st.subheader("Raw Aspect Data")
            st.dataframe(aspect_df, use_container_width=True)
        else:
            st.info("No aspect sentiment data available in the analyzed posts.")
    else:
        st.info("No sentiment data available. Please collect and analyze data first.")

# Search results display
if "search_results" in st.session_state and st.session_state.search_results:
    st.header("Search Results")

    for result in st.session_state.search_results:
        with st.expander(
            f"{result['metadata'].get('subreddit', 'Unknown')} - {result['id']}"
        ):
            st.markdown(
                f"**Sentiment:** {result['metadata'].get('overall_sentiment', 'Unknown')}"
            )
            st.markdown(
                f"**Confidence:** {result['metadata'].get('overall_confidence', 0):.2f}"
            )
            st.markdown(f"**Document:**\n{result['document']}")
            if result.get("distance") is not None:
                st.markdown(f"**Relevance Score:** {1 - result['distance']:.4f}")

# Footer
st.markdown("---")
st.markdown("Reddit Sentiment Analysis Dashboard | Powered by LangChain & LangGraph")


def run_gui():
    """Run the dashboard GUI directly using streamlit."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    # Get the path to this file
    dashboard_path = Path(__file__).absolute()

    # Check if streamlit is available
    try:
        import streamlit

        # Run this file with streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_path)]
        subprocess.run(cmd)
    except ImportError:
        print(
            "Streamlit is not installed. Please install it with: pip install streamlit"
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error running dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # This will be executed when the file is run directly
    pass  # The Streamlit server will handle execution
