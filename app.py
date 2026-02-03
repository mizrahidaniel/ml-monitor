"""
ML Monitor - Real-Time Model Performance Tracking
FastAPI backend for ingesting and querying ML metrics
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from database import Database, MetricType

app = FastAPI(
    title="ML Monitor",
    description="Real-time ML model performance tracking API",
    version="0.1.0"
)

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class MetricIngestion(BaseModel):
    """Single metric data point"""
    model_name: str = Field(..., description="Unique model identifier")
    metric_type: str = Field(..., description="accuracy|latency|error_rate|drift_score|custom")
    value: float = Field(..., description="Metric value")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    timestamp: Optional[datetime] = Field(default=None, description="Metric timestamp (defaults to now)")

class BatchIngestion(BaseModel):
    """Batch metric ingestion"""
    metrics: List[MetricIngestion]

class AlertRule(BaseModel):
    """Alert configuration"""
    model_name: str
    metric_type: str
    condition: str = Field(..., description="gt|lt|eq - greater than, less than, equals")
    threshold: float
    window_minutes: int = Field(default=5, description="Time window for alert evaluation")
    enabled: bool = True

# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize database"""
    await db.init()

@app.on_event("shutdown")
async def shutdown():
    """Close database"""
    await db.close()

# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/")
def root():
    """API info"""
    return {
        "service": "ML Monitor",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy"}

# ============================================================================
# METRIC INGESTION
# ============================================================================

@app.post("/api/v1/metrics")
async def ingest_metric(metric: MetricIngestion):
    """
    Ingest a single metric data point
    
    Example:
    ```json
    {
      "model_name": "sentiment-classifier-v2",
      "metric_type": "accuracy",
      "value": 0.94,
      "metadata": {"dataset": "test-set-1", "version": "v2.1"}
    }
    ```
    """
    try:
        metric_type = MetricType[metric.metric_type.upper()]
    except KeyError:
        # Allow custom metrics
        metric_type = MetricType.CUSTOM
    
    timestamp = metric.timestamp or datetime.utcnow()
    
    await db.insert_metric(
        model_name=metric.model_name,
        metric_type=metric_type,
        value=metric.value,
        metadata=metric.metadata,
        timestamp=timestamp
    )
    
    return {
        "success": True,
        "model": metric.model_name,
        "metric": metric.metric_type,
        "value": metric.value,
        "timestamp": timestamp.isoformat()
    }

@app.post("/api/v1/metrics/batch")
async def ingest_batch(batch: BatchIngestion):
    """
    Ingest multiple metrics at once (more efficient)
    
    Example:
    ```json
    {
      "metrics": [
        {"model_name": "model-a", "metric_type": "accuracy", "value": 0.95},
        {"model_name": "model-a", "metric_type": "latency", "value": 45.2}
      ]
    }
    ```
    """
    results = []
    for metric in batch.metrics:
        try:
            metric_type = MetricType[metric.metric_type.upper()]
        except KeyError:
            metric_type = MetricType.CUSTOM
        
        timestamp = metric.timestamp or datetime.utcnow()
        
        await db.insert_metric(
            model_name=metric.model_name,
            metric_type=metric_type,
            value=metric.value,
            metadata=metric.metadata,
            timestamp=timestamp
        )
        
        results.append({
            "model": metric.model_name,
            "metric": metric.metric_type,
            "value": metric.value
        })
    
    return {
        "success": True,
        "ingested": len(results),
        "results": results
    }

# ============================================================================
# METRIC QUERIES
# ============================================================================

@app.get("/api/v1/models")
async def list_models():
    """List all monitored models with recent stats"""
    models = await db.get_all_models()
    return {"models": models}

@app.get("/api/v1/models/{model_name}/metrics")
async def get_model_metrics(
    model_name: str,
    metric_type: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours (max 7 days)"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Max data points")
):
    """
    Get time-series metrics for a model
    
    Returns all metrics or filtered by metric_type over the specified time window
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    if metric_type:
        try:
            mt = MetricType[metric_type.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid metric_type: {metric_type}")
        metrics = await db.get_metrics(model_name, mt, since, limit)
    else:
        metrics = await db.get_all_metrics_for_model(model_name, since, limit)
    
    return {
        "model": model_name,
        "metric_type": metric_type,
        "window_hours": hours,
        "data_points": len(metrics),
        "metrics": metrics
    }

@app.get("/api/v1/models/{model_name}/summary")
async def get_model_summary(
    model_name: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """
    Get aggregated summary stats for a model
    
    Returns min/max/avg/latest for each metric type
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    summary = await db.get_model_summary(model_name, since)
    
    return {
        "model": model_name,
        "window_hours": hours,
        "summary": summary
    }

# ============================================================================
# ALERTS
# ============================================================================

@app.post("/api/v1/alerts")
async def create_alert(rule: AlertRule):
    """
    Create an alert rule
    
    Example:
    ```json
    {
      "model_name": "sentiment-classifier",
      "metric_type": "accuracy",
      "condition": "lt",
      "threshold": 0.85,
      "window_minutes": 5
    }
    ```
    
    This will fire when accuracy drops below 0.85 for 5+ minutes
    """
    alert_id = await db.create_alert_rule(
        model_name=rule.model_name,
        metric_type=rule.metric_type,
        condition=rule.condition,
        threshold=rule.threshold,
        window_minutes=rule.window_minutes,
        enabled=rule.enabled
    )
    
    return {
        "success": True,
        "alert_id": alert_id,
        "rule": rule.dict()
    }

@app.get("/api/v1/alerts")
async def list_alerts(model_name: Optional[str] = None):
    """List all alert rules (optionally filtered by model)"""
    alerts = await db.get_alert_rules(model_name)
    return {"alerts": alerts}

@app.get("/api/v1/alerts/triggered")
async def get_triggered_alerts(hours: int = Query(default=24, ge=1, le=168)):
    """Get recently triggered alerts"""
    since = datetime.utcnow() - timedelta(hours=hours)
    triggered = await db.get_triggered_alerts(since)
    
    return {
        "window_hours": hours,
        "triggered_alerts": triggered
    }

@app.delete("/api/v1/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    """Delete an alert rule"""
    await db.delete_alert_rule(alert_id)
    return {"success": True, "deleted": alert_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
