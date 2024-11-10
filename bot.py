import discord
import asyncio
import os
from dotenv import load_dotenv
import requests
import sqlite3
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from discord.utils import get
import re

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ACCOUNT_USER = os.getenv('ACCOUNT_USER')

# Kết nối đến cơ sở dữ liệu SQLite
conn = sqlite3.connect('submissions_1.db')
cursor = conn.cursor()

# Tạo bảng nếu chưa tồn tại
cursor.execute('''
CREATE TABLE IF NOT EXISTS completed_problems (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE,
    accepted_date TEXT,
    review_next TEXT,
    review_lastest TEXT,
    review_times INTEGER
)
''')
conn.commit()

def convert_to_slug(title):
    # Chuyển đổi title sang chữ thường và thay khoảng trắng bằng dấu '-'
    title_slug = title.lower()
    title_slug = re.sub(r'[^a-z0-9\s-]', '', title_slug)  # Loại bỏ các ký tự đặc biệt
    title_slug = re.sub(r'\s+', '-', title_slug)  # Thay khoảng trắng bằng dấu '-'
    return title_slug

def fetch_submissions():
    url = f"https://alfa-leetcode-api.onrender.com/{ACCOUNT_USER}/acSubmission"
    print("fetch from ", url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("submission", [])
        else:
            # Print error status code and response content for debugging
            print(f"Error: Received status code {response.status_code}")
            print("Response content:", response.text)
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (like connection issues)
        print("Request failed:", e)
    return []  # Return an empty list if there's an error

# Hàm lấy link bài tập từ tiêu đề
def get_problem_link(title_slug):
    return f"https://leetcode.com/problems/{title_slug}"

# Hàm cập nhật bài tập và review date
def update_or_add_problem(submission):
    title = submission['title']
    time_stamp = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d') 
    print(f"update_or_add_problem() {title} {time_stamp}")
    cursor.execute('SELECT review_lastest FROM completed_problems WHERE title = ?', (title,))
    existing = cursor.fetchone()
    # print(f"update_or_add_problem() {title} {time_stamp} {existing}")
    today = datetime.now().strftime('%Y-%m-%d')
    if existing:  #This problem exists -> consider it is a new problem learned today or a revise problem
        review_lastest = existing[0]
        print(f"update_or_add_problem() {title} {time_stamp} {existing}")
        if review_lastest != today:
            cursor.execute('UPDATE completed_problems SET review_latest = ? WHERE title = ?', (today, title))
            cursor.execute('SELECT review_times FROM completed_problems WHERE title = ?', (title,))
            review_times_result = cursor.fetchone()
            if review_times_result:
                review_times = review_times_result[0]  # Extract the value from the tuple
                cursor.execute('UPDATE completed_problems SET review_times = ? WHERE title = ?', (review_times + 1, title))
                cursor.execute('SELECT review_next FROM completed_problems WHERE title = ?', (title,))
                review_next_result = cursor.fetchone()
                if review_next_result:
                    # Calculate new `review_next` date based on `review_lastest`
                    review_next = (datetime.strptime(review_lastest, '%Y-%m-%d') + timedelta(days=2 * (review_times + 1))).strftime('%Y-%m-%d')
                    cursor.execute('UPDATE completed_problems SET review_next = ? WHERE title = ?', (review_next, title))
                    print(f"Updated problem: {title} | review_next set to: {review_next}")
                else:
                    print("No review_next found for the given title.")
            else:
                print("No review_times found for the given title.")
    else:  # This problem doesn't exist -> create it with default value
        print("Can't find ", title)
        accepted_date = time_stamp
        review_lastest = time_stamp
        review_next = (datetime.strptime(time_stamp, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        cursor.execute('INSERT INTO completed_problems (title, accepted_date, review_next, review_lastest, review_times) VALUES (?, ?, ?, ?, ?)', 
                       (title, accepted_date, review_next, review_lastest, 0))
        print(f"Inserted new problem: {title} | accepted_date: {accepted_date} | review_next: {review_next}")
    print("update_or_add_problem() done")
    conn.commit()

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.my_background_task())

        async def on_ready(self):
            print(f'Logged in as {self.user} (ID: {self.user.id})')
            print('------')
    @tasks.loop(seconds=60)
    async def my_background_task(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)  # channel ID goes here
        submissions = fetch_submissions()
        print("fetch_submissions() ", submissions)
    
        today = datetime.now().strftime('%Y-%m-%d')
        print("Today:", today)
        new_problems = []
        to_review_problems = []
        reviewed_problems = []

        for submission in submissions:
            accepted_date = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d')
            print(f"Submission: {submission['title']} | Accepted Date: {accepted_date}")            
            if accepted_date >= '2024-11-07':  # Lọc kết quả từ 28/10/2024 trở về hiện tại
                print("Valid submission because this submission was accepted after ", accepted_date)
                update_or_add_problem(submission)
            else:
                print("Invalid submission because this submission was accepted before ", accepted_date)

        cursor.execute('SELECT title, accepted_date, review_next , review_lastest FROM completed_problems')
        all_problems = cursor.fetchall()

        for title, accepted_date, review_next, review_lastest in all_problems:
            if accepted_date == today:
                new_problems.append(f"{title}: {get_problem_link(convert_to_slug(title))}")
            if review_next <= today and review_lastest != today:
                to_review_problems.append(f"{title}: {get_problem_link(convert_to_slug(title))}")
            if review_lastest == today and accepted_date != today:
                reviewed_problems.append(f"{title}: {get_problem_link(convert_to_slug(title))}")

        # Tạo thông báo
        message = f"Hôm nay bạn đã làm {len(new_problems)} bài mới:\n" + "\n".join(new_problems) + "\n\n"
        message += f"Hôm nay cần ôn luyện các bài sau:\n" + "\n".join(to_review_problems) + "\n\n"
        message += f"Những bài đã ôn luyện hôm nay:\n" + "\n".join(reviewed_problems)
        conn.close()

        await channel.send(message)


client = MyClient(intents=discord.Intents.default())
client.run(BOT_TOKEN)