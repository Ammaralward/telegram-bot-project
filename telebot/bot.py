from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from telebot.credentials import bot_token
from models import SessionLocal, User, FilteredMessage
from datetime import datetime

(
    MAIN_MENU,
    KEYWORDS_MENU,
    TYPING_KEYWORDS,
    DELETE_MENU,
    DELETE_ONE_KEYWORD,
) = range(5)

ADMIN_USERNAME = "AmmarAlward"  # معرف مدير الدعم
YOUR_ADMIN_TELEGRAM_ID = 1416341802  # قم بتعديلها بمعرف الأدمن الخاص بك

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username or ""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username, active=False, keywords=[])
        db.add(user)
        db.commit()
        admin_chat_id = YOUR_ADMIN_TELEGRAM_ID
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"مستخدم جديد بانتظار الموافقة: @{username} (ID: {telegram_id})"
        )
        await update.message.reply_text("شكراً لتسجيلك! يرجى الانتظار حتى يتم قبول طلبك من المدير.")
        db.close()
        return ConversationHandler.END
    if not user.active:
        await update.message.reply_text("طلبك قيد المراجعة، نرجو الانتظار حتى يتم قبوله من المدير.")
        db.close()
        return ConversationHandler.END
    main_menu_keyboard = [
        ["keywords", "help"],
    ]
    reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "مرحباً! اختر أمر:\n- keywords لإدارة كلمات الفلترة\n- help للمساعدة",
        reply_markup=reply_markup
    )
    db.close()
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text == "keywords":
        keywords_menu_keyboard = [
            ["new keywords", "delete keywords"],
            ["show keywords"],
            ["back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "قائمة كلمات الفلترة:\n- new keywords لإضافة كلمات\n- delete keywords لحذف كلمات\n- show keywords لعرض الكلمات\n- back للعودة",
            reply_markup=reply_markup
        )
        return KEYWORDS_MENU
    elif text == "help":
        await update.message.reply_text(
            f"للدعم والمساعدة تواصل مع مدير البوت: @{ADMIN_USERNAME}",
            reply_markup=ReplyKeyboardMarkup([["back"]], resize_keyboard=True, one_time_keyboard=True)
        )
        return MAIN_MENU
    else:
        await update.message.reply_text("الرجاء اختيار أمر صحيح من القائمة.")
        return MAIN_MENU

async def keywords_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text == "new keywords":
        await update.message.reply_text("أدخل كلمات الفلترة مفصولة بفواصل (, أو ،):", reply_markup=ReplyKeyboardRemove())
        return TYPING_KEYWORDS
    elif text == "delete keywords":
        delete_menu_keyboard = [
            ["delete all keywords", "delete a keyword"],
            ["back"]
        ]
        reply_markup = ReplyKeyboardMarkup(delete_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "اختر طريقة الحذف:\n- delete all keywords لحذف كل الكلمات\n- delete a keyword لحذف كلمة معينة\n- back للعودة",
            reply_markup=reply_markup
        )
        return DELETE_MENU
    elif text == "show keywords":
        telegram_id = update.effective_user.id
        db = SessionLocal()
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            if user.keywords:
                numbered_keywords = "\n".join([f"{i+1}. {kw}" for i, kw in enumerate(user.keywords)])
                await update.message.reply_text("كلمات الفلترة الخاصة بك:\n" + numbered_keywords)
            else:
                await update.message.reply_text("لا توجد كلمات فلترة لديك.")
        db.close()
        keywords_menu_keyboard = [
            ["new keywords", "delete keywords"],
            ["show keywords"],
            ["back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("اختر خياراً:", reply_markup=reply_markup)
        return KEYWORDS_MENU
    elif text == "back":
        main_menu_keyboard = [
            ["keywords", "help"],
        ]
        reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("تم الرجوع للقائمة الرئيسية.", reply_markup=reply_markup)
        return MAIN_MENU
    else:
        await update.message.reply_text("اختر خياراً صحيحاً من القائمة.")
        return KEYWORDS_MENU

async def delete_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    telegram_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if text == "delete all keywords":
        if user:
            user.keywords = []
            db.commit()
            await update.message.reply_text("تم حذف جميع كلمات الفلترة.")
        db.close()
        keywords_menu_keyboard = [
            ["new keywords", "delete keywords"],
            ["show keywords"],
            ["back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("اختر خياراً:", reply_markup=reply_markup)
        return KEYWORDS_MENU
    elif text == "delete a keyword":
        if user and user.keywords:
            numbered_keywords = "\n".join([f"{i+1}. {kw}" for i, kw in enumerate(user.keywords)])
            await update.message.reply_text(
                f"كلماتك المفتاحية:\n{numbered_keywords}\n\nأدخل رقم الكلمة التي تريد حذفها:",
                reply_markup=ReplyKeyboardRemove()
            )
            db.close()
            return DELETE_ONE_KEYWORD
        else:
            await update.message.reply_text("لا توجد كلمات مفتاحية للحذف.")
            db.close()
            keywords_menu_keyboard = [
                ["new keywords", "delete keywords"],
                ["show keywords"],
                ["back"]
            ]
            reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text("اختر خياراً:", reply_markup=reply_markup)
            return KEYWORDS_MENU
    elif text == "back":
        keywords_menu_keyboard = [
            ["new keywords", "delete keywords"],
            ["show keywords"],
            ["back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("تم الرجوع للقائمة السابقة.", reply_markup=reply_markup)
        db.close()
        return KEYWORDS_MENU
    else:
        await update.message.reply_text("اختر خياراً صحيحاً من القائمة.")
        db.close()
        return DELETE_MENU

async def delete_one_keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    text = update.message.text.strip()
    if user and user.keywords:
        try:
            idx = int(text) - 1
            if 0 <= idx < len(user.keywords):
                removed_keyword = user.keywords[idx]
                new_keywords = user.keywords[:idx] + user.keywords[idx+1:]
                user.keywords = new_keywords
                db.commit()
                await update.message.reply_text(f"تم حذف الكلمة: {removed_keyword}")
            else:
                await update.message.reply_text("رقم غير صالح، يرجى المحاولة مجددًا.")
                db.close()
                return DELETE_ONE_KEYWORD
        except ValueError:
            await update.message.reply_text("يرجى إدخال رقم صحيح.")
            db.close()
            return DELETE_ONE_KEYWORD
    else:
        await update.message.reply_text("لا توجد كلمات مفتاحية للحذف.")
    db.close()
    keywords_menu_keyboard = [
        ["new_keywords", "delete keywords"],
        ["show keywords"],
        ["back"]
    ]
    reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("اختر خياراً:", reply_markup=reply_markup)
    return KEYWORDS_MENU

async def receive_new_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = []
    for sep in [",", "،"]:
        if parts:
            tmp = []
            for p in parts:
                tmp.extend(p.split(sep))
            parts = [x.strip() for x in tmp if x.strip()]
        else:
            parts = [x.strip() for x in text.split(sep) if x.strip()]
    telegram_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        existing = user.keywords or []
        user.keywords = existing + parts
        db.commit()
        await update.message.reply_text("تم تحديث كلمات الفلترة:\n" + "\n".join(user.keywords))
    db.close()
    keywords_menu_keyboard = [
        ["new keywords", "delete keywords"],
        ["show keywords"],
        ["back"]
    ]
    reply_markup = ReplyKeyboardMarkup(keywords_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("اختر خياراً:", reply_markup=reply_markup)
    return KEYWORDS_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def monitor_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return
    message_text = update.message.text
    message_text_lower = message_text.lower()
    db = SessionLocal()
    users = db.query(User).filter(User.active == True).all()
    for user in users:
        if user.keywords and any(keyword.lower() in message_text_lower for keyword in user.keywords):
            user_obj = update.message.from_user
            full_name = user_obj.full_name or "Unknown"
            username = f" (@{user_obj.username})" if user_obj.username else ""
            sender_name = f"{full_name}{username}"
            message_date = update.message.date.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            chat_id = update.message.chat_id
            message_id = update.message.message_id
            group_link = f"https://t.me/c/{str(chat_id)[4:]}" if str(chat_id).startswith("-100") else None
            message_link = f"{group_link}/{message_id}" if group_link else None

            filtered_message = FilteredMessage(
                user_id=user.id,
                content=message_text,
                timestamp=datetime.utcnow(),
                sender_name=sender_name,
                group_link=group_link,
                message_link=message_link,
            )
            db.add(filtered_message)
            db.commit()

            reply_text = (
                f"رسالة مفلترة:\n{message_text}\n\n"
                f"المستخدم: {sender_name}\n"
                f"التاريخ والوقت: {message_date}\n"
                f"رابط المجموعة: {group_link or 'رابط المجموعة غير متوفر'}\n"
                f"رابط الرسالة: {message_link or 'رابط الرسالة غير متوفر'}"
            )
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text=reply_text)
            except Exception as e:
                print(f"Error sending message to {user.telegram_id}: {e}")
    db.close()

def main():
    app = ApplicationBuilder().token(bot_token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            KEYWORDS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, keywords_menu_handler)],
            TYPING_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_keywords)],
            DELETE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_menu_handler)],
            DELETE_ONE_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_one_keyword_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), monitor_messages))
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
