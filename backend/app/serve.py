import sys
import uvicorn
from app.config import load_settings


def main():
    try:
        settings = load_settings()
        uvicorn.run("app.main:create_app", factory=True, host=settings.host, port=settings.port,
                    log_level=settings.log_level, access_log=False)
        return 0
    except Exception:
        print("Application startup failed; check documented configuration", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
