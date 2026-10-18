from decimal import Decimal
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str
    jwt_secret: str = Field(min_length=48)
    jwt_issuer: str = 'freedom-api'
    jwt_audience: str = 'freedom-web'
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    cors_origins: list[str] = ['http://localhost:5173']
    smtp_host: str = 'localhost'
    smtp_port: int = 1025
    smtp_starttls: bool = True
    smtp_username: str = ''
    smtp_password: str = ''
    mail_from: str = 'no-reply@example.com'
    frontend_reset_url: str = 'http://localhost:5173/reset-password'
    shipping_fee: Decimal = Field(default=Decimal('30000'), ge=0)
    media_root: Path = Path(__file__).resolve().parents[1] / 'uploads'

settings = Settings()
