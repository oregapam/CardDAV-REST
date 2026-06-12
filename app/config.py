import os
from dataclasses import dataclass
from typing import Literal

_REQUIRED_VARS = ("BAIKAL_URL", "BAIKAL_USER", "BAIKAL_PASS", "API_KEY")

NameFormat = Literal["western", "eastern", "eastern_full"]
_VALID_NAME_FORMATS: tuple[str, ...] = ("western", "eastern", "eastern_full")


@dataclass(frozen=True)
class Settings:
    baikal_url: str
    baikal_user: str
    baikal_pass: str
    api_key: str
    name_format: NameFormat = "western"

    @property
    def principal_url(self) -> str:
        base = self.baikal_url.rstrip("/")
        return f"{base}/addressbooks/{self.baikal_user}/"


def load_settings() -> Settings:
    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    raw_format = os.getenv("NAME_FORMAT", "western")
    if raw_format not in _VALID_NAME_FORMATS:
        raise RuntimeError(
            f"Invalid NAME_FORMAT '{raw_format}'. Must be one of: {', '.join(_VALID_NAME_FORMATS)}"
        )
    return Settings(
        baikal_url=os.environ["BAIKAL_URL"],
        baikal_user=os.environ["BAIKAL_USER"],
        baikal_pass=os.environ["BAIKAL_PASS"],
        api_key=os.environ["API_KEY"],
        name_format=raw_format,  # type: ignore[arg-type]
    )
