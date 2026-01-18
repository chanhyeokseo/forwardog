import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dd_api_key: str = os.getenv("DD_API_KEY", "")
    dd_site: str = os.getenv("DD_SITE", "datadoghq.com")
    dd_agent_host: str = os.getenv("DD_AGENT_HOST", "127.0.0.1")
    dogstatsd_port: int = int(os.getenv("DOGSTATSD_PORT", "8125"))
    forwardog_log_path: str = os.getenv("FORWARDOG_LOG_PATH", "/var/log/forwardog/forwardog.log")
    default_tags: str = os.getenv("DEFAULT_TAGS", "")
    max_requests_per_second: int = int(os.getenv("MAX_REQUESTS_PER_SECOND", "10"))
    max_payload_size_mb: int = int(os.getenv("MAX_PAYLOAD_SIZE_MB", "5"))
    max_history_items: int = int(os.getenv("MAX_HISTORY_ITEMS", "100"))
    
    @property
    def dd_api_url(self) -> str:
        return f"https://api.{self.dd_site}"
    
    @property
    def dd_logs_url(self) -> str:
        site_mapping = {
            "datadoghq.com": "https://http-intake.logs.datadoghq.com",
            "datadoghq.eu": "https://http-intake.logs.datadoghq.eu",
            "us3.datadoghq.com": "https://http-intake.logs.us3.datadoghq.com",
            "us5.datadoghq.com": "https://http-intake.logs.us5.datadoghq.com",
            "ap1.datadoghq.com": "https://http-intake.logs.ap1.datadoghq.com",
            "ddog-gov.com": "https://http-intake.logs.ddog-gov.com",
        }
        return site_mapping.get(self.dd_site, f"https://http-intake.logs.{self.dd_site}")
    
    @property
    def default_tags_list(self) -> list[str]:
        if not self.default_tags:
            return []
        return [tag.strip() for tag in self.default_tags.split(",") if tag.strip()]
    
    def is_configured(self) -> bool:
        return bool(self.dd_api_key)
    
    def get_masked_api_key(self) -> str:
        if not self.dd_api_key:
            return "(not configured)"
        if len(self.dd_api_key) <= 4:
            return "*" * len(self.dd_api_key)
        return "*" * (len(self.dd_api_key) - 4) + self.dd_api_key[-4:]

    class Config:
        env_file = ".env"


settings = Settings()
