"""
Database layer - SQLite with time-series optimizations
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import json

DATABASE_URL = "sqlite+aiosqlite:///./ml_monitor.db"

Base = declarative_base()

class MetricType(Enum):
    """Supported metric types"""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    DRIFT_SCORE = "drift_score"
    CUSTOM = "custom"

# ============================================================================
# MODELS
# ============================================================================

class Metric(Base):
    """Time-series metric storage"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for efficient time-range queries
    __table_args__ = (
        Index('idx_model_metric_time', 'model_name', 'metric_type', 'timestamp'),
    )

class AlertRule(Base):
    """Alert configuration"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)
    condition = Column(String(10), nullable=False)  # gt, lt, eq
    threshold = Column(Float, nullable=False)
    window_minutes = Column(Integer, default=5)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertEvent(Base):
    """Triggered alert history"""
    __tablename__ = "alert_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String(255), nullable=False)
    metric_type = Column(String(50), nullable=False)
    condition = Column(String(10), nullable=False)
    threshold = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)

# ============================================================================
# DATABASE CLASS
# ============================================================================

class Database:
    """Async database interface"""
    
    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init(self):
        """Create tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Close engine"""
        await self.engine.dispose()
    
    # ========================================================================
    # METRIC OPERATIONS
    # ========================================================================
    
    async def insert_metric(
        self,
        model_name: str,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Insert a metric data point"""
        async with self.SessionLocal() as session:
            metric = Metric(
                model_name=model_name,
                metric_type=metric_type.value,
                value=value,
                metadata_json=json.dumps(metadata) if metadata else None,
                timestamp=timestamp or datetime.utcnow()
            )
            session.add(metric)
            await session.commit()
            
            # Check if this triggers any alerts
            await self._check_alerts(session, model_name, metric_type, value, timestamp or datetime.utcnow())
    
    async def get_metrics(
        self,
        model_name: str,
        metric_type: MetricType,
        since: datetime,
        limit: int = 1000
    ) -> List[Dict]:
        """Get time-series metrics"""
        async with self.SessionLocal() as session:
            stmt = (
                select(Metric)
                .where(
                    and_(
                        Metric.model_name == model_name,
                        Metric.metric_type == metric_type.value,
                        Metric.timestamp >= since
                    )
                )
                .order_by(Metric.timestamp.desc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            metrics = result.scalars().all()
            
            return [
                {
                    "id": m.id,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else None
                }
                for m in reversed(metrics)  # Oldest first for charting
            ]
    
    async def get_all_metrics_for_model(
        self,
        model_name: str,
        since: datetime,
        limit: int = 1000
    ) -> List[Dict]:
        """Get all metric types for a model"""
        async with self.SessionLocal() as session:
            stmt = (
                select(Metric)
                .where(
                    and_(
                        Metric.model_name == model_name,
                        Metric.timestamp >= since
                    )
                )
                .order_by(Metric.timestamp.desc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            metrics = result.scalars().all()
            
            return [
                {
                    "id": m.id,
                    "metric_type": m.metric_type,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else None
                }
                for m in reversed(metrics)
            ]
    
    async def get_all_models(self) -> List[Dict]:
        """List all monitored models with latest metrics"""
        async with self.SessionLocal() as session:
            # Get distinct models
            stmt = select(Metric.model_name).distinct()
            result = await session.execute(stmt)
            model_names = [row[0] for row in result.all()]
            
            models = []
            for model_name in model_names:
                # Get latest metric for each type
                stmt = (
                    select(Metric)
                    .where(Metric.model_name == model_name)
                    .order_by(Metric.timestamp.desc())
                    .limit(10)
                )
                result = await session.execute(stmt)
                recent_metrics = result.scalars().all()
                
                latest = {}
                for m in recent_metrics:
                    if m.metric_type not in latest:
                        latest[m.metric_type] = {
                            "value": m.value,
                            "timestamp": m.timestamp.isoformat()
                        }
                
                models.append({
                    "name": model_name,
                    "latest_metrics": latest
                })
            
            return models
    
    async def get_model_summary(self, model_name: str, since: datetime) -> Dict[str, Dict]:
        """Get aggregated stats per metric type"""
        async with self.SessionLocal() as session:
            summary = {}
            
            for metric_type in MetricType:
                stmt = select(
                    func.min(Metric.value).label("min"),
                    func.max(Metric.value).label("max"),
                    func.avg(Metric.value).label("avg"),
                    func.count(Metric.id).label("count")
                ).where(
                    and_(
                        Metric.model_name == model_name,
                        Metric.metric_type == metric_type.value,
                        Metric.timestamp >= since
                    )
                )
                
                result = await session.execute(stmt)
                row = result.one_or_none()
                
                if row and row.count > 0:
                    # Get latest value
                    latest_stmt = (
                        select(Metric.value, Metric.timestamp)
                        .where(
                            and_(
                                Metric.model_name == model_name,
                                Metric.metric_type == metric_type.value
                            )
                        )
                        .order_by(Metric.timestamp.desc())
                        .limit(1)
                    )
                    latest_result = await session.execute(latest_stmt)
                    latest = latest_result.one_or_none()
                    
                    summary[metric_type.value] = {
                        "min": round(row.min, 4) if row.min is not None else None,
                        "max": round(row.max, 4) if row.max is not None else None,
                        "avg": round(row.avg, 4) if row.avg is not None else None,
                        "latest": round(latest[0], 4) if latest else None,
                        "latest_timestamp": latest[1].isoformat() if latest else None,
                        "data_points": row.count
                    }
            
            return summary
    
    # ========================================================================
    # ALERT OPERATIONS
    # ========================================================================
    
    async def create_alert_rule(
        self,
        model_name: str,
        metric_type: str,
        condition: str,
        threshold: float,
        window_minutes: int = 5,
        enabled: bool = True
    ) -> int:
        """Create an alert rule"""
        async with self.SessionLocal() as session:
            rule = AlertRule(
                model_name=model_name,
                metric_type=metric_type,
                condition=condition,
                threshold=threshold,
                window_minutes=window_minutes,
                enabled=enabled
            )
            session.add(rule)
            await session.commit()
            return rule.id
    
    async def get_alert_rules(self, model_name: Optional[str] = None) -> List[Dict]:
        """List alert rules"""
        async with self.SessionLocal() as session:
            stmt = select(AlertRule)
            if model_name:
                stmt = stmt.where(AlertRule.model_name == model_name)
            stmt = stmt.order_by(AlertRule.created_at.desc())
            
            result = await session.execute(stmt)
            rules = result.scalars().all()
            
            return [
                {
                    "id": r.id,
                    "model_name": r.model_name,
                    "metric_type": r.metric_type,
                    "condition": r.condition,
                    "threshold": r.threshold,
                    "window_minutes": r.window_minutes,
                    "enabled": r.enabled,
                    "created_at": r.created_at.isoformat()
                }
                for r in rules
            ]
    
    async def delete_alert_rule(self, alert_id: int):
        """Delete an alert rule"""
        async with self.SessionLocal() as session:
            stmt = select(AlertRule).where(AlertRule.id == alert_id)
            result = await session.execute(stmt)
            rule = result.scalar_one_or_none()
            
            if rule:
                await session.delete(rule)
                await session.commit()
    
    async def get_triggered_alerts(self, since: datetime) -> List[Dict]:
        """Get recently triggered alerts"""
        async with self.SessionLocal() as session:
            stmt = (
                select(AlertEvent)
                .where(AlertEvent.triggered_at >= since)
                .order_by(AlertEvent.triggered_at.desc())
            )
            
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            return [
                {
                    "id": e.id,
                    "alert_rule_id": e.alert_rule_id,
                    "model_name": e.model_name,
                    "metric_type": e.metric_type,
                    "condition": e.condition,
                    "threshold": e.threshold,
                    "actual_value": e.actual_value,
                    "triggered_at": e.triggered_at.isoformat()
                }
                for e in events
            ]
    
    async def _check_alerts(
        self,
        session: AsyncSession,
        model_name: str,
        metric_type: MetricType,
        value: float,
        timestamp: datetime
    ):
        """Check if this metric triggers any alert rules"""
        # Get active rules for this model + metric
        stmt = select(AlertRule).where(
            and_(
                AlertRule.model_name == model_name,
                AlertRule.metric_type == metric_type.value,
                AlertRule.enabled == True
            )
        )
        
        result = await session.execute(stmt)
        rules = result.scalars().all()
        
        for rule in rules:
            triggered = False
            
            if rule.condition == "gt" and value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and value < rule.threshold:
                triggered = True
            elif rule.condition == "eq" and abs(value - rule.threshold) < 0.0001:
                triggered = True
            
            if triggered:
                # Log alert event
                event = AlertEvent(
                    alert_rule_id=rule.id,
                    model_name=model_name,
                    metric_type=metric_type.value,
                    condition=rule.condition,
                    threshold=rule.threshold,
                    actual_value=value,
                    triggered_at=timestamp
                )
                session.add(event)
                await session.commit()
