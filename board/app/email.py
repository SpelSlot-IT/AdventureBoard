from flask import current_app

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .provider import smtp_server

def notifications_enabled(email_config):
    return  email_config and email_config.get("active", False)

def init_email_app(app):
    """
    Initialize the SMTP connection and attach it to the Flask app.
    """
    email_config = app.config.get("EMAIL")
    
    if not notifications_enabled(email_config):
        app.logger.warning("Email configuration is missing or inactive. Skipping email setup.")
        return

    sender_email = email_config.get("address")
    sender_password = email_config.get("password")
    smtp_address = email_config.get("smtp_address", "smtp.gmail.com")  # default to Gmail
    smtp_port = email_config.get("smtp_port", 465)  # default SSL port
    
    smtp_server.connect(smtp_address, smtp_port)
    smtp_server.login(sender_email, sender_password)
    app.logger.info(f"SMTP server logged in successfully into {smtp_address}:{smtp_port}.")


def notify_user(user, message):
    """
    Send an email notification to a user.
    """
    email_config = current_app.config.get("EMAIL")
    if not notifications_enabled(email_config):
        current_app.logger.warning("Notifications are disabled. Skipping email notification.")
        return
        
    # Make sure user has an email
    if not hasattr(user, "email"):
        raise ValueError("User object must have an 'email' attribute.")
    
    sender_email = email_config.get("address", "signup.spelslot@gemail.com") # type: ignore
    receiver_email = user.email
    
    subject = "Notification"
    body = f"""
    Hello {getattr(user, 'name', 'Player')},
    
    {message}

    This is a automated notification email by spelslots signup system. Please do not respond to this email.
    """

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    smtp_server.sendmail(sender_email, receiver_email, msg.as_string())
    current_app.logger.info(f"Email sent to {receiver_email}")
