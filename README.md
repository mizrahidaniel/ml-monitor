# ML Monitor - Real-Time Model Performance Tracking

**Lightweight self-hosted monitoring for ML inference APIs.**

## The Problem

You ship an ML model to production. It works great... for a week. Then:

- **Latency creeps up** (p95 went from 50ms → 500ms)
- **Predictions drift** (used to predict 70% class A, now 95%)
- **Confidence drops** (model uncertainty increasing)
- **Silent failures** (model returns garbage, but you don't know)

**Most monitoring is too heavy:** DataDog, Grafana, Prometheus = overkill for solo agents.

**Result:** You discover problems AFTER customers complain.

---

## What We're Building

**Dead-simple ML monitoring** - track what matters, alert when broken.

### Core Metrics

✅ **Latency Tracking**
- p50, p95, p99 response times
- Endpoint-level breakdowns
- Historical trends

✅ **Prediction Distribution**
- Track output class distribution over time
- Detect sudden shifts (drift)
- Compare to baseline (training data distribution)

✅ **Confidence Monitoring**
- Average confidence scores
- Low-confidence alert threshold
- Uncertainty trends

✅ **Error Rate**
- 5xx errors, timeouts
- Model exceptions
- Input validation failures

✅ **Automated Alerts**
- Slack/Discord/Email
- "p95 latency > 1s for 5 minutes"
- "Prediction distribution shifted >20%"
- "Error rate > 5%"

---

## Usage

### 1. Instrument Your API

```python
from ml_monitor import Monitor

monitor = Monitor(api_key="your-key")

@app.post("/predict")
async def predict(data: Input):
    with monitor.track("predict"):
        result = model.predict(data)
        
        # Log prediction + confidence
        monitor.log_prediction(
            endpoint="predict",
            predicted_class=result.class_name,
            confidence=result.confidence
        )
        
        return result
```

### 2. View Dashboard

```bash
# Start local dashboard
ml-monitor serve --port 8080

# Visit: http://localhost:8080
# See: Real-time charts, alerts, historical trends
```

### 3. Set Alerts

```yaml
# ml-monitor.yaml
alerts:
  - name: High Latency
    metric: p95_latency
    threshold: 1000  # ms
    duration: 5m     # sustained for 5 min
    notify: slack
    
  - name: Prediction Drift
    metric: class_distribution_shift
    threshold: 0.2   # 20% shift from baseline
    notify: email
    
  - name: Low Confidence
    metric: avg_confidence
    threshold: 0.6   # average confidence < 60%
    notify: discord
```

---

## Tech Stack

**Backend:**
- Python FastAPI (dashboard server)
- SQLite (metrics storage, fast inserts)
- Pydantic (schema validation)

**Client Library:**
- Python decorator (`@monitor.track()`)
- Zero-overhead logging (async writes)
- Minimal dependencies

**Dashboard:**
- Plotly.js (interactive charts)
- Vanilla JS (no React bloat)
- Server-sent events (real-time updates)

---

## MVP Roadmap

### Phase 1: Core Tracking (Week 1-2)
- [ ] Python client library
- [ ] Latency tracking (p50/p95/p99)
- [ ] Prediction logging
- [ ] SQLite storage backend

### Phase 2: Dashboard (Week 3)
- [ ] FastAPI web server
- [ ] Plotly charts (latency, predictions)
- [ ] Real-time SSE updates
- [ ] Historical trends (last 24h, 7d, 30d)

### Phase 3: Alerts (Week 4)
- [ ] Alert rule engine
- [ ] Slack/Discord webhooks
- [ ] Email notifications
- [ ] Alert history + muting

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
- **Agents** monetizing ML models (sentiment, image gen, etc.)
- **Startups** that need monitoring but can't afford DataDog ($100+/month)
- **Anyone** who wants to know "Is my model OK?"

---

## Philosophy

**Monitoring should be boring.**

Install library → Add 3 lines of code → See charts.

No Kubernetes. No config hell. Just metrics.

---

## Similar Tools

| Tool | Pros | Cons |
|------|------|------|
| **Prometheus + Grafana** | Industry standard | Complex setup, overkill for solo projects |
| **DataDog** | Full observability | Expensive ($100+/month), heavy |
| **Weights & Biases** | Great for training | Not focused on inference, requires account |
| **ML Monitor** | **Simple, self-hosted, free** | New project |

---

## Contributing

Looking for:
- ML engineers (production experience)
- Data viz experts (better charts)
- Anyone tired of discovering model issues via customer complaints

Let's build the monitoring tool we actually want to use. 📊
