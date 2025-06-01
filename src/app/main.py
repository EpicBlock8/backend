import logging

from fastapi import (
    FastAPI,
)
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import RateLimit
from app.routers import get_routers
from app.shared import Logger, load_config

logger = Logger(__name__, level=logging.DEBUG).get_logger()

config = load_config()
endpoint = config.endpoint


# ================================================================================
#       FastAPI Setup
# ================================================================================
app = FastAPI()

# Routers must be added before web, otherwise the web routes will take precedence
for router in get_routers():
    app.include_router(router)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimit)


# ================================================================================
#       Command Line
# ================================================================================
def welcome():
    # Log server banner
    for line in config.general.title.split("\n"):
        logger.info(line)

    # Log server startup information
    logger.info("Starting metric collection server")


def main(argv=None):
    welcome()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.network.host,
        port=config.network.port,
        reload=config.network.reload,
    )


if __name__ == "__main__":
    main()
