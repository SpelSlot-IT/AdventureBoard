from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # This alters the column to TEXT so it can handle the long Google URL
        db.session.execute(text("ALTER TABLE users MODIFY profile_pic TEXT"))
        db.session.commit()
        print("Success! profile_pic column is now TEXT.")
    except Exception as e:
        print(f"Error: {e}")