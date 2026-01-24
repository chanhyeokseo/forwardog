from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.models import (
    EventsJsonRequest,
    SubmitResponse,
    EventCategory,
    EventAlertStatus,
    EventAlertPriority,
    EventChangeResourceType,
    EventAuthorType,
    HistoryEntryType,
)
from app.services.datadog_client import datadog_client
from app.services.history import history_service

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/v1/submit-json", response_model=SubmitResponse)
async def submit_events_v1_json(request: EventsJsonRequest):
    """Submit raw JSON payload to Datadog Events API v1
    
    The v1 API expects a payload with:
    - title (required)
    - text (required)
    - date_happened (POSIX timestamp)
    - priority (normal/low)
    - alert_type (error/warning/info/success/user_update/recommendation/snapshot)
    - host, tags, aggregation_key, source_type_name, device_name, related_event_id
    """
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    response = await datadog_client.submit_event_v1(request.payload)
    
    history_service.add(
        HistoryEntryType.EVENTS_API,
        {"payload": request.payload, "api_version": "v1"},
        response
    )
    
    return response


@router.post("/v2/submit-json", response_model=SubmitResponse)
async def submit_events_v2_json(request: EventsJsonRequest):
    """Submit raw JSON payload to Datadog Events API v2
    
    The v2 API expects a payload in this format:
    {
        "data": {
            "type": "event",
            "attributes": {
                "title": "...",
                "category": "change" | "alert",
                "attributes": { ... category-specific ... },
                "message": "...",
                "host": "...",
                "tags": [...],
                "timestamp": "ISO8601",
                "aggregation_key": "..."
            }
        }
    }
    """
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    response = await datadog_client.submit_event(request.payload)
    
    history_service.add(
        HistoryEntryType.EVENTS_API,
        {"payload": request.payload, "api_version": "v2"},
        response
    )
    
    return response


# Keep old endpoint for backwards compatibility
@router.post("/api/submit-json", response_model=SubmitResponse)
async def submit_events_json(request: EventsJsonRequest):
    """Submit raw JSON payload to Datadog Events API v2 (deprecated, use /v2/submit-json)"""
    return await submit_events_v2_json(request)


@router.get("/categories")
async def get_categories():
    """Get available event categories"""
    return {
        "categories": [c.value for c in EventCategory]
    }


@router.get("/alert-statuses")
async def get_alert_statuses():
    """Get available alert statuses"""
    return {
        "statuses": [s.value for s in EventAlertStatus]
    }


@router.get("/alert-priorities")
async def get_alert_priorities():
    """Get available alert priorities"""
    return {
        "priorities": [p.value for p in EventAlertPriority]
    }


@router.get("/change-resource-types")
async def get_change_resource_types():
    """Get available change resource types"""
    return {
        "resource_types": [t.value for t in EventChangeResourceType]
    }


@router.get("/author-types")
async def get_author_types():
    """Get available author types"""
    return {
        "author_types": [t.value for t in EventAuthorType]
    }


@router.get("/v1/presets")
async def get_events_v1_presets():
    """Get event presets/templates for v1 API"""
    import time
    now_unix = int(time.time())
    
    return {
        "api_presets": [
            {
                "name": "Simple Info Event",
                "description": "Basic info event",
                "payload": {
                    "title": "Test Event from Forwardog",
                    "text": "This is a test event submitted via Forwardog v1 API.",
                    "date_happened": now_unix,
                    "priority": "normal",
                    "alert_type": "info",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog"]
                }
            },
            {
                "name": "Warning Event",
                "description": "Warning level event",
                "payload": {
                    "title": "High Memory Usage Warning",
                    "text": "%%% \n**Memory Alert**\n\nMemory usage has exceeded 85% on the server.\n\n| Metric | Value |\n|--------|-------|\n| Current | 85% |\n| Threshold | 80% |\n\n%%%",
                    "date_happened": now_unix,
                    "priority": "normal",
                    "alert_type": "warning",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog", "type:resource"],
                    "aggregation_key": "memory-alert"
                }
            },
            {
                "name": "Error Event",
                "description": "Error level event with details",
                "payload": {
                    "title": "Application Error Detected",
                    "text": "%%% \n**Error Details**\n\n```\nTraceback (most recent call last):\n  File \"app.py\", line 42\n    raise Exception(\"Something went wrong\")\nException: Something went wrong\n```\n\n%%%",
                    "date_happened": now_unix,
                    "priority": "normal",
                    "alert_type": "error",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog", "type:error"],
                    "aggregation_key": "app_error_001",
                    "source_type_name": "python"
                }
            },
            {
                "name": "Success Event",
                "description": "Success notification event",
                "payload": {
                    "title": "Deployment Successful",
                    "text": "%%% \n**Deployment Info**\n\n- Version: v1.2.3\n- Environment: production\n- Duration: 45s\n\n✅ All health checks passed\n%%%",
                    "date_happened": now_unix,
                    "priority": "normal",
                    "alert_type": "success",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog", "type:deployment"],
                    "source_type_name": "jenkins"
                }
            },
            {
                "name": "Low Priority Event",
                "description": "Low priority background event",
                "payload": {
                    "title": "Scheduled Maintenance Complete",
                    "text": "Scheduled maintenance has been completed successfully.",
                    "date_happened": now_unix,
                    "priority": "low",
                    "alert_type": "info",
                    "tags": ["env:test", "source:forwardog", "type:maintenance"]
                }
            },
            {
                "name": "User Update Event",
                "description": "User activity event",
                "payload": {
                    "title": "User Settings Updated",
                    "text": "User john.doe@example.com updated their notification preferences.",
                    "date_happened": now_unix,
                    "priority": "low",
                    "alert_type": "user_update",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog", "type:user"]
                }
            },
            {
                "name": "Recommendation Event",
                "description": "System recommendation",
                "payload": {
                    "title": "Performance Optimization Recommended",
                    "text": "%%% \n**Recommendation**\n\nBased on current metrics, consider:\n\n1. Increasing connection pool size\n2. Enabling query caching\n3. Upgrading to larger instance type\n\n%%%",
                    "date_happened": now_unix,
                    "priority": "low",
                    "alert_type": "recommendation",
                    "host": "forwardog-test",
                    "tags": ["env:test", "source:forwardog", "type:optimization"]
                }
            }
        ]
    }


@router.get("/v2/presets")
@router.get("/presets")
async def get_events_presets():
    """Get event presets/templates for v2 API"""
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    
    return {
        "api_presets": [
            {
                "name": "Change Event - Feature Flag",
                "description": "Feature flag change event",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "Feature flag updated: dark_mode_enabled",
                            "category": "change",
                            "message": "Feature flag dark_mode_enabled was updated from false to true",
                            "host": "forwardog-test",
                            "tags": ["env:test", "source:forwardog", "team:platform"],
                            "timestamp": now_iso,
                            "aggregation_key": "feature-flag-dark-mode",
                            "attributes": {
                                "author": {
                                    "name": "forwardog-user",
                                    "type": "user"
                                },
                                "changed_resource": {
                                    "name": "dark_mode_enabled",
                                    "type": "feature_flag"
                                },
                                "impacted_resources": [
                                    {
                                        "name": "web-frontend",
                                        "type": "service"
                                    }
                                ],
                                "prev_value": {
                                    "enabled": False,
                                    "rollout_percentage": 0
                                },
                                "new_value": {
                                    "enabled": True,
                                    "rollout_percentage": 100
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "Change Event - Configuration",
                "description": "Configuration change event",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "Configuration updated: database connection pool",
                            "category": "change",
                            "message": "Database connection pool size increased from 10 to 20",
                            "host": "forwardog-test",
                            "tags": ["env:test", "source:forwardog", "component:database"],
                            "timestamp": now_iso,
                            "aggregation_key": "config-db-pool",
                            "attributes": {
                                "author": {
                                    "name": "deployment-automation",
                                    "type": "automation"
                                },
                                "changed_resource": {
                                    "name": "db_connection_pool_size",
                                    "type": "configuration"
                                },
                                "impacted_resources": [
                                    {
                                        "name": "api-service",
                                        "type": "service"
                                    }
                                ],
                                "prev_value": {
                                    "pool_size": 10,
                                    "timeout_ms": 5000
                                },
                                "new_value": {
                                    "pool_size": 20,
                                    "timeout_ms": 5000
                                },
                                "change_metadata": {
                                    "reason": "High load detected",
                                    "ticket": "OPS-1234"
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "Alert Event - Warning",
                "description": "Warning alert event",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "High Memory Usage Warning",
                            "category": "alert",
                            "message": "Memory usage has exceeded 85% on the server",
                            "host": "forwardog-test",
                            "tags": ["env:test", "source:forwardog", "type:resource"],
                            "timestamp": now_iso,
                            "aggregation_key": "memory-alert",
                            "attributes": {
                                "status": "warn",
                                "priority": "3",
                                "custom": {
                                    "metric": "system.mem.used",
                                    "threshold": 80,
                                    "current_value": 85,
                                    "unit": "percent"
                                },
                                "links": [
                                    {
                                        "category": "runbook",
                                        "title": "Memory High Runbook",
                                        "url": "https://wiki.example.com/runbooks/memory-high"
                                    },
                                    {
                                        "category": "dashboard",
                                        "title": "System Metrics Dashboard",
                                        "url": "https://app.datadoghq.com/dashboard/abc123"
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {
                "name": "Alert Event - Error",
                "description": "Error alert event",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "Database Connection Failed",
                            "category": "alert",
                            "message": "Unable to connect to primary database. Failover initiated.",
                            "host": "forwardog-test",
                            "tags": ["env:test", "source:forwardog", "type:database"],
                            "timestamp": now_iso,
                            "aggregation_key": "db-connection-error",
                            "attributes": {
                                "status": "error",
                                "priority": "1",
                                "custom": {
                                    "database": "primary-db",
                                    "error_code": "CONNECTION_TIMEOUT",
                                    "retry_count": 3,
                                    "failover_status": "initiated"
                                },
                                "links": [
                                    {
                                        "category": "runbook",
                                        "title": "Database Failover Runbook",
                                        "url": "https://wiki.example.com/runbooks/db-failover"
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            {
                "name": "Alert Event - OK (Recovery)",
                "description": "Recovery alert event",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "Service Recovered",
                            "category": "alert",
                            "message": "API service has recovered and is now healthy",
                            "host": "forwardog-test",
                            "tags": ["env:test", "source:forwardog", "type:recovery"],
                            "timestamp": now_iso,
                            "aggregation_key": "api-health",
                            "attributes": {
                                "status": "ok",
                                "priority": "4",
                                "custom": {
                                    "recovery_time_seconds": 45,
                                    "previous_status": "error",
                                    "health_check_url": "/api/health"
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "Change Event - Minimal",
                "description": "Minimal change event (required fields only)",
                "payload": {
                    "data": {
                        "type": "event",
                        "attributes": {
                            "title": "Simple change event",
                            "category": "change",
                            "attributes": {
                                "changed_resource": {
                                    "name": "test-resource",
                                    "type": "configuration"
                                }
                            }
                        }
                    }
                }
            }
        ]
    }
