import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка ключей API
openai_api_key = os.getenv("OPENAI_API_KEY")
google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
telegram_api_key = os.getenv("TELEGRAM_API_KEY")
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
bucket_name = os.getenv("BUCKET_NAME")
news_api_key = os.getenv("NEWS_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")

# Установка учетных данных для Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials
