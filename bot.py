import sqlite3
import uuid
import asyncio
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
import requests
import telegram

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка версии библиотеки
logger.info(f"Версия python-telegram-bot: {telegram.__version__}")

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    return conn

# Генерация API-токена
def generate_api_token():
    return str(uuid.uuid4())

# Отправка главного меню с улучшенными кнопками
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Подключить кассу", callback_data="connect"), 
         InlineKeyboardButton("💳 Создать счет", callback_data="create_invoice")],
        [InlineKeyboardButton("📜 История транзакций", callback_data="transactions"), 
         InlineKeyboardButton("💸 Запрос на вывод", callback_data="withdraw")],
        [InlineKeyboardButton("🔑 Генерация API токена", callback_data="generate_api_token")],  # Новая кнопка
        [InlineKeyboardButton("❓ Помощь", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Добро пожаловать в онлайн-кассу!\nВыберите действие:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("Добро пожаловать в онлайн-кассу!\nВыберите действие:", reply_markup=reply_markup)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context)

# Команда /register
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone():
        await update.message.reply_text("Вы уже зарегистрированы.")
        conn.close()
        return
    api_token = generate_api_token()
    cursor.execute("INSERT INTO Merchants (api_token, chat_id) VALUES (?, ?)", (api_token, chat_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Вы зарегистрированы! Ваш API-токен: {api_token}")

# Команда /connect
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /connect <api_token>")
        return
    api_token = context.args[0]
    chat_id = update.message.chat_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE api_token = ?", (api_token,))
    merchant = cursor.fetchone()
    if merchant:
        cursor.execute("UPDATE Merchants SET chat_id = ? WHERE api_token = ?", (chat_id, api_token))
        await update.message.reply_text("Касса успешно подключена!")
    else:
        await update.message.reply_text("Неверный API-токен.")
    conn.commit()
    conn.close()

# Команда /create_invoice с исправленным URL и оптимизацией
async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /create_invoice <amount> <description>")
        return
    try:
        amount = float(context.args[0])
        description = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом!")
        return
    chat_id = update.message.chat_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
    merchant = cursor.fetchone()
    if not merchant:
        await update.message.reply_text("Сначала подключите кассу с помощью /connect")
        conn.close()
        return
    invoice_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO Invoices (id, merchant_id, amount, description, status, created_at) "
        "VALUES (?, ?, ?, ?, 'pending', ?)",
        (invoice_id, merchant['id'], amount, description, created_at)
    )
    conn.commit()
    conn.close()
    payment_url = f"https://ck45726.tw1.ru{invoice_id}"  # Замените на ваш реальный домен
    keyboard = [[InlineKeyboardButton("Оплатить", url=payment_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Счет создан!\nСумма: {amount} RUB\nОписание: {description}\nID: {invoice_id}",
        reply_markup=reply_markup
    )

# Команда /transactions с исправленной функцией подключения
async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    conn = get_db_connection()  # Исправлено с get_db_dev_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
    merchant = cursor.fetchone()
    if not merchant:
        await update.message.reply_text("Сначала подключите кассу с помощью /connect")
        conn.close()
        return
    cursor.execute(
        "SELECT t.id, t.invoice_id, t.amount_paid, t.commission, t.net_amount, t.paid_at "
        "FROM Transactions t JOIN Invoices i ON t.invoice_id = i.id "
        "WHERE i.merchant_id = ?", (merchant['id'],)
    )
    transactions = cursor.fetchall()
    conn.close()
    if not transactions:
        await update.message.reply_text("История транзакций пуста.")
        return
    response = "История транзакций:\n"
    for t in transactions:
        response += (
            f"ID: {t['id']}\nСчет: {t['invoice_id']}\nОплачено: {t['amount_paid']} RUB\n"
            f"Комиссия: {t['commission']} RUB\nЧистая сумма: {t['net_amount']} RUB\n"
            f"Дата: {t['paid_at']}\n\n"
        )
    await update.message.reply_text(response)

# Команда /withdraw
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Использование: /withdraw <amount> <method> <address>")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом!")
        return
    method = context.args[1]
    address = context.args[2]
    chat_id = update.message.chat_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
    merchant = cursor.fetchone()
    if not merchant:
        await update.message.reply_text("Сначала подключите кассу с помощью /connect")
        conn.close()
        return
    cursor.execute(
        "INSERT INTO Withdrawals (merchant_id, amount, method, address, status, requested_at) "
        "VALUES (?, ?, ?, ?, 'pending', ?)",
        (merchant['id'], amount, method, address, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"Запрос на вывод создан!\nСумма: {amount} RUB\nМетод: {method}\nАдрес: {address}"
    )

# Периодическая проверка оплаченных счетов
async def check_paid_invoices(context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT i.id, i.amount, i.description, m.chat_id "
        "FROM Invoices i JOIN Merchants m ON i.merchant_id = m.id "
        "WHERE i.status = 'paid' AND i.id NOT IN (SELECT invoice_id FROM Transactions)"
    )
    paid_invoices = cursor.fetchall()
    for invoice in paid_invoices:
        amount_paid = invoice['amount']
        commission = amount_paid * 0.2
        net_amount = amount_paid - commission
        cursor.execute(
            "INSERT INTO Transactions (invoice_id, amount_paid, commission, net_amount, paid_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (invoice['id'], amount_paid, commission, net_amount, datetime.now().isoformat())
        )
        await context.bot.send_message(
            chat_id=invoice['chat_id'],
            text=f"Счет оплачен!\nID: {invoice['id']}\nСумма: {amount_paid} RUB\n"
                 f"Комиссия: {commission} RUB\nЧистая сумма: {net_amount} RUB"
        )
    conn.commit()
    conn.close()

# Обработка нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
    merchant = cursor.fetchone()
    conn.close()
    
    if data == "connect":
        if merchant:
            await query.edit_message_text(text="Ваша касса уже подключена.")
        else:
            await query.edit_message_text(text="Введите ваш API-токен:")
            context.user_data['waiting_for'] = 'api_token'
    elif data == "create_invoice":
        if not merchant:
            await query.edit_message_text(text="Сначала подключите кассу с помощью /connect или /register")
            return
        await query.edit_message_text(text="Введите сумму:")
        context.user_data['waiting_for'] = 'amount'
    elif data == "transactions":
        if not merchant:
            await query.edit_message_text(text="Сначала подключите кассу с помощью /connect или /register")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT t.id, t.invoice_id, t.amount_paid, t.commission, t.net_amount, t.paid_at "
            "FROM Transactions t JOIN Invoices i ON t.invoice_id = i.id "
            "WHERE i.merchant_id = ?", (merchant['id'],)
        )
        transactions = cursor.fetchall()
        conn.close()
        if not transactions:
            await query.edit_message_text(text="История транзакций пуста.")
            return
        response = "История транзакций:\n"
        for t in transactions:
            response += (
                f"ID: {t['id']}\nСчет: {t['invoice_id']}\nОплачено: {t['amount_paid']} RUB\n"
                f"Комиссия: {t['commission']} RUB\nЧистая сумма: {t['net_amount']} RUB\n"
                f"Дата: {t['paid_at']}\n\n"
            )
        await query.edit_message_text(text=response)
    elif data == "withdraw":
        if not merchant:
            await query.edit_message_text(text="Сначала подключите кассу с помощью /connect или /register")
            return
        await query.edit_message_text(text="Введите сумму, метод и адрес для вывода (например: 100 BTC 123456789):")
        context.user_data['waiting_for'] = 'withdraw'
    elif data == "help":
        await query.edit_message_text(text="Справка:\n- Подключить кассу: /connect <api_token>\n- Создать счет: /create_invoice <amount> <description>\n- Посмотреть транзакции: /transactions\n- Запрос на вывод: /withdraw <amount> <method> <address>\n- Зарегистрировать новую кассу: /register")
    elif data == "generate_api_token":  # Новый обработчик
        if merchant:
            await query.edit_message_text(text="Вы уже зарегистрированы и имеете API токен.")
        else:
            api_token = generate_api_token()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Merchants (api_token, chat_id) VALUES (?, ?)", (api_token, chat_id))
            conn.commit()
            conn.close()
            await query.edit_message_text(text=f"Ваш новый API токен: {api_token}\nИспользуйте его для подключения кассы с помощью /connect <api_token>")

# Обработка ввода пользователя с исправленным URL и оптимизацией
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'waiting_for' not in context.user_data:
        return
    waiting_for = context.user_data['waiting_for']
    chat_id = update.message.chat_id
    if waiting_for == 'api_token':
        api_token = update.message.text
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Merchants WHERE api_token = ?", (api_token,))
        merchant = cursor.fetchone()
        if merchant:
            cursor.execute("UPDATE Merchants SET chat_id = ? WHERE api_token = ?", (chat_id, api_token))
            await update.message.reply_text("Касса успешно подключена!")
        else:
            await update.message.reply_text("Неверный API-токен. Попробуйте снова или используйте /register для генерации нового.")
        conn.commit()
        conn.close()
        del context.user_data['waiting_for']
        await send_main_menu(update, context)
    elif waiting_for == 'amount':
        try:
            amount = float(update.message.text)
            context.user_data['amount'] = amount
            await update.message.reply_text("Введите описание:")
            context.user_data['waiting_for'] = 'description'
        except ValueError:
            await update.message.reply_text("Сумма должна быть числом! Попробуйте снова.")
    elif waiting_for == 'description':
        description = update.message.text
        amount = context.user_data['amount']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
        merchant = cursor.fetchone()
        if not merchant:
            await update.message.reply_text("Сначала подключите кассу с помощью /connect или /register")
            del context.user_data['waiting_for']
            conn.close()
            return
        invoice_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO Invoices (id, merchant_id, amount, description, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (invoice_id, merchant['id'], amount, description, created_at)
        )
        conn.commit()
        conn.close()
        payment_url = f"https://ck45726.tw1.ru{invoice_id}"  # Замените на ваш реальный домен
        keyboard = [[InlineKeyboardButton("Оплатить", url=payment_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Счет создан!\nСумма: {amount} RUB\nОписание: {description}\nID: {invoice_id}",
            reply_markup=reply_markup
        )
        del context.user_data['waiting_for']
        await send_main_menu(update, context)
    elif waiting_for == 'withdraw':
        parts = update.message.text.split()
        if len(parts) != 3:
            await update.message.reply_text("Неверный формат. Используйте: сумма метод адрес")
            return
        try:
            amount = float(parts[0])
            method = parts[1]
            address = parts[2]
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Merchants WHERE chat_id = ?", (chat_id,))
            merchant = cursor.fetchone()
            if not merchant:
                await update.message.reply_text("Сначала подключите кассу с помощью /connect или /register")
                del context.user_data['waiting_for']
                conn.close()
                return
            cursor.execute(
                "INSERT INTO Withdrawals (merchant_id, amount, method, address, status, requested_at) "
                "VALUES (?, ?, ?, ?, 'pending', ?)",
                (merchant['id'], amount, method, address, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            await update.message.reply_text(
                f"Запрос на вывод создан!\nСумма: {amount} RUB\nМетод: {method}\nАдрес: {address}"
            )
            del context.user_data['waiting_for']
            await send_main_menu(update, context)
        except ValueError:
            await update.message.reply_text("Сумма должна быть числом! Попробуйте снова.")

# Основная функция
def main():
    application = Application.builder().token("7531112417:AAG8C5tTGHiYOvn1x6TsPzfqBozT_OHFzMA").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("create_invoice", create_invoice))
    application.add_handler(CommandHandler("transactions", transactions))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Исправлено на обработку текста без команд
    if application.job_queue is None:
        logger.error("JobQueue недоступен. Установите python-telegram-bot с модулем job-queue.")
        exit(1)
    application.job_queue.run_repeating(check_paid_invoices, interval=300)
    application.run_polling()

if __name__ == "__main__":
    main()
