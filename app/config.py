from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dd_api_key: str = ""
    dd_site: str = "datadoghq.com"
    dd_agent_host: str = "127.0.0.1"
    dogstatsd_port: int = 8125
    max_requests_per_second: int = 10
    max_payload_size_mb: int = 5
    max_history_items: int = 100
    
    @property
    def forwardog_log_path(self) -> str:
        return "/var/log/forwardog/forwardog.log"
    
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
    def dd_events_url(self) -> str:
        site_mapping = {
            "datadoghq.com": "https://event-management-intake.datadoghq.com",
            "datadoghq.eu": "https://event-management-intake.datadoghq.eu",
            "us3.datadoghq.com": "https://event-management-intake.us3.datadoghq.com",
            "us5.datadoghq.com": "https://event-management-intake.us5.datadoghq.com",
            "ap1.datadoghq.com": "https://event-management-intake.ap1.datadoghq.com",
            "ddog-gov.com": "https://event-management-intake.ddog-gov.com",
        }
        return site_mapping.get(self.dd_site, f"https://event-management-intake.{self.dd_site}")
    
    @property
    def default_tags_list(self) -> list[str]:
        return ["source:forwardog"]
    
    def is_configured(self) -> bool:
        return bool(self.dd_api_key)
    
    def get_masked_api_key(self) -> str:
        if not self.dd_api_key:
            return "(not configured)"
        if len(self.dd_api_key) <= 4:
            return "*" * len(self.dd_api_key)
        return "*" * (len(self.dd_api_key) - 4) + self.dd_api_key[-4:]


settings = Settings()
