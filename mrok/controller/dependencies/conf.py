from typing import Annotated

from fastapi import Depends

from mrok.conf import Settings, get_settings

AppSettings = Annotated[Settings, Depends(get_settings)]
