import os
from dotenv import load_dotenv
import discord
import requests
import sqlite3
from discord.ext import commands, tasks
from datetime import datetime, timedelta

# Tải biến môi trường từ tệp .env
load_dotenv()

# Khởi tạo bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Kết nối đến cơ sở dữ liệu SQLite
conn = sqlite3.connect('submissions.db')
cursor = conn.cursor()

# Tạo bảng nếu chưa tồn tại
cursor.execute('''
CREATE TABLE IF NOT EXISTS completed_problems (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE,
    accepted_date TEXT,
    review_date TEXT
)
''')
conn.commit()

# Lấy token và tên người dùng từ biến môi trường
BOT_TOKEN = os.getenv('BOT_TOKEN')
USERNAME = os.getenv('USERNAME')

# ... (Phần còn lại của mã bot không thay đổi)
# Hàm lấy dữ liệu từ API
def fetch_submissions():
    response = requests.get("https://alfa-leetcode-api.onrender.com/huyhoang3082001/acSubmission")
    if response.status_code == 200:
        return response.json().get("submission", [])
    return []

# Hàm lấy link bài tập từ tiêu đề
def get_problem_link(title_slug):
    return f"https://leetcode.com/problems/{title_slug}"

# Hàm cập nhật bài tập và review date
def update_or_add_problem(submission):
    title = submission['title']
    title_slug = submission['titleSlug']
    accepted_date = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d')
    
    cursor.execute('SELECT review_date FROM completed_problems WHERE title = ?', (title,))
    existing = cursor.fetchone()

    today = datetime.now().strftime('%Y-%m-%d')
    
    if existing:  # Nếu bài tập đã tồn tại
        review_date = existing[0]
        if accepted_date == today:
            # Bài mới làm hôm nay
            review_date = (datetime.strptime(today, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        else:
            # Bài ôn tập
            review_date_date = datetime.strptime(review_date, '%Y-%m-%d')
            accepted_date_date = datetime.strptime(accepted_date, '%Y-%m-%d')
            
            if review_date == today:  # Đúng hạn
                review_date = (review_date_date + (review_date_date - accepted_date_date) * 2).strftime('%Y-%m-%d')
            elif today < review_date:  # Trước hạn
                review_date = (datetime.strptime(today, '%Y-%m-%d') + (datetime.strptime(today, '%Y-%m-%d') - accepted_date_date) * 2).strftime('%Y-%m-%d')
            else:  # Trễ hạn
                review_date = (review_date_date + (review_date_date - accepted_date_date) * 2).strftime('%Y-%m-%d')

            cursor.execute('UPDATE completed_problems SET review_date = ? WHERE title = ?', (review_date, title))
    else:  # Nếu bài tập chưa tồn tại
        review_date = (datetime.strptime(accepted_date, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        cursor.execute('INSERT INTO completed_problems (title, accepted_date, review_date) VALUES (?, ?, ?)', 
                       (title, accepted_date, review_date))

    conn.commit()

# Nhiệm vụ chính để thực hiện các tác vụ
@tasks.loop(hours=6)
async def perform_tasks():
    channel = bot.get_channel(YOUR_CHANNEL_ID)  # Thay YOUR_CHANNEL_ID bằng ID kênh Discord
    submissions = fetch_submissions()
    
    today = datetime.now().strftime('%Y-%m-%d')
    new_problems = []
    on_time_problems = []
    early_problems = []
    late_problems = []

    for submission in submissions:
        accepted_date = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d')
        
        if accepted_date >= '2024-10-28':  # Lọc kết quả từ 28/10/2024 trở về hiện tại
            update_or_add_problem(submission)

    cursor.execute('SELECT title, review_date FROM completed_problems')
    all_problems = cursor.fetchall()

    for title, review_date in all_problems:
        if review_date == today:
            new_problems.append(f"{title}: {get_problem_link(submission['titleSlug'])}")
        elif review_date < today:
            late_problems.append(f"{title}: {get_problem_link(submission['titleSlug'])}")
        else:
            early_problems.append(f"{title}: {get_problem_link(submission['titleSlug'])}")

    # Tạo thông báo
    message = f"Hôm nay bạn đã làm {len(new_problems)} bài mới:\n" + "\n".join(new_problems) + "\n\n"
    message += f"Hôm nay cần ôn luyện các bài sau:\n" + "\n".join(early_problems) + "\n\n"
    message += f"Những bài cần ôn luyện nhưng đã trễ hạn:\n" + "\n".join(late_problems)

    await channel.send(message)

@bot.event
async def on_ready():
    print(f"Đã đăng nhập dưới tên: {bot.user.name}")
    perform_tasks.start()

@bot.event
async def on_close():
    conn.close()

# Bắt đầu bot
bot.run(BOT_TOKEN)
