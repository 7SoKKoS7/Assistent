import os
import json
import requests
from google.cloud import storage
from dotenv import load_dotenv
from googletrans import Translator

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка клиента для Google Cloud Storage
storage_client = storage.Client()
bucket_name = os.getenv("BUCKET_NAME")
bucket = storage_client.bucket(bucket_name)

# Настройка переводчика
translator = Translator()

# Функция для сохранения данных в облако
def save_to_cloud_storage(filename, data):
    blob = bucket.blob(filename)
    blob.upload_from_string(data)
    return f"File {filename} uploaded to {bucket_name}."

# Функция для загрузки данных из облака
def load_from_cloud_storage(filename):
    blob = bucket.blob(filename)
    data = blob.download_as_string()
    return data

# Функция для получения данных о погоде
def get_weather(api_key, location):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric&lang=ru"
    response = requests.get(url)
    weather_data = response.json()
    if weather_data.get("cod") != 200:
        return "Не удалось получить данные о погоде."
    temp = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]
    return f"Температура: {temp}°C\nОписание: {description}"

# Функция для получения новостей
def get_news(api_key):
    url = f"http://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    response = requests.get(url)
    news_data = response.json()
    articles = news_data.get("articles", [])
    headlines = [article["title"] for article in articles]
    translated_headlines = [translator.translate(headline, src='en', dest='ru').text for headline in headlines]
    return "\n".join(translated_headlines)
