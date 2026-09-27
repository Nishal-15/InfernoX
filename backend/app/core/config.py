from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, model_validator

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Thermal Intelligence"
    
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
    FIRMS_API_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    FIRMS_INGEST_INTERVAL_MINUTES: int = 15

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

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
