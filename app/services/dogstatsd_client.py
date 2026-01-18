import socket
import time
from datetime import datetime
from typing import Optional
from app.config import settings
from app.models import DogStatsDMetricType, SubmitResponse


class DogStatsDClient:
    def __init__(self):
        self.host = settings.dd_agent_host
        self.port = settings.dogstatsd_port
        self._socket: Optional[socket.socket] = None
    
    def _get_socket(self) -> socket.socket:
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(False)
        return self._socket
    
    def _format_metric(
        self,
        metric: str,
        value: float,
        metric_type: DogStatsDMetricType,
        tags: list[str],
        sample_rate: float = 1.0,
        namespace: Optional[str] = None
    ) -> str:
        if namespace:
            metric = f"{namespace}.{metric}"
        
        line = f"{metric}:{value}|{metric_type.value}"
        
        if sample_rate < 1.0:
            line += f"|@{sample_rate}"
        
        all_tags = settings.default_tags_list + tags
        if all_tags:
            line += f"|#{','.join(all_tags)}"
        
        return line
    
    def send(
        self,
        metric: str,
        value: float,
        metric_type: DogStatsDMetricType = DogStatsDMetricType.GAUGE,
        tags: list[str] = None,
        sample_rate: float = 1.0,
        namespace: Optional[str] = None
    ) -> SubmitResponse:
        if tags is None:
            tags = []
            
        start_time = time.time()
        request_id = f"dogstatsd-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        line = self._format_metric(metric, value, metric_type, tags, sample_rate, namespace)
        
        try:
            sock = self._get_socket()
            sock.sendto(line.encode('utf-8'), (self.host, self.port))
            
            latency_ms = (time.time() - start_time) * 1000
            
            return SubmitResponse(
                success=True,
                message=f"Metric sent via DogStatsD",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={"line": line, "host": self.host, "port": self.port}
            )
            
        except socket.error as e:
            return SubmitResponse(
                success=False,
                message=f"Socket error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Failed to send UDP packet to {self.host}:{self.port}. Check DD_AGENT_HOST and DOGSTATSD_PORT."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    def send_raw(self, line: str) -> SubmitResponse:
        start_time = time.time()
        request_id = f"dogstatsd-raw-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            sock = self._get_socket()
            sock.sendto(line.encode('utf-8'), (self.host, self.port))
            
            latency_ms = (time.time() - start_time) * 1000
            
            return SubmitResponse(
                success=True,
                message="Raw line sent via DogStatsD",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={"line": line, "host": self.host, "port": self.port}
            )
            
        except socket.error as e:
            return SubmitResponse(
                success=False,
                message=f"Socket error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Failed to send UDP packet to {self.host}:{self.port}. Check DD_AGENT_HOST and DOGSTATSD_PORT."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    def send_batch(self, lines: list[str]) -> SubmitResponse:
        start_time = time.time()
        request_id = f"dogstatsd-batch-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        try:
            sock = self._get_socket()
            payload = '\n'.join(lines)
            sock.sendto(payload.encode('utf-8'), (self.host, self.port))
            
            latency_ms = (time.time() - start_time) * 1000
            
            return SubmitResponse(
                success=True,
                message=f"Batch sent via DogStatsD ({len(lines)} metrics)",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={"lines": lines, "count": len(lines), "host": self.host, "port": self.port}
            )
            
        except socket.error as e:
            return SubmitResponse(
                success=False,
                message=f"Socket error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Failed to send UDP packet to {self.host}:{self.port}. Check DD_AGENT_HOST and DOGSTATSD_PORT."
            )
        except Exception as e:
            return SubmitResponse(
                success=False,
                message=f"Error: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                error_hint=f"Unexpected error: {type(e).__name__}"
            )
    
    def close(self):
        if self._socket:
            self._socket.close()
            self._socket = None


dogstatsd_client = DogStatsDClient()
