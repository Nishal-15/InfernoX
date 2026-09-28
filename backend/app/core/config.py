from typing import List, Union, Any, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, model_validator

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "InfernoX"
    VERSION: str = "v1.0.0-RC1"
    
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "thermal_db"
    POSTGRES_PORT: str = "5432"
    SQLALCHEMY_DATABASE_URI: str | None = None

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

    # FIRMS Configuration
    FIRMS_MAP_KEY: str = ""
    FIRMS_SOURCE: str = "VIIRS_SNPP_NRT"
    FIRMS_AREA: str = "68,7,97,36" # Default India BBOX
    FIRMS_DAYS: int = 1
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    FIRMS_API_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    FIRMS_INGEST_INTERVAL_MINUTES: int = 15
    HISTORICAL_DATA_DIR: str = "data/historical/firms"

    # Multi-Satellite Source Registry (Section 5)
    # Configurable satellite instruments with priority, refresh interval, and activation flag
    FIRMS_SOURCES_REGISTRY: list[dict[str, Any]] = [
        {
            "source_name": "VIIRS_SNPP_NRT",
            "enabled": True,
            "priority": 1,
            "refresh_interval_minutes": 15,
            "satellite": "Suomi NPP",
            "instrument": "VIIRS",
            "resolution_m": 375,
            "description": "Suomi NPP VIIRS 375m active fire data (Primary NRT)"
        },
        {
            "source_name": "VIIRS_NOAA20_NRT",
            "enabled": True,
            "priority": 2,
            "refresh_interval_minutes": 15,
            "satellite": "NOAA-20",
            "instrument": "VIIRS",
            "resolution_m": 375,
            "description": "NOAA-20 (JPSS-1) VIIRS 375m active fire data"
        },
        {
            "source_name": "VIIRS_NOAA21_NRT",
            "enabled": True,
            "priority": 3,
            "refresh_interval_minutes": 15,
            "satellite": "NOAA-21",
            "instrument": "VIIRS",
            "resolution_m": 375,
            "description": "NOAA-21 (JPSS-2) VIIRS 375m active fire data"
        },
        {
            "source_name": "MODIS_NRT",
            "enabled": False,
            "priority": 4,
            "refresh_interval_minutes": 60,
            "satellite": "Terra/Aqua",
            "instrument": "MODIS",
            "resolution_m": 1000,
            "description": "Terra and Aqua MODIS 1km active fire data (Secondary)"
        }
    ]

    # OSM Configuration
    OSM_OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OSM_BBOX: str = "68,7,97,36"

    # Phase 3: Temporal & Intelligence Parameters
    TEMPORAL_LOOKBACK_DAYS: int = 90
    SPATIAL_CLUSTER_RADIUS_METERS: float = 1000.0
    PERSISTENCE_MIN_ACTIVE_DAYS: int = 5
    RECURRING_MIN_DETECTIONS: int = 2
    ABNORMAL_FRP_MULTIPLIER: float = 2.5
    INDUSTRIAL_PROXIMITY_THRESHOLD_METERS: float = 2000.0
    DEMO_MODE: bool = False

    # Phase 4: Land Cover & Satellite Intelligence
    ESA_WORLDCOVER_VERSION: str = "v200 (2021)"
    ESA_WORLDCOVER_DATA_PATH: str | None = None
    SATELLITE_PROVIDER: str = "sentinel2"
    MAX_SATELLITE_CLOUD_COVER: float = 30.0
    SATELLITE_SEARCH_DAYS_WINDOW: int = 10
    STAC_API_URL: str = "https://earth-search.aws.element84.com/v1"
    MODEL_REGISTRY_PATH: str = "models"
    ACTIVE_MODEL_VERSION: str = "xgb-v1"
    FALLBACK_TO_PROTOTYPE: bool = True

    # Phase 8: Autonomous Pipeline & Monitoring
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 1.0
    PIPELINE_TIMEOUT_SECONDS: float = 60.0
    SATELLITE_TIMEOUT_SECONDS: float = 10.0
    ALERT_COOLDOWN_MINUTES: int = 60
    INCIDENT_CORRELATION_RADIUS_METERS: float = 1500.0
    INCIDENT_CORRELATION_HOURS: float = 48.0
    AUTO_FLY_ENABLED_DEFAULT: bool = False
    LIVE_UPDATE_INTERVAL_SECONDS: int = 15
    DEMO_EVENT_ENABLED: bool = True

    # Phase 9: SaaS, Multi-Tenancy, RBAC & Billing
    JWT_SECRET_KEY: str = "inferno-x-production-saas-jwt-secret-key-2026-secure-token-hash"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Razorpay Integration
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder"
    RAZORPAY_KEY_SECRET: str = "rzp_secret_placeholder"
    RAZORPAY_WEBHOOK_SECRET: str = "rzp_webhook_secret_placeholder"
    
    # Email Provider
    EMAIL_PROVIDER: str = "console"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@infernox.ai"

    # Plan Limits Defaults
    MAX_FREE_USERS: int = 2
    MAX_FREE_FACILITIES: int = 5
    MAX_FREE_REPORTS_PER_MONTH: int = 5
    MAX_FREE_REPORTS: int = 5
    MAX_FREE_API_REQUESTS: int = 100
    MAX_FREE_ALERT_RULES: int = 3

    MAX_PRO_USERS: int = 15
    MAX_PRO_FACILITIES: int = 50
    MAX_PRO_REPORTS_PER_MONTH: int = 100
    MAX_PRO_REPORTS: int = 200
    MAX_PRO_API_REQUESTS: int = 10000
    MAX_PRO_ALERT_RULES: int = 25

    EMAILS_FROM_EMAIL: str = "noreply@infernox.ai"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()

