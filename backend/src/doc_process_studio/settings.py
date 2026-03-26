from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "my-service"
    env: str = "dev"
    db_dsn: str | None = None

    class Config:
        env_prefix = "APP_"
        env_file = ".env"


settings = Settings()
