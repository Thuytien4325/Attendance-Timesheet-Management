from __future__ import annotations

from src.attendance_system.attendance_system.main import create_app

__all__ = ["create_app"]


if __name__ == "__main__":
	app = create_app()
	app.run(debug=bool(app.config.get("DEBUG", False)))
