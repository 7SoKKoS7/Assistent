from twilio.rest import Client
from config import twilio_account_sid, twilio_auth_token, twilio_whatsapp_number

client = Client(twilio_account_sid, twilio_auth_token)

def send_whatsapp_message(to, body):
    message = client.messages.create(
        body=body,
        from_=f'whatsapp:{twilio_whatsapp_number}',
        to=f'whatsapp:{to}'
    )
    return message.sid
