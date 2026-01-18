"""Forwardog - Datadog Metrics & Logs Test Tool"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import httpx

from app.config import settings
from app.routers import metrics, logs, history

app = FastAPI(
    title="Forwardog",
    description="Datadog Metrics & Logs submission test tool",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(metrics.router)
app.include_router(logs.router)
app.include_router(history.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": {
                "is_configured": settings.is_configured(),
                "masked_api_key": settings.get_masked_api_key(),
                "dd_site": settings.dd_site,
                "dd_agent_host": settings.dd_agent_host,
                "dogstatsd_port": settings.dogstatsd_port,
                "log_path": settings.forwardog_log_path,
            }
        }
    )


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "configured": settings.is_configured(),
        "dd_site": settings.dd_site
    }


@app.get("/api/config")
async def get_config():
    return {
        "is_configured": settings.is_configured(),
        "masked_api_key": settings.get_masked_api_key(),
        "dd_site": settings.dd_site,
        "dd_agent_host": settings.dd_agent_host,
        "dogstatsd_port": settings.dogstatsd_port,
        "log_path": settings.forwardog_log_path,
        "default_tags": settings.default_tags_list,
        "max_requests_per_second": settings.max_requests_per_second,
        "max_payload_size_mb": settings.max_payload_size_mb,
    }


@app.get("/api/validate-key")
async def validate_api_key():
    if not settings.is_configured():
        return {
            "valid": False,
            "message": "API key not configured"
        }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.{settings.dd_site}/api/v1/validate",
                headers={
                    "DD-API-KEY": settings.dd_api_key
                }
            )
            
            if response.status_code == 200:
                return {
                    "valid": True,
                    "message": "API key is valid"
                }
            else:
                return {
                    "valid": False,
                    "message": f"Invalid API key (HTTP {response.status_code})"
                }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Failed to validate: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
