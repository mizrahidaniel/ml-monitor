"""
Example: How to send metrics to ML Monitor from your ML service
"""
import requests
from datetime import datetime
import time
import random

# Your ML Monitor instance
API_URL = "http://localhost:8000"

def log_metric(model_name: str, metric_type: str, value: float, metadata=None):
    """Send a single metric to ML Monitor"""
    response = requests.post(
        f"{API_URL}/api/v1/metrics",
        json={
            "model_name": model_name,
            "metric_type": metric_type,
            "value": value,
            "metadata": metadata
        }
    )
    return response.json()

def log_metrics_batch(metrics: list):
    """Send multiple metrics at once (more efficient)"""
    response = requests.post(
        f"{API_URL}/api/v1/metrics/batch",
        json={"metrics": metrics}
    )
    return response.json()

# ============================================================================
# EXAMPLE 1: Simple accuracy tracking
# ============================================================================

def example_accuracy_tracking():
    """Track model accuracy after each evaluation"""
    print("Example 1: Accuracy tracking")
    
    result = log_metric(
        model_name="sentiment-classifier-v2",
        metric_type="accuracy",
        value=0.94,
        metadata={
            "dataset": "test-set-1",
            "version": "v2.1",
            "samples": 10000
        }
    )
    print(f"  Logged: {result}")

# ============================================================================
# EXAMPLE 2: Latency monitoring
# ============================================================================

def example_latency_monitoring():
    """Track prediction latency"""
    print("\nExample 2: Latency monitoring")
    
    # Simulate some predictions with varying latency
    for i in range(5):
        latency_ms = random.uniform(20, 100)
        result = log_metric(
            model_name="image-classifier",
            metric_type="latency",
            value=latency_ms,
            metadata={"batch_size": 32}
        )
        print(f"  Request {i+1}: {latency_ms:.1f}ms")
        time.sleep(0.5)

# ============================================================================
# EXAMPLE 3: Batch ingestion
# ============================================================================

def example_batch_ingestion():
    """Send multiple metrics at once"""
    print("\nExample 3: Batch ingestion")
    
    metrics = [
        {
            "model_name": "recommendation-engine",
            "metric_type": "accuracy",
            "value": 0.87
        },
        {
            "model_name": "recommendation-engine",
            "metric_type": "latency",
            "value": 42.5
        },
        {
            "model_name": "recommendation-engine",
            "metric_type": "error_rate",
            "value": 0.03
        }
    ]
    
    result = log_metrics_batch(metrics)
    print(f"  Ingested {result['ingested']} metrics")

# ============================================================================
# EXAMPLE 4: Create alert
# ============================================================================

def example_create_alert():
    """Set up an alert for low accuracy"""
    print("\nExample 4: Create alert")
    
    response = requests.post(
        f"{API_URL}/api/v1/alerts",
        json={
            "model_name": "sentiment-classifier-v2",
            "metric_type": "accuracy",
            "condition": "lt",  # less than
            "threshold": 0.85,
            "window_minutes": 5
        }
    )
    result = response.json()
    print(f"  Alert created: ID {result['alert_id']}")
    print(f"  Will fire when accuracy < 0.85 for 5+ minutes")

# ============================================================================
# EXAMPLE 5: Query metrics
# ============================================================================

def example_query_metrics():
    """Retrieve recent metrics"""
    print("\nExample 5: Query metrics")
    
    # Get all models
    response = requests.get(f"{API_URL}/api/v1/models")
    models = response.json()["models"]
    print(f"  Monitored models: {len(models)}")
    
    if models:
        model = models[0]
        print(f"\n  Model: {model['name']}")
        
        # Get summary stats
        response = requests.get(
            f"{API_URL}/api/v1/models/{model['name']}/summary",
            params={"hours": 24}
        )
        summary = response.json()["summary"]
        
        for metric_type, stats in summary.items():
            print(f"    {metric_type}:")
            print(f"      Latest: {stats['latest']}")
            print(f"      Avg: {stats['avg']}")
            print(f"      Min/Max: {stats['min']} / {stats['max']}")

# ============================================================================
# RUN EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ML Monitor - Example Client")
    print("=" * 60)
    
    try:
        # Check if server is running
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print("ERROR: ML Monitor server not running!")
            print("Start it with: uvicorn app:app --reload")
            exit(1)
        
        # Run examples
        example_accuracy_tracking()
        example_latency_monitoring()
        example_batch_ingestion()
        example_create_alert()
        
        time.sleep(1)  # Let metrics settle
        
        example_query_metrics()
        
        print("\n" + "=" * 60)
        print("✅ All examples complete!")
        print("View dashboard at: http://localhost:8000/docs")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to ML Monitor")
        print("Make sure the server is running:")
        print("  uvicorn app:app --reload")
