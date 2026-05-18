import os
import shutil
import webbrowser
import threading
import random
import re
import calendar
import json
from datetime import datetime, date, timedelta
from collections import Counter

# ============================================================
# БЛОК 1: ПРИВЕТСТВИЕ И ОЧИСТКА
# ============================================================


# Принудительная очистка старых файлов, чтобы избежать конфликтов
paths_to_clean = ['moodmap.db', 'instance']
for path in paths_to_clean:
    try:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
    except Exception as e:
        print(f"[WARN] Не удалось удалить {path}: {e}")

# Полная очистка старой папки app
if os.path.exists('app'):
    try:
        shutil.rmtree('app', ignore_errors=True)
    except:
        pass

# ============================================================
# БЛОК 2: СОЗДАНИЕ СТРУКТУРЫ ПАПОК
# ============================================================
folders = [
    'app',
    'app/blueprints',
    'app/templates',
    'app/templates/social',
    'app/templates/chat',
    'app/templates/admin',
    'app/templates/groups',
    'app/templates/email',
    'app/static',
    'app/static/uploads',
    'app/static/banners',
    'app/static/icons',
    'app/static/chat_bg',
    'app/static/sounds'
]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# ============================================================
# БЛОК 3: CONFIG.PY
# ============================================================
with open('config.py', 'w', encoding='utf-8') as f:
    f.write("""import os

class Config:
    # Основные настройки Flask
    SECRET_KEY = "moodmap-ultimate-secret-key-2024"

    # Настройки базы данных
    SQLALCHEMY_DATABASE_URI = "sqlite:///moodmap.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Пути для загрузки файлов
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "app", "static", "uploads")
    BANNER_FOLDER = os.path.join(os.getcwd(), "app", "static", "banners")
    CHAT_BG_FOLDER = os.path.join(os.getcwd(), "app", "static", "chat_bg")

    # Настройки почты (заглушка)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = "your-email@gmail.com"
    MAIL_PASSWORD = "your-password"
""")


# ============================================================
# БЛОК 4: APP/__INIT__.PY
# ============================================================
with open('app/__init__.py', 'w', encoding='utf-8') as f:
    f.write("""from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config
import os

# Глобальные объекты расширений
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    # Создание приложения Flask
    app = Flask(__name__)
    app.config.from_object(Config)

    # Создание папок для загрузок, если их нет
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["BANNER_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CHAT_BG_FOLDER"], exist_ok=True)

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    socketio.init_app(app)

    # Регистрация Blueprint'ов
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.social import social_bp
    from app.blueprints.chat import chat_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp
    from app.blueprints.groups import groups_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(social_bp, url_prefix="/social")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(groups_bp, url_prefix="/groups")

    # Специальные маршруты для PWA
    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('static', 'manifest.json')

    @app.route('/sw.js')
    def service_worker():
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')

    return app
""")


# ============================================================
# БЛОК 5: APP/MODELS.PY (ПОЛНАЯ МОДЕЛЬ ДАННЫХ)
# ============================================================
with open('app/models.py', 'w', encoding='utf-8') as f:
    f.write("""from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import random

# ----------------------------------------------------------
# ЗАГРУЗЧИК ПОЛЬЗОВАТЕЛЯ
# ----------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------------------------------------
# ТАБЛИЦА ДЛЯ ДРУЗЕЙ (МНОГО-КО-МНОГИМ)
# ----------------------------------------------------------
friends_table = db.Table(
    'friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# ----------------------------------------------------------
# МОДЕЛЬ: ЗАЯВКА В ДРУЗЬЯ
# ----------------------------------------------------------
class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_requests')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='received_requests')

# ----------------------------------------------------------
# МОДЕЛЬ: ПОЛЬЗОВАТЕЛЬ
# ----------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    # Профиль
    avatar = db.Column(db.String(200), default="default.png")
    banner = db.Column(db.String(200), default="")
    status_emoji = db.Column(db.String(10), default="😊")
    status_text = db.Column(db.String(100), default="")
    accent_color = db.Column(db.String(20), default="#0071e3")
    bio = db.Column(db.String(500), default="")

    # Настройки интерфейса
    theme = db.Column(db.String(10), default="light")
    auto_theme = db.Column(db.Boolean, default=True)
    chat_bg = db.Column(db.String(20), default="gradient1")
    font_style = db.Column(db.String(50), default="Inter")
    sound_enabled = db.Column(db.Boolean, default=True)

    # Игровые механики
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    streak_days = db.Column(db.Integer, default=0)
    max_streak = db.Column(db.Integer, default=0)
    last_entry_date = db.Column(db.Date)
    total_entries = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    experience = db.Column(db.Integer, default=0)
    daily_reward_date = db.Column(db.Date)

    # Социальные связи
    friends = db.relationship(
        'User', secondary=friends_table,
        primaryjoin=(friends_table.c.user_id == id),
        secondaryjoin=(friends_table.c.friend_id == id),
        backref=db.backref('friend_of', lazy='dynamic'),
        lazy='dynamic'
    )

    # Контент пользователя
    entries = db.relationship('Entry', backref='author', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='user', lazy=True, cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True)
    achievements = db.relationship('Achievement', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    # Статус и права
    public_profile = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)

    # Сообщения
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

    # Группы
    groups = db.relationship('GroupMember', backref='user', lazy=True)

    # ----------------------------------------------------------
    # МЕТОДЫ ПОЛЬЗОВАТЕЛЯ
    # ----------------------------------------------------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_streak(self):
        today = date.today()
        if self.last_entry_date == today:
            return False
        elif self.last_entry_date == today - timedelta(days=1):
            self.streak_days += 1
        else:
            self.streak_days = 1
        self.last_entry_date = today
        if self.streak_days > self.max_streak:
            self.max_streak = self.streak_days
        return True

    def claim_daily_reward(self):
        today = date.today()
        if self.daily_reward_date == today:
            return 0
        self.daily_reward_date = today
        xp = random.randint(10, 50)
        self.experience += xp
        if self.experience >= self.level * 100:
            self.level += 1
            self.experience = 0
        return xp

    def get_streak_emoji(self):
        if self.streak_days >= 30: return "🌈🔥🔥🔥🔥🔥"
        elif self.streak_days >= 14: return "👑🔥🔥🔥🔥"
        elif self.streak_days >= 7: return "🔥🔥🔥"
        elif self.streak_days >= 3: return "🔥🔥"
        elif self.streak_days >= 1: return "🔥"
        return ""

    def is_friend(self, user):
        return self.friends.filter(friends_table.c.friend_id == user.id).count() > 0

    def send_friend_request(self, user):
        if not self.is_friend(user):
            existing = FriendRequest.query.filter_by(
                from_user_id=self.id, to_user_id=user.id, status='pending'
            ).first()
            if not existing:
                db.session.add(FriendRequest(from_user_id=self.id, to_user_id=user.id))
                return True
        return False

    def accept_friend_request(self, request_id):
        req = FriendRequest.query.get(request_id)
        if req and req.to_user_id == self.id and req.status == 'pending':
            req.status = 'accepted'
            self.friends.append(req.from_user)
            req.from_user.friends.append(self)
            return req.from_user
        return None

    def get_unread_messages_count(self):
        return Message.query.filter_by(receiver_id=self.id, is_read=False).count()

# ----------------------------------------------------------
# МОДЕЛЬ: ЗАПИСЬ В ДНЕВНИКЕ
# ----------------------------------------------------------
class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    text_content = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float)
    mood_label = db.Column(db.String(20))
    category = db.Column(db.String(50), default="Общее")
    tags = db.Column(db.String(200))
    is_public = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200), default="")
    audio = db.Column(db.String(200), default="")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)

    comments = db.relationship('Comment', backref='entry', lazy=True, cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='entry', lazy=True)

# ----------------------------------------------------------
# МОДЕЛЬ: КОММЕНТАРИЙ
# ----------------------------------------------------------
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey("entry.id"), nullable=False)
    user = db.relationship('User', backref='comments')

# ----------------------------------------------------------
# МОДЕЛЬ: ЛАЙК
# ----------------------------------------------------------
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey("entry.id"), nullable=False)

# ----------------------------------------------------------
# МОДЕЛЬ: ЗАКЛАДКА
# ----------------------------------------------------------
class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey("entry.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
# МОДЕЛЬ: ЦЕЛЬ
# ----------------------------------------------------------
class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    target_value = db.Column(db.Integer, default=7)
    current_value = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# ----------------------------------------------------------
# МОДЕЛЬ: ДОСТИЖЕНИЕ
# ----------------------------------------------------------
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# ----------------------------------------------------------
# МОДЕЛЬ: УВЕДОМЛЕНИЕ
# ----------------------------------------------------------
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    message = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    link = db.Column(db.String(200))

# ----------------------------------------------------------
# МОДЕЛЬ: СООБЩЕНИЕ
# ----------------------------------------------------------
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------------------------------------
# МОДЕЛЬ: ГРУППА
# ----------------------------------------------------------
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship('GroupMember', backref='group', lazy=True, cascade='all, delete-orphan')
    entries = db.relationship('Entry', backref='group', lazy=True)

# ----------------------------------------------------------
# МОДЕЛЬ: УЧАСТНИК ГРУППЫ
# ----------------------------------------------------------
class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
""")


# ============================================================
# БЛОК 6: APP/UTILS.PY (ИИ, АНАЛИЗ, РЕКОМЕНДАЦИИ)
# ============================================================
with open('app/utils.py', 'w', encoding='utf-8') as f:
    f.write(r"""import re
import calendar
import random
from datetime import date
from collections import Counter
from textblob import TextBlob

# ============================================================
# СЛОВАРИ ДЛЯ АНАЛИЗА НАСТРОЕНИЯ
# ============================================================
POSITIVE_WORDS = {
    # Базовые позитивные
    "хорошо", "отлично", "супер", "рад", "счастлив", "люблю", "круто",
    "кайф", "прекрасно", "замечательно", "позитив", "бомба", "топ",
    "класс", "клёво", "зашибись", "офигенно", "потрясно", "шикарно",
    "великолепно", "восхитительно", "благодарю", "спасибо",
    # Сленг
    "краш", "пушка", "имба", "вайб", "хайп", "чилл", "няшно",
    "милота", "уютно", "лампово", "кайфую", "балдею", "в восторге",
    # Эмодзи
    ":)", "(:", "=)", "=D", ":D", "😊", "😁", "😄", "😍", "🥰", "😎", "🤩", "😇"
}

NEGATIVE_WORDS = {
    # Базовые негативные
    "плохо", "ужасно", "грустно", "бесит", "ненавижу", "отвратительно",
    "тоскливо", "печально", "хреново", "кошмар", "жуть", "мрак",
    "тоска", "уныние", "депрессия", "больно", "страдаю", "разочарован",
    "расстроен", "обидно", "противно", "мерзко",
    # Сленг
    "кринж", "зашквар", "дно", "треш", "жесть", "фиаско", "провал",
    "апатия", "токсик", "бесят", "триггерит", "фу", "отстой",
    # Эмодзи
    ":(", ":'(", "😞", "😔", "😟", "😢", "😭", "😠", "😡", "🤬", "💔", "😿"
}

# Усилители
INTENSIFIERS = {
    "очень": 1.5, "весьма": 1.4, "крайне": 1.6,
    "невероятно": 1.7, "совсем": 1.3, "абсолютно": 1.5,
    "чуть-чуть": 0.5, "немного": 0.6, "слегка": 0.5
}

# ============================================================
# ФУНКЦИЯ: АНАЛИЗ НАСТРОЕНИЯ
# ============================================================
def analyze_mood(text):
    # Базовый анализ через TextBlob
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    # Кастомный анализ по словарям
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]+|[😊😁😄😍🥰😎🤩😇🤗😞😔😟😢😭😠😡🤬👎💔😿]', text)
    custom_score = 0
    word_count = 0

    for i, word in enumerate(words):
        clean = word.lower()

        # Проверяем усилители (они влияют на следующее слово)
        if clean in INTENSIFIERS:
            continue

        score_mod = 1.0
        # Если перед словом был усилитель
        if i > 0 and words[i-1].lower() in INTENSIFIERS:
            score_mod *= INTENSIFIERS[words[i-1].lower()]

        # Проверяем позитивные слова
        if word in POSITIVE_WORDS or clean in POSITIVE_WORDS:
            custom_score += (0.5 * score_mod)
            word_count += 1

        # Проверяем негативные слова
        elif word in NEGATIVE_WORDS or clean in NEGATIVE_WORDS:
            custom_score -= (0.5 * score_mod)
            word_count += 1

    # Объединяем результаты
    if word_count > 0:
        custom_polarity = custom_score / word_count
        polarity = (polarity * 0.3) + (custom_polarity * 0.7)
    else:
        polarity = polarity * 0.8

    # Нормализация
    polarity = max(-1.0, min(1.0, polarity))

    # Определяем метку
    if polarity > 0.15:
        label = "Positive"
    elif polarity < -0.15:
        label = "Negative"
    else:
        label = "Neutral"

    return round(polarity, 2), label

# ============================================================
# ФУНКЦИЯ: ИЗВЛЕЧЕНИЕ ТЕГОВ
# ============================================================
def extract_tags(text):
    tags = re.findall(r"#(\w+)", text)
    return ",".join(tags) if tags else ""

# ============================================================
# ФУНКЦИЯ: ОБЛАКО СЛОВ
# ============================================================
def get_word_cloud(entries):
    words = []
    for e in entries:
        words.extend(re.findall(r"[а-яА-Яa-zA-Z]{4,}", e.text_content.lower()))
    return Counter(words).most_common(20)

# ============================================================
# ФУНКЦИЯ: ИИ-РЕКОМЕНДАЦИИ
# ============================================================
def get_ai_recommendation(score, label, streak):
    if label == "Positive":
        return random.choice([
            "Отличное настроение! Запиши 3 вещи за которые благодарен.",
            "Супер! Поделись позитивом с другом!",
            "Ты на волне! Сделай что-то приятное для себя."
        ])
    elif label == "Negative":
        return random.choice([
            "Сделай глубокий вдох. Прогулка на 15 минут поможет.",
            "Позвони близкому человеку. Разговор лечит.",
            "Послушай спокойную музыку. Всё наладится.",
            "Не держи в себе. Выговориться в дневнике — уже шаг."
        ])
    else:
        return random.choice([
            "Попробуй что-то новое сегодня!",
            "Запиши свои мысли — это помогает.",
            "Маленькое приключение поднимет настроение."
        ])

# ============================================================
# ФУНКЦИЯ: МУЗЫКАЛЬНЫЕ РЕКОМЕНДАЦИИ
# ============================================================
def get_music_recommendation(score):
    if score > 0.5:
        return random.choice([
            "🎵 Happy — Pharrell Williams",
            "🎵 Can't Stop The Feeling — Justin Timberlake",
            "🎵 Walking On Sunshine — Katrina & The Waves"
        ])
    elif score > 0.1:
        return random.choice([
            "🎵 Good Vibes — HRVY",
            "🎵 Sunroof — Nicky Youre",
            "🎵 Budapest — George Ezra"
        ])
    elif score < -0.5:
        return random.choice([
            "🎵 Let Her Go — Passenger",
            "🎵 Someone You Loved — Lewis Capaldi",
            "🎵 Fix You — Coldplay"
        ])
    elif score < -0.1:
        return random.choice([
            "🎵 Drivers License — Olivia Rodrigo",
            "🎵 When The Party's Over — Billie Eilish",
            "🎵 The Night We Met — Lord Huron"
        ])
    else:
        return random.choice([
            "🎵 Banana Pancakes — Jack Johnson",
            "🎵 Sunday Morning — Maroon 5",
            "🎵 Riptide — Vance Joy"
        ])

# ============================================================
# ФУНКЦИЯ: ЦВЕТ НАСТРОЕНИЯ
# ============================================================
def get_mood_color(score):
    if score is None:
        return '#f8f9fa'
    if score > 0.3:
        return '#28a745'
    elif score > 0.1:
        return '#90ee90'
    elif score < -0.3:
        return '#dc3545'
    elif score < -0.1:
        return '#ffb6c1'
    else:
        return '#ffc107'

# ============================================================
# ФУНКЦИЯ: ДАННЫЕ КАЛЕНДАРЯ
# ============================================================
def get_calendar_data(year, month, entries):
    cal = calendar.monthcalendar(year, month)
    data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day': 0, 'score': None, 'color': '#f0f0f0'})
            else:
                day_entries = [e for e in entries if e.date.year == year and e.date.month == month and e.date.day == day]
                if day_entries:
                    avg_score = sum(e.sentiment_score for e in day_entries) / len(day_entries)
                    color = get_mood_color(avg_score)
                    week_data.append({'day': day, 'score': round(avg_score, 2), 'color': color})
                else:
                    week_data.append({'day': day, 'score': None, 'color': '#f8f9fa'})
        data.append(week_data)
    return data

# ============================================================
# ФУНКЦИЯ: ОБНОВЛЕНИЕ СТАТИСТИКИ ПОЛЬЗОВАТЕЛЯ
# ============================================================
def update_user_stats(user):
    updated = user.update_streak()
    user.total_entries += 1
    user.experience += 10
    leveled = False
    if user.experience >= user.level * 100:
        user.level += 1
        user.experience = 0
        leveled = True
    return updated, leveled

# ============================================================
# ФУНКЦИЯ: ПРОВЕРКА ДОСТИЖЕНИЙ
# ============================================================
def check_achievements(user):
    from app.models import Achievement, db
    new_achs = []

    if user.total_entries == 1:
        new_achs.append(("Первый шаг", "🎯", "Сделал первую запись!"))
    elif user.total_entries == 10:
        new_achs.append(("Писатель", "✍️", "10 записей!"))
    elif user.total_entries == 50:
        new_achs.append(("Мудрец", "🧠", "50 записей!"))
    elif user.total_entries == 100:
        new_achs.append(("Эксперт", "📚", "100 записей!"))

    if user.streak_days == 7:
        new_achs.append(("Неделя огня", "🔥🔥🔥", "7 дней подряд!"))
    elif user.streak_days == 14:
        new_achs.append(("Две недели", "👑", "14 дней подряд!"))
    elif user.streak_days == 30:
        new_achs.append(("Месяц огня", "🌈🔥", "30 дней подряд!"))

    for name, icon, desc in new_achs:
        if not Achievement.query.filter_by(user_id=user.id, name=name).first():
            ach = Achievement(name=name, icon=icon, description=desc, user_id=user.id)
            db.session.add(ach)

    return new_achs

# ============================================================
# ФУНКЦИЯ: СТАТУС СТРИКА
# ============================================================
def get_streak_status(streak_days):
    if streak_days >= 30: return "🌈🔥 ЛЕГЕНДА!"
    elif streak_days >= 14: return "👑🔥 КОРОЛЬ ОГНЯ!"
    elif streak_days >= 7: return "🔥🔥🔥 НЕДЕЛЯ ОГНЯ!"
    elif streak_days >= 3: return "🔥🔥 РАЗГОРАЕТСЯ!"
    elif streak_days >= 1: return "🔥 НАЧАЛО!"
    return "😴 Начни стрик!"
""")


# ============================================================
# БЛОК 7: PWA ФАЙЛЫ
# ============================================================
with open('app/static/manifest.json', 'w', encoding='utf-8') as f:
    f.write("""{
  "name": "MoodMap Ultimate",
  "short_name": "MoodMap",
  "description": "Дневник настроения с ИИ и друзьями",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#6366f1",
  "background_color": "#f8fafc",
  "icons": [
    {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}""")

with open('app/static/sw.js', 'w', encoding='utf-8') as f:
    f.write("""const CACHE_NAME = 'moodmap-v4';
const urlsToCache = ['/', '/static/manifest.json'];

// Установка Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('Кэш открыт');
      return cache.addAll(urlsToCache);
    })
  );
});

// Перехват запросов
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      // Возвращаем из кэша или делаем запрос
      return response || fetch(event.request);
    })
  );
});

// Активация
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
""")

with open('app/blueprints/auth.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для авторизации
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, db, Notification, Achievement
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Создание Blueprint'а для авторизации
auth_bp = Blueprint("auth", __name__)

# ----------------------------------------------------------
# МАРШРУТ: ВХОД В СИСТЕМУ (LOGIN)
# ----------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Обработка отправки формы
    if request.method == "POST":
        # Получаем данные из формы
        login_username = request.form.get("username")
        login_password = request.form.get("password")

        # Ищем пользователя в базе данных
        user = User.query.filter_by(username=login_username).first()

        # Проверяем существование пользователя и правильность пароля
        if user and user.check_password(login_password):
            # Проверяем, не заблокирован ли аккаунт
            if user.is_blocked:
                flash("Ваш аккаунт заблокирован администратором.", "error")
                return redirect(url_for("auth.login"))

            # Выполняем вход
            login_user(user, remember=True)

            # Обновляем статус онлайн
            user.is_online = True
            user.last_seen = datetime.utcnow()
            db.session.commit()

            # Приветственное сообщение
            flash(f"С возвращением, {user.username}!", "success")

            # Перенаправляем на главную страницу
            return redirect(url_for("main.dashboard"))
        else:
            # Неверный логин или пароль
            flash("Неверный логин или пароль. Попробуйте снова.", "error")

    # Отображаем страницу входа
    return render_template("login.html")

# ----------------------------------------------------------
# МАРШРУТ: РЕГИСТРАЦИЯ (REGISTER)
# ----------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Обработка отправки формы
    if request.method == "POST":
        # Получаем данные из формы регистрации
        register_username = request.form.get("username")
        register_email = request.form.get("email")
        register_password = request.form.get("password")
        register_theme = request.form.get("theme", "light")

        # Проверяем, не занято ли имя пользователя
        if User.query.filter_by(username=register_username).first():
            flash("Пользователь с таким именем уже существует.", "error")
            return redirect(url_for("auth.register"))

        # Проверяем, не занят ли email
        if User.query.filter_by(email=register_email).first():
            flash("Этот email уже используется.", "error")
            return redirect(url_for("auth.register"))

        # Создаем нового пользователя
        user = User(
            username=register_username,
            email=register_email,
            theme=register_theme
        )

        # Устанавливаем пароль (хешируется внутри метода)
        user.set_password(register_password)

        # Первый зарегистрированный пользователь становится админом
        if User.query.count() == 0:
            user.is_admin = True

        # Сохраняем пользователя в базе данных
        db.session.add(user)
        db.session.commit()

        # Автоматически входим после регистрации
        login_user(user)
        user.is_online = True
        user.last_seen = datetime.utcnow()
        db.session.commit()

        flash(f"Добро пожаловать в MoodMap, {user.username}!", "success")
        return redirect(url_for("main.dashboard"))

    # Отображаем страницу регистрации
    return render_template("register.html")

# ----------------------------------------------------------
# МАРШРУТ: ВЫХОД ИЗ СИСТЕМЫ (LOGOUT)
# ----------------------------------------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    # Обновляем статус перед выходом
    current_user.is_online = False
    current_user.last_seen = datetime.utcnow()
    db.session.commit()

    # Выполняем выход
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))

# ----------------------------------------------------------
# МАРШРУТ: СМЕНА ТЕМЫ (SET THEME)
# ----------------------------------------------------------
@auth_bp.route("/theme/<theme>")
def set_theme(theme):
    # Проверяем, что тема допустимая
    if theme not in ["light", "dark"]:
        theme = "light"

    # Сохраняем тему для авторизованного пользователя
    if current_user.is_authenticated:
        current_user.theme = theme
        db.session.commit()

    # Сохраняем тему в сессии (для неавторизованных)
    session["theme"] = theme

    # Возвращаемся на предыдущую страницу
    return redirect(request.referrer or url_for("main.dashboard"))

# ----------------------------------------------------------
# МАРШРУТ: ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ (PROFILE)
# ----------------------------------------------------------
@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Обработка отправки формы профиля
    if request.method == "POST":
        # Обновляем основные поля
        current_user.username = request.form.get("username", current_user.username)
        current_user.email = request.form.get("email", current_user.email)
        current_user.bio = request.form.get("bio", "")
        current_user.status_emoji = request.form.get("status_emoji", "😊")
        current_user.status_text = request.form.get("status_text", "")
        current_user.accent_color = request.form.get("accent_color", "#0071e3")

        # Настройки интерфейса
        current_user.chat_bg = request.form.get("chat_bg", "gradient1")
        current_user.font_style = request.form.get("font_style", "Inter")
        current_user.sound_enabled = bool(request.form.get("sound_enabled"))
        current_user.auto_theme = bool(request.form.get("auto_theme"))
        current_user.public_profile = bool(request.form.get("public_profile"))

        # Обработка загрузки аватара
        if "avatar" in request.files:
            avatar_file = request.files["avatar"]
            if avatar_file.filename:
                # Создаем безопасное имя файла
                filename = secure_filename(f"avatar_{current_user.id}_{avatar_file.filename}")
                # Сохраняем файл
                filepath = os.path.join("app", "static", "uploads", filename)
                avatar_file.save(filepath)
                # Обновляем путь в базе данных
                current_user.avatar = filename

        # Обработка загрузки баннера
        if "banner" in request.files:
            banner_file = request.files["banner"]
            if banner_file.filename:
                filename = secure_filename(f"banner_{current_user.id}_{banner_file.filename}")
                filepath = os.path.join("app", "static", "banners", filename)
                banner_file.save(filepath)
                current_user.banner = filename

        # Смена пароля (если заполнены оба поля)
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password and new_password == confirm_password:
            current_user.set_password(new_password)
            flash("Пароль успешно изменён!", "success")
        elif new_password:
            flash("Пароли не совпадают!", "error")

        # Сохраняем все изменения
        db.session.commit()
        flash("Профиль успешно обновлён!", "success")
        return redirect(url_for("auth.profile"))

    # Получаем достижения пользователя
    user_achievements = Achievement.query.filter_by(user_id=current_user.id).all()

    # Отображаем страницу профиля
    return render_template("profile.html", achievements=user_achievements)

# ----------------------------------------------------------
# МАРШРУТ: УВЕДОМЛЕНИЯ (NOTIFICATIONS)
# ----------------------------------------------------------
@auth_bp.route("/notifications")
@login_required
def notifications():
    # Получаем непрочитанные уведомления
    user_notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).all()

    # Отображаем страницу уведомлений
    return render_template("notifications.html", notifications=user_notifications)

# ----------------------------------------------------------
# МАРШРУТ: ОТМЕТИТЬ УВЕДОМЛЕНИЕ ПРОЧИТАННЫМ
# ----------------------------------------------------------
@auth_bp.route("/notifications/read/<int:id>")
@login_required
def mark_read(id):
    # Находим уведомление
    notification = Notification.query.get_or_404(id)

    # Проверяем, что уведомление принадлежит текущему пользователю
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()

        # Если у уведомления есть ссылка, переходим по ней
        if notification.link:
            return redirect(notification.link)

    # Возвращаемся к списку уведомлений
    return redirect(url_for("auth.notifications"))
''')


# ============================================================
# БЛОК 9: APP/BLUEPRINTS/MAIN.PY
# ============================================================
with open('app/blueprints/main.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для основных маршрутов
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import Entry, db, Goal, Bookmark, Achievement
from app.utils import *
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# Создание Blueprint'а для основных маршрутов
main_bp = Blueprint("main", __name__)

# ----------------------------------------------------------
# МАРШРУТ: ДАШБОРД (ГЛАВНАЯ СТРАНИЦА)
# ----------------------------------------------------------
@main_bp.route("/")
@login_required
def dashboard():
    # Получаем последние записи пользователя
    user_entries = Entry.query.filter_by(
        user_id=current_user.id
    ).order_by(Entry.date.desc()).all()

    # Получаем статус стрика
    streak_status = get_streak_status(current_user.streak_days)

    # Генерируем облако слов из последних 50 записей
    word_cloud_data = get_word_cloud(user_entries[:50]) if user_entries else []

    # Случайная цитата для вдохновения
    inspirational_quotes = [
        "Всё получится! Продолжай в том же духе.",
        "Ты молодец! Каждая запись — шаг к самопознанию.",
        "Продолжай в том же духе! Твой дневник — твоя сила.",
        "Сегодня отличный день для новых свершений!",
        "Помни: ты уникален и твои чувства важны."
    ]
    random_quote = random.choice(inspirational_quotes)

    # Статистика по дням недели
    weekday_averages = []
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    for day_index in range(7):
        day_entries = [e for e in user_entries if e.date.weekday() == day_index]
        if day_entries:
            avg = sum(e.sentiment_score for e in day_entries) / len(day_entries)
            weekday_averages.append(round(avg, 2))
        else:
            weekday_averages.append(0)

    # Отображаем дашборд
    return render_template(
        "dashboard.html",
        entries=user_entries[:10],
        streak_status=streak_status,
        word_cloud=word_cloud_data,
        quote=random_quote,
        weekday_avg=weekday_averages,
        weekdays=days_of_week
    )

# ----------------------------------------------------------
# МАРШРУТ: КАЛЕНДАРЬ НАСТРОЕНИЯ
# ----------------------------------------------------------
@main_bp.route("/calendar")
@login_required
def mood_calendar():
    # Получаем параметры года и месяца из URL
    current_year = datetime.now().year
    current_month = datetime.now().month

    year = request.args.get("year", current_year, type=int)
    month = request.args.get("month", current_month, type=int)
    selected_day = request.args.get("day", type=int)

    # Получаем все записи пользователя
    all_entries = Entry.query.filter_by(user_id=current_user.id).all()

    # Генерируем данные для календаря
    calendar_data = get_calendar_data(year, month, all_entries)

    # Получаем записи за выбранный день
    day_entries_list = []
    if selected_day:
        day_entries_list = [
            e for e in all_entries 
            if e.date.year == year and e.date.month == month and e.date.day == selected_day
        ]

    # Вычисляем предыдущий и следующий месяц
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    # Отображаем календарь
    return render_template(
        "calendar.html",
        calendar_data=calendar_data,
        year=year,
        month=month,
        day=selected_day,
        month_name=month_names[month - 1],
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        day_entries=day_entries_list
    )

# ----------------------------------------------------------
# МАРШРУТ: ДОБАВЛЕНИЕ ЗАПИСИ (ADD ENTRY)
# ----------------------------------------------------------
@main_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_entry():
    # Обработка отправки формы
    if request.method == "POST":
        # Получаем данные из формы
        entry_content = request.form.get("content", "").strip()
        entry_category = request.form.get("category", "Общее")
        is_public = bool(request.form.get("is_public"))

        # Проверяем, что контент не пустой
        if not entry_content:
            flash("Запись не может быть пустой!", "error")
            return redirect(url_for("main.add_entry"))

        # Анализируем настроение текста
        mood_score, mood_label = analyze_mood(entry_content)

        # Извлекаем теги из текста
        entry_tags = extract_tags(entry_content)

        # Создаем новую запись
        new_entry = Entry(
            text_content=entry_content,
            sentiment_score=mood_score,
            mood_label=mood_label,
            category=entry_category,
            tags=entry_tags,
            is_public=is_public,
            author=current_user
        )

        # Обработка загрузки изображения
        if "image" in request.files:
            image_file = request.files["image"]
            if image_file.filename:
                filename = secure_filename(f"entry_{current_user.id}_{datetime.now().timestamp()}_{image_file.filename}")
                filepath = os.path.join("app", "static", "uploads", filename)
                image_file.save(filepath)
                new_entry.image = filename

        # Обработка загрузки аудио
        if "audio" in request.files:
            audio_file = request.files["audio"]
            if audio_file.filename:
                filename = secure_filename(f"audio_{current_user.id}_{datetime.now().timestamp()}.webm")
                filepath = os.path.join("app", "static", "uploads", filename)
                audio_file.save(filepath)
                new_entry.audio = filename

        # Сохраняем запись в базу данных
        db.session.add(new_entry)

        # Обновляем статистику пользователя
        streak_updated, leveled_up = update_user_stats(current_user)
        db.session.commit()

        # Проверяем достижения
        new_achievements = check_achievements(current_user)
        for ach_name, ach_icon, ach_desc in new_achievements:
            flash(f"🏆 Достижение разблокировано: {ach_icon} {ach_name} — {ach_desc}", "success")

        # Получаем рекомендации от ИИ
        ai_recommendation = get_ai_recommendation(mood_score, mood_label, current_user.streak_days)
        music_recommendation = get_music_recommendation(mood_score)

        # Показываем рекомендации
        flash(f"🤖 ИИ-совет: {ai_recommendation}", "success")
        flash(f"🎵 Музыка под настроение: {music_recommendation}", "info")

        # Если повысился уровень
        if leveled_up:
            flash(f"🎉 Поздравляем! Вы достигли уровня {current_user.level}!", "success")

        # Перенаправляем на дашборд
        return redirect(url_for("main.dashboard"))

    # Категории для выпадающего списка
    categories = [
        "Общее", "Работа", "Отношения", "Здоровье", 
        "Хобби", "Учёба", "Путешествия", "Спорт", "Еда"
    ]

    # Отображаем страницу добавления записи
    return render_template("add_entry.html", categories=categories)

# ----------------------------------------------------------
# МАРШРУТ: ДОБАВИТЬ В ЗАКЛАДКИ (BOOKMARK)
# ----------------------------------------------------------
@main_bp.route("/bookmark/<int:entry_id>")
@login_required
def bookmark_entry(entry_id):
    # Находим запись
    entry = Entry.query.get_or_404(entry_id)

    # Проверяем, есть ли уже закладка
    existing_bookmark = Bookmark.query.filter_by(
        user_id=current_user.id, 
        entry_id=entry_id
    ).first()

    if existing_bookmark:
        # Удаляем закладку
        db.session.delete(existing_bookmark)
        db.session.commit()
        flash("Закладка удалена.", "info")
    else:
        # Добавляем закладку
        new_bookmark = Bookmark(user_id=current_user.id, entry_id=entry_id)
        db.session.add(new_bookmark)
        db.session.commit()
        flash("Запись добавлена в закладки!", "success")

    # Возвращаемся на предыдущую страницу
    return redirect(request.referrer or url_for("main.dashboard"))

# ----------------------------------------------------------
# МАРШРУТ: СПИСОК ЗАКЛАДОК (BOOKMARKS)
# ----------------------------------------------------------
@main_bp.route("/bookmarks")
@login_required
def bookmarks_list():
    # Получаем все закладки пользователя
    user_bookmarks = Bookmark.query.filter_by(
        user_id=current_user.id
    ).order_by(Bookmark.created_at.desc()).all()

    # Отображаем страницу закладок
    return render_template("bookmarks.html", bookmarks=user_bookmarks)

# ----------------------------------------------------------
# МАРШРУТ: РЕДАКТИРОВАНИЕ ЗАПИСИ (EDIT ENTRY)
# ----------------------------------------------------------
@main_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_entry(id):
    # Находим запись
    entry = Entry.query.get_or_404(id)

    # Проверяем права доступа
    if entry.user_id != current_user.id and not current_user.is_admin:
        flash("У вас нет прав для редактирования этой записи.", "error")
        return redirect(url_for("main.dashboard"))

    # Обработка отправки формы
    if request.method == "POST":
        # Обновляем содержимое записи
        entry.text_content = request.form.get("content", entry.text_content)
        entry.category = request.form.get("category", entry.category)
        entry.is_public = bool(request.form.get("is_public"))

        # Заново анализируем настроение
        new_score, new_label = analyze_mood(entry.text_content)
        entry.sentiment_score = new_score
        entry.mood_label = new_label

        # Извлекаем теги
        entry.tags = extract_tags(entry.text_content)

        # Сохраняем изменения
        db.session.commit()
        flash("Запись успешно обновлена!", "success")
        return redirect(url_for("main.dashboard"))

    # Категории для выпадающего списка
    categories = [
        "Общее", "Работа", "Отношения", "Здоровье", 
        "Хобби", "Учёба", "Путешествия", "Спорт", "Еда"
    ]

    # Отображаем страницу редактирования
    return render_template("edit_entry.html", entry=entry, categories=categories)

# ----------------------------------------------------------
# МАРШРУТ: УДАЛЕНИЕ ЗАПИСИ (DELETE ENTRY)
# ----------------------------------------------------------
@main_bp.route("/delete/<int:id>")
@login_required
def delete_entry(id):
    # Находим запись
    entry = Entry.query.get_or_404(id)

    # Проверяем права доступа
    if entry.user_id != current_user.id and not current_user.is_admin:
        flash("У вас нет прав для удаления этой записи.", "error")
    else:
        # Удаляем запись
        db.session.delete(entry)
        db.session.commit()
        flash("Запись успешно удалена.", "success")

    return redirect(url_for("main.dashboard"))

# ----------------------------------------------------------
# МАРШРУТ: ЦЕЛИ (GOALS)
# ----------------------------------------------------------
@main_bp.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    # Обработка создания новой цели
    if request.method == "POST":
        goal_title = request.form.get("title", "").strip()
        goal_target = int(request.form.get("target_value", 7))

        if goal_title:
            new_goal = Goal(
                title=goal_title,
                target_value=goal_target,
                user_id=current_user.id
            )
            db.session.add(new_goal)
            db.session.commit()
            flash("Новая цель добавлена!", "success")
        else:
            flash("Название цели не может быть пустым.", "error")

        return redirect(url_for("main.goals"))

    # Получаем все цели пользователя
    user_goals = Goal.query.filter_by(user_id=current_user.id).all()

    # Отображаем страницу целей
    return render_template("goals.html", goals=user_goals)

# ----------------------------------------------------------
# МАРШРУТ: ВЫПОЛНИТЬ ЦЕЛЬ (COMPLETE GOAL)
# ----------------------------------------------------------
@main_bp.route("/goals/complete/<int:id>")
@login_required
def complete_goal(id):
    # Находим цель
    goal = Goal.query.get_or_404(id)

    # Проверяем, что цель принадлежит пользователю
    if goal.user_id == current_user.id:
        goal.is_completed = True
        current_user.experience += 50
        db.session.commit()
        flash("Цель выполнена! +50 XP", "success")

    return redirect(url_for("main.goals"))

# ----------------------------------------------------------
# МАРШРУТ: WRAPPED (ГОДОВОЙ ОТЧЁТ)
# ----------------------------------------------------------
@main_bp.route("/wrapped")
@login_required
def wrapped():
    # Получаем все записи пользователя
    all_entries = Entry.query.filter_by(user_id=current_user.id).all()

    if not all_entries:
        flash("Недостаточно данных для годового отчёта.", "error")
        return redirect(url_for("main.dashboard"))

    # Общая статистика
    total_entries = len(all_entries)
    average_score = round(sum(e.sentiment_score for e in all_entries) / total_entries, 2)

    # Определяем лучший месяц
    month_counts = {}
    for e in all_entries:
        month_key = e.date.month
        month_counts[month_key] = month_counts.get(month_key, 0) + 1

    best_month_num = max(month_counts, key=month_counts.get)
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    best_month_name = month_names[best_month_num - 1]

    # Облако слов
    word_cloud_data = get_word_cloud(all_entries)[:15]

    # Отображаем страницу Wrapped
    return render_template(
        "wrapped.html",
        total=total_entries,
        avg_score=average_score,
        best_month=best_month_name,
        streak_max=current_user.max_streak,
        word_cloud=word_cloud_data,
        level=current_user.level
    )

# ----------------------------------------------------------
# МАРШРУТ: ЭКСПОРТ (EXPORT)
# ----------------------------------------------------------
@main_bp.route("/export")
@login_required
def export():
    # Получаем все записи пользователя
    all_entries = Entry.query.filter_by(
        user_id=current_user.id
    ).order_by(Entry.date.desc()).all()

    # Отображаем страницу экспорта
    return render_template("export.html", entries=all_entries)

# ----------------------------------------------------------
# МАРШРУТ: ЕЖЕДНЕВНАЯ НАГРАДА (CLAIM REWARD)
# ----------------------------------------------------------
@main_bp.route("/claim_reward")
@login_required
def claim_daily_reward():
    # Пытаемся получить награду
    xp_reward = current_user.claim_daily_reward()

    if xp_reward > 0:
        flash(f"🎁 Ежедневная награда получена: +{xp_reward} XP!", "success")
    else:
        flash("Вы уже получили награду сегодня. Возвращайтесь завтра!", "info")

    return redirect(url_for("main.dashboard"))
''')

with open('app/blueprints/social.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для социальных функций
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Entry, FriendRequest, db, Notification

# Создание Blueprint'а
social_bp = Blueprint("social", __name__)

# ----------------------------------------------------------
# МАРШРУТ: СПИСОК ДРУЗЕЙ
# ----------------------------------------------------------
@social_bp.route("/friends")
@login_required
def friends():
    # Получаем список всех друзей текущего пользователя
    user_friends = current_user.friends.all()

    # Передаем список в шаблон
    return render_template("social/friends.html", friends=user_friends)

# ----------------------------------------------------------
# МАРШРУТ: ПОИСК ПОЛЬЗОВАТЕЛЕЙ
# ----------------------------------------------------------
@social_bp.route("/search")
@login_required
def search():
    # Получаем поисковый запрос из URL
    search_query = request.args.get("q", "")

    # Если запрос есть, ищем пользователей
    if search_query:
        found_users = User.query.filter(
            User.username.contains(search_query),
            User.id != current_user.id
        ).all()
    else:
        found_users = []

    # Передаем результаты в шаблон
    return render_template("social/search.html", users=found_users, query=search_query)

# ----------------------------------------------------------
# МАРШРУТ: ОТПРАВИТЬ ЗАЯВКУ В ДРУЗЬЯ
# ----------------------------------------------------------
@social_bp.route("/send_request/<int:user_id>")
@login_required
def send_request(user_id):
    # Находим пользователя, которому отправляем заявку
    target_user = User.query.get_or_404(user_id)

    # Проверяем, не друзья ли мы уже
    if current_user.is_friend(target_user):
        flash("Вы уже друзья!", "info")
        return redirect(url_for("social.search"))

    # Проверяем, не отправляли ли уже заявку
    existing_request = FriendRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=user_id,
        status='pending'
    ).first()

    if existing_request:
        flash("Заявка уже отправлена и ожидает ответа.", "info")
        return redirect(url_for("social.search"))

    # Отправляем заявку
    success = current_user.send_friend_request(target_user)

    if success:
        # Создаем уведомление для получателя
        notification_message = f"{current_user.username} хочет добавить вас в друзья!"
        notification_link = url_for("social.requests")

        new_notification = Notification(
            user_id=user_id,
            type="friend_request",
            message=notification_message,
            link=notification_link
        )

        db.session.add(new_notification)
        db.session.commit()

        flash("Заявка в друзья отправлена!", "success")
    else:
        flash("Не удалось отправить заявку.", "error")

    return redirect(url_for("social.search"))

# ----------------------------------------------------------
# МАРШРУТ: ВХОДЯЩИЕ ЗАЯВКИ
# ----------------------------------------------------------
@social_bp.route("/requests")
@login_required
def requests():
    # Получаем все входящие заявки со статусом "ожидает"
    pending_requests = FriendRequest.query.filter_by(
        to_user_id=current_user.id,
        status='pending'
    ).all()

    # Передаем заявки в шаблон
    return render_template("social/requests.html", requests=pending_requests)

# ----------------------------------------------------------
# МАРШРУТ: ПРИНЯТЬ ЗАЯВКУ
# ----------------------------------------------------------
@social_bp.route("/accept_request/<int:req_id>")
@login_required
def accept_request(req_id):
    # Принимаем заявку
    new_friend = current_user.accept_friend_request(req_id)

    if new_friend:
        # Создаем уведомление для отправителя заявки
        notification_message = f"{current_user.username} принял вашу заявку в друзья!"

        new_notification = Notification(
            user_id=new_friend.id,
            type="friend_accepted",
            message=notification_message
        )

        db.session.add(new_notification)
        db.session.commit()

        flash(f"Вы и {new_friend.username} теперь друзья!", "success")
    else:
        flash("Не удалось принять заявку.", "error")

    return redirect(url_for("social.requests"))

# ----------------------------------------------------------
# МАРШРУТ: ОТКЛОНИТЬ ЗАЯВКУ
# ----------------------------------------------------------
@social_bp.route("/reject_request/<int:req_id>")
@login_required
def reject_request(req_id):
    # Находим заявку
    friend_request = FriendRequest.query.get_or_404(req_id)

    # Проверяем, что заявка адресована нам
    if friend_request.to_user_id == current_user.id:
        friend_request.status = 'rejected'
        db.session.commit()
        flash("Заявка отклонена.", "info")

    return redirect(url_for("social.requests"))

# ----------------------------------------------------------
# МАРШРУТ: ЛЕНТА ЗАПИСЕЙ (FEED)
# ----------------------------------------------------------
@social_bp.route("/feed")
@login_required
def feed():
    # Получаем ID всех друзей
    friends_ids = [friend.id for friend in current_user.friends.all()]
    # Добавляем свой ID для отображения своих записей
    friends_ids.append(current_user.id)

    # Получаем записи друзей и публичные записи
    feed_entries = Entry.query.filter(
        (Entry.user_id.in_(friends_ids)) | (Entry.is_public == True)
    ).order_by(Entry.date.desc()).limit(50).all()

    # Передаем записи в шаблон
    return render_template("social/feed.html", entries=feed_entries)

# ----------------------------------------------------------
# МАРШРУТ: ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ----------------------------------------------------------
@social_bp.route("/profile/<int:user_id>")
@login_required
def user_profile(user_id):
    # Находим пользователя
    profile_user = User.query.get_or_404(user_id)

    # Получаем публичные записи пользователя
    user_entries = Entry.query.filter_by(
        user_id=user_id,
        is_public=True
    ).order_by(Entry.date.desc()).all()

    # Проверяем статус дружбы
    is_friend = current_user.is_friend(profile_user)

    # Проверяем, есть ли ожидающая заявка
    pending_request = FriendRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=user_id,
        status='pending'
    ).first()

    # Передаем данные в шаблон
    return render_template(
        "social/profile.html",
        user=profile_user,
        entries=user_entries,
        is_friend=is_friend,
        pending_request=pending_request is not None
    )
''')



# ============================================================
# БЛОК 11: APP/BLUEPRINTS/GROUPS.PY
# ============================================================
with open('app/blueprints/groups.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для групп
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Group, GroupMember, Entry, db
from app.utils import analyze_mood

# Создание Blueprint'а
groups_bp = Blueprint("groups", __name__)

# ----------------------------------------------------------
# МАРШРУТ: СПИСОК ГРУПП
# ----------------------------------------------------------
@groups_bp.route("/")
@login_required
def index():
    # Группы, в которых состоит пользователь
    my_groups = Group.query.filter(
        Group.members.any(user_id=current_user.id)
    ).all()

    # Все существующие группы
    all_groups = Group.query.all()

    # Передаем данные в шаблон
    return render_template(
        "groups/index.html",
        my_groups=my_groups,
        all_groups=all_groups
    )

# ----------------------------------------------------------
# МАРШРУТ: СОЗДАТЬ ГРУППУ
# ----------------------------------------------------------
@groups_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    # Обработка отправки формы
    if request.method == "POST":
        group_name = request.form.get("name", "").strip()
        group_description = request.form.get("description", "").strip()

        # Проверяем, что название группы не пустое
        if not group_name:
            flash("Название группы не может быть пустым!", "error")
            return redirect(url_for("groups.create"))

        # Создаем новую группу
        new_group = Group(
            name=group_name,
            description=group_description,
            created_by=current_user.id
        )

        db.session.add(new_group)
        db.session.commit()

        # Добавляем создателя в участники группы
        creator_membership = GroupMember(
            user_id=current_user.id,
            group_id=new_group.id
        )

        db.session.add(creator_membership)
        db.session.commit()

        flash(f"Группа '{group_name}' успешно создана!", "success")
        return redirect(url_for("groups.index"))

    # Отображаем форму создания
    return render_template("groups/create.html")

# ----------------------------------------------------------
# МАРШРУТ: ПРОСМОТР ГРУППЫ
# ----------------------------------------------------------
@groups_bp.route("/<int:group_id>")
@login_required
def view(group_id):
    # Находим группу
    group = Group.query.get_or_404(group_id)

    # Получаем записи группы
    group_entries = Entry.query.filter_by(
        group_id=group_id
    ).order_by(Entry.date.desc()).all()

    # Проверяем, является ли текущий пользователь участником
    is_member = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first() is not None

    # Передаем данные в шаблон
    return render_template(
        "groups/view.html",
        group=group,
        entries=group_entries,
        is_member=is_member
    )

# ----------------------------------------------------------
# МАРШРУТ: ВСТУПИТЬ В ГРУППУ
# ----------------------------------------------------------
@groups_bp.route("/join/<int:group_id>")
@login_required
def join(group_id):
    # Проверяем, не состоит ли пользователь уже в группе
    existing_membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()

    if existing_membership:
        flash("Вы уже состоите в этой группе.", "info")
    else:
        # Добавляем пользователя в группу
        new_membership = GroupMember(
            user_id=current_user.id,
            group_id=group_id
        )
        db.session.add(new_membership)
        db.session.commit()
        flash("Вы успешно вступили в группу!", "success")

    return redirect(url_for("groups.view", group_id=group_id))

# ----------------------------------------------------------
# МАРШРУТ: ДОБАВИТЬ ЗАПИСЬ В ГРУППУ
# ----------------------------------------------------------
@groups_bp.route("/add_entry/<int:group_id>", methods=["GET", "POST"])
@login_required
def add_entry(group_id):
    # Проверяем, является ли пользователь участником группы
    is_member = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()

    if not is_member:
        flash("Вы должны вступить в группу, чтобы писать в ней.", "error")
        return redirect(url_for("groups.view", group_id=group_id))

    # Обработка отправки формы
    if request.method == "POST":
        entry_content = request.form.get("content", "").strip()

        if not entry_content:
            flash("Запись не может быть пустой.", "error")
            return redirect(url_for("groups.add_entry", group_id=group_id))

        # Анализируем настроение
        mood_score, mood_label = analyze_mood(entry_content)

        # Создаем новую запись
        new_entry = Entry(
            text_content=entry_content,
            sentiment_score=mood_score,
            mood_label=mood_label,
            author=current_user,
            group_id=group_id
        )

        db.session.add(new_entry)
        db.session.commit()

        flash("Запись добавлена в группу!", "success")
        return redirect(url_for("groups.view", group_id=group_id))

    # Отображаем форму добавления записи
    return render_template("groups/add_entry.html", group_id=group_id)
''')


# ============================================================
# БЛОК 12: APP/BLUEPRINTS/CHAT.PY
# ============================================================
with open('app/blueprints/chat.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для чата
from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from flask_socketio import emit, join_room
from app import socketio, db
from app.models import User, Message
from datetime import datetime

# Создание Blueprint'а
chat_bp = Blueprint("chat", __name__)

# ----------------------------------------------------------
# МАРШРУТ: СПИСОК ЧАТОВ
# ----------------------------------------------------------
@chat_bp.route("/")
@login_required
def index():
    # Получаем список друзей для чата
    user_friends = current_user.friends.all()

    # Передаем список в шаблон
    return render_template("chat/index.html", friends=user_friends)

# ----------------------------------------------------------
# МАРШРУТ: ЧАТ С ДРУГОМ
# ----------------------------------------------------------
@chat_bp.route("/<int:friend_id>")
@login_required
def chat_with(friend_id):
    # Находим друга
    chat_friend = User.query.get_or_404(friend_id)

    # Проверяем, что это действительно друг
    if not current_user.is_friend(chat_friend):
        flash("Вы не друзья с этим пользователем.", "error")
        return redirect(url_for("chat.index"))

    # Отмечаем все сообщения от этого друга как прочитанные
    Message.query.filter_by(
        sender_id=friend_id,
        receiver_id=current_user.id,
        is_read=False
    ).update({"is_read": True})
    db.session.commit()

    # Получаем историю сообщений
    chat_messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
        ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    # Передаем данные в шаблон
    return render_template(
        "chat/chat.html",
        friend=chat_friend,
        messages=chat_messages
    )

# ----------------------------------------------------------
# WEBSOCKET: ОТПРАВКА СООБЩЕНИЯ
# ----------------------------------------------------------
@socketio.on('send_message')
def handle_send_message(data):
    # Проверяем авторизацию
    if not current_user.is_authenticated:
        return

    # Получаем данные
    recipient_id = data.get('friend_id')
    message_text = data.get('text', '').strip()

    # Проверяем данные
    if not message_text or not recipient_id:
        return

    # Находим получателя
    recipient = User.query.get(recipient_id)

    # Проверяем, что получатель существует и является другом
    if not recipient or not current_user.is_friend(recipient):
        return

    # Создаем новое сообщение
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=recipient_id,
        text=message_text,
        created_at=datetime.utcnow()
    )

    db.session.add(new_message)
    db.session.commit()

    # Формируем данные для отправки
    message_data = {
        'sender_id': current_user.id,
        'text': message_text,
        'created_at': new_message.created_at.strftime('%H:%M')
    }

    # Отправляем сообщение получателю
    emit('new_message', message_data, room=f'user_{recipient_id}')

    # Отправляем сообщение отправителю (для обновления своего интерфейса)
    emit('new_message', message_data, room=f'user_{current_user.id}')

# ----------------------------------------------------------
# WEBSOCKET: ИНДИКАТОР ПЕЧАТИ
# ----------------------------------------------------------
@socketio.on('typing')
def handle_typing(data):
    # Проверяем авторизацию
    if not current_user.is_authenticated:
        return

    # Получаем ID друга
    recipient_id = data.get('friend_id')

    # Отправляем событие о печати
    emit('user_typing', {
        'user_id': current_user.id
    }, room=f'user_{recipient_id}')

# ----------------------------------------------------------
# WEBSOCKET: ПОДКЛЮЧЕНИЕ К КОМНАТЕ
# ----------------------------------------------------------
@socketio.on('join')
def handle_join():
    # Проверяем авторизацию
    if current_user.is_authenticated:
        # Обновляем статус онлайн
        current_user.is_online = True
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        # Подключаем пользователя к его личной комнате
        join_room(f'user_{current_user.id}')

# ----------------------------------------------------------
# WEBSOCKET: ОТКЛЮЧЕНИЕ
# ----------------------------------------------------------
@socketio.on('disconnect')
def handle_disconnect():
    # Обновляем статус при отключении
    if current_user.is_authenticated:
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
''')


# ============================================================
# БЛОК 13: APP/BLUEPRINTS/ADMIN.PY
# ============================================================
with open('app/blueprints/admin.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для админ-панели
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Entry, db
from functools import wraps

# Создание Blueprint'а
admin_bp = Blueprint("admin", __name__)

# ----------------------------------------------------------
# ДЕКОРАТОР ДЛЯ ПРОВЕРКИ ПРАВ АДМИНИСТРАТОРА
# ----------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, что пользователь авторизован и является админом
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("У вас нет прав для доступа к этой странице.", "error")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------------
# МАРШРУТ: ГЛАВНАЯ СТРАНИЦА АДМИН-ПАНЕЛИ
# ----------------------------------------------------------
@admin_bp.route("/")
@login_required
@admin_required
def index():
    # Получаем список всех пользователей
    all_users = User.query.all()

    # Статистика
    total_users = User.query.count()
    total_entries = Entry.query.count()

    # Передаем данные в шаблон
    return render_template(
        "admin/index.html",
        users=all_users,
        total_users=total_users,
        total_entries=total_entries
    )

# ----------------------------------------------------------
# МАРШРУТ: ЗАБЛОКИРОВАТЬ/РАЗБЛОКИРОВАТЬ ПОЛЬЗОВАТЕЛЯ
# ----------------------------------------------------------
@admin_bp.route("/block/<int:user_id>")
@login_required
@admin_required
def block_user(user_id):
    # Находим пользователя
    target_user = User.query.get_or_404(user_id)

    # Нельзя заблокировать самого себя
    if target_user.id == current_user.id:
        flash("Вы не можете заблокировать сами себя.", "error")
    else:
        # Переключаем статус блокировки
        target_user.is_blocked = not target_user.is_blocked
        db.session.commit()

        status_text = "заблокирован" if target_user.is_blocked else "разблокирован"
        flash(f"Пользователь {target_user.username} {status_text}.", "success")

    return redirect(url_for("admin.index"))

# ----------------------------------------------------------
# МАРШРУТ: УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ
# ----------------------------------------------------------
@admin_bp.route("/delete/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    # Находим пользователя
    target_user = User.query.get_or_404(user_id)

    # Нельзя удалить самого себя
    if target_user.id == current_user.id:
        flash("Вы не можете удалить сами себя.", "error")
    else:
        username = target_user.username
        db.session.delete(target_user)
        db.session.commit()
        flash(f"Пользователь {username} удалён.", "success")

    return redirect(url_for("admin.index"))

# ----------------------------------------------------------
# МАРШРУТ: НАЗНАЧИТЬ АДМИНИСТРАТОРОМ
# ----------------------------------------------------------
@admin_bp.route("/make_admin/<int:user_id>")
@login_required
@admin_required
def make_admin(user_id):
    # Находим пользователя
    target_user = User.query.get_or_404(user_id)

    # Делаем пользователя админом
    target_user.is_admin = True
    db.session.commit()

    flash(f"Пользователь {target_user.username} теперь администратор.", "success")
    return redirect(url_for("admin.index"))
''')


# ============================================================
# БЛОК 14: APP/BLUEPRINTS/API.PY
# ============================================================
with open('app/blueprints/api.py', 'w', encoding='utf-8') as f:
    f.write('''
# Импорты для API
from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from app.models import Entry, Notification, db
from datetime import datetime

# Создание Blueprint'а
api_bp = Blueprint("api", __name__)

# ----------------------------------------------------------
# API: ДАННЫЕ ДЛЯ ГРАФИКА НАСТРОЕНИЯ
# ----------------------------------------------------------
@api_bp.route("/data")
@login_required
def get_chart_data():
    # Получаем все записи пользователя
    user_entries = Entry.query.filter_by(
        user_id=current_user.id
    ).order_by(Entry.date.asc()).all()

    # Формируем данные для графика
    dates = []
    scores = []

    for entry in user_entries:
        dates.append(entry.date.strftime('%d.%m %H:%M'))
        scores.append(entry.sentiment_score)

    # Возвращаем JSON
    return jsonify({
        "dates": dates,
        "scores": scores
    })

# ----------------------------------------------------------
# API: КОЛИЧЕСТВО НЕПРОЧИТАННЫХ УВЕДОМЛЕНИЙ
# ----------------------------------------------------------
@api_bp.route("/notifications/count")
@login_required
def get_notifications_count():
    # Считаем непрочитанные уведомления
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()

    # Возвращаем JSON
    return jsonify({
        "count": count
    })

# ----------------------------------------------------------
# API: ИНФОРМАЦИЯ О СТРИКЕ
# ----------------------------------------------------------
@api_bp.route("/streak")
@login_required
def get_streak_info():
    # Проверяем, писал ли пользователь сегодня
    today = datetime.utcnow().date()
    wrote_today = Entry.query.filter_by(
        user_id=current_user.id
    ).filter(
        db.func.date(Entry.date) == today
    ).count() > 0

    # Возвращаем JSON
    return jsonify({
        "streak": current_user.streak_days,
        "max_streak": current_user.max_streak,
        "emoji": current_user.get_streak_emoji(),
        "wrote_today": wrote_today
    })
''')


# ============================================================
# БЛОК 15: ШАБЛОНЫ (ЧАСТЬ 1)
# ============================================================
templates_part1 = {
    # ----------------------------------------------------------
    # ШАБЛОН: BASE.HTML
    # ----------------------------------------------------------
    'base.html': '''<!DOCTYPE html>
<html data-theme="{{ session.get('theme', current_user.theme if current_user.is_authenticated else 'light') }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#6366f1">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <title>MoodMap ✦</title>

    <!-- Подключение иконок Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

    <!-- Подключение Socket.IO для чата -->
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>

    <!-- Подключение библиотеки конфетти -->
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1"></script>

    <!-- Подключение Chart.js для графиков -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        /* ============================================================
           ПОДКЛЮЧЕНИЕ ШРИФТОВ
           ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

        /* ============================================================
           БАЗОВЫЕ СТИЛИ
           ============================================================ */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: '{{ current_user.font_style if current_user.is_authenticated else "Inter" }}', -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            overflow-x: hidden;
            line-height: 1.5;
        }

        /* ============================================================
           ПЕРЕМЕННЫЕ ТЕМ
           ============================================================ */
        [data-theme="light"] {
            --bg-color: #f8fafc;
            --glass-bg: rgba(255, 255, 255, 0.55);
            --glass-border: rgba(255, 255, 255, 0.7);
            --text-primary: #1a1a2e;
            --text-secondary: #64748b;
            --accent-color: #6366f1;
            --success-color: #10b981;
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --online-color: #10b981;
            --card-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
            --card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.08);
        }

        [data-theme="dark"] {
            --bg-color: #0f0f23;
            --glass-bg: rgba(15, 15, 35, 0.65);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --accent-color: #818cf8;
            --success-color: #34d399;
            --danger-color: #f87171;
            --warning-color: #fbbf24;
            --online-color: #34d399;
            --card-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            --card-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.5);
        }

        /* ============================================================
           БАЗОВЫЙ ФОН И ТЕКСТ
           ============================================================ */
        body {
            background-color: var(--bg-color);
            min-height: 100vh;
            color: var(--text-primary);
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        /* ============================================================
           АНИМИРОВАННЫЕ БЛОБЫ НА ФОНЕ
           ============================================================ */
        .bg-blobs {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -1;
            pointer-events: none;
            overflow: hidden;
        }

        .bg-blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.2;
            animation: blobFloat 25s ease-in-out infinite;
        }

        .bg-blob:nth-child(1) {
            width: 400px;
            height: 400px;
            background-color: var(--accent-color);
            top: -100px;
            left: -100px;
        }

        .bg-blob:nth-child(2) {
            width: 300px;
            height: 300px;
            background-color: var(--success-color);
            bottom: -100px;
            right: -100px;
            animation-delay: -8s;
        }

        @keyframes blobFloat {
            0%, 100% {
                transform: translate(0, 0) scale(1);
            }
            50% {
                transform: translate(50px, -50px) scale(1.05);
            }
        }

        /* ============================================================
           НАВИГАЦИОННАЯ ПАНЕЛЬ
           ============================================================ */
        .nav {
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-bottom: 1px solid var(--glass-border);
            padding: 0 20px;
            transition: all 0.3s ease;
        }

        .nav-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 56px;
        }

        .logo {
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-color), var(--success-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-decoration: none;
            letter-spacing: -0.02em;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .nav-link {
            color: var(--text-primary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            opacity: 0.8;
            transition: opacity 0.2s ease;
            position: relative;
        }

        .nav-link:hover {
            opacity: 1;
        }

        /* ============================================================
           ОСНОВНОЙ КОНТЕЙНЕР
           ============================================================ */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 28px 20px;
            animation: fadeInUp 0.4s ease;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(12px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* ============================================================
           СТЕКЛЯННЫЕ КАРТОЧКИ
           ============================================================ */
        .card {
            background: var(--glass-bg);
            backdrop-filter: blur(24px) saturate(180%);
            -webkit-backdrop-filter: blur(24px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 24px;
            box-shadow: var(--card-shadow);
            margin-bottom: 20px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: var(--card-shadow-hover);
        }

        /* ============================================================
           КНОПКИ
           ============================================================ */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 11px 24px;
            border-radius: 40px;
            font-size: 15px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s ease;
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            color: var(--text-primary);
            cursor: pointer;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: var(--card-shadow);
        }

        .btn:active {
            transform: scale(0.98);
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-color), var(--accent-color));
            color: white;
            border: none;
        }

        .btn-sm {
            padding: 8px 14px;
            font-size: 13px;
        }

        /* ============================================================
           ПЛАВАЮЩАЯ КНОПКА ДЕЙСТВИЯ (FAB)
           ============================================================ */
        .fab {
            position: fixed;
            bottom: 32px;
            right: 32px;
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--accent-color), var(--accent-color));
            color: white;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
            z-index: 99;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .fab:hover {
            transform: scale(1.05);
            border-radius: 20px;
        }

        /* ============================================================
           ФОРМЫ ВВОДА
           ============================================================ */
        .input {
            width: 100%;
            padding: 14px 18px;
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            color: var(--text-primary);
            font-size: 15px;
            font-family: inherit;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .input:focus {
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
        }

        textarea.input {
            min-height: 120px;
            resize: vertical;
            line-height: 1.6;
        }

        /* ============================================================
           БЕЙДЖИ
           ============================================================ */
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 30px;
            font-size: 12px;
            font-weight: 500;
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            color: var(--text-secondary);
        }

        .badge-success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success-color);
            border-color: rgba(16, 185, 129, 0.3);
        }

        .badge-danger {
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger-color);
            border-color: rgba(239, 68, 68, 0.3);
        }

        /* ============================================================
           УВЕДОМЛЕНИЯ (АЛЕРТЫ)
           ============================================================ */
        .alert {
            padding: 14px 20px;
            border-radius: 16px;
            margin-bottom: 16px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid;
            animation: alertSlideIn 0.3s ease;
        }

        @keyframes alertSlideIn {
            from {
                opacity: 0;
                transform: translateY(-8px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .alert-success {
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.3);
            color: var(--success-color);
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.3);
            color: var(--danger-color);
        }

        .alert-info {
            background: rgba(99, 102, 241, 0.1);
            border-color: rgba(99, 102, 241, 0.3);
            color: var(--accent-color);
        }

        /* ============================================================
           АНИМАЦИЯ ОГОНЬКА СТРИКА
           ============================================================ */
        .streak-fire {
            display: inline-block;
            animation: fireFloat 1.5s ease-in-out infinite;
        }

        @keyframes fireFloat {
            0%, 100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(-3px);
            }
        }

        /* ============================================================
           ТАБЛИЦА
           ============================================================ */
        .table {
            width: 100%;
            border-collapse: collapse;
        }

        .table th {
            text-align: left;
            padding: 14px 16px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--glass-border);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }

        .table td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--glass-border);
            font-size: 15px;
        }

        .table tbody tr {
            transition: background-color 0.2s ease;
        }

        .table tbody tr:hover {
            background-color: var(--glass-bg);
        }

        /* ============================================================
           АВАТАРЫ
           ============================================================ */
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--glass-border);
            transition: transform 0.2s ease;
        }

        .avatar:hover {
            transform: scale(1.1);
        }

        .avatar-large {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--glass-border);
        }

        /* ============================================================
           БАННЕР ПРОФИЛЯ
           ============================================================ */
        .banner {
            width: 100%;
            height: 160px;
            background-size: cover;
            background-position: center;
            border-radius: 20px 20px 0 0;
        }

        /* ============================================================
           ИНДИКАТОР ОНЛАЙН
           ============================================================ */
        .online-dot {
            width: 8px;
            height: 8px;
            background-color: var(--online-color);
            border-radius: 50%;
            display: inline-block;
            animation: pulseDot 2s ease-in-out infinite;
        }

        @keyframes pulseDot {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
            }
            50% {
                box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
            }
        }

        /* ============================================================
           ОБЛАКО СЛОВ
           ============================================================ */
        .word-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 12px 20px;
            justify-content: center;
            padding: 10px 0;
        }

        .word-cloud span {
            opacity: 0.8;
            transition: opacity 0.2s ease;
            cursor: default;
        }

        .word-cloud span:hover {
            opacity: 1;
        }

        /* ============================================================
           УТИЛИТАРНЫЕ КЛАССЫ
           ============================================================ */
        .flex { display: flex; }
        .items-center { align-items: center; }
        .justify-between { justify-content: space-between; }
        .gap-2 { gap: 8px; }
        .gap-3 { gap: 12px; }
        .gap-4 { gap: 16px; }
        .grid { display: grid; gap: 20px; }
        .grid-cols-2 { grid-template-columns: 1fr 1fr; }
        .grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
        .mb-4 { margin-bottom: 16px; }
        .mb-6 { margin-bottom: 24px; }
        .w-full { width: 100%; }
        .max-w-md { max-width: 520px; }
        .mx-auto { margin-left: auto; margin-right: auto; }
        .text-center { text-align: center; }
        .text-secondary { color: var(--text-secondary); }
        .text-sm { font-size: 13px; }

        h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }

        h2 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 16px;
            letter-spacing: -0.01em;
        }

        h3 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        /* ============================================================
           АДАПТИВНОСТЬ ДЛЯ МОБИЛЬНЫХ
           ============================================================ */
        @media (max-width: 768px) {
            .nav-links {
                display: none;
            }

            .grid-cols-2 {
                grid-template-columns: 1fr;
            }

            .grid-cols-3 {
                grid-template-columns: 1fr;
            }

            .fab {
                bottom: 20px;
                right: 20px;
                width: 48px;
                height: 48px;
                font-size: 22px;
            }

            .container {
                padding: 20px 12px;
            }

            h1 {
                font-size: 26px;
            }

            h2 {
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <!-- Анимированные блобы на фоне -->
    <div class="bg-blobs">
        <div class="bg-blob"></div>
        <div class="bg-blob"></div>
    </div>

    <!-- Навигационная панель -->
    <nav class="nav">
        <div class="nav-content">
            <!-- Логотип -->
            <a href="/" class="logo">✦ MoodMap</a>

            <!-- Ссылки навигации -->
            <div class="nav-links">
                {% if current_user.is_authenticated %}
                    <a href="{{ url_for('main.dashboard') }}" class="nav-link">Дневник</a>
                    <a href="{{ url_for('main.mood_calendar') }}" class="nav-link">Календарь</a>
                    <a href="{{ url_for('social.feed') }}" class="nav-link">Лента</a>
                    <a href="{{ url_for('social.friends') }}" class="nav-link">Друзья</a>
                    <a href="{{ url_for('chat.index') }}" class="nav-link">Чат</a>
                    <a href="{{ url_for('groups.index') }}" class="nav-link">Группы</a>
                    <a href="{{ url_for('main.bookmarks') }}" class="nav-link">🔖</a>
                    <a href="{{ url_for('main.goals') }}" class="nav-link">Цели</a>
                    <a href="{{ url_for('main.wrapped') }}" class="nav-link">Wrapped</a>

                    {% if current_user.is_admin %}
                        <a href="{{ url_for('admin.index') }}" class="nav-link">👑 Админ</a>
                    {% endif %}

                    <!-- Уведомления с счётчиком -->
                    <a href="{{ url_for('auth.notifications') }}" class="nav-link" style="position: relative;">
                        <i class="far fa-bell"></i>
                        <span id="bell-count" class="badge badge-danger" style="display: none; position: absolute; top: -8px; right: -10px; font-size: 10px; padding: 2px 6px;"></span>
                    </a>

                    <!-- Огонёк стрика -->
                    <span class="streak-fire">{{ current_user.get_streak_emoji() }}</span>

                    <!-- Профиль -->
                    <a href="{{ url_for('auth.profile') }}" class="nav-link">
                        {{ current_user.username }}
                        {% if current_user.is_admin %}👑{% endif %}
                    </a>

                    <!-- Переключение темы -->
                    {% if session.get('theme', current_user.theme) == 'light' %}
                        <a href="{{ url_for('auth.set_theme', theme='dark') }}" class="nav-link" title="Тёмная тема">
                            <i class="far fa-moon"></i>
                        </a>
                    {% else %}
                        <a href="{{ url_for('auth.set_theme', theme='light') }}" class="nav-link" title="Светлая тема">
                            <i class="far fa-sun"></i>
                        </a>
                    {% endif %}

                    <!-- Выход -->
                    <a href="{{ url_for('auth.logout') }}" class="btn btn-sm">Выйти</a>
                {% else %}
                    <a href="{{ url_for('auth.login') }}" class="nav-link">Вход</a>
                    <a href="{{ url_for('auth.register') }}" class="nav-link">Регистрация</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <!-- Основной контент -->
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message|safe }}</div>
            {% endfor %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <!-- Плавающая кнопка добавления записи -->
    {% if current_user.is_authenticated %}
        <a href="{{ url_for('main.add_entry') }}" class="fab" title="Новая запись">
            <i class="fas fa-plus"></i>
        </a>
    {% endif %}

    <script>
        // ----------------------------------------------------------
        // КОНФЕТТИ ПРИ СТРИКЕ 7+ ДНЕЙ
        // ----------------------------------------------------------
        {% if current_user.is_authenticated and current_user.streak_days >= 7 %}
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            });
        {% endif %}

        // ----------------------------------------------------------
        // АВТОМАТИЧЕСКАЯ ТЕМА ПО ВРЕМЕНИ СУТОК
        // ----------------------------------------------------------
        {% if current_user.is_authenticated and current_user.auto_theme %}
            const currentHour = new Date().getHours();
            if (currentHour >= 20 || currentHour < 6) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
            }
        {% endif %}

        // ----------------------------------------------------------
        // ОБНОВЛЕНИЕ СЧЁТЧИКА УВЕДОМЛЕНИЙ
        // ----------------------------------------------------------
        async function updateNotificationBell() {
            try {
                const response = await fetch('/api/notifications/count');
                const data = await response.json();
                const bellCountElement = document.getElementById('bell-count');

                if (data.count > 0) {
                    bellCountElement.textContent = data.count;
                    bellCountElement.style.display = 'inline-block';
                } else {
                    bellCountElement.style.display = 'none';
                }
            } catch (error) {
                // Игнорируем ошибки
            }
        }

        // Запускаем обновление сразу и каждые 15 секунд
        updateNotificationBell();
        setInterval(updateNotificationBell, 15000);
    </script>
</body>
</html>''',

    # ----------------------------------------------------------
    # ШАБЛОН: LOGIN.HTML
    # ----------------------------------------------------------
    'login.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex items-center" style="min-height: 70vh;">
    <div class="max-w-md mx-auto w-full">
        <div class="card">
            <h2 class="text-center">Вход в MoodMap</h2>
            <p class="text-secondary text-center mb-4">Войдите, чтобы продолжить вести дневник</p>

            <form method="POST">
                <div class="mb-4">
                    <input type="text" name="username" class="input" placeholder="Логин" required autocomplete="username">
                </div>

                <div class="mb-4">
                    <input type="password" name="password" class="input" placeholder="Пароль" required autocomplete="current-password">
                </div>

                <button type="submit" class="btn btn-primary w-full">
                    <i class="fas fa-sign-in-alt"></i> Войти
                </button>
            </form>

            <div class="mt-6 text-center">
                <p class="text-secondary mb-3">Ещё нет аккаунта?</p>
                <a href="{{ url_for('auth.register') }}" class="btn w-full">
                    <i class="fas fa-user-plus"></i> Создать аккаунт
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: REGISTER.HTML
    # ----------------------------------------------------------
    'register.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex items-center" style="min-height: 70vh;">
    <div class="max-w-md mx-auto w-full">
        <div class="card">
            <h2 class="text-center">Регистрация</h2>
            <p class="text-secondary text-center mb-4">Создайте аккаунт за пару секунд</p>

            <form method="POST">
                <div class="mb-4">
                    <input type="text" name="username" class="input" placeholder="Придумайте логин" required autocomplete="username">
                </div>

                <div class="mb-4">
                    <input type="email" name="email" class="input" placeholder="Ваш email" required autocomplete="email">
                </div>

                <div class="mb-4">
                    <input type="password" name="password" class="input" placeholder="Придумайте пароль" required autocomplete="new-password">
                </div>

                <div class="mb-4">
                    <label class="text-secondary text-sm">Выберите тему оформления</label>
                    <select name="theme" class="input">
                        <option value="light">☀️ Светлая тема</option>
                        <option value="dark">🌙 Тёмная тема</option>
                    </select>
                </div>

                <button type="submit" class="btn btn-primary w-full">
                    <i class="fas fa-check-circle"></i> Зарегистрироваться
                </button>
            </form>

            <div class="mt-6 text-center">
                <p class="text-secondary mb-3">Уже есть аккаунт?</p>
                <a href="{{ url_for('auth.login') }}" class="btn w-full">
                    <i class="fas fa-sign-in-alt"></i> Войти
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: PROFILE.HTML
    # ----------------------------------------------------------
    'profile.html': '''{% extends "base.html" %}

{% block content %}
<div class="max-w-md mx-auto">
    <div class="card">
        <!-- Баннер профиля -->
        {% if current_user.banner %}
            <div class="banner" style="background-image: url('{{ url_for('static', filename='banners/' + current_user.banner) }}');"></div>
        {% endif %}

        <!-- Аватар и имя -->
        <div class="flex items-center gap-4 mb-6">
            {% if current_user.avatar != 'default.png' %}
                <img src="{{ url_for('static', filename='uploads/' + current_user.avatar) }}" class="avatar-large" alt="Аватар">
            {% else %}
                <div class="avatar-large" style="background: {{ current_user.accent_color }}; display: flex; align-items: center; justify-content: center; color: white; font-size: 40px;">
                    {{ current_user.username[0].upper() }}
                </div>
            {% endif %}

            <div>
                <h2>
                    {{ current_user.username }}
                    {% if current_user.is_admin %}👑{% endif %}
                </h2>
                <p class="text-secondary">{{ current_user.status_emoji }} {{ current_user.status_text }}</p>
            </div>
        </div>

        <!-- Форма редактирования профиля -->
        <form method="POST" enctype="multipart/form-data">
            <div class="mb-4">
                <label class="text-secondary text-sm">Имя пользователя</label>
                <input type="text" name="username" class="input" value="{{ current_user.username }}">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">О себе</label>
                <textarea name="bio" class="input" placeholder="Расскажите о себе...">{{ current_user.bio }}</textarea>
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Эмодзи статуса</label>
                <input type="text" name="status_emoji" class="input" value="{{ current_user.status_emoji }}" placeholder="😊">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Текст статуса</label>
                <input type="text" name="status_text" class="input" value="{{ current_user.status_text }}" placeholder="Всё отлично!">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Цвет акцента</label>
                <input type="color" name="accent_color" class="input" value="{{ current_user.accent_color }}" style="height: 44px;">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Фон чата</label>
                <select name="chat_bg" class="input">
                    <option value="gradient1" {% if current_user.chat_bg == 'gradient1' %}selected{% endif %}>Светлый градиент</option>
                    <option value="gradient2" {% if current_user.chat_bg == 'gradient2' %}selected{% endif %}>Тёмный градиент</option>
                    <option value="gradient3" {% if current_user.chat_bg == 'gradient3' %}selected{% endif %}>Фиолетовый градиент</option>
                </select>
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Шрифт интерфейса</label>
                <select name="font_style" class="input">
                    <option value="Inter" {% if current_user.font_style == 'Inter' %}selected{% endif %}>Inter (Современный)</option>
                    <option value="Roboto" {% if current_user.font_style == 'Roboto' %}selected{% endif %}>Roboto (Классический)</option>
                    <option value="Montserrat" {% if current_user.font_style == 'Montserrat' %}selected{% endif %}>Montserrat (Стильный)</option>
                </select>
            </div>

            <div class="mb-4">
                <label class="flex items-center gap-2">
                    <input type="checkbox" name="sound_enabled" {% if current_user.sound_enabled %}checked{% endif %}>
                    <span class="text-sm">Включить звуки интерфейса</span>
                </label>
            </div>

            <div class="mb-4">
                <label class="flex items-center gap-2">
                    <input type="checkbox" name="auto_theme" {% if current_user.auto_theme %}checked{% endif %}>
                    <span class="text-sm">Автоматическая тема (тёмная после 20:00)</span>
                </label>
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Аватар</label>
                <input type="file" name="avatar" class="input" accept="image/*">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Баннер профиля</label>
                <input type="file" name="banner" class="input" accept="image/*">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Новый пароль (оставьте пустым, если не хотите менять)</label>
                <input type="password" name="new_password" class="input" placeholder="Новый пароль">
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm">Подтвердите новый пароль</label>
                <input type="password" name="confirm_password" class="input" placeholder="Подтвердите пароль">
            </div>

            <div class="flex gap-3">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Сохранить изменения
                </button>
                <a href="{{ url_for('main.dashboard') }}" class="btn">Отмена</a>
            </div>
        </form>

        <!-- Достижения -->
        {% if achievements %}
            <h3 class="mt-6">🏆 Достижения</h3>
            <div class="flex gap-2 flex-wrap">
                {% for achievement in achievements %}
                    <span class="badge" title="{{ achievement.description }}">
                        {{ achievement.icon }} {{ achievement.name }}
                    </span>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: DASHBOARD.HTML
    # ----------------------------------------------------------
    'dashboard.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1>Мой дневник</h1>
    <div class="flex gap-2">
        <a href="{{ url_for('main.claim_reward') }}" class="btn btn-primary btn-sm">
            🎁 Ежедневная награда
        </a>
        <a href="{{ url_for('main.wrapped') }}" class="btn btn-sm">
            📊 Wrapped
        </a>
    </div>
</div>

<!-- Карточки стрика и уровня -->
<div class="grid grid-cols-2 mb-4">
    <!-- Карточка стрика -->
    <div class="card">
        <h3>{{ streak_status }}</h3>
        <div class="streak-fire" style="font-size: 48px;">
            {{ current_user.get_streak_emoji() }}
        </div>
        <p class="text-secondary">
            🔥 {{ current_user.streak_days }} дней подряд
        </p>
        <p class="text-secondary">
            🏆 Рекорд: {{ current_user.max_streak }} дней
        </p>
    </div>

    <!-- Карточка уровня -->
    <div class="card">
        <h3>Уровень {{ current_user.level }}</h3>
        <div style="font-size: 48px; text-align: center;">
            ⭐
        </div>
        <div style="margin: 16px 0; height: 8px; background: var(--glass-bg); border-radius: 4px; overflow: hidden;">
            <div style="width: {{ (current_user.experience / (current_user.level * 100)) * 100 }}%; height: 100%; background: linear-gradient(90deg, var(--accent-color), var(--success-color)); border-radius: 4px; transition: width 0.5s ease;"></div>
        </div>
        <p class="text-secondary">
            {{ current_user.experience }} / {{ current_user.level * 100 }} XP
        </p>
    </div>
</div>

<!-- Вдохновляющая цитата -->
<div class="card">
    <p class="text-center text-secondary">
        💬 {{ quote }}
    </p>
</div>

<!-- График настроения -->
<div class="card">
    <canvas id="moodChart" height="80"></canvas>
</div>

<!-- Облако слов -->
{% if word_cloud %}
    <div class="card">
        <h3>☁️ Облако слов</h3>
        <div class="word-cloud">
            {% for word, count in word_cloud %}
                <span style="font-size: {{ 12 + count * 2 }}px; color: var(--text-primary);">
                    #{{ word }}
                </span>
            {% endfor %}
        </div>
    </div>
{% endif %}

<!-- Таблица последних записей -->
<div class="card" style="padding: 0; overflow: hidden;">
    <table class="table">
        <thead>
            <tr>
                <th>Дата</th>
                <th>Запись</th>
                <th>Настроение</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for entry in entries %}
                <tr>
                    <td class="text-secondary text-sm">
                        {{ entry.date.strftime('%d.%m.%Y %H:%M') }}
                    </td>
                    <td>
                        {{ entry.text_content[:50] }}{% if entry.text_content|length > 50 %}...{% endif %}
                    </td>
                    <td>
                        <span class="badge {% if entry.mood_label == 'Positive' %}badge-success{% elif entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                            {{ entry.mood_label }} {{ entry.sentiment_score }}
                        </span>
                    </td>
                    <td>
                        <div class="flex gap-2">
                            <a href="{{ url_for('main.edit_entry', id=entry.id) }}" class="btn btn-sm" title="Редактировать">
                                ✏️
                            </a>
                            <a href="{{ url_for('main.delete_entry', id=entry.id) }}" class="btn btn-sm" title="Удалить" onclick="return confirm('Вы уверены, что хотите удалить эту запись?')">
                                🗑️
                            </a>
                            <a href="{{ url_for('main.bookmark_entry', entry_id=entry.id) }}" class="btn btn-sm" title="В закладки">
                                🔖
                            </a>
                        </div>
                    </td>
                </tr>
            {% else %}
                <tr>
                    <td colspan="4" class="text-center text-secondary" style="padding: 40px;">
                        <p>У вас пока нет записей.</p>
                        <a href="{{ url_for('main.add_entry') }}" class="btn btn-primary mt-4">Создать первую запись</a>
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
    // Загрузка данных для графика
    async function loadMoodChart() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();

            if (data.dates.length === 0) return;

            const canvasElement = document.getElementById('moodChart');
            const chartContext = canvasElement.getContext('2d');

            new Chart(chartContext, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Настроение',
                        data: data.scores,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: function(context) {
                            const value = context.raw;
                            if (value > 0.15) return '#10b981';
                            if (value < -0.15) return '#ef4444';
                            return '#94a3b8';
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: -1,
                            max: 1,
                            grid: {
                                color: 'rgba(148, 163, 184, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Ошибка загрузки графика:', error);
        }
    }

    // Загружаем график при загрузке страницы
    loadMoodChart();
</script>
{% endblock %}''',
}

# Сохранение первой части шаблонов
for template_name, template_content in templates_part1.items():
    # Определяем путь к файлу
    template_folder = os.path.dirname(f'app/templates/{template_name}')
    if template_folder:
        os.makedirs(f'app/templates/{template_folder}', exist_ok=True)

    # Записываем файл шаблона
    with open(f'app/templates/{template_name}', 'w', encoding='utf-8') as f:
        f.write(template_content)

# ============================================================
# БЛОК 16: ШАБЛОНЫ (ЧАСТЬ 2) — CALENDAR, ADD, EDIT, GOALS, WRAPPED, BOOKMARKS, EXPORT, NOTIFICATIONS
# ============================================================
templates_part2 = {
    # ----------------------------------------------------------
    # ШАБЛОН: CALENDAR.HTML
    # ----------------------------------------------------------
    'calendar.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1>{{ month_name }} {{ year }}</h1>

    <div class="flex gap-2">
        <a href="?year={{ prev_year }}&month={{ prev_month }}" class="btn btn-sm">
            ← Предыдущий
        </a>
        <a href="{{ url_for('main.mood_calendar') }}" class="btn btn-primary btn-sm">
            Сегодня
        </a>
        <a href="?year={{ next_year }}&month={{ next_month }}" class="btn btn-sm">
            Следующий →
        </a>
    </div>
</div>

<div class="card">
    <!-- Заголовки дней недели -->
    <div class="grid" style="grid-template-columns: repeat(7, 1fr); gap: 8px; margin-bottom: 12px;">
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Пн</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Вт</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Ср</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Чт</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Пт</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Сб</div>
        <div style="text-align: center; font-weight: 600; font-size: 14px; color: var(--text-secondary);">Вс</div>
    </div>

    <!-- Ячейки дней -->
    {% for week in calendar_data %}
        <div class="grid" style="grid-template-columns: repeat(7, 1fr); gap: 8px; margin-bottom: 8px;">
            {% for day in week %}
                {% if day.day > 0 %}
                    <a href="?year={{ year }}&month={{ month }}&day={{ day.day }}" 
                       style="background: {{ day.color }}; 
                              aspect-ratio: 1; 
                              display: flex; 
                              align-items: center; 
                              justify-content: center; 
                              border-radius: 12px; 
                              text-decoration: none; 
                              color: var(--text-primary); 
                              font-weight: 600;
                              font-size: 16px;
                              transition: transform 0.2s ease;
                              {% if day.day == request.args.get('day')|int %}
                                  border: 3px solid var(--accent-color);
                              {% endif %}"
                       onmouseover="this.style.transform='scale(1.1)'"
                       onmouseout="this.style.transform='scale(1)'">
                        {{ day.day }}
                    </a>
                {% else %}
                    <div></div>
                {% endif %}
            {% endfor %}
        </div>
    {% endfor %}
</div>

<!-- Записи за выбранный день -->
{% if day %}
    <div class="card mt-4">
        <h2>Записи за {{ day }}.{{ month }}.{{ year }}</h2>

        {% if day_entries %}
            {% for entry in day_entries %}
                <div class="card mb-3" style="padding: 16px;">
                    <div class="flex justify-between items-center mb-2">
                        <span class="badge">{{ entry.category }}</span>
                        <span class="text-secondary text-sm">{{ entry.date.strftime('%H:%M') }}</span>
                    </div>

                    <p style="line-height: 1.6;">{{ entry.text_content }}</p>

                    <div class="mt-2">
                        <span class="badge {% if entry.mood_label == 'Positive' %}badge-success{% elif entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                            {{ entry.mood_label }} {{ entry.sentiment_score }}
                        </span>
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <p class="text-secondary text-center py-4">Нет записей за этот день.</p>
        {% endif %}
    </div>
{% endif %}

<!-- Легенда цветов -->
<div class="card mt-4">
    <h3>Легенда цветов</h3>
    <div class="flex gap-4 flex-wrap">
        <div class="flex items-center gap-2">
            <div style="width: 20px; height: 20px; background: #28a745; border-radius: 4px;"></div>
            <span class="text-sm">Отлично (0.3+)</span>
        </div>
        <div class="flex items-center gap-2">
            <div style="width: 20px; height: 20px; background: #90ee90; border-radius: 4px;"></div>
            <span class="text-sm">Хорошо (0.1+)</span>
        </div>
        <div class="flex items-center gap-2">
            <div style="width: 20px; height: 20px; background: #ffc107; border-radius: 4px;"></div>
            <span class="text-sm">Нейтрально</span>
        </div>
        <div class="flex items-center gap-2">
            <div style="width: 20px; height: 20px; background: #ffb6c1; border-radius: 4px;"></div>
            <span class="text-sm">Плохо (-0.1-)</span>
        </div>
        <div class="flex items-center gap-2">
            <div style="width: 20px; height: 20px; background: #dc3545; border-radius: 4px;"></div>
            <span class="text-sm">Ужасно (-0.3-)</span>
        </div>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: ADD_ENTRY.HTML
    # ----------------------------------------------------------
    'add_entry.html': '''{% extends "base.html" %}

{% block content %}
<div class="max-w-md mx-auto">
    <div class="card">
        <div class="flex items-center gap-4 mb-6">
            <a href="{{ url_for('main.dashboard') }}" class="btn btn-sm" title="Назад">
                ← Назад
            </a>
            <h2>Новая запись</h2>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <!-- Выбор категории -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Категория</label>
                <select name="category" class="input">
                    {% for category in categories %}
                        <option value="{{ category }}">{{ category }}</option>
                    {% endfor %}
                </select>
            </div>

            <!-- Текст записи -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Ваши мысли и чувства</label>
                <textarea name="content" class="input" placeholder="Напишите о том, что у вас на душе... Используйте #теги для категоризации." required id="voice-input-textarea"></textarea>
                <p class="text-secondary text-sm mt-1">
                    <i class="far fa-lightbulb"></i> Чем больше вы напишете, тем точнее ИИ проанализирует настроение.
                </p>
            </div>

            <!-- Кнопка голосового ввода -->
            <div class="mb-4">
                <button type="button" class="btn btn-sm" onclick="startVoiceRecognition()">
                    <i class="fas fa-microphone"></i> Голосовой ввод
                </button>
                <span class="text-secondary text-sm ml-2">Работает в Chrome</span>
            </div>

            <!-- Публичная запись -->
            <div class="mb-4">
                <label class="flex items-center gap-2">
                    <input type="checkbox" name="is_public">
                    <span class="text-sm">Сделать запись публичной (увидят друзья в ленте)</span>
                </label>
            </div>

            <!-- Загрузка изображения -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Прикрепить изображение</label>
                <input type="file" name="image" class="input" accept="image/*">
            </div>

            <!-- Загрузка аудио -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Записать аудио</label>
                <input type="file" name="audio" class="input" accept="audio/*">
            </div>

            <!-- Кнопки -->
            <div class="flex gap-3">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Сохранить запись
                </button>
                <a href="{{ url_for('main.dashboard') }}" class="btn">
                    Отмена
                </a>
            </div>
        </form>
    </div>
</div>

<script>
    function startVoiceRecognition() {
        // Проверяем поддержку браузером
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert('Голосовой ввод поддерживается только в браузере Chrome.');
            return;
        }

        // Создаем экземпляр распознавания речи
        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // При получении результата добавляем текст в поле ввода
        recognition.onresult = function(event) {
            const transcribedText = event.results[0][0].transcript;
            const textareaElement = document.getElementById('voice-input-textarea');

            if (textareaElement.value) {
                textareaElement.value += ' ' + transcribedText;
            } else {
                textareaElement.value = transcribedText;
            }
        };

        // При ошибке
        recognition.onerror = function(event) {
            console.error('Ошибка распознавания речи:', event.error);
            alert('Не удалось распознать речь. Попробуйте снова.');
        };

        // Запускаем распознавание
        recognition.start();
    }
</script>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: EDIT_ENTRY.HTML
    # ----------------------------------------------------------
    'edit_entry.html': '''{% extends "base.html" %}

{% block content %}
<div class="max-w-md mx-auto">
    <div class="card">
        <div class="flex items-center gap-4 mb-6">
            <a href="{{ url_for('main.dashboard') }}" class="btn btn-sm" title="Назад">
                ← Назад
            </a>
            <h2>Редактирование записи</h2>
        </div>

        <form method="POST">
            <!-- Выбор категории -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Категория</label>
                <select name="category" class="input">
                    {% for category in categories %}
                        <option value="{{ category }}" {% if entry.category == category %}selected{% endif %}>
                            {{ category }}
                        </option>
                    {% endfor %}
                </select>
            </div>

            <!-- Текст записи -->
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">Содержание записи</label>
                <textarea name="content" class="input" required>{{ entry.text_content }}</textarea>
            </div>

            <!-- Публичная запись -->
            <div class="mb-4">
                <label class="flex items-center gap-2">
                    <input type="checkbox" name="is_public" {% if entry.is_public %}checked{% endif %}>
                    <span class="text-sm">Сделать запись публичной</span>
                </label>
            </div>

            <!-- Кнопки -->
            <div class="flex gap-3">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-check"></i> Сохранить изменения
                </button>
                <a href="{{ url_for('main.dashboard') }}" class="btn">
                    Отмена
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: GOALS.HTML
    # ----------------------------------------------------------
    'goals.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1>🎯 Мои цели</h1>
    <button onclick="document.getElementById('goal-form-container').classList.toggle('hidden')" class="btn btn-primary">
        + Новая цель
    </button>
</div>

<!-- Форма создания цели -->
<div id="goal-form-container" class="card mb-4 hidden">
    <h3>Создать новую цель</h3>
    <form method="POST">
        <div class="mb-3">
            <label class="text-secondary text-sm mb-1" style="display: block;">Название цели</label>
            <input type="text" name="title" class="input" placeholder="Например: Писать 7 дней подряд" required>
        </div>

        <div class="mb-3">
            <label class="text-secondary text-sm mb-1" style="display: block;">Целевое значение</label>
            <input type="number" name="target_value" class="input" value="7" min="1" required>
        </div>

        <div class="flex gap-2">
            <button type="submit" class="btn btn-primary">Создать цель</button>
            <button type="button" onclick="document.getElementById('goal-form-container').classList.add('hidden')" class="btn">
                Отмена
            </button>
        </div>
    </form>
</div>

<!-- Список целей -->
<div class="grid">
    {% for goal in goals %}
        <div class="card">
            <div class="flex justify-between items-center">
                <div>
                    <h3>{{ goal.title }}</h3>
                    <p class="text-secondary">
                        Прогресс: {{ goal.current_value }} / {{ goal.target_value }}
                    </p>
                </div>

                {% if not goal.is_completed %}
                    <a href="{{ url_for('main.complete_goal', id=goal.id) }}" class="btn btn-sm btn-primary">
                        ✓ Выполнено
                    </a>
                {% else %}
                    <span class="badge badge-success">Выполнена!</span>
                {% endif %}
            </div>

            <!-- Прогресс-бар -->
            <div style="margin-top: 12px; height: 6px; background: var(--glass-bg); border-radius: 3px; overflow: hidden;">
                <div style="width: {{ (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0 }}%; height: 100%; background: linear-gradient(90deg, var(--accent-color), var(--success-color)); border-radius: 3px; transition: width 0.5s ease;"></div>
            </div>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">У вас пока нет целей.</p>
            <button onclick="document.getElementById('goal-form-container').classList.remove('hidden')" class="btn btn-primary mt-4">
                Создать первую цель
            </button>
        </div>
    {% endfor %}
</div>

<style>
    .hidden {
        display: none;
    }
</style>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: WRAPPED.HTML
    # ----------------------------------------------------------
    'wrapped.html': '''{% extends "base.html" %}

{% block content %}
<h1>📊 Твой годовой отчёт (Wrapped)</h1>
<p class="text-secondary mb-4">Статистика на основе всех твоих записей</p>

<div class="grid grid-cols-2">
    <!-- Всего записей -->
    <div class="card text-center">
        <h2 style="font-size: 48px; color: var(--accent-color);">{{ total }}</h2>
        <p class="text-secondary">Всего записей</p>
    </div>

    <!-- Среднее настроение -->
    <div class="card text-center">
        <h2 style="font-size: 48px; color: {% if avg_score > 0 %}var(--success-color){% elif avg_score < 0 %}var(--danger-color){% else %}var(--warning-color){% endif %};">
            {{ avg_score }}
        </h2>
        <p class="text-secondary">Среднее настроение</p>
    </div>

    <!-- Лучший месяц -->
    <div class="card text-center">
        <h2 style="font-size: 36px; color: var(--accent-color);">{{ best_month }}</h2>
        <p class="text-secondary">Самый активный месяц</p>
    </div>

    <!-- Максимальный стрик -->
    <div class="card text-center">
        <h2 style="font-size: 48px;">🔥 {{ streak_max }}</h2>
        <p class="text-secondary">Максимальный стрик</p>
    </div>

    <!-- Уровень -->
    <div class="card text-center">
        <h2 style="font-size: 48px;">⭐ {{ level }}</h2>
        <p class="text-secondary">Текущий уровень</p>
    </div>

    <!-- Всего достижений -->
    <div class="card text-center">
        <h2 style="font-size: 48px;">🏆 {{ achievements|length if achievements else 0 }}</h2>
        <p class="text-secondary">Достижений</p>
    </div>
</div>

<!-- Облако слов -->
{% if word_cloud %}
    <div class="card mt-4">
        <h3>☁️ Твои самые частые слова</h3>
        <div class="word-cloud">
            {% for word, count in word_cloud %}
                <span style="font-size: {{ 14 + count * 2 }}px; color: var(--text-primary);">
                    #{{ word }}
                </span>
            {% endfor %}
        </div>
    </div>
{% endif %}

<!-- Экспорт -->
<div class="mt-4">
    <a href="{{ url_for('main.export') }}" class="btn btn-primary">
        📄 Экспортировать все записи
    </a>
    <a href="{{ url_for('main.dashboard') }}" class="btn">
        ← Назад к дневнику
    </a>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: BOOKMARKS.HTML
    # ----------------------------------------------------------
    'bookmarks.html': '''{% extends "base.html" %}

{% block content %}
<h1>🔖 Мои закладки</h1>

<div class="grid">
    {% for bookmark in bookmarks %}
        <div class="card">
            <div class="flex justify-between items-center mb-2">
                <span class="badge">{{ bookmark.entry.category }}</span>
                <span class="text-secondary text-sm">
                    {{ bookmark.entry.date.strftime('%d.%m.%Y %H:%M') }}
                </span>
            </div>

            <p style="line-height: 1.6;">
                {{ bookmark.entry.text_content[:200] }}
                {% if bookmark.entry.text_content|length > 200 %}...{% endif %}
            </p>

            {% if bookmark.entry.image %}
                <img src="{{ url_for('static', filename='uploads/' + bookmark.entry.image) }}" 
                     style="max-width: 100%; border-radius: 12px; margin-top: 12px;" alt="Изображение">
            {% endif %}

            <div class="flex gap-2 mt-3">
                <span class="badge {% if bookmark.entry.mood_label == 'Positive' %}badge-success{% elif bookmark.entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                    {{ bookmark.entry.mood_label }} {{ bookmark.entry.sentiment_score }}
                </span>

                <a href="{{ url_for('main.bookmark_entry', entry_id=bookmark.entry.id) }}" class="btn btn-sm">
                    Убрать из закладок
                </a>

                <span class="text-secondary text-sm" style="margin-left: auto;">
                    Автор: {{ bookmark.entry.author.username }}
                </span>
            </div>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">У вас пока нет закладок.</p>
            <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary mt-4">
                Перейти к записям
            </a>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: EXPORT.HTML
    # ----------------------------------------------------------
    'export.html': '''{% extends "base.html" %}

{% block content %}
<h1>📄 Экспорт данных</h1>
<p class="text-secondary mb-4">Всего записей: {{ entries|length }}</p>

<div class="card mb-4">
    <button onclick="window.print()" class="btn btn-primary">
        🖨️ Распечатать / Сохранить как PDF
    </button>
    <a href="{{ url_for('main.dashboard') }}" class="btn">
        ← Назад
    </a>
</div>

<div class="grid">
    {% for entry in entries %}
        <div class="card">
            <div class="flex justify-between items-center mb-2">
                <span class="badge">{{ entry.category }}</span>
                <span class="text-secondary text-sm">
                    {{ entry.date.strftime('%d.%m.%Y %H:%M') }}
                </span>
            </div>

            <p style="line-height: 1.6;">{{ entry.text_content }}</p>

            <div class="mt-2">
                <span class="badge {% if entry.mood_label == 'Positive' %}badge-success{% elif entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                    Настроение: {{ entry.mood_label }} ({{ entry.sentiment_score }})
                </span>

                {% if entry.tags %}
                    <div class="flex gap-2 mt-2 flex-wrap">
                        {% for tag in entry.tags.split(',') %}
                            <span class="badge">#{{ tag.strip() }}</span>
                        {% endfor %}
                    </div>
                {% endif %}
            </div>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ШАБЛОН: NOTIFICATIONS.HTML
    # ----------------------------------------------------------
    'notifications.html': '''{% extends "base.html" %}

{% block content %}
<h1>🔔 Уведомления</h1>

<div class="grid">
    {% for notification in notifications %}
        <a href="{{ url_for('auth.mark_read', id=notification.id) }}" 
           class="card" 
           style="text-decoration: none; transition: transform 0.2s ease;">

            <div class="flex items-center gap-3">
                <!-- Иконка типа уведомления -->
                <div style="font-size: 24px;">
                    {% if notification.type == 'friend_request' %}
                        👋
                    {% elif notification.type == 'friend_accepted' %}
                        🤝
                    {% elif notification.type == 'streak' %}
                        🔥
                    {% elif notification.type == 'achievement' %}
                        🏆
                    {% elif notification.type == 'level_up' %}
                        ⭐
                    {% else %}
                        🔔
                    {% endif %}
                </div>

                <div style="flex: 1;">
                    <p>{{ notification.message }}</p>
                    <span class="text-secondary text-sm">
                        {{ notification.created_at.strftime('%d.%m.%Y %H:%M') }}
                    </span>
                </div>

                <i class="fas fa-chevron-right text-secondary"></i>
            </div>
        </a>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">У вас нет новых уведомлений.</p>
        </div>
    {% endfor %}
</div>
{% endblock %}''',
}

# Сохранение второй части шаблонов
for template_name, template_content in templates_part2.items():
    template_folder = os.path.dirname(f'app/templates/{template_name}')
    if template_folder:
        os.makedirs(f'app/templates/{template_folder}', exist_ok=True)

    with open(f'app/templates/{template_name}', 'w', encoding='utf-8') as f:
        f.write(template_content)


# ============================================================
# БЛОК 17: ШАБЛОНЫ (ЧАСТЬ 3) — SOCIAL, CHAT, GROUPS, ADMIN
# ============================================================
templates_part3 = {
    # ----------------------------------------------------------
    # SOCIAL/FEED.HTML
    # ----------------------------------------------------------
    'social/feed.html': '''{% extends "base.html" %}

{% block content %}
<h1>🔥 Лента новостей</h1>
<p class="text-secondary mb-4">Записи друзей и публичные записи</p>

<div class="grid">
    {% for entry in entries %}
        <div class="card">
            <!-- Автор записи -->
            <div class="flex items-center gap-3 mb-3">
                <a href="{{ url_for('social.user_profile', user_id=entry.author.id) }}" 
                   style="display: flex; align-items: center; gap: 8px; text-decoration: none;">

                    {% if entry.author.avatar != 'default.png' %}
                        <img src="{{ url_for('static', filename='uploads/' + entry.author.avatar) }}" 
                             class="avatar" alt="Аватар">
                    {% else %}
                        <div class="avatar" style="background: {{ entry.author.accent_color }}; 
                                   display: flex; align-items: center; justify-content: center; 
                                   color: white; font-size: 16px;">
                            {{ entry.author.username[0].upper() }}
                        </div>
                    {% endif %}

                    <div>
                        <b style="color: var(--text-primary);">{{ entry.author.username }}</b>
                        {% if entry.author.is_admin %}👑{% endif %}
                    </div>
                </a>

                <span class="badge">{{ entry.author.get_streak_emoji() }}</span>
                <span class="text-secondary text-sm" style="margin-left: auto;">
                    {{ entry.date.strftime('%d.%m.%Y %H:%M') }}
                </span>
            </div>

            <!-- Содержание записи -->
            <p style="line-height: 1.6; margin-bottom: 12px;">{{ entry.text_content }}</p>

            <!-- Изображение -->
            {% if entry.image %}
                <img src="{{ url_for('static', filename='uploads/' + entry.image) }}" 
                     style="max-width: 100%; border-radius: 16px; margin-bottom: 12px;" alt="Изображение">
            {% endif %}

            <!-- Аудио -->
            {% if entry.audio %}
                <audio controls src="{{ url_for('static', filename='uploads/' + entry.audio) }}" 
                       style="width: 100%; margin-bottom: 12px;"></audio>
            {% endif %}

            <!-- Теги и настроение -->
            <div class="flex gap-2 flex-wrap">
                <span class="badge {% if entry.mood_label == 'Positive' %}badge-success{% elif entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                    {{ entry.mood_label }} {{ entry.sentiment_score }}
                </span>

                <span class="badge">{{ entry.category }}</span>

                {% if entry.tags %}
                    {% for tag in entry.tags.split(',') %}
                        <span class="badge">#{{ tag.strip() }}</span>
                    {% endfor %}
                {% endif %}

                <a href="{{ url_for('main.bookmark_entry', entry_id=entry.id) }}" 
                   class="btn btn-sm" style="margin-left: auto;" title="В закладки">
                    🔖
                </a>
            </div>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">Лента пуста.</p>
            <p class="text-secondary">Добавьте друзей или создайте публичную запись!</p>
            <a href="{{ url_for('social.search') }}" class="btn btn-primary mt-4">
                🔍 Найти друзей
            </a>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # SOCIAL/FRIENDS.HTML
    # ----------------------------------------------------------
    'social/friends.html': '''{% extends "base.html" %}

{% block content %}
<h1>👥 Мои друзья</h1>

<div class="flex gap-3 mb-4">
    <a href="{{ url_for('social.search') }}" class="btn btn-primary">
        🔍 Найти друзей
    </a>
    <a href="{{ url_for('social.requests') }}" class="btn">
        📬 Заявки в друзья
    </a>
</div>

<div class="grid grid-cols-3">
    {% for friend in friends %}
        <a href="{{ url_for('social.user_profile', user_id=friend.id) }}" 
           class="card text-center" style="text-decoration: none;">

            <!-- Аватар друга -->
            {% if friend.avatar != 'default.png' %}
                <img src="{{ url_for('static', filename='uploads/' + friend.avatar) }}" 
                     style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; 
                            margin: 0 auto 12px; border: 2px solid {{ friend.accent_color }};" alt="Аватар">
            {% else %}
                <div style="width: 60px; height: 60px; background: {{ friend.accent_color }}; 
                           border-radius: 50%; display: flex; align-items: center; justify-content: center; 
                           color: white; font-size: 24px; margin: 0 auto 12px;">
                    {{ friend.username[0].upper() }}
                </div>
            {% endif %}

            <h3 style="color: var(--text-primary);">
                {{ friend.username }}
                {% if friend.is_admin %}👑{% endif %}
            </h3>

            {% if friend.is_online %}
                <span class="online-dot"></span>
                <span class="text-sm text-secondary">Онлайн</span>
            {% else %}
                <span class="text-sm text-secondary">⚫ Не в сети</span>
            {% endif %}
        </a>
    {% else %}
        <div class="card text-center" style="grid-column: span 3;">
            <p class="text-secondary">У вас пока нет друзей.</p>
            <a href="{{ url_for('social.search') }}" class="btn btn-primary mt-4">
                Найти друзей
            </a>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # SOCIAL/SEARCH.HTML
    # ----------------------------------------------------------
    'social/search.html': '''{% extends "base.html" %}

{% block content %}
<h1>🔍 Поиск пользователей</h1>

<form method="GET" class="card mb-4">
    <div class="flex gap-2">
        <input type="text" name="q" class="input" value="{{ query }}" 
               placeholder="Введите имя пользователя..." style="flex: 1;">
        <button type="submit" class="btn btn-primary">
            <i class="fas fa-search"></i> Найти
        </button>
    </div>
</form>

{% if query %}
    <h2 class="mb-4">Результаты поиска: "{{ query }}"</h2>
{% endif %}

<div class="grid">
    {% for user in users %}
        <div class="card">
            <div class="flex items-center justify-between">
                <!-- Аватар и имя -->
                <div class="flex items-center gap-3">
                    {% if user.avatar != 'default.png' %}
                        <img src="{{ url_for('static', filename='uploads/' + user.avatar) }}" 
                             class="avatar" alt="Аватар">
                    {% else %}
                        <div class="avatar" style="background: {{ user.accent_color }}; 
                                   display: flex; align-items: center; justify-content: center; 
                                   color: white; font-size: 16px;">
                            {{ user.username[0].upper() }}
                        </div>
                    {% endif %}

                    <div>
                        <h3>
                            {{ user.username }}
                            {% if user.is_admin %}👑{% endif %}
                        </h3>
                        <span class="text-sm text-secondary">
                            {{ user.get_streak_emoji() }} {{ user.streak_days }} дней
                        </span>
                        {% if user.is_online %}
                            <span class="online-dot"></span>
                            <span class="text-sm text-secondary">Онлайн</span>
                        {% endif %}
                    </div>
                </div>

                <!-- Кнопка добавления в друзья -->
                <a href="{{ url_for('social.send_request', user_id=user.id) }}" 
                   class="btn btn-primary btn-sm">
                    + Добавить в друзья
                </a>
            </div>
        </div>
    {% else %}
        {% if query %}
            <div class="card text-center">
                <p class="text-secondary">Пользователи не найдены.</p>
            </div>
        {% endif %}
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # SOCIAL/REQUESTS.HTML
    # ----------------------------------------------------------
    'social/requests.html': '''{% extends "base.html" %}

{% block content %}
<h1>📬 Заявки в друзья</h1>

<div class="grid">
    {% for request in requests %}
        <div class="card">
            <div class="flex items-center justify-between">
                <!-- Информация об отправителе -->
                <div class="flex items-center gap-3">
                    {% if request.from_user.avatar != 'default.png' %}
                        <img src="{{ url_for('static', filename='uploads/' + request.from_user.avatar) }}" 
                             class="avatar" alt="Аватар">
                    {% else %}
                        <div class="avatar" style="background: {{ request.from_user.accent_color }}; 
                                   display: flex; align-items: center; justify-content: center; 
                                   color: white; font-size: 16px;">
                            {{ request.from_user.username[0].upper() }}
                        </div>
                    {% endif %}

                    <div>
                        <h3>
                            {{ request.from_user.username }}
                            {% if request.from_user.is_admin %}👑{% endif %}
                        </h3>
                        <span class="text-sm text-secondary">
                            {{ request.created_at.strftime('%d.%m.%Y %H:%M') }}
                        </span>
                    </div>
                </div>

                <!-- Кнопки принятия/отклонения -->
                <div class="flex gap-2">
                    <a href="{{ url_for('social.accept_request', req_id=request.id) }}" 
                       class="btn btn-sm btn-primary">
                        ✓ Принять
                    </a>
                    <a href="{{ url_for('social.reject_request', req_id=request.id) }}" 
                       class="btn btn-sm">
                        ✗ Отклонить
                    </a>
                </div>
            </div>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">Нет входящих заявок в друзья.</p>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # SOCIAL/PROFILE.HTML
    # ----------------------------------------------------------
    'social/profile.html': '''{% extends "base.html" %}

{% block content %}
<div class="card mb-4">
    <!-- Баннер -->
    {% if user.banner %}
        <div class="banner" style="background-image: url('{{ url_for('static', filename='banners/' + user.banner) }}');"></div>
    {% endif %}

    <!-- Аватар и основная информация -->
    <div class="flex items-center gap-4">
        {% if user.avatar != 'default.png' %}
            <img src="{{ url_for('static', filename='uploads/' + user.avatar) }}" 
                 class="avatar-large" alt="Аватар">
        {% else %}
            <div class="avatar-large" style="background: {{ user.accent_color }}; 
                       display: flex; align-items: center; justify-content: center; 
                       color: white; font-size: 36px;">
                {{ user.username[0].upper() }}
            </div>
        {% endif %}

        <div>
            <h1>
                {{ user.username }}
                {% if user.is_admin %}👑{% endif %}
            </h1>
            <p>{{ user.status_emoji }} {{ user.status_text }}</p>
            <p class="text-secondary text-sm mt-1">{{ user.bio }}</p>

            <!-- Статус онлайн -->
            {% if user.is_online %}
                <span class="online-dot"></span>
                <span class="text-sm">Онлайн</span>
            {% else %}
                <span class="text-sm text-secondary">
                    Был(а): {{ user.last_seen.strftime('%d.%m.%Y %H:%M') if user.last_seen else 'Давно' }}
                </span>
            {% endif %}
        </div>

        <!-- Кнопки действий -->
        <div style="margin-left: auto;">
            {% if not is_friend and user.id != current_user.id %}
                {% if pending_request %}
                    <span class="badge">Заявка отправлена</span>
                {% else %}
                    <a href="{{ url_for('social.send_request', user_id=user.id) }}" 
                       class="btn btn-primary btn-sm">
                        + Добавить в друзья
                    </a>
                {% endif %}
            {% elif is_friend %}
                <a href="{{ url_for('chat.chat_with', friend_id=user.id) }}" 
                   class="btn btn-primary btn-sm">
                    💬 Чат
                </a>
            {% endif %}
        </div>
    </div>
</div>

<!-- Публичные записи пользователя -->
<h2>📝 Публичные записи</h2>
<div class="grid">
    {% for entry in entries %}
        <div class="card">
            <div class="flex justify-between mb-2">
                <span class="badge">{{ entry.category }}</span>
                <span class="text-secondary text-sm">
                    {{ entry.date.strftime('%d.%m.%Y %H:%M') }}
                </span>
            </div>

            <p style="line-height: 1.6;">{{ entry.text_content }}</p>

            {% if entry.image %}
                <img src="{{ url_for('static', filename='uploads/' + entry.image) }}" 
                     style="max-width: 100%; border-radius: 12px; margin-top: 12px;" alt="Изображение">
            {% endif %}

            <div class="mt-2">
                <span class="badge {% if entry.mood_label == 'Positive' %}badge-success{% elif entry.mood_label == 'Negative' %}badge-danger{% endif %}">
                    {{ entry.mood_label }} {{ entry.sentiment_score }}
                </span>

                <a href="{{ url_for('main.bookmark_entry', entry_id=entry.id) }}" 
                   class="btn btn-sm" title="В закладки">
                    🔖
                </a>
            </div>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">У этого пользователя нет публичных записей.</p>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # CHAT/INDEX.HTML
    # ----------------------------------------------------------
    'chat/index.html': '''{% extends "base.html" %}

{% block content %}
<h1>💬 Чаты</h1>
<p class="text-secondary mb-4">Выберите друга для начала разговора</p>

<div class="grid">
    {% for friend in friends %}
        <a href="{{ url_for('chat.chat_with', friend_id=friend.id) }}" 
           class="card flex items-center gap-3" style="text-decoration: none; transition: transform 0.2s ease;">

            <!-- Аватар друга -->
            {% if friend.avatar != 'default.png' %}
                <img src="{{ url_for('static', filename='uploads/' + friend.avatar) }}" 
                     class="avatar" alt="Аватар">
            {% else %}
                <div class="avatar" style="background: {{ friend.accent_color }}; 
                           display: flex; align-items: center; justify-content: center; color: white;">
                    {{ friend.username[0].upper() }}
                </div>
            {% endif %}

            <div>
                <h3 style="color: var(--text-primary);">
                    {{ friend.username }}
                    {% if friend.is_admin %}👑{% endif %}
                </h3>

                <!-- Статус онлайн -->
                {% if friend.is_online %}
                    <span class="online-dot"></span>
                    <span class="text-sm">Онлайн</span>
                {% else %}
                    <span class="text-sm text-secondary">⚫ Не в сети</span>
                {% endif %}
            </div>

            <!-- Индикатор непрочитанных сообщений -->
            {% if friend.get_unread_messages_count() > 0 %}
                <span class="badge badge-danger" style="margin-left: auto;">
                    {{ friend.get_unread_messages_count() }}
                </span>
            {% endif %}
        </a>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">У вас пока нет друзей для чата.</p>
            <a href="{{ url_for('social.search') }}" class="btn btn-primary mt-4">
                🔍 Найти друзей
            </a>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # CHAT/CHAT.HTML
    # ----------------------------------------------------------
    'chat/chat.html': '''{% extends "base.html" %}

{% block content %}
<div class="card chat-bg-{{ current_user.chat_bg }}" style="height: 70vh; display: flex; flex-direction: column;">

    <!-- Заголовок чата -->
    <div class="flex items-center gap-3 mb-4">
        <a href="{{ url_for('chat.index') }}" class="btn btn-sm" title="Назад к списку чатов">
            ← Назад
        </a>

        <!-- Аватар друга -->
        {% if friend.avatar != 'default.png' %}
            <img src="{{ url_for('static', filename='uploads/' + friend.avatar) }}" 
                 class="avatar" alt="Аватар">
        {% else %}
            <div class="avatar" style="background: {{ friend.accent_color }}; 
                       display: flex; align-items: center; justify-content: center; color: white;">
                {{ friend.username[0].upper() }}
            </div>
        {% endif %}

        <div>
            <h2>
                {{ friend.username }}
                {% if friend.is_admin %}👑{% endif %}
            </h2>

            <!-- Статус друга -->
            {% if friend.is_online %}
                <span class="online-dot"></span>
                <span class="text-sm">Онлайн</span>
            {% else %}
                <span class="text-sm text-secondary">⚫ Не в сети</span>
            {% endif %}
        </div>
    </div>

    <!-- Область сообщений -->
    <div id="messages-container" style="flex: 1; overflow-y: auto; padding: 12px;">
        {% for message in messages %}
            <div style="text-align: {{ 'right' if message.sender_id == current_user.id else 'left' }}; margin-bottom: 8px;">
                <span style="background: {{ 'var(--accent-color)' if message.sender_id == current_user.id else 'var(--glass-bg)' }}; 
                           color: {{ 'white' if message.sender_id == current_user.id else 'var(--text-primary)' }}; 
                           padding: 10px 18px; 
                           border-radius: 22px; 
                           display: inline-block; 
                           max-width: 70%;
                           line-height: 1.5;
                           word-wrap: break-word;">
                    {{ message.text }}
                    <br>
                    <small style="opacity: 0.6; font-size: 11px;">
                        {{ message.created_at.strftime('%H:%M') }}
                    </small>
                </span>
            </div>
        {% endfor %}
    </div>

    <!-- Индикатор "печатает..." -->
    <div id="typing-indicator" style="padding: 0 12px; font-size: 13px; color: var(--text-secondary); display: none;">
        <em>печатает...</em>
    </div>

    <!-- Форма отправки сообщения -->
    <form id="chat-message-form" class="flex gap-2 mt-3">
        <input type="text" id="chat-message-input" class="input" 
               placeholder="Напишите сообщение..." autocomplete="off">
        <button type="submit" class="btn btn-primary">
            <i class="fas fa-paper-plane"></i>
        </button>
    </form>
</div>

<script>
    // Инициализация Socket.IO
    const socket = io();
    const currentFriendId = {{ friend.id }};
    let typingTimeout;

    // Подключаемся к комнате
    socket.emit('join');

    // Получение нового сообщения
    socket.on('new_message', function(data) {
        if (data.sender_id === currentFriendId || data.sender_id === {{ current_user.id }}) {
            // Создаем элемент сообщения
            const messageDiv = document.createElement('div');
            messageDiv.style.textAlign = data.sender_id === {{ current_user.id }} ? 'right' : 'left';
            messageDiv.style.marginBottom = '8px';

            const isOwnMessage = data.sender_id === {{ current_user.id }};
            const backgroundColor = isOwnMessage ? 'var(--accent-color)' : 'var(--glass-bg)';
            const textColor = isOwnMessage ? 'white' : 'var(--text-primary)';

            messageDiv.innerHTML = `
                <span style="background: ${backgroundColor}; 
                           color: ${textColor}; 
                           padding: 10px 18px; 
                           border-radius: 22px; 
                           display: inline-block; 
                           max-width: 70%;
                           line-height: 1.5;
                           word-wrap: break-word;">
                    ${data.text}
                    <br>
                    <small style="opacity: 0.6; font-size: 11px;">
                        ${data.created_at}
                    </small>
                </span>
            `;

            // Добавляем сообщение в контейнер
            const messagesContainer = document.getElementById('messages-container');
            messagesContainer.appendChild(messageDiv);

            // Прокручиваем вниз
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Скрываем индикатор печати
            document.getElementById('typing-indicator').style.display = 'none';
        }
    });

    // Индикатор печати
    socket.on('user_typing', function(data) {
        if (data.user_id === currentFriendId) {
            const typingIndicator = document.getElementById('typing-indicator');
            typingIndicator.style.display = 'block';

            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(function() {
                typingIndicator.style.display = 'none';
            }, 2000);
        }
    });

    // Отправка уведомления о печати
    document.getElementById('chat-message-input').addEventListener('input', function() {
        socket.emit('typing', { friend_id: currentFriendId });
    });

    // Отправка сообщения
    document.getElementById('chat-message-form').addEventListener('submit', function(event) {
        event.preventDefault();

        const messageInput = document.getElementById('chat-message-input');
        const messageText = messageInput.value.trim();

        if (!messageText) return;

        // Отправляем сообщение через WebSocket
        socket.emit('send_message', {
            friend_id: currentFriendId,
            text: messageText
        });

        // Очищаем поле ввода
        messageInput.value = '';
        messageInput.focus();
    });
</script>
{% endblock %}''',

    # ----------------------------------------------------------
    # GROUPS/INDEX.HTML
    # ----------------------------------------------------------
    'groups/index.html': '''{% extends "base.html" %}

{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1>👥 Группы</h1>
    <a href="{{ url_for('groups.create') }}" class="btn btn-primary">
        + Создать группу
    </a>
</div>

<!-- Мои группы -->
<h2 class="mb-4">Мои группы</h2>
<div class="grid">
    {% for group in my_groups %}
        <a href="{{ url_for('groups.view', group_id=group.id) }}" 
           class="card" style="text-decoration: none;">
            <h3>{{ group.name }}</h3>
            <p class="text-secondary">{{ group.description or 'Нет описания' }}</p>
            <span class="text-sm text-secondary">
                Участников: {{ group.members|length }}
            </span>
        </a>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">Вы не состоите ни в одной группе.</p>
        </div>
    {% endfor %}
</div>

<!-- Все группы -->
<h2 class="mb-4 mt-6">Все группы</h2>
<div class="grid">
    {% for group in all_groups %}
        <div class="card">
            <h3>{{ group.name }}</h3>
            <p class="text-secondary">{{ group.description or 'Нет описания' }}</p>
            <div class="flex justify-between items-center mt-3">
                <span class="text-sm text-secondary">
                    Участников: {{ group.members|length }}
                </span>
                <a href="{{ url_for('groups.view', group_id=group.id) }}" class="btn btn-sm btn-primary">
                    Открыть
                </a>
            </div>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # GROUPS/CREATE.HTML
    # ----------------------------------------------------------
    'groups/create.html': '''{% extends "base.html" %}

{% block content %}
<div class="max-w-md mx-auto">
    <div class="card">
        <h2>Создать новую группу</h2>

        <form method="POST">
            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">
                    Название группы
                </label>
                <input type="text" name="name" class="input" 
                       placeholder="Введите название группы" required>
            </div>

            <div class="mb-4">
                <label class="text-secondary text-sm mb-2" style="display: block;">
                    Описание группы
                </label>
                <textarea name="description" class="input" 
                          placeholder="Расскажите, о чём эта группа"></textarea>
            </div>

            <button type="submit" class="btn btn-primary">
                Создать группу
            </button>
        </form>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # GROUPS/VIEW.HTML
    # ----------------------------------------------------------
    'groups/view.html': '''{% extends "base.html" %}

{% block content %}
<div class="card mb-4">
    <h1>{{ group.name }}</h1>
    <p class="text-secondary">{{ group.description or 'Нет описания' }}</p>
    <p class="text-sm text-secondary mt-2">
        Участников: {{ group.members|length }}
    </p>

    {% if not is_member %}
        <a href="{{ url_for('groups.join', group_id=group.id) }}" class="btn btn-primary mt-4">
            Вступить в группу
        </a>
    {% else %}
        <a href="{{ url_for('groups.add_entry', group_id=group.id) }}" class="btn btn-primary mt-4">
            + Новая запись
        </a>
    {% endif %}
</div>

<h2>Записи группы</h2>
<div class="grid">
    {% for entry in entries %}
        <div class="card">
            <div class="flex items-center gap-3 mb-3">
                <b>{{ entry.author.username }}</b>
                <span class="text-secondary text-sm">
                    {{ entry.date.strftime('%d.%m.%Y %H:%M') }}
                </span>
            </div>
            <p style="line-height: 1.6;">{{ entry.text_content }}</p>
        </div>
    {% else %}
        <div class="card text-center">
            <p class="text-secondary">В группе пока нет записей.</p>
        </div>
    {% endfor %}
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # GROUPS/ADD_ENTRY.HTML
    # ----------------------------------------------------------
    'groups/add_entry.html': '''{% extends "base.html" %}

{% block content %}
<div class="max-w-md mx-auto">
    <div class="card">
        <h2>Новая запись в группу</h2>

        <form method="POST">
            <div class="mb-4">
                <textarea name="content" class="input" rows="6" 
                          placeholder="Напишите что-нибудь..." required></textarea>
            </div>

            <button type="submit" class="btn btn-primary">
                Опубликовать
            </button>
        </form>
    </div>
</div>
{% endblock %}''',

    # ----------------------------------------------------------
    # ADMIN/INDEX.HTML
    # ----------------------------------------------------------
    'admin/index.html': '''{% extends "base.html" %}

{% block content %}
<h1>👑 Админ-панель</h1>

<!-- Статистика -->
<div class="grid grid-cols-2 mb-4">
    <div class="card text-center">
        <h2 style="font-size: 48px; color: var(--accent-color);">{{ total_users }}</h2>
        <p class="text-secondary">Всего пользователей</p>
    </div>
    <div class="card text-center">
        <h2 style="font-size: 48px; color: var(--success-color);">{{ total_entries }}</h2>
        <p class="text-secondary">Всего записей</p>
    </div>
</div>

<!-- Таблица пользователей -->
<div class="card" style="padding: 0; overflow: hidden;">
    <table class="table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Имя</th>
                <th>Email</th>
                <th>Статус</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for user in users %}
                <tr>
                    <td>{{ user.id }}</td>
                    <td>
                        {{ user.username }}
                        {% if user.is_admin %}👑{% endif %}
                        {% if user.is_online %}<span class="online-dot"></span>{% endif %}
                    </td>
                    <td class="text-secondary text-sm">{{ user.email }}</td>
                    <td>
                        {% if user.is_blocked %}
                            <span class="badge badge-danger">Заблокирован</span>
                        {% else %}
                            <span class="badge badge-success">Активен</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="flex gap-2">
                            {% if not user.is_admin %}
                                <a href="{{ url_for('admin.make_admin', user_id=user.id) }}" 
                                   class="btn btn-sm" title="Сделать админом">
                                    👑
                                </a>
                            {% endif %}
                            <a href="{{ url_for('admin.block_user', user_id=user.id) }}" 
                               class="btn btn-sm" title="Заблокировать/Разблокировать">
                                {{ '🔓' if user.is_blocked else '🔒' }}
                            </a>
                            <a href="{{ url_for('admin.delete_user', user_id=user.id) }}" 
                               class="btn btn-sm" title="Удалить"
                               onclick="return confirm('Вы уверены, что хотите удалить пользователя {{ user.username }}? Это действие необратимо.')">
                                🗑️
                            </a>
                        </div>
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}''',
}

# Сохранение третьей части шаблонов
for template_name, template_content in templates_part3.items():
    template_folder = os.path.dirname(f'app/templates/{template_name}')
    if template_folder:
        os.makedirs(f'app/templates/{template_folder}', exist_ok=True)

    with open(f'app/templates/{template_name}', 'w', encoding='utf-8') as f:
        f.write(template_content)



import os as os_fix

# Исправление 1: base.html (bookmarks -> bookmarks_list)
base_html_fix_path = 'app/templates/base.html'
if os_fix.path.exists(base_html_fix_path):
    with open(base_html_fix_path, 'r', encoding='utf-8') as fix_file:
        fixed_content = fix_file.read()

    fixed_content = fixed_content.replace("url_for('main.bookmarks')", "url_for('main.bookmarks_list')")

    with open(base_html_fix_path, 'w', encoding='utf-8') as fix_file:
        fix_file.write(fixed_content)


# Исправление 2: dashboard.html (claim_reward -> claim_daily_reward)
dashboard_html_fix_path = 'app/templates/dashboard.html'
if os_fix.path.exists(dashboard_html_fix_path):
    with open(dashboard_html_fix_path, 'r', encoding='utf-8') as fix_file:
        fixed_content = fix_file.read()

    fixed_content = fixed_content.replace("url_for('main.claim_reward')", "url_for('main.claim_daily_reward')")

    with open(dashboard_html_fix_path, 'w', encoding='utf-8') as fix_file:
        fix_file.write(fixed_content)


# Импортируем приложение
from app import create_app, db, socketio

# Создаем приложение
app = create_app()

# Создаем все таблицы базы данных
with app.app_context():
    db.create_all()



# Функция для открытия браузера
def open_browser():
    webbrowser.open('http://127.0.0.1:5000')


# Запускаем браузер через 1.5 секунды после старта сервера
threading.Timer(1.5, open_browser).start()

# Вывод информации о запуске
print("   🥃 MOODMAP ULTIMATE ЗАПУЩЕН!")
print("   🌐 http://127.0.0.1:5000")
print("   📱 http://[ваш-ip]:5000 (для телефона)")

# Запуск сервера с Socket.IO
if __name__ == '__main__':
    socketio.run(
        app,
        debug=False,
        host='0.0.0.0',  # Доступен для всех устройств в сети
        port=5000,
        allow_unsafe_werkzeug=True
    )
