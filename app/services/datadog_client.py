import time
import json
import gzip
from typing import Any, Optional
from datetime import datetime
import httpx
from app.config import settings
from app.models import SubmitResponse


class DatadogClient:
    def __init__(self):
        self.api_url = settings.dd_api_url
        self.logs_url = settings.dd_logs_url
        self.events_url = settings.dd_events_url
        self.api_key = settings.dd_api_key
        
    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        return {
            "DD-API-KEY": self.api_key,
            "Content-Type": content_type,
        }
    
    def _get_error_hint(self, status_code: int, response_body: Any) -> Optional[str]:
        hints = {
            400: "Invalid payload format. Check metric/log structure and required fields.",
            401: "Invalid API key. Verify DD_API_KEY environment variable.",
            403: "API key doesn't have permission for this operation.",
            408: "Request timeout. Check network connectivity.",
            413: "Payload too large. Max 5MB per request, 1MB per log entry.",
            429: "Rate limited. Too many requests. Wait before retrying.",
            500: "Datadog server error. Try again later.",
            502: "Bad gateway. Datadog service temporarily unavailable.",
            503: "Service unavailable. Datadog is under maintenance.",
        }
        return hints.get(status_code)
    
    async def submit_metrics(self, payload: dict[str, Any], compress: bool = False) -> SubmitResponse:
        url = f"{self.api_url}/api/v2/series"
        headers = self._get_headers()
        
        start_time = time.time()
        request_id = f"metrics-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            body = json.dumps(payload).encode()
            if compress:
                headers["Content-Encoding"] = "gzip"
                body = gzip.compress(body)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=30.0
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            
            if response.status_code in (200, 202):
                return SubmitResponse(
                    success=True,
                    message="Metrics submitted successfully",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body
                )
            else:
                return SubmitResponse(
                    success=False,
                    message=f"Failed to submit metrics: HTTP {response.status_code}",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body,
                    error_hint=self._get_error_hint(response.status_code, response_body)
                )
                
        except httpx.TimeoutException:
            return SubmitResponse(
                success=False,
                message="Request timeout",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Request timed out. Check network connectivity to Datadog."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    async def submit_logs(
        self, 
        logs: list[dict[str, Any]], 
        ddtags: Optional[str] = None,
        compress: bool = False
    ) -> SubmitResponse:
        url = f"{self.logs_url}/api/v2/logs"
        headers = self._get_headers()
        
        if ddtags:
            url = f"{url}?ddtags={ddtags}"
        
        start_time = time.time()
        request_id = f"logs-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            body = json.dumps(logs).encode()
            if compress:
                headers["Content-Encoding"] = "gzip"
                body = gzip.compress(body)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=30.0
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            
            if response.status_code in (200, 202):
                return SubmitResponse(
                    success=True,
                    message=f"Logs submitted successfully ({len(logs)} entries)",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body
                )
            else:
                return SubmitResponse(
                    success=False,
                    message=f"Failed to submit logs: HTTP {response.status_code}",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body,
                    error_hint=self._get_error_hint(response.status_code, response_body)
                )
                
        except httpx.TimeoutException:
            return SubmitResponse(
                success=False,
                message="Request timeout",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Request timed out. Check network connectivity to Datadog."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )

    async def submit_event_v1(self, event: dict[str, Any]) -> SubmitResponse:
        """Submit event via Datadog Events API v1
        
        The v1 API expects a payload with:
        - title (required)
        - text (required)
        - date_happened (POSIX timestamp)
        - priority (normal/low)
        - host, tags, alert_type, aggregation_key, etc.
        """
        url = f"{self.api_url}/api/v1/events"
        headers = self._get_headers()
        
        start_time = time.time()
        request_id = f"event-v1-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            body = json.dumps(event).encode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=30.0
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            
            if response.status_code in (200, 201, 202):
                return SubmitResponse(
                    success=True,
                    message="Event submitted successfully (v1 API)",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body
                )
            else:
                return SubmitResponse(
                    success=False,
                    message=f"Failed to submit event: HTTP {response.status_code}",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body,
                    error_hint=self._get_error_hint(response.status_code, response_body)
                )
                
        except httpx.TimeoutException:
            return SubmitResponse(
                success=False,
                message="Request timeout",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Request timed out. Check network connectivity to Datadog."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )

    async def submit_event(self, event: dict[str, Any]) -> SubmitResponse:
        """Submit event via Datadog Events API v2
        
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
        url = f"{self.events_url}/api/v2/events"
        headers = self._get_headers()
        
        start_time = time.time()
        request_id = f"event-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            body = json.dumps(event).encode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=30.0
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            
            if response.status_code in (200, 201, 202):
                return SubmitResponse(
                    success=True,
                    message="Event submitted successfully (v2 API)",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body
                )
            else:
                return SubmitResponse(
                    success=False,
                    message=f"Failed to submit event: HTTP {response.status_code}",
                    request_id=request_id,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    response_body=response_body,
                    error_hint=self._get_error_hint(response.status_code, response_body)
                )
                
        except httpx.TimeoutException:
            return SubmitResponse(
                success=False,
                message="Request timeout",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Request timed out. Check network connectivity to Datadog."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )


datadog_client = DatadogClient()
