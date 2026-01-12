#!/usr/bin/env python3
"""Run the MoIP Manager web application."""
import uvicorn
import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        reload=True
    )
