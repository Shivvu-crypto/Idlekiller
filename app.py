from flask import Flask, render_template, request, jsonify, session, send_from_directory
import sqlite3
import time
import os
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'my-super-secret-key-12345'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, creator TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, sender TEXT, content TEXT, timestamp INTEGER, file_path TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS blogs (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, timestamp INTEGER, file_path TEXT)''')
    c.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', ('admin', 'admin123'))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/join/<int:room_id>')
def join_room(room_id):
    return render_template('index.html', join_room_id=room_id)

@app.route('/blog/<int:blog_id>')
def view_blog(blog_id):
    return render_template('index.html', view_blog_id=blog_id)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'status': 'error', 'message': 'Username and password required'})
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            logger.info(f"User {username} logged in successfully")
            return jsonify({'status': 'success', 'username': username})
        logger.warning(f"Login failed for {username}")
        return jsonify({'status': 'error', 'message': 'Invalid credentials'})
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Login error: {str(e)}'}), 500

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        if c.fetchone():
            conn.close()
            logger.warning(f"Signup failed: {username} already exists")
            return jsonify({'status': 'error', 'message': 'Username already exists'})
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        logger.info(f"User {username} signed up successfully")
        return jsonify({'status': 'success', 'message': 'User created'})
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Signup error: {str(e)}'}), 500

@app.route('/rooms', methods=['GET', 'POST'])
def rooms():
    try:
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        username = session.get('username')
        if not username:
            logger.warning("Rooms accessed without login")
            return jsonify({'status': 'error', 'message': 'Not logged in'})
        if request.method == 'POST':
            data = request.get_json()
            room_name = data.get('room_name')
            if not room_name:
                return jsonify({'status': 'error', 'message': 'Room name required'})
            c.execute('INSERT INTO rooms (name, creator) VALUES (?, ?)', (room_name, username))
            conn.commit()
            logger.info(f"Room {room_name} created by {username}")
        c.execute('SELECT * FROM rooms WHERE creator = ?', (username,))
        rooms = [{'id': r[0], 'name': r[1], 'creator': r[2]} for r in c.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'rooms': rooms})
    except Exception as e:
        logger.error(f"Rooms error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Rooms error: {str(e)}'}), 500

@app.route('/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    try:
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'Not logged in'})
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT creator FROM rooms WHERE id = ?', (room_id,))
        room = c.fetchone()
        if not room or room[0] != username:
            conn.close()
            return jsonify({'status': 'error', 'message': 'You can only delete your own rooms'})
        c.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
        c.execute('DELETE FROM messages WHERE room_id = ?', (room_id,))
        conn.commit()
        conn.close()
        logger.info(f"Room {room_id} deleted by {username}")
        return jsonify({'status': 'success', 'message': 'Room deleted'})
    except Exception as e:
        logger.error(f"Delete room error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Delete room error: {str(e)}'}), 500

@app.route('/messages/<int:room_id>', methods=['GET'])
def get_messages(room_id):
    try:
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': 'Room not found'})
        c.execute('SELECT * FROM messages WHERE room_id = ? ORDER BY timestamp ASC', (room_id,))
        messages = [{'id': m[0], 'room_id': m[1], 'sender': m[2], 'content': m[3], 'timestamp': m[4], 'file_path': m[5]} for m in c.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'messages': messages})
    except Exception as e:
        logger.error(f"Messages error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Messages error: {str(e)}'}), 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'Not logged in'})
        file_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{int(time.time())}_{filename}")
                file.save(file_path)
                logger.info(f"File uploaded: {file_path}")
        data = request.form
        room_id = data.get('room_id')
        content = data.get('content', '')
        if not room_id:
            return jsonify({'status': 'error', 'message': 'Room ID required'})
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT INTO messages (room_id, sender, content, timestamp, file_path) VALUES (?, ?, ?, ?, ?)',
                  (room_id, username, content, int(time.time() * 1000), file_path))
        conn.commit()
        conn.close()
        logger.info(f"Message posted in room {room_id} by {username}")
        return jsonify({'status': 'success', 'message': 'Message posted'})
    except Exception as e:
        logger.error(f"Post message error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Post message error: {str(e)}'}), 500

@app.route('/blogs', methods=['GET', 'POST'])
def blogs():
    try:
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        username = session.get('username')
        if not username:
            logger.warning("Blogs accessed without login")
            return jsonify({'status': 'error', 'message': 'Not logged in'})
        if request.method == 'POST':
            file_path = None
            if 'file' in request.files:
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{int(time.time())}_{filename}")
                    file.save(file_path)
                    logger.info(f"File uploaded for blog: {file_path}")
                else:
                    logger.warning(f"Invalid file upload attempt: {file.filename if file else 'No file'}")
                    return jsonify({'status': 'error', 'message': 'Invalid file type'})
            data = request.form
            content = data.get('content', '')
            if not content and not file_path:
                logger.warning("Blog post attempted without content or file")
                return jsonify({'status': 'error', 'message': 'Content or file required'})
            c.execute('INSERT INTO blogs (author, content, timestamp, file_path) VALUES (?, ?, ?, ?)', 
                      (username, content, int(time.time() * 1000), file_path))
            conn.commit()
            logger.info(f"Blog posted by {username}")
        c.execute('SELECT * FROM blogs WHERE author = ?', (username,))
        blogs = [{'id': b[0], 'author': b[1], 'content': b[2], 'timestamp': b[3], 'file_path': b[4]} for b in c.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'blogs': blogs})
    except Exception as e:
        logger.error(f"Blogs error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Blogs error: {str(e)}'}), 500

@app.route('/blogs/<int:blog_id>', methods=['GET', 'DELETE'])
def blog(blog_id):
    try:
        conn = sqlite3.connect('idlekiller.db', check_same_thread=False)
        c = conn.cursor()
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'Not logged in'})
        if request.method == 'DELETE':
            c.execute('SELECT author FROM blogs WHERE id = ?', (blog_id,))
            blog = c.fetchone()
            if not blog or blog[0] != username:
                conn.close()
                return jsonify({'status': 'error', 'message': 'You can only delete your own blogs'})
            c.execute('DELETE FROM blogs WHERE id = ?', (blog_id,))
            conn.commit()
            conn.close()
            logger.info(f"Blog {blog_id} deleted by {username}")
            return jsonify({'status': 'success', 'message': 'Blog deleted'})
        c.execute('SELECT * FROM blogs WHERE id = ? AND author = ?', (blog_id, username))
        blog = c.fetchone()
        conn.close()
        if blog:
            return jsonify({'status': 'success', 'blog': {'id': blog[0], 'author': blog[1], 'content': blog[2], 'timestamp': blog[3], 'file_path': blog[4]}})
        return jsonify({'status': 'error', 'message': 'Blog not found or not yours'})
    except Exception as e:
        logger.error(f"Blog error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Blog error: {str(e)}'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"File error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'File error: {str(e)}'}), 500

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='0.0.0.0', port=5001, debug=True)