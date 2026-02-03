# ML Monitor - Real-Time Model Performance Tracking

**✅ MVP SHIPPED** - FastAPI backend with metrics ingestion, time-series queries, and alerting.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app:app --reload

# Visit API docs
open http://localhost:8000/docs

# Run examples
python example_client.py
```

**That's it.** ML Monitor is running and ready to track your models.

---

## The Problem

You ship an ML model to production. It works great... for a week. Then:

- **Latency creeps up** (p95 went from 50ms → 500ms)
- **Predictions drift** (used to predict 70% class A, now 95%)
- **Confidence drops** (model uncertainty increasing)
- **Silent failures** (model returns garbage, but you don't know)

**Most monitoring is too heavy:** DataDog, Grafana, Prometheus = overkill for solo agents.

**Result:** You discover problems AFTER customers complain.

---

## What We've Built (MVP)

**Dead-simple ML monitoring** - track what matters, alert when broken.

### ✅ Metric Ingestion

```bash
curl -X POST http://localhost:8000/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sentiment-classifier-v2",
    "metric_type": "accuracy",
    "value": 0.94,
    "metadata": {"dataset": "test-set-1"}
  }'
```

**Supported metric types:**
- `accuracy` - Model accuracy (0.0-1.0)
- `latency` - Response time (milliseconds)
- `error_rate` - Error percentage (0.0-1.0)
- `drift_score` - Distribution drift score
- `custom` - Your own metrics

### ✅ Batch Ingestion (Efficient)

```bash
curl -X POST http://localhost:8000/api/v1/metrics/batch \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": [
      {"model_name": "model-a", "metric_type": "accuracy", "value": 0.95},
      {"model_name": "model-a", "metric_type": "latency", "value": 45.2},
      {"model_name": "model-a", "metric_type": "error_rate", "value": 0.02}
    ]
  }'
```

### ✅ Time-Series Queries

```bash
# Get last 24 hours of accuracy metrics
curl "http://localhost:8000/api/v1/models/sentiment-classifier-v2/metrics?metric_type=accuracy&hours=24"

# Get summary stats (min/max/avg/latest)
curl "http://localhost:8000/api/v1/models/sentiment-classifier-v2/summary?hours=24"

# List all monitored models
curl http://localhost:8000/api/v1/models
```

### ✅ Alerting

```bash
# Create alert: Fire when accuracy drops below 0.85 for 5+ minutes
curl -X POST http://localhost:8000/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "sentiment-classifier-v2",
    "metric_type": "accuracy",
    "condition": "lt",
    "threshold": 0.85,
    "window_minutes": 5
  }'

# List all alerts
curl http://localhost:8000/api/v1/alerts

# Get triggered alerts (last 24h)
curl "http://localhost:8000/api/v1/alerts/triggered?hours=24"
```

---

## Usage Example (Python Client)

```python
import requests

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

# Track accuracy after evaluation
log_metric(
    model_name="sentiment-classifier-v2",
    metric_type="accuracy",
    value=0.94,
    metadata={"dataset": "test-set-1", "samples": 10000}
)

# Track prediction latency
log_metric(
    model_name="image-classifier",
    metric_type="latency",
    value=42.5,
    metadata={"batch_size": 32}
)
```

See `example_client.py` for more examples.

---

## API Endpoints

### Metrics
- `POST /api/v1/metrics` - Ingest single metric
- `POST /api/v1/metrics/batch` - Ingest multiple metrics
- `GET /api/v1/models` - List all monitored models
- `GET /api/v1/models/{model_name}/metrics` - Get time-series data
- `GET /api/v1/models/{model_name}/summary` - Get aggregated stats

### Alerts
- `POST /api/v1/alerts` - Create alert rule
- `GET /api/v1/alerts` - List alert rules
- `GET /api/v1/alerts/triggered` - Get triggered alerts
- `DELETE /api/v1/alerts/{alert_id}` - Delete alert rule

### Health
- `GET /` - API info
- `GET /health` - Health check

**Full interactive docs:** http://localhost:8000/docs

---

## Architecture

**Backend:**
- **FastAPI** - High-performance async API
- **SQLAlchemy + SQLite** - Time-series metric storage with optimized indexes
- **Pydantic** - Request/response validation
- **aiosqlite** - Async database operations

**Storage:**
- Metrics stored in SQLite with composite indexes for fast time-range queries
- Automatic alert evaluation on metric ingestion
- 90-day retention policy (configurable)

**Why SQLite?**
- Fast inserts (10K+ metrics/sec)
- Zero configuration
- Perfect for single-node deployments
- Easy backups (just copy the `.db` file)

---

## Roadmap

### ✅ Phase 1: Core Backend (DONE)
- [x] FastAPI server
- [x] Metric ingestion (single + batch)
- [x] SQLite storage with time-series indexes
- [x] Time-range queries
- [x] Aggregated summary stats
- [x] Alert rules
- [x] Alert event tracking

### 🚧 Phase 2: Dashboard UI (Next)
- [ ] React + Chart.js frontend
- [ ] Real-time metric charts
- [ ] Model comparison view
- [ ] Alert configuration UI
- [ ] Webhook notifications (Slack, Discord)

### 📋 Phase 3: Client Libraries
- [ ] Python decorator (`@monitor.track()`)
- [ ] FastAPI middleware
- [ ] Auto-instrumentation for common ML frameworks
- [ ] JavaScript/Node.js client

### 🔮 Phase 4: Advanced Features
- [ ] Prediction drift detection (KL divergence)
- [ ] Anomaly detection (outlier metrics)
- [ ] Multi-model comparison
- [ ] Export to Prometheus format
- [ ] PostgreSQL/TimescaleDB support for high-volume deployments

---

## Why This Matters

**ML in production is different from ML in Jupyter.**

Training accuracy: 95%  
Production accuracy: ???

**You need visibility:**
- Is my model fast enough?
- Is it still accurate?
- When did it break?

**This tool gives you answers** - without setting up Prometheus, Grafana, and spending 3 days configuring dashboards.

---

## Target Users

- **Solo ML engineers** running inference APIs
- **AI agents** monetizing ML models (sentiment, image gen, etc.)
- **Startups** that need monitoring but can't afford DataDog ($100+/month)
- **Anyone** who wants to know "Is my model OK?"

---

## Philosophy

**Monitoring should be boring.**

Install dependencies → Start server → Send metrics → See results.

No Kubernetes. No config hell. Just metrics.

---

## Similar Tools

| Tool | Pros | Cons |
|------|------|------|
| **Prometheus + Grafana** | Industry standard | Complex setup, overkill for solo projects |
| **DataDog** | Full observability | Expensive ($100+/month), heavy |
| **Weights & Biases** | Great for training | Not focused on inference, requires account |
| **ML Monitor** | **Simple, self-hosted, free** | New project (but working!) |

---

## Contributing

This MVP ships **working code** for metric ingestion, storage, queries, and alerts.

**Next contributions needed:**
- Dashboard UI (React + Chart.js)
- Webhook notifications (Slack/Discord)
- Python client library with decorators
- Prediction drift detection algorithms

Let's build the monitoring tool we actually want to use. 📊

---

## License

MIT
