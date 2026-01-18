import time
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.models import (
    MetricsSubmitRequest,
    MetricsJsonRequest,
    DogStatsDRequest,
    DogStatsDRawRequest,
    SubmitResponse,
    MetricType,
    DogStatsDMetricType,
    HistoryEntryType,
)
from app.services.datadog_client import datadog_client
from app.services.dogstatsd_client import dogstatsd_client
from app.services.code_executor import code_executor, get_dogstatsd_examples
from app.services.history import history_service


class CodeExecuteRequest(BaseModel):
    code: str

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.post("/api/submit", response_model=SubmitResponse)
async def submit_metrics_api(request: MetricsSubmitRequest):
    """Submit metrics via Datadog API v2"""
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    # Build payload
    payload = {
        "series": []
    }
    
    current_time = int(time.time())
    
    for series in request.series:
        series_data = {
            "metric": series.metric,
            "type": series.type.value if series.type != MetricType.UNSPECIFIED else MetricType.GAUGE.value,
            "points": [],
            "tags": series.tags + settings.default_tags_list,
        }
        
        # Add resources
        if series.resources:
            series_data["resources"] = [
                {"name": r.name, "type": r.type} for r in series.resources
            ]
        else:
            # Default host resource
            series_data["resources"] = [{"name": "forwardog", "type": "host"}]
        
        # Add points
        for point in series.points:
            ts = point.timestamp if point.timestamp else current_time
            series_data["points"].append({
                "timestamp": ts,
                "value": point.value
            })
        
        # If no points, add one with current time
        if not series_data["points"]:
            series_data["points"].append({
                "timestamp": current_time,
                "value": 0
            })
        
        # Add optional fields
        if series.unit:
            series_data["unit"] = series.unit
        if series.interval:
            series_data["interval"] = series.interval
        
        payload["series"].append(series_data)
    
    response = await datadog_client.submit_metrics(payload)
    
    # Save to history
    history_service.add(
        HistoryEntryType.METRICS_API,
        {"series": [s.model_dump() for s in request.series]},
        response
    )
    
    return response


@router.post("/api/submit-json", response_model=SubmitResponse)
async def submit_metrics_json(request: MetricsJsonRequest):
    """Submit raw JSON payload to Datadog Metrics API"""
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    response = await datadog_client.submit_metrics(request.payload)
    
    # Save to history
    history_service.add(
        HistoryEntryType.METRICS_API,
        {"payload": request.payload},
        response
    )
    
    return response


@router.post("/dogstatsd/submit", response_model=SubmitResponse)
async def submit_dogstatsd(request: DogStatsDRequest):
    """Submit metric via DogStatsD"""
    response = dogstatsd_client.send(
        metric=request.metric,
        value=request.value,
        metric_type=request.metric_type,
        tags=request.tags,
        sample_rate=request.sample_rate,
        namespace=request.namespace
    )
    
    # Save to history
    history_service.add(
        HistoryEntryType.METRICS_DOGSTATSD,
        request.model_dump(),
        response
    )
    
    return response


@router.post("/dogstatsd/submit-raw", response_model=SubmitResponse)
async def submit_dogstatsd_raw(request: DogStatsDRawRequest):
    """Submit raw DogStatsD line"""
    response = dogstatsd_client.send_raw(request.line)
    
    # Save to history
    history_service.add(
        HistoryEntryType.METRICS_DOGSTATSD,
        {"line": request.line},
        response
    )
    
    return response


@router.post("/dogstatsd/execute", response_model=SubmitResponse)
async def execute_dogstatsd_code(request: CodeExecuteRequest):
    """Execute Python code with DogStatsD context"""
    response = code_executor.execute(request.code)
    
    # Save to history
    history_service.add(
        HistoryEntryType.METRICS_DOGSTATSD,
        {"code": request.code[:500] + "..." if len(request.code) > 500 else request.code},
        response
    )
    
    return response


@router.get("/dogstatsd/examples")
async def get_dogstatsd_examples_endpoint():
    """Get DogStatsD Python code examples"""
    examples = get_dogstatsd_examples()
    return {
        "examples": [
            {"id": key, "name": key.replace("_", " ").title(), "code": code}
            for key, code in examples.items()
        ]
    }


@router.get("/types")
async def get_metric_types():
    """Get available metric types"""
    return {
        "api_types": [t.value for t in MetricType],
        "dogstatsd_types": [
            {"value": t.value, "name": t.name} for t in DogStatsDMetricType
        ]
    }


@router.get("/presets")
async def get_metrics_presets():
    """Get metric presets/templates"""
    current_time = int(time.time())
    
    return {
        "api_presets": [
            {
                "name": "Simple Gauge",
                "description": "Basic gauge metric",
                "payload": {
                    "series": [{
                        "metric": "forwardog.api.gauge",
                        "type": 3,
                        "points": [{"timestamp": current_time, "value": 42}],
                        "resources": [{"name": "forwardog-test", "type": "host"}],
                        "tags": ["env:test", "source:forwardog"]
                    }]
                }
            },
            {
                "name": "Counter with Interval",
                "description": "Counter metric with interval",
                "payload": {
                    "series": [{
                        "metric": "forwardog.api.counter",
                        "type": 1,
                        "interval": 10,
                        "points": [{"timestamp": current_time, "value": 100}],
                        "resources": [{"name": "forwardog-test", "type": "host"}],
                        "tags": ["env:test", "source:forwardog"]
                    }]
                }
            },
            {
                "name": "Rate Metric",
                "description": "Rate metric example",
                "payload": {
                    "series": [{
                        "metric": "forwardog.api.rate",
                        "type": 2,
                        "interval": 10,
                        "points": [{"timestamp": current_time, "value": 5.5}],
                        "resources": [{"name": "forwardog-test", "type": "host"}],
                        "tags": ["env:test", "source:forwardog"]
                    }]
                }
            },
            {
                "name": "Multiple Series",
                "description": "Multiple metrics in one request",
                "payload": {
                    "series": [
                        {
                            "metric": "forwardog.api.cpu",
                            "type": 3,
                            "points": [{"timestamp": current_time, "value": 65.5}],
                            "resources": [{"name": "forwardog-test", "type": "host"}],
                            "tags": ["env:test"]
                        },
                        {
                            "metric": "forwardog.api.memory",
                            "type": 3,
                            "points": [{"timestamp": current_time, "value": 78.2}],
                            "resources": [{"name": "forwardog-test", "type": "host"}],
                            "tags": ["env:test"]
                        }
                    ]
                }
            }
        ],
        "dogstatsd_presets": [
            {
                "name": "Gauge",
                "description": "Simple gauge metric",
                "line": "forwardog.test.gauge:42|g|#env:test,source:forwardog"
            },
            {
                "name": "Counter",
                "description": "Increment counter",
                "line": "forwardog.test.counter:1|c|#env:test,source:forwardog"
            },
            {
                "name": "Histogram",
                "description": "Histogram/Timer",
                "line": "forwardog.test.histogram:125|h|#env:test,source:forwardog"
            },
            {
                "name": "Distribution",
                "description": "Distribution metric",
                "line": "forwardog.test.distribution:50|d|#env:test,source:forwardog"
            },
            {
                "name": "Set",
                "description": "Unique value set",
                "line": "forwardog.test.set:user123|s|#env:test,source:forwardog"
            },
            {
                "name": "Counter with Sample Rate",
                "description": "Counter with 50% sample rate",
                "line": "forwardog.test.sampled:1|c|@0.5|#env:test,source:forwardog"
            }
        ]
    }

