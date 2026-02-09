from app import create_app
import os, webbrowser
from flask import render_template

print("Starting application...")
print(f"Current directory: {os.getcwd()}")
config_path = "app/config/config.local.json"
if not os.path.exists(config_path):
    print(f"ERROR: Config file not found at {config_path}")
    print(f"Expected absolute path: {os.path.abspath(config_path)}")
    print("Please create config.local.json based on config.example")
    exit(1)

# Use absolute path to avoid Flask path resolution issues
abs_config_path = os.path.abspath(config_path)
print(f"Loading config from: {abs_config_path}")
app = create_app(abs_config_path)
print("App created successfully")

if __name__ == "__main__":
    # local development only
    app.secret_key = os.urandom(24)

    # --- Apply old Basic provider routs ---
    @app.route('/')
    def home():
        return render_template('app.html')

    #webbrowser.open("https://localhost:5000")
    print("Backend app running on https://localhost:5000")
    app.run(ssl_context="adhoc")
