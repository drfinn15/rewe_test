from pathlib import Path
from dataclasses import dataclass
from typing import ClassVar, Iterable, Optional, TypeVar
import logging

from tqdm import tqdm

from viktualien.util.tqdm_handler import TqdmHandler

R = TypeVar("R")  # pylint: disable=invalid-name


# Zentrale Klasse für Konfiguration, diese beinhaltet:
# - Speicherpfad für Cache
# - Flag ob detaillierte Ausgaben geloggt werden sollen
# - Flag ob Fortschritsbalken angezeigt werden sollen
# Standardmäßig werden diese Werte wie folgt belegt:
# - 'data' im aktuellen Verzeichnis
# - False
# - True
@dataclass(frozen=True)
class Config:
    data_path: Path = Path("data")
    verbose: bool = False
    progress: bool = True

    _config: ClassVar[Optional["Config"]] = None

    def _ensure_data_path(self) -> None:
        self.data_path.mkdir(parents=True, exist_ok=True)

    def cache_path(self) -> Path:
        self._ensure_data_path()
        return self.data_path / "cache.db"

    def logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if self.verbose:
            logger.setLevel(logging.INFO)
        if self.progress:
            handler: logging.Handler = TqdmHandler()
        else:
            handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(levelname)s %(name)s %(asctime)s %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.handlers = [handler]
        return logger

    def meter(self, iterable: Iterable[R]) -> Iterable[R]:
        if self.progress:
            return tqdm(iterable)
        return iterable

    @staticmethod
    def set(cfg) -> "Config":
        assert Config._config is None
        Config._config = cfg
        return cfg

    @staticmethod
    def get() -> "Config":
        assert Config._config is not None
        return Config._config
