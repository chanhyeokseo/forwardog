from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class MetricType(int, Enum):
    UNSPECIFIED = 0
    COUNT = 1
    RATE = 2
    GAUGE = 3


class DogStatsDMetricType(str, Enum):
    COUNTER = "c"
    GAUGE = "g"
    HISTOGRAM = "h"
    DISTRIBUTION = "d"
    SET = "s"
    TIMER = "ms"


class MetricPoint(BaseModel):
    timestamp: Optional[int] = None
    value: float


class MetricResource(BaseModel):
    name: str = "host"
    type: str = "host"


class MetricSeries(BaseModel):
    metric: str
    type: MetricType = MetricType.GAUGE
    points: list[MetricPoint] = Field(default_factory=list)
    resources: list[MetricResource] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    unit: Optional[str] = None
    interval: Optional[int] = None


class MetricsSubmitRequest(BaseModel):
    series: list[MetricSeries]


class MetricsJsonRequest(BaseModel):
    payload: dict[str, Any]


class DogStatsDRequest(BaseModel):
    metric: str
    value: float
    metric_type: DogStatsDMetricType = DogStatsDMetricType.GAUGE
    tags: list[str] = Field(default_factory=list)
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    namespace: Optional[str] = None


class DogStatsDRawRequest(BaseModel):
    line: str


class LogStatus(str, Enum):
    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class LogEntry(BaseModel):
    message: str
    ddsource: Optional[str] = "forwardog"
    ddtags: Optional[str] = None
    hostname: Optional[str] = None
    service: Optional[str] = "forwardog"
    status: Optional[LogStatus] = LogStatus.INFO
    extra: Optional[dict[str, Any]] = None


class LogsApiRequest(BaseModel):
    logs: list[LogEntry]
    ddtags: Optional[str] = None


class LogsJsonRequest(BaseModel):
    payload: list[dict[str, Any]] | dict[str, Any]


class LogsRawRequest(BaseModel):
    messages: list[str]
    ddsource: Optional[str] = "forwardog"
    ddtags: Optional[str] = None
    service: Optional[str] = "forwardog"


class AgentFileLogRequest(BaseModel):
    messages: list[str]
    format: str = Field(default="raw")
    service: Optional[str] = "forwardog"
    source: Optional[str] = "forwardog"
    tags: list[str] = Field(default_factory=list)
    status: Optional[LogStatus] = LogStatus.INFO


class SubmitResponse(BaseModel):
    success: bool
    message: str
    request_id: Optional[str] = None
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    response_body: Optional[Any] = None
    error_hint: Optional[str] = None


class HistoryEntryType(str, Enum):
    METRICS_API = "metrics_api"
    METRICS_DOGSTATSD = "metrics_dogstatsd"
    LOGS_API = "logs_api"
    LOGS_AGENT_FILE = "logs_agent_file"


class HistoryEntry(BaseModel):
    id: str
    type: HistoryEntryType
    timestamp: datetime
    request: dict[str, Any]
    response: SubmitResponse
    

class PresetCategory(str, Enum):
    METRICS = "metrics"
    LOGS = "logs"


class Preset(BaseModel):
    id: str
    name: str
    description: str
    category: PresetCategory
    payload: dict[str, Any]
