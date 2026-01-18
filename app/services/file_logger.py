import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.config import settings
from app.models import SubmitResponse, LogStatus


class FileLogger:
    def __init__(self):
        self.log_path = Path(settings.forwardog_log_path)
        self._directory_available = self._ensure_log_directory()
    
    def _ensure_log_directory(self) -> bool:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            return True
        except PermissionError:
            return False
        except Exception:
            return False
    
    def write_raw(self, messages: list[str]) -> SubmitResponse:
        start_time = time.time()
        request_id = f"agent-file-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        if not self._directory_available:
            return SubmitResponse(
                success=False,
                message=f"Log directory not available: {self.log_path.parent}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Log directory is not writable. This feature requires Docker with shared volumes."
            )
        
        try:
            with open(self.log_path, 'a') as f:
                for message in messages:
                    line = message if message.endswith('\n') else message + '\n'
                    f.write(line)
            
            latency_ms = (time.time() - start_time) * 1000
            
            return SubmitResponse(
                success=True,
                message=f"Written {len(messages)} log lines to {self.log_path}",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={
                    "path": str(self.log_path),
                    "lines_written": len(messages)
                }
            )
            
        except PermissionError:
            return SubmitResponse(
                success=False,
                message=f"Permission denied writing to {self.log_path}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Check file permissions and volume mount configuration."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    def write_json(
        self,
        messages: list[str],
        service: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[list[str]] = None,
        status: Optional[LogStatus] = None
    ) -> SubmitResponse:
        start_time = time.time()
        request_id = f"agent-file-json-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        if not self._directory_available:
            return SubmitResponse(
                success=False,
                message=f"Log directory not available: {self.log_path.parent}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Log directory is not writable. This feature requires Docker with shared volumes."
            )
        
        try:
            with open(self.log_path, 'a') as f:
                for message in messages:
                    log_entry = {
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    if service:
                        log_entry["service"] = service
                    if source:
                        log_entry["source"] = source
                    if status:
                        log_entry["status"] = status.value
                    if tags:
                        log_entry["ddtags"] = ",".join(tags)
                    
                    f.write(json.dumps(log_entry) + '\n')
            
            latency_ms = (time.time() - start_time) * 1000
            
            return SubmitResponse(
                success=True,
                message=f"Written {len(messages)} JSON log entries to {self.log_path}",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={
                    "path": str(self.log_path),
                    "lines_written": len(messages),
                    "format": "json"
                }
            )
            
        except PermissionError:
            return SubmitResponse(
                success=False,
                message=f"Permission denied writing to {self.log_path}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Check file permissions and volume mount configuration."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    def get_recent_lines(self, n: int = 20) -> list[str]:
        if not self._directory_available:
            return []
        try:
            if not self.log_path.exists():
                return []
            
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return lines[-n:]
        except Exception:
            return []
    
    def clear_log(self) -> SubmitResponse:
        start_time = time.time()
        request_id = f"agent-file-clear-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        if not self._directory_available:
            return SubmitResponse(
                success=False,
                message=f"Log directory not available: {self.log_path.parent}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint="Log directory is not writable. This feature requires Docker with shared volumes."
            )
        
        try:
            with open(self.log_path, 'w') as f:
                pass
            
            return SubmitResponse(
                success=True,
                message=f"Log file cleared: {self.log_path}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )


file_logger = FileLogger()
