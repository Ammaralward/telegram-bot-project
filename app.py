from flask import Flask, render_template, request, redirect, url_for, session, flash
from telebot.credentials import admin_password, bot_token
from models import SessionLocal, User, Notification, FilteredMessage
from telegram import Bot, Update
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret-key'
telegram_bot = Bot(token=bot_token)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_notification(user_id, type_, message):
    db = next(get_db())
    notif = Notification(user_id=user_id, type=type_, message=message, created_at=datetime.utcnow())
    db.add(notif)
    db.commit()
    db.close()

def add_filtered_message(user_id, content):
    db = SessionLocal()
    try:
        new_msg = FilteredMessage(user_id=user_id, content=content, timestamp=datetime.utcnow())
        db.add(new_msg)
        db.commit()
    finally:
        db.close()

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, telegram_bot)
    message = update.message
    if message and message.text:
        user_telegram_id = message.from_user.id
        text = message.text
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
        db.close()
        if user:
            if user.keywords and any(kw in text for kw in user.keywords):
                add_filtered_message(user.id, text)
                telegram_bot.send_message(chat_id=user_telegram_id, text="تم تسجيل رسالتك المفلترة.")
    return "ok"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == admin_password:
            session['logged_in'] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="كلمة مرور خاطئة")
    return render_template("login.html")

@app.route("/")
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    search = request.args.get("search", "")
    if search:
        users = db.query(User).filter(User.username.contains(search)).all()
    else:
        users = db.query(User).all()
    return render_template("index.html", users=users)

@app.route("/user/<int:user_id>", methods=["GET", "POST"])
def user_detail(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user:
        return "المستخدم غير موجود"
    if request.method == "POST":
        keywords = request.form.get("keywords", "")
        parts = []
        for sep in [",", "،"]:
            if parts:
                tmp = []
                for p in parts:
                    tmp.extend(p.split(sep))
                parts = [x.strip() for x in tmp if x.strip()]
            else:
                parts = [x.strip() for x in keywords.split(sep) if x.strip()]
        user.keywords = user.keywords + parts if user.keywords else parts
        db.commit()
    return render_template("user_detail.html", user=user)

@app.route("/delete_keyword/<int:user_id>/<int:kw_index>")
def delete_keyword(user_id, kw_index):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if user and 0 <= kw_index < len(user.keywords):
        new_keywords = user.keywords[:kw_index] + user.keywords[kw_index+1:]
        user.keywords = new_keywords
        db.commit()
    return redirect(url_for('user_detail', user_id=user_id))

@app.route("/accept/<int:user_id>")
def accept_user(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if user:
        user.active = True
        db.commit()
        add_notification(user.id, "قبول", "تم قبول المستخدم.")
        try:
            telegram_bot.send_message(chat_id=user.telegram_id, text="تم قبول طلبك، يمكنك الآن استخدام البوت.")
        except:
            pass
    return redirect(url_for("dashboard"))

@app.route("/reject/<int:user_id>")
def reject_user(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if user:
        user.active = False
        db.commit()
        add_notification(user.id, "رفض", "تم رفض المستخدم.")
        try:
            telegram_bot.send_message(chat_id=user.telegram_id, text="تم رفض طلبك، لا يمكنك استخدام البوت.")
        except:
            pass
    return redirect(url_for("dashboard"))

@app.route("/toggle_active/<int:user_id>", methods=["POST"])
def toggle_active(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if user:
        user.active = not user.active
        db.commit()
    return redirect(url_for("dashboard"))

@app.route("/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)
    if user:
        db.delete(user)
        db.commit()
    return redirect(url_for("dashboard"))

@app.route("/notifications")
def notifications():
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    query = request.args.get("q", "")
    if query:
        notifs = db.query(Notification).filter(Notification.message.contains(query)).order_by(Notification.created_at.desc()).all()
    else:
        notifs = db.query(Notification).order_by(Notification.created_at.desc()).all()
    return render_template("notifications.html", notifications=notifs)

@app.route("/user_messages/<int:user_id>")
def user_messages(user_id):
    if not session.get('logged_in'):
        return redirect(url_for("login"))
    db = next(get_db())
    user = db.query(User).get(user_id)

    # استعلام شامل كافة الحقول (تأكد أن موديل FilteredMessage يحتوي على الحقول المطلوبة)
    messages = db.query(FilteredMessage).filter(FilteredMessage.user_id == user_id).order_by(FilteredMessage.timestamp.asc()).all()

    if not messages:
        flash("لا توجد رسائل مفلترة لهذا المستخدم.", "info")
    
    db.close()
    return render_template("user_messages.html", messages=messages, user=user)

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
