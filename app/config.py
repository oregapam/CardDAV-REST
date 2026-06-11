import os
from dataclasses import dataclass

_REQUIRED_VARS = ("BAIKAL_URL", "BAIKAL_USER", "BAIKAL_PASS", "API_KEY")


@dataclass(frozen=True)
class Settings:
    baikal_url: str
    baikal_user: str
    baikal_pass: str
    baikal_addressbook: str
    api_key: str

    @property
    def addressbook_url(self) -> str:
        base = self.baikal_url.rstrip("/")
        return f"{base}/addressbooks/{self.baikal_user}/{self.baikal_addressbook}/"


def load_settings() -> Settings:
    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return Settings(
        baikal_url=os.environ["BAIKAL_URL"],
        baikal_user=os.environ["BAIKAL_USER"],
        baikal_pass=os.environ["BAIKAL_PASS"],
        baikal_addressbook=os.getenv("BAIKAL_ADDRESSBOOK", "default"),
        api_key=os.environ["API_KEY"],
    )
