import os
from pathlib import Path

from dotenv import find_dotenv
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudFront(BaseModel):
    key_pair_id: str
    signature: SecretStr
    policy: SecretStr


class Area(BaseModel):
    apex: str = Field("46.90946, 30.19284")
    vertex: str = Field("46.10655, 31.39070")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(), env_file_encoding="utf-8", extra="ignore", env_nested_delimiter="__"
    )
    cloud_front: CloudFront
    area: Area
    cache_dir: str = Field(str(Path(os.path.abspath(os.path.dirname(__file__)), "../cache").resolve()))


config = Settings()
