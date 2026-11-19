from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BlueIsland Coffee API"
    api_prefix: str = "/api"
    secret_key: str = "change-me-before-deployment"
    access_token_expire_minutes: int = 480
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "blueisland_cafe"
    mysql_user: str = "root"
    mysql_password: str = ""
    cors_origins: str = "http://127.0.0.1:5500,http://localhost:5500"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        return (f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
