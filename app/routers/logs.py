from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.models import (
    LogsApiRequest,
    LogsJsonRequest,
    LogsRawRequest,
    AgentFileLogRequest,
    SubmitResponse,
    LogStatus,
    HistoryEntryType,
)
from app.services.datadog_client import datadog_client
from app.services.file_logger import file_logger
from app.services.history import history_service

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/api/submit", response_model=SubmitResponse)
async def submit_logs_api(request: LogsApiRequest):
    """Submit logs via Datadog HTTP intake API"""
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    # Build log payload
    logs = []
    for entry in request.logs:
        log_data = {
            "message": entry.message,
            "ddsource": entry.ddsource or "forwardog",
            "service": entry.service or "forwardog",
        }
        
        if entry.ddtags:
            log_data["ddtags"] = entry.ddtags
        if entry.hostname:
            log_data["hostname"] = entry.hostname
        if entry.status:
            log_data["status"] = entry.status.value
        if entry.extra:
            log_data.update(entry.extra)
        
        logs.append(log_data)
    
    # Build global ddtags
    ddtags = request.ddtags
    if settings.default_tags_list:
        default_tags = ",".join(settings.default_tags_list)
        if ddtags:
            ddtags = f"{ddtags},{default_tags}"
        else:
            ddtags = default_tags
    
    response = await datadog_client.submit_logs(logs, ddtags=ddtags)
    
    # Save to history
    history_service.add(
        HistoryEntryType.LOGS_API,
        {"logs": [e.model_dump() for e in request.logs], "ddtags": request.ddtags},
        response
    )
    
    return response


@router.post("/api/submit-json", response_model=SubmitResponse)
async def submit_logs_json(request: LogsJsonRequest):
    """Submit raw JSON payload to Datadog Logs API"""
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    response = await datadog_client.submit_logs(request.payload)
    
    # Save to history
    history_service.add(
        HistoryEntryType.LOGS_API,
        {"payload": request.payload},
        response
    )
    
    return response


@router.post("/api/submit-raw", response_model=SubmitResponse)
async def submit_logs_raw(request: LogsRawRequest):
    """Submit raw message logs via Datadog HTTP intake API"""
    if not settings.is_configured():
        raise HTTPException(status_code=400, detail="DD_API_KEY not configured")
    
    # Convert raw messages to log format
    logs = []
    for message in request.messages:
        log_data = {
            "message": message,
            "ddsource": request.ddsource or "forwardog",
            "service": request.service or "forwardog",
        }
        if request.ddtags:
            log_data["ddtags"] = request.ddtags
        logs.append(log_data)
    
    response = await datadog_client.submit_logs(logs)
    
    # Save to history
    history_service.add(
        HistoryEntryType.LOGS_API,
        request.model_dump(),
        response
    )
    
    return response


@router.post("/agent-file/submit", response_model=SubmitResponse)
async def submit_agent_file_logs(request: AgentFileLogRequest):
    """Write logs to file for Datadog Agent collection"""
    if request.format == "json":
        response = file_logger.write_json(
            messages=request.messages,
            service=request.service,
            source=request.source,
            tags=request.tags,
            status=request.status
        )
    else:
        response = file_logger.write_raw(request.messages)
    
    # Save to history
    history_service.add(
        HistoryEntryType.LOGS_AGENT_FILE,
        request.model_dump(),
        response
    )
    
    return response


@router.get("/agent-file/recent")
async def get_recent_logs(n: int = 20):
    """Get recent lines from log file"""
    lines = file_logger.get_recent_lines(n)
    return {
        "path": str(file_logger.log_path),
        "lines": lines,
        "count": len(lines)
    }


@router.post("/agent-file/clear", response_model=SubmitResponse)
async def clear_log_file():
    """Clear the agent log file"""
    return file_logger.clear_log()


@router.get("/statuses")
async def get_log_statuses():
    """Get available log status levels"""
    return {
        "statuses": [s.value for s in LogStatus]
    }


@router.get("/presets")
async def get_logs_presets():
    """Get log presets/templates"""
    return {
        "api_presets": [
            {
                "name": "Simple Info Log",
                "description": "Basic info log message",
                "payload": [{
                    "message": "This is a test log from forwardog",
                    "ddsource": "forwardog",
                    "service": "forwardog-test",
                    "status": "info"
                }]
            },
            {
                "name": "Error Log with Stack",
                "description": "Error log with stack trace",
                "payload": [{
                    "message": "Error: Something went wrong\n  at function1 (file.js:10)\n  at function2 (file.js:20)",
                    "ddsource": "forwardog",
                    "service": "forwardog-test",
                    "status": "error",
                    "error.kind": "RuntimeError",
                    "error.message": "Something went wrong"
                }]
            },
            {
                "name": "JSON Structured Log",
                "description": "Log with structured data",
                "payload": [{
                    "message": "User login successful",
                    "ddsource": "forwardog",
                    "service": "forwardog-test",
                    "status": "info",
                    "usr.id": "user123",
                    "usr.email": "user@example.com",
                    "http.method": "POST",
                    "http.url": "/api/login"
                }]
            },
            {
                "name": "Batch Logs (10)",
                "description": "10 log entries in batch",
                "payload": [
                    {"message": f"Batch log entry {i}", "ddsource": "forwardog", "service": "forwardog-test", "status": "info"}
                    for i in range(1, 11)
                ]
            },
            {
                "name": "Warning Log",
                "description": "Warning level log",
                "payload": [{
                    "message": "High memory usage detected: 85%",
                    "ddsource": "forwardog",
                    "service": "forwardog-test",
                    "status": "warning",
                    "metric": "memory.percent",
                    "value": 85
                }]
            }
        ],
        "agent_file_presets": [
            {
                "name": "Raw Single Line",
                "description": "Simple raw log line",
                "messages": ["This is a raw log line from forwardog"]
            },
            {
                "name": "JSON with Timestamp",
                "description": "JSON log with current timestamp",
                "messages": ['{"timestamp": NOW, "message": "Application started", "service": "forwardog-test", "status": "info"}'],
                "has_timestamp": True
            },
            {
                "name": "Multiline Stack Trace",
                "description": "Java-style exception",
                "messages": [
                    "Exception in thread \"main\" java.lang.NullPointerException",
                    "    at com.example.MyClass.method(MyClass.java:123)",
                    "    at com.example.Main.main(Main.java:45)"
                ]
            },
            {
                "name": "Access Log Format",
                "description": "Apache-style access log",
                "messages": ['192.168.1.1 - - [NOW_ISO] "GET /api/health HTTP/1.1" 200 1234'],
                "has_timestamp": True
            },
            {
                "name": "Syslog Format",
                "description": "Syslog-style log line",
                "messages": ["<14>NOW_ISO forwardog-host forwardog-app: User authentication successful for user123"],
                "has_timestamp": True
            },
            {
                "name": "Multiple JSON Logs",
                "description": "5 JSON log entries",
                "messages": [
                    '{"timestamp": NOW, "message": "Log entry 1", "level": "info"}',
                    '{"timestamp": NOW, "message": "Log entry 2", "level": "debug"}',
                    '{"timestamp": NOW, "message": "Log entry 3", "level": "info"}',
                    '{"timestamp": NOW, "message": "Log entry 4", "level": "warn"}',
                    '{"timestamp": NOW, "message": "Log entry 5", "level": "error"}'
                ],
                "has_timestamp": True
            },
            {
                "name": "Old Timestamp (Warning Test)",
                "description": "Log with outdated timestamp - will trigger warning",
                "messages": ['{"timestamp": 1609459200, "message": "This log has an old timestamp from 2021", "service": "forwardog-test"}'],
                "has_timestamp": True
            }
        ]
    }

