import logging

from uvicorn.config import Config
from uvicorn.lifespan.on import LifespanOn


class MrokLifespan(LifespanOn):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.logger = logging.getLogger("mrok.proxy")
