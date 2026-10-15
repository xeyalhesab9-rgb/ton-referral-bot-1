import time
import sqlite3
import telebot
from telebot import types, apihelper

# ==========================================
# AYARLAR
# ==========================================
TOKEN = "8938147451:AAF4R_Yg_Q..."  # Öz bot token-inizi yazın
ADMIN_ID = 8591374417                  # Admin Telegram ID-niz
CHANNEL_USERNAME = "@meoww122134"      # Qrup istifadəçi adınız
ADMIN_WALLET = "UQCgPJ6q8eKxDsMsijRe0UFkgDlRf654olp78dzIxrQYdfoh" # TON Pul kisəsi adresi

bot = telebot.TeleBot(TOKEN)

# ==========================================
# VERİTABANI KURULUMU (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            ref_balance REAL DEFAULT 0.0,
            referred_by INTEGER
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN ref_balance REAL DEFAULT 0.0")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            title TEXT,
            reward REAL,
            link TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_proofs (
            proof_id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER,
            creator_id INTEGER,
            reward REAL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, ref_balance, referred_by FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, referrer_id=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance, ref_balance, referred_by) VALUES (?, 0.0, 0.0, ?)", (user_id, referrer_id))
    if referrer_id:
        # Referal bonusu 0.01 TON olaraq dəyişdirildi
        cursor.execute("UPDATE users SET ref_balance = ref_balance + 0.01 WHERE user_id = ?", (referrer_id,))
        try:
            bot.send_message(referrer_id, "🎉 Congratulations! A new user joined via your referral link: +0.01 TON added to your Referral Balance!")
        except:
            pass
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ==========================================
# MENÜLER
# ==========================================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_balance = types.KeyboardButton('💰 Balance')
    btn_ref = types.KeyboardButton('🔗 Referral Link')
    btn_tasks = types.KeyboardButton('📋 Earn (Tasks)')
    btn_create_task = types.KeyboardButton('➕ Create Task')
    btn_deposit = types.KeyboardButton('💎 Deposit')
    btn_withdraw = types.KeyboardButton('💸 Withdraw')
    markup.add(btn_balance, btn_ref, btn_tasks, btn_create_task, btn_deposit, btn_withdraw)
    return markup

def sub_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_channel = types.InlineKeyboardButton("📢 Join Our Group", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
    btn_check = types.InlineKeyboardButton("✅ Continue to Bot", callback_data="check_sub")
    markup.add(btn_channel)
    markup.add(btn_check)
    return markup

# ==========================================
# KOMUTLAR & ADMİN ÖZƏLLİKLƏRİ
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        args = message.text.split()
        referrer_id = None
        if len(args) > 1 and args[1].isdigit():
            possible_referrer = int(args[1])
            if possible_referrer != user_id and get_user(possible_referrer):
                referrer_id = possible_referrer
                
        add_user(user_id, referrer_id)

        bot.send_message(
            message.chat.id,
            f"👋 Welcome to Honeyfarm!\n\n"
            f"Please join our official group before continuing:\n{CHANNEL_USERNAME}\n\n"
            f"After joining, click the button below to start!",
            reply_markup=sub_keyboard(),
            parse_mode="Markdown"
        )
    else:
        welcome_text = (
            "Welcome to Honeyfarm Referral & Task Bot! 🍯\n\n"
            "Invite friends, complete social tasks, or create your own tasks!"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")

# ADMIN: Bütün istifadəçilərin balansını göstərən komut
@bot.message_handler(commands=['users'])
def show_all_users(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, ref_balance FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Hələ heç bir istifadəçi yoxdur.")
        return

    text = "👥 **Bütün İstifadəçilər və Balanslar:**\n\n"
    for u in users:
        uid, bal, ref_bal = u
        text += f"👤 ID: `{uid}`\n💳 Əsas: **{bal:.2f} TON** | 🔗 Ref: **{ref_bal:.2f} TON**\n-------------------\n"

    # Mesaj çox uzun olarsa hissələrə bölürük
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            bot.send_message(message.chat.id, text[x:x+4000], parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ADMIN: Bütün istifadəçilərə toplu mesaj göndərmə komutu (/send mesaj)
@bot.message_handler(commands=['send'])
def broadcast_message(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return

    msg_to_send = message.text.replace('/send', '').strip()
    if not msg_to_send:
        bot.reply_to(message, "❌ Lütfən göndərmək istədiyiniz mesajı yazın.\nMəsələn: `/send Salam hər kəsə!`", parse_mode="Markdown")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    failed = 0

    bot.reply_to(message, "🚀 Mesaj bütün istifadəçilərə göndərilir...")

    for u in users:
        target_id = u[0]
        try:
            bot.send_message(target_id, msg_to_send, parse_mode="Markdown")
            success += 1
            time.sleep(0.05) # Telegram spama düşməmək üçün kiçik fasilə
        except:
            failed += 1

    bot.send_message(message.chat.id, f"✅ **Yayın Tamamlandı!**\n\n🟢 Uğurla göndərildi: {success}\n🔴 Uğursuz (Botu bloklayanlar): {failed}", parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]
    conn.close()
    
    stats_text = (
        f"📊 **Bot Statistikası:**\n\n"
        f"👥 Ümumi İstifadəçi Sayı: **{total_users}**\n"
        f"📋 Ümumi Yaradılan Tapşırıqlar: **{total_tasks}**"
    )
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    bot.answer_callback_query(call.id, "✅ Welcome!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    welcome_text = (
        "Welcome to Honeyfarm Referral & Task Bot! 🍯\n\n"
        "Invite friends, complete social tasks, or create your own tasks!"
    )
    bot.send_message(call.message.chat.id, welcome_text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '💰 Balance')
def show_balance(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, ref_balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    balance = user[0] if user else 0.0
    ref_balance = user[1] if user else 0.0
    total = balance + ref_balance
    
    msg = (
        f"💳 **Your Balances:**\n\n"
        f"💎 Main Balance (Withdrawable): **{balance:.2f} TON**\n"
        f"🔗 Referral Balance (Tasks Only): **{ref_balance:.2f} TON**\n"
        f"📊 Total Available: **{total:.2f} TON**"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '🔗 Referral Link')
def show_referral(message):
    user_id = message.from_user.id
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    msg = f"🔗 **Your Personal Referral Link:**\n`{ref_link}`\n\n📌 Share to earn **0.01 TON** per referral!"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '📋 Earn (Tasks)')
def show_tasks(message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task_id, title, reward, link FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        bot.reply_to(message, "📭 There are no available tasks right now. Check back later!")
        return
        
    markup = types.InlineKeyboardMarkup()
    for task in tasks:
        task_id, title, reward, link = task
        btn = types.InlineKeyboardButton(f"{title} (+{reward} TON)", callback_data=f"do_task_{task_id}")
        markup.add(btn)
        
    bot.reply_to(message, "📋 **Available Tasks:**\nClick a task, complete it, and send a screenshot as proof!", reply_markup=markup, parse_mode="Markdown")

user_active_task = {}

@bot.callback_query_handler(func=lambda call: call.data.startswith("do_task_"))
def task_clicked(call):
    task_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, reward, link FROM tasks WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        bot.answer_callback_query(call.id, "❌ Task not found!", show_alert=True)
        return
        
    title, reward, link = task
    user_active_task[user_id] = task_id
    
    msg_text = (
        f"📌 **Task:** {title}\n"
        f"💰 **Reward:** {reward} TON\n"
        f"🔗 **Link:** {link}\n\n"
        f"👉 Please complete the task, then send a **screenshot (photo)** here as proof!"
    )
    
    bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    
    if user_id not in user_active_task:
        bot.reply_to(message, "❌ Please choose a task from 'Earn (Tasks)' before sending a screenshot.")
        return
        
    task_id = user_active_task[user_id]
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT creator_id, reward FROM tasks WHERE task_id = ?", (task_id,))
    task_info = cursor.fetchone()
    conn.close()
    
    if not task_info:
        bot.reply_to(message, "❌ This task no longer exists.")
        return
        
    creator_id, reward = task_info
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pending_proofs (worker_id, creator_id, reward) VALUES (?, ?, ?)", (user_id, creator_id, reward))
    proof_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    photo_id = message.photo[-1].file_id
    username = message.from_user.username
    username_str = f"@{username}" if username else f"ID: {user_id}"
    
    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ Approve & Pay", callback_data=f"tapp_{proof_id}")
    btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"trej_{proof_id}")
    markup.add(btn_approve, btn_reject)
    
    caption = f"📸 **New Task Proof for your task!**\n👤 Worker: {username_str} (`{user_id}`)\n💰 Reward to pay: {reward} TON"
    
    try:
        bot.send_photo(creator_id, photo_id, caption=caption, reply_markup=markup, parse_mode="Markdown")
        bot.reply_to(message, "✅ Screenshot sent to the task creator! Waiting for review.")
        del user_active_task[user_id]
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to send proof to task creator.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("tapp_") or call.data.startswith("trej_"))
def creator_task_action(call):
    data = call.data.split("_")
    action = data[0]
    proof_id = int(data[1])
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT worker_id, creator_id, reward FROM pending_proofs WHERE proof_id = ?", (proof_id,))
    proof = cursor.fetchone()
    conn.close()
    
    if not proof:
        bot.answer_callback_query(call.id, "❌ Proof data not found or already processed!", show_alert=True)
        return
        
    worker_id, creator_id, reward = proof
    
    if call.from_user.id != creator_id:
        bot.answer_callback_query(call.id, "❌ You are not allowed to review this!", show_alert=True)
        return
        
    if action == "tapp":
        update_balance(worker_id, reward)
        bot.answer_callback_query(call.id, "✅ Approved! Reward paid to the worker.")
        try:
            bot.edit_message_caption(caption=call.message.caption + "\n\n**STATUS: APPROVED & PAID ✅**", reply_markup=None, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        except:
            pass
        try:
            bot.send_message(worker_id, f"🎉 Your task proof was approved by the task creator! **+{reward} TON** added to your balance.")
        except:
            pass
            
    elif action == "trej":
        bot.answer_callback_query(call.id, "❌ Rejected.")
        try:
            bot.edit_message_caption(caption=call.message.caption + "\n\n**STATUS: REJECTED ❌**", reply_markup=None, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        except:
            pass
        try:
            bot.send_message(worker_id, "❌ Your task proof was rejected by the task creator.")
        except:
            pass
            
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_proofs WHERE proof_id = ?", (proof_id,))
    conn.commit()
    conn.close()

@bot.message_handler(func=lambda message: message.text == '➕ Create Task')
def create_task_start(message):
    msg = bot.reply_to(
        message, 
        "📝 **Create a New Task**\n\n"
        "Please send the task details in this exact format:\n"
        "`Title | Reward per user | Link`\n\n"
        "*(Example: Follow my Instagram | 0.02 | https://instagram.com/...)*\n\n"
        "📌 *Note: A 10% platform fee will be added to your total cost.*", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_create_task)

def process_create_task(message):
    try:
        text_data = message.text
        parts = text_data.split('|')
        if len(parts) != 3:
            bot.reply_to(message, "❌ Invalid format! Please use: `Title | Reward | Link`", parse_mode="Markdown")
            return
            
        title = parts[0].strip()
        reward = float(parts[1].strip())
        link = parts[2].strip()
        
        user_id = message.from_user.id
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance, ref_balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        balance = user[0] if user else 0.0
        ref_balance = user[1] if user else 0.0
        total_balance = balance + ref_balance
        
        if reward < 0.01:
            bot.reply_to(message, "❌ Minimum reward per task must be at least 0.01 TON.")
            return
            
        fee = reward * 0.10
        total_cost = reward + fee
            
        if total_balance < total_cost:
            bot.reply_to(
                message, 
                f"❌ You don't have enough total balance!\n\n"
                f"💰 Task Cost + Fee: **{total_cost:.2f} TON**\n"
                f"💳 Your Total Balance: **{total_balance:.2f} TON**",
                parse_mode="Markdown"
            )
            return
            
        if balance >= total_cost:
            new_balance = balance - total_cost
            new_ref_balance = ref_balance
        else:
            remaining = total_cost - balance
            new_balance = 0.0
            new_ref_balance = ref_balance - remaining
            
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ?, ref_balance = ? WHERE user_id = ?", (new_balance, new_ref_balance, user_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (fee, ADMIN_ID))
        cursor.execute("INSERT INTO tasks (creator_id, title, reward, link) VALUES (?, ?, ?, ?)", (user_id, title, reward, link))
        conn.commit()
        conn.close()
        
        bot.reply_to(
            message, 
            f"✅ **Task successfully created and published!**\n\n"
            f"📌 Title: {title}\n"
            f"💰 Reward: {reward} TON\n"
            f"📊 Fee deducted (10%): {fee:.2f} TON\n"
            f"🔗 Link: {link}", 
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error creating task: Please check the format.")

@bot.message_handler(func=lambda message: message.text == '💎 Deposit')
def deposit_request(message):
    msg = (
        f"💎 **Deposit TON:**\n\n"
        f"To deposit funds for creating tasks, send TON to the official wallet address below:\n\n"
        f"`{ADMIN_WALLET}`\n\n"
        f"📌 After sending, send your transaction hash (TXID) or contact the admin."
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '💸 Withdraw')
def withdraw_request(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    balance = user[0] if user else 0.0
    min_withdraw = 0.5  
    
    if balance < min_withdraw:
        bot.reply_to(message, f"❌ Minimum withdrawal limit is **{min_withdraw} TON**.\nYour **Main Balance** (Referral balance cannot be withdrawn): **{balance:.2f} TON**", parse_mode="Markdown")
    else:
        msg = bot.reply_to(message, f"✅ Your withdrawable balance: {balance:.2f} TON.\nPlease send your TON wallet address:")
        bot.register_next_step_handler(msg, process_withdraw_address, balance)

def process_withdraw_address(message, balance):
    wallet_address = message.text
    user_id = message.from_user.id
    username = message.from_user.username
    username_str = f"@{username}" if username else f"ID: {user_id}"
    
    update_balance(user_id, -balance)
    
    bot.reply_to(message, f"🚀 Withdrawal request received!\n💵 Amount: **{balance:.2f} TON**\n🏦 Wallet: `{wallet_address}`", parse_mode="Markdown")
    
    admin_notification = f"🔔 **New Withdrawal Request!**\n👤 User: {username_str} (`{user_id}`)\n💵 Amount: **{balance:.2f} TON**\n🏦 Wallet:\n`{wallet_address}`"
    try:
        bot.send_message(ADMIN_ID, admin_notification, parse_mode="Markdown")
    except Exception as e:
        print(f"Admin notification error: {e}")

# ==========================================
# 7/24 RUNNER
# ==========================================
if __name__ == '__main__':
    print("Bot 7/24 modunda başladılır...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Sistem xətası oldu: {e}. 5 saniyə sonra bərpa olunur...")
            time.sleep(5)
