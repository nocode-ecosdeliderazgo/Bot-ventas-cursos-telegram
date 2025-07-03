from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    telegram_api_token: str
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    advisor_email: str
    class Config:
        env_file = ".env"

settings = Settings() 