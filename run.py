import os

from app import create_app


def main() -> None:
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=env == "development")


if __name__ == "__main__":
    main()
