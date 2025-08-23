from app import create_app
import os, webbrowser

app = create_app("config/config.local.json")

if __name__ == "__main__":
    # local development only
    app.secret_key = os.urandom(24)
    webbrowser.open("https://localhost:5000/app")
    app.run(ssl_context="adhoc")
