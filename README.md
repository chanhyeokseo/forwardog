<p align="center">
  <img src="app/static/images/logo.png" alt="Forwardog Logo" width="120">
</p>

<h1 align="center">Forwardog</h1>

<p align="center"><strong>Datadog Metrics & Logs Submission Test Tool</strong></p>

Forwardog is a Web UI service that helps you test and validate Datadog metrics and log submission paths. It provides an intuitive interface for sending metrics and logs via various methods.

![Forwardog Screenshot](forwardog.png)

## Features

### Metrics Submission
- **API-based** - Submit metrics via Datadog Metrics API v2 (`/api/v2/series`)
- **DogStatsD** - Send metrics via UDP to Datadog Agent's DogStatsD

### Logs Submission
- **API-based** - Submit logs via Datadog HTTP intake API
- **Agent File** - Write logs to a file for Datadog Agent collection

### Payload Modes
- **JSON Editor** - Full control with raw JSON payload editing
- **Form Mode** - Easy dropdown and input-based metric/log configuration
- **Presets** - Pre-built templates for common scenarios


## Quick Start

### Prerequisites
- Docker and Docker Compose
- Datadog API Key

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/forwardog.git
cd forwardog

# Copy and edit environment file
cp env.example .env
# Edit .env and add your DD_API_KEY
```

### 2. Start with Docker Compose

**Full setup (with Datadog Agent):**
```bash
docker-compose up -d
```

### 3. Access the UI

Open your browser and navigate to: **http://localhost:8000**

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DD_API_KEY` | **Required.** Your Datadog API key | - |
| `DD_SITE` | Datadog site | `datadoghq.com` |
| `DD_AGENT_HOST` | Datadog Agent hostname | `datadog-agent` |
| `DOGSTATSD_PORT` | DogStatsD UDP port | `8125` |
| `FORWARDOG_LOG_PATH` | Path for Agent file logs | `/var/log/forwardog/forwardog.log` |
| `DEFAULT_TAGS` | Default tags (comma-separated) | - |
| `MAX_REQUESTS_PER_SECOND` | Rate limit | `10` |
| `MAX_PAYLOAD_SIZE_MB` | Max payload size | `5` |

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/health` | GET | Health check |
| `/api/config` | GET | Get configuration (masked) |
| `/api/metrics/api/submit` | POST | Submit metrics via form |
| `/api/metrics/api/submit-json` | POST | Submit raw JSON metrics |
| `/api/metrics/dogstatsd/submit` | POST | Send metric via DogStatsD |
| `/api/metrics/dogstatsd/submit-raw` | POST | Send raw DogStatsD line |
| `/api/metrics/presets` | GET | Get metric presets |
| `/api/logs/api/submit` | POST | Submit logs via form |
| `/api/logs/api/submit-json` | POST | Submit raw JSON logs |
| `/api/logs/agent-file/submit` | POST | Write logs to file |
| `/api/logs/presets` | GET | Get log presets |
| `/api/history/` | GET | Get submission history |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
