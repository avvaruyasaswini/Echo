import sqlite3
import json
import bcrypt

DB_FILE = "echo.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            scope TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, scope, key)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            scope TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            avatar TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash.decode('utf-8')))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
        return user[0]
    return None

def remember(user_id, scope, key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO memories (user_id, scope, key, value) VALUES (?, ?, ?, ?)", (user_id, scope, key, json.dumps(value)))
    conn.commit()
    conn.close()

def recall(user_id, scope, key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM memories WHERE user_id = ? AND scope = ? AND key = ?", (user_id, scope, key))
    result = cursor.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

def create_conversation(user_id, title, scope):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (user_id, title, scope) VALUES (?, ?, ?)", (user_id, title, scope))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_conversations(user_id, scope):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM conversations WHERE user_id = ? AND scope = ? ORDER BY created_at DESC", (user_id, scope))
    conversations = cursor.fetchall()
    conn.close()
    return conversations

def add_message(conversation_id, role, content, avatar):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (conversation_id, role, content, avatar) VALUES (?, ?, ?, ?)", (conversation_id, role, content, avatar))
    conn.commit()
    conn.close()

def get_messages(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, avatar, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """, (conversation_id,))
    messages = [
        {"role": row[0], "content": row[1], "avatar": row[2], "timestamp": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return messages

def get_conversation_title(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
    title = cursor.fetchone()
    conn.close()
    return title[0] if title else None

def update_password(user_id, current_password, new_password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user and bcrypt.checkpw(current_password.encode('utf-8'), user[0].encode('utf-8')):
        # Current password is correct, hash and update the new one
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash.decode('utf-8'), user_id))
        conn.commit()
        conn.close()
        return True
    else:
        # Incorrect current password
        conn.close()
        return False

def clear_conversation(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()

# --- ADD THE NEW FUNCTION RIGHT HERE, AT THE END OF THE FILE ---

def delete_conversation(conversation_id):
    """Deletes a conversation and all its messages."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # First, delete all messages associated with the conversation
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    # Then, delete the conversation itself
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()

def update_conversation_title(conversation_id, new_title):
    """Updates the title of a specific conversation."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id))
    conn.commit()
    conn.close()