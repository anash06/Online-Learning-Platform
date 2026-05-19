import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENV: str = "development"
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "lms_db"
    
    # JWT & Hashing
    JWT_SECRET_KEY: str = "supersecretjwtaccesskeyforonlinelearningplatform2026"
    JWT_REFRESH_SECRET_KEY: str = "supersecretjwtrefreshkeyforonlinelearningplatform2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Razorpay Configuration
    RAZORPAY_KEY_ID: str = "rzp_test_samplekeyid12345"
    RAZORPAY_KEY_SECRET: str = "samplesecretkey67890"
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10485760
    
    # Email Simulation Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "noreply@example.com"
    SMTP_PASSWORD: str = "yoursecretmailpassword"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
