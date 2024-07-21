import openai
import os
import json
import requests
import sqlite3
import tkinter as tk
from tkinter import scrolledtext, Canvas
from google.cloud import storage, texttospeech, speech_v1p1beta1 as speech
from dotenv import load_dotenv
import telebot
from telebot import types
import speech_recognition as sr
from langdetect import detect
from twilio.rest import Client
from pydub import AudioSegment
from pydub.playback import play
import threading
import time
from googletrans import Translator

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка ключей API
openai.api_key = os.getenv("OPENAI_API_KEY")
google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials

# Настройка клиента для Google Cloud Storage
storage_client = storage.Client()
bucket_name = os.getenv("BUCKET_NAME")
bucket = storage_client.bucket(bucket_name)

# Настройка клиента для Google Text-to-Speech
tts_client = texttospeech.TextToSpeechClient()

# Настройка клиента для Google Speech-to-Text
stt_client = speech.SpeechClient()

# Настройка клиента для Telegram
telegram_api_key = os.getenv("TELEGRAM_API_KEY")
bot = telebot.TeleBot(telegram_api_key)

# Настройка клиента для Twilio (WhatsApp)
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Проверка наличия учетных данных для Twilio
if not twilio_account_sid or not twilio_auth_token or not twilio_whatsapp_number:
    raise ValueError("Twilio credentials are not set in the environment variables.")

client = Client(twilio_account_sid, twilio_auth_token)

# История чата
chat_history = []

# Настройка переводчика
translator = Translator()

# Глобальная переменная для состояния микрофона
mic_active = True
response_active = False

# Проверка и создание необходимых файлов и папок
def check_and_create_files():
    if not os.path.exists('important_notes.db'):
        create_db()

# Функция для добавления сообщений в историю
def add_to_chat_history(message):
    if len(chat_history) >= 10:
        chat_history.pop(0)
    chat_history.append(message)

# Функция для получения последних 10 сообщений
def get_last_10_messages():
    return chat_history

# Функция для преобразования текста в речь
def text_to_speech(text, language_code="ru-RU"):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

# Функция для воспроизведения аудио
def play_audio(audio_content):
    global response_active
    response_active = True
    filename = "output.mp3"
    with open(filename, "wb") as out:
        out.write(audio_content)
    audio = AudioSegment.from_mp3(filename)
    play(audio)
    response_active = False

# Функция для преобразования речи в текст
def speech_to_text(audio_content, language_code="ru-RU"):
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
    )
    response = stt_client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript if response.results else ""

# Функция для взаимодействия с ChatGPT
def chat_with_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response['choices'][0]['message']['content'].strip()

# Функция для многоязычной поддержки
def chat_with_gpt_multilang(prompt):
    lang = detect(prompt)
    response = chat_with_gpt(prompt)
    return response

# Функция для получения новостей
def get_news(api_key):
    url = f"http://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    response = requests.get(url)
    news_data = response.json()
    articles = news_data.get("articles", [])
    headlines = [article["title"] for article in articles]
    translated_headlines = [translator.translate(headline, src='en', dest='ru').text for headline in headlines]
    return "\n".join(translated_headlines)

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

# Функция для синхронизации истории чата с Google Cloud Storage
def sync_chat_history():
    history_data = json.dumps(chat_history)
    save_to_cloud_storage("chat_history.json", history_data)

def load_chat_history():
    try:
        history_data = load_from_cloud_storage("chat_history.json")
        global chat_history
        chat_history = json.loads(history_data)
    except Exception as e:
        print("No existing chat history found.")

# Функция для синхронизации важных заметок с Google Cloud Storage
def sync_important_notes():
    conn = sqlite3.connect('important_notes.db')
    c = conn.cursor()
    c.execute("SELECT * FROM notes")
    notes = c.fetchall()
    notes_data = json.dumps(notes)
    save_to_cloud_storage("important_notes.json", notes_data)
    conn.close()

def load_important_notes():
    try:
        notes_data = load_from_cloud_storage("important_notes.json")
        notes = json.loads(notes_data)
        conn = sqlite3.connect('important_notes.db')
        c = conn.cursor()
        c.execute("DELETE FROM notes")
        c.executemany("INSERT INTO notes (id, note) VALUES (?, ?)", notes)
        conn.commit()
        conn.close()
    except Exception as e:
        print("No existing important notes found.")

# Функция для создания базы данных для важных заметок
def create_db():
    conn = sqlite3.connect('important_notes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY, note TEXT)''')
    conn.commit()
    conn.close()

# Функция для проверки ключевых слов и сохранения важной информации
def check_and_save_important_info(message):
    important_keywords = ["запомни это как важное", "добавить в важное", "сохранить как важное", "записать как важное"]
    if any(keyword in message.lower() for keyword in important_keywords):
        save_important_info(message)
        return "Важная информация сохранена."
    return None

# Функция для отправки сообщений в графическом интерфейсе
def send_message(event=None):
    user_message = user_input.get()
    chat_window.insert(tk.END, f"User: {user_message}\n")
    important_response = check_and_save_important_info(user_message)
    if important_response:
        response = important_response
    else:
        if "погода" in user_message.lower():
            response = get_weather(os.getenv("WEATHER_API_KEY"), "Moscow")
        elif "новости" in user_message.lower():
            response = get_news(os.getenv("NEWS_API_KEY"))
        else:
            response = chat_with_gpt_multilang(user_message)
    chat_window.insert(tk.END, f"Assistant: {response}\n")
    audio_response = text_to_speech(response, language_code="ru-RU")
    threading.Thread(target=play_audio, args=(audio_response,)).start()
    user_input.set("")
    sync_chat_history()

# Функция для сохранения важной информации
def save_important_info(info):
    conn = sqlite3.connect('important_notes.db')
    c = conn.cursor()
    c.execute("INSERT INTO notes (note) VALUES (?)", (info,))
    conn.commit()
    conn.close()
    sync_important_notes()

# Функция для обработки голосового ввода
def voice_input():
    global response_active
    if response_active:
        return

    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        chat_window.insert(tk.END, f"User (Voice): {text}\n")
        important_response = check_and_save_important_info(text)
        if important_response:
            response = important_response
        else:
            if "погода" in text.lower():
                response = get_weather(os.getenv("WEATHER_API_KEY"), "Moscow")
            elif "новости" in text.lower():
                response = get_news(os.getenv("NEWS_API_KEY"))
            else:
                response = chat_with_gpt_multilang(text)
        chat_window.insert(tk.END, f"Assistant: {response}\n")
        audio_response = text_to_speech(response, language_code="ru-RU")
        threading.Thread(target=play_audio, args=(audio_response,)).start()
        sync_chat_history()
    except sr.UnknownValueError:
        chat_window.insert(tk.END, "Assistant: Sorry, I did not understand that.\n")
    except sr.RequestError:
        chat_window.insert(tk.END, "Assistant: Sorry, there was an issue with the request.\n")

# Функция для индикации голоса
def update_voice_indicator(canvas):
    global mic_active
    canvas.delete("all")
    if mic_active:
        canvas.create_oval(10, 10, 50, 50, fill="green")
    else:
        canvas.create_oval(10, 10, 50, 50, fill="red")
    canvas.after(500, update_voice_indicator, canvas)

# Функция для создания графического интерфейса
def create_gui():
    global window
    window = tk.Tk()
    window.title("Chat Assistant")

    global chat_window
    chat_window = scrolledtext.ScrolledText(window, wrap=tk.WORD)
    chat_window.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    global user_input
    user_input = tk.StringVar()
    user_entry = tk.Entry(window, textvariable=user_input)
    user_entry.pack(padx=10, pady=5, fill=tk.X)
    user_entry.bind("<Return>", send_message)

    send_button = tk.Button(window, text="Send", command=send_message)
    send_button.pack(padx=10, pady=5)

    mute_button = tk.Button(window, text="Mute", command=toggle_mic)
    mute_button.pack(padx=10, pady=5)

    voice_canvas = Canvas(window, width=60, height=60, bg="white")
    voice_canvas.pack(padx=10, pady=5)

    exit_button = tk.Button(window, text="Exit", command=exit_program)
    exit_button.pack(padx=10, pady=5)

    window.protocol("WM_DELETE_WINDOW", exit_program)
    window.after(500, update_voice_indicator, voice_canvas)
    window.mainloop()

def toggle_mic():
    global mic_active
    mic_active = not mic_active

def exit_program():
    sync_chat_history()
    sync_important_notes()
    window.destroy()

# Обработчики команд для Telegram бота
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! How can I assist you today?")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    response = chat_with_gpt_multilang(message.text)
    bot.reply_to(message, response)

# Функция для отправки сообщений в WhatsApp с использованием Twilio
def send_whatsapp_message(to, body):
    message = client.messages.create(
        body=body,
        from_=f'whatsapp:{twilio_whatsapp_number}',
        to=f'whatsapp:{to}'
    )
    return message.sid

# Функция для запуска Telegram бота
def run_telegram_bot():
    bot.polling()

if __name__ == "__main__":
    # Проверка и создание необходимых файлов и папок
    check_and_create_files()

    # Загрузка истории чата и важных заметок из облака
    load_chat_history()
    load_important_notes()

    # Запуск графического интерфейса
    threading.Thread(target=create_gui).start()

    # Запуск Telegram бота
    threading.Thread(target=run_telegram_bot).start()

    # Запуск прослушивания голосовых команд
    while True:
        if mic_active:
            voice_input()
        time.sleep(1)
