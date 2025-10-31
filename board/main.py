from .app import create_app
import os, webbrowser
from flask import render_template

app = create_app("config/config.local.json")

if __name__ == "__main__":
    # local development only
    app.secret_key = os.urandom(24)

    # --- Apply old Basic provider routs ---
    @app.route('/')
    def home():
        return render_template('app.html')

    @app.route('/help')
    def send_help():
        return render_template('help.html')

    @app.route('/profile/me')
    def view_own_profile():
        return render_template('profile.html', user_id="me")

    @app.route('/profile/<int:user_id>')
    def view_profile(user_id):
        return render_template('profile.html', user_id=user_id)


    webbrowser.open("https://localhost:5000")
    app.run(ssl_context="adhoc")
