import tkinter as tk
from tkinter import scrolledtext

def send_message():
    user_message = user_input.get()
    chat_window.insert(tk.END, f"User: {user_message}\n")
    user_input.set("")

def create_gui():
    window = tk.Tk()
    window.title("Chat Assistant")

    global chat_window
    chat_window = scrolledtext.ScrolledText(window, wrap=tk.WORD)
    chat_window.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    global user_input
    user_input = tk.StringVar()
    user_entry = tk.Entry(window, textvariable=user_input)
    user_entry.pack(padx=10, pady=5, fill=tk.X)

    send_button = tk.Button(window, text="Send", command=send_message)
    send_button.pack(padx=10, pady=5)

    window.mainloop()

if __name__ == "__main__":
    create_gui()
