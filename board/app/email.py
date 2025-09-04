from flask import current_app

from flask_mail import Message
from .provider import mail

def notifications_enabled(email_config):
    return  email_config and email_config.get("active", False)

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
    
    subject = "Spelslot Signup System Notification"
    body = f"""
    Hello {getattr(user, 'name', 'Player')},
    
    {message}

    This is a automated notification email by spelslots signup system. Please do not respond to this email. 
    Any information in this mail is without guarantee, please always check signup.spelslot.com for more information.
    """

    # Create the email
    msg = Message(
        subject=subject, 
        sender=sender_email,
        recipients=receiver_email
    )
    msg.body = body

    # Send the email
    mail.send(msg)
    current_app.logger.info(f"Email sent to {receiver_email}")
