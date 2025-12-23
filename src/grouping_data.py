import polars as pl

def clean_types(df: pl.DataFrame) -> pl.DataFrame:
    """
    Convert numeric and boolean-like fields to proper dtypes.
    Preprocessed CSV stores everything as strings, so we fix them here.
    """
    return df.with_columns([
        pl.col("rating").cast(pl.Float64),
        pl.col("helpful_votes").cast(pl.Int64),
        pl.col("review_timestamp").cast(pl.Int64),
        pl.col("review_count").cast(pl.Int64),

        pl.col("is_verified")
            .str.replace("True", "1")
            .str.replace("False", "0")
            .cast(pl.Int64)
    ])


def group_reviews_by_product(df: pl.DataFrame) -> pl.DataFrame:
    """
    Group reviews by product_id to prepare data for:
    - Abstractive Summarization
    - Aspect-based Summarization
    - Sentiment Analysis
    - Embedding + Recommendation
    """
    grouped = (
        df
        .group_by("product_id")
        .agg([
            pl.col("cleaned_review").str.concat("\n ").alias("all_reviews"),
            pl.col("user_summary").str.concat("\n ").alias("all_user_summaries"),

            pl.col("rating").mean().alias("avg_rating"),
            pl.col("rating").count().alias("review_count"),
            pl.col("helpful_votes").sum().alias("total_helpful_votes"),

            pl.col("product_style")
                .drop_nulls()
                .mode()
                .first()
                .alias("dominant_style"),

            pl.col("review_timestamp").min().alias("oldest_review_timestamp"),
            pl.col("review_timestamp").max().alias("newest_review_timestamp"),
        ])
    )

    return grouped
