import numpy as np

def recall_at_k(ground_truth, predictions, k):
    """
    Recall@K = fraction of relevant items retrieved in top K
    
    ground_truth: set or list of relevant product_ids
    predictions: list of predicted product_ids (rank-ordered)
    """
    ground_truth = set(ground_truth)
    top_k = predictions[:k]
    
    hits = len([p for p in top_k if p in ground_truth])
    return hits / len(ground_truth) if len(ground_truth) > 0 else 0.0


def precision_at_k(ground_truth, predictions, k):
    """
    Precision@K = fraction of retrieved items in top K that are relevant
    """
    ground_truth = set(ground_truth)
    top_k = predictions[:k]
    
    hits = len([p for p in top_k if p in ground_truth])
    return hits / k


def mrr(ground_truth, predictions):
    """
    Mean Reciprocal Rank:
    1/rank of first relevant item in predictions
    """
    ground_truth = set(ground_truth)
    
    for rank, p in enumerate(predictions, start=1):
        if p in ground_truth:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ground_truth, predictions, k):
    """
    Normalized Discounted Cumulative Gain@K
    
    Rank relevant items higher → higher score.
    """
    ground_truth = set(ground_truth)

    def dcg(items):
        score = 0.0
        for idx, item in enumerate(items):
            if item in ground_truth:
                score += 1 / np.log2(idx + 2)  # log2(rank + 1)
        return score

    ideal_order = list(ground_truth)[:k]
    
    dcg_k = dcg(predictions[:k])
    idcg_k = dcg(ideal_order)

    return dcg_k / idcg_k if idcg_k > 0 else 0.0


class Evaluator:
    """
    General evaluation wrapper.
    Pass predictions + ground truth and compute all metrics.
    """
    def __init__(self):
        pass

    def evaluate(self, ground_truth, predictions):
        """
        ground_truth: list or set of true relevant product_ids
        predictions: ordered list of predicted product_ids
        """
        return {
            "Recall@5": recall_at_k(ground_truth, predictions, 5),
            "Recall@10": recall_at_k(ground_truth, predictions, 10),
            "Precision@5": precision_at_k(ground_truth, predictions, 5),
            "MRR": mrr(ground_truth, predictions),
            "NDCG@10": ndcg_at_k(ground_truth, predictions, 10),
        }
