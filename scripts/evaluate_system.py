import sys
import os
sys.path.append(os.path.abspath("."))
                
from models.hybrid_search_engine import HybridSearchEngine
from models.evaluation_metrics import Evaluator
from data.evaluation_queries import EVALUATION_QUERIES
import numpy as np

print("SYSTEM EVALUATION")

# Initialize
print("\nInitializing search engine")
engine = HybridSearchEngine()
evaluator = Evaluator()

# Collect metrics
all_metrics = {
    "Recall@5": [],
    "Recall@10": [],
    "Precision@5": [],
    "MRR": [],
    "NDCG@10": []
}

print(f"\nEvaluating on {len(EVALUATION_QUERIES)} test queries\n")

# Evaluate each query
for i, test in enumerate(EVALUATION_QUERIES, 1):
    query = test['query']
    ground_truth = test['ground_truth']
    
    # Skip if no ground truth
    if not ground_truth:
        print(f"  Skipping query {i}: No ground truth labels")
        continue
    
    print(f"{i}. Query: {query}")
    
    # Get predictions
    results = engine.hybrid_search(query, top_k=10, alpha=0.65)
    predictions = [r['product_id'] for r in results]
    
    # Evaluate
    scores = evaluator.evaluate(ground_truth, predictions)
    
    # Display
    print(f"   Recall@5: {scores['Recall@5']:.3f} | "
          f"Precision@5: {scores['Precision@5']:.3f} | "
          f"MRR: {scores['MRR']:.3f} | "
          f"NDCG@10: {scores['NDCG@10']:.3f}")
    
    # Collect
    for metric, value in scores.items():
        all_metrics[metric].append(value)

# Calculate averages
print("AVERAGE METRICS (Across All Queries)")

for metric, values in all_metrics.items():
    if values:
        avg = np.mean(values)
        std = np.std(values)
        print(f"{metric:15s}: {avg:.4f} ± {std:.4f}")

# Save results
import json
with open("evaluation_results.json", "w") as f:
    json.dump({
        'average_metrics': {k: float(np.mean(v)) for k, v in all_metrics.items()},
        'per_query': [
            {
                'query': test['query'],
                'metrics': evaluator.evaluate(
                    test['ground_truth'],
                    [r['product_id'] for r in engine.hybrid_search(test['query'], 10, 0.65)]
                )
            }
            for test in EVALUATION_QUERIES if test['ground_truth']
        ]
    }, f, indent=2)

print("\nResults saved to evaluation_results.json")