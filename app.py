from src.app_factory import create_app


app = create_app()


if __name__ == "__main__":
    app_config = app.config["APP_CONFIG"]
    app.run(host=app_config.host, port=app_config.port, debug=app_config.debug)
