import sqlite3

def create_db():
    conn = sqlite3.connect('important_notes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY, note TEXT)''')
    conn.commit()
    conn.close()

def save_important_info(info):
    conn = sqlite3.connect('important_notes.db')
    c = conn.cursor()
    c.execute("INSERT INTO notes (note) VALUES (?)", (info,))
    conn.commit()
    conn.close()

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
