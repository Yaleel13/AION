"""Entry-point script to run the AION server."""

import uvicorn
from aion import config

if __name__ == "__main__":
    uvicorn.run(
        "aion.main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=True,
    )
