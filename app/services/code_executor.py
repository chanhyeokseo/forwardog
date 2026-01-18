import sys
import time
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from typing import Any

from datadog import initialize, statsd
from app.config import settings
from app.models import SubmitResponse


class CodeExecutor:
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize DogStatsD client"""
        if not self._initialized:
            initialize(
                statsd_host=settings.dd_agent_host,
                statsd_port=settings.dogstatsd_port,
            )
            self._initialized = True
    
    def execute(self, code: str) -> SubmitResponse:
        """Execute Python code and return result"""
        start_time = time.time()
        request_id = f"dogstatsd-exec-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Ensure DogStatsD is initialized
        self._ensure_initialized()
        
        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Build execution context with DogStatsD client
        exec_globals = {
            '__builtins__': __builtins__,
            'statsd': statsd,
            'time': time,
            'print': print,
        }
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals)
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            latency_ms = (time.time() - start_time) * 1000
            
            output_lines = []
            if stdout_output:
                output_lines.append(stdout_output.strip())
            if stderr_output:
                output_lines.append(f"[stderr] {stderr_output.strip()}")
            
            return SubmitResponse(
                success=True,
                message="Code executed successfully",
                request_id=request_id,
                latency_ms=latency_ms,
                response_body={
                    "output": "\n".join(output_lines) if output_lines else "(no output)",
                    "host": settings.dd_agent_host,
                    "port": settings.dogstatsd_port,
                }
            )
            
        except SyntaxError as e:
            return SubmitResponse(
                success=False,
                message=f"Syntax Error: {e.msg}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                response_body={
                    "error": str(e),
                    "line": e.lineno,
                },
                error_hint=f"Check syntax at line {e.lineno}"
            )
        except Exception as e:
            tb = traceback.format_exc()
            return SubmitResponse(
                success=False,
                message=f"Error: {type(e).__name__}: {str(e)}",
                request_id=request_id,
                latency_ms=(time.time() - start_time) * 1000,
                response_body={
                    "error": str(e),
                    "traceback": tb,
                },
                error_hint=f"Runtime error: {type(e).__name__}"
            )


code_executor = CodeExecutor()


def get_dogstatsd_examples():
    """Get DogStatsD examples with dynamic host/port from settings"""
    host = settings.dd_agent_host
    port = settings.dogstatsd_port
    
    return {
        "gauge": f'''from datadog import initialize, statsd

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Gauge - Current value
statsd.gauge('forwardog.dogstatsd.gauge', 42, tags=['env:test', 'source:forwardog'])
''',
        
        "counter": f'''from datadog import initialize, statsd

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Counter - Increment/decrement
statsd.increment('forwardog.dogstatsd.counter', tags=['env:test', 'source:forwardog'])
print("Incremented counter: forwardog.dogstatsd.counter")

# You can also decrement
# statsd.decrement('forwardog.dogstatsd.counter', tags=['env:test'])
''',
    
        "histogram": f'''from datadog import initialize, statsd
import random

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Histogram - Distribution of values
for i in range(10):
    value = random.randint(50, 150)
    statsd.histogram('forwardog.dogstatsd.histogram', value, tags=['env:test', 'source:forwardog'])
    print(f"Sent histogram value: {{value}}")
''',
    
        "distribution": f'''from datadog import initialize, statsd
import random

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Distribution
for i in range(10):
    value = random.gauss(100, 20)  # Normal distribution
    statsd.distribution('forwardog.dogstatsd.distribution', value, tags=['env:test', 'source:forwardog'])
    print(f"Sent distribution value: {{value:.2f}}")
''',
    
        "set": f'''from datadog import initialize, statsd

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Set - Count unique values
statsd.set('forwardog.dogstatsd.unique_users', 'user_123', tags=['env:test', 'source:forwardog'])
statsd.set('forwardog.dogstatsd.unique_users', 'user_456', tags=['env:test', 'source:forwardog'])
statsd.set('forwardog.dogstatsd.unique_users', 'user_123', tags=['env:test'])  # Duplicate, won't increase count
print("Sent 3 set values (2 unique)")
''',
    
        "timing": f'''from datadog import initialize, statsd
import time

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Timing - Measure execution time (milliseconds)
start = time.time()
time.sleep(0.1)  # Simulate some work
elapsed_ms = (time.time() - start) * 1000

statsd.timing('forwardog.dogstatsd.timing', elapsed_ms, tags=['env:test', 'source:forwardog'])
print(f"Sent timing: {{elapsed_ms:.2f}}ms")
''',
    
        "timed_decorator": f'''from datadog import initialize, statsd
import time

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Timed decorator - Automatically measure function execution
@statsd.timed('forwardog.dogstatsd.function_time', tags=['env:test', 'source:forwardog'])
def my_function():
    time.sleep(0.05)
    return "done"

result = my_function()
print(f"Function executed with timing: {{result}}")
''',

        "multiple": f'''from datadog import initialize, statsd
import random

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Multiple metrics at once
# System-like metrics
statsd.gauge('forwardog.dogstatsd.system.cpu', random.uniform(10, 90), tags=['env:test', 'host:forwardog'])
statsd.gauge('forwardog.dogstatsd.system.memory', random.uniform(40, 80), tags=['env:test', 'host:forwardog'])
statsd.gauge('forwardog.dogstatsd.system.disk', random.uniform(20, 60), tags=['env:test', 'host:forwardog'])

# Application metrics
statsd.increment('forwardog.dogstatsd.app.requests', tags=['env:test', 'endpoint:/api/test'])
statsd.histogram('forwardog.dogstatsd.app.latency', random.uniform(10, 200), tags=['env:test'])

print("Sent multiple system and application metrics")
''',

        "service_check": f'''from datadog import initialize, statsd

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Service Check - Report service status
# Status: 0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN
statsd.service_check(
    'forwardog.dogstatsd.health',
    statsd.OK,  # or statsd.WARNING, statsd.CRITICAL, statsd.UNKNOWN
    tags=['env:test', 'source:forwardog'],
    message='Service is healthy'
)
print("Sent service check: OK")
''',

        "event": f'''from datadog import initialize, statsd

# Initialize DogStatsD client
options = {{
    'statsd_host': '{host}',
    'statsd_port': {port}
}}
initialize(**options)

# Event - Send an event to Datadog
statsd.event(
    title='Forwardog Test Event',
    message='This is a test event from Forwardog DogStatsD executor',
    tags=['env:test', 'source:forwardog'],
    alert_type='info'  # info, warning, error, success
)
print("Sent event: Forwardog Test Event")
''',
    }

