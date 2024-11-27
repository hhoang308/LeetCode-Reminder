import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
import re
import requests


load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ACCOUNT_USER = os.getenv('ACCOUNT_USER')


intents = discord.Intents.default()  
intents.message_content = True  


bot = commands.Bot(command_prefix='!', intents=intents)

def convert_to_slug(title):
    title_slug = title.lower()
    title_slug = re.sub(r'[^a-z0-9\s-]', '', title_slug)  
    title_slug = re.sub(r'\s+', '-', title_slug) 
    return title_slug

def get_problem_link(title_slug):
    return f"https://leetcode.com/problems/{title_slug}"

def fetch_submissions():
    url = f"https://alfa-leetcode-api.onrender.com/{ACCOUNT_USER}/acSubmission"
    print("Fetch data from API", url)
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

def update_accepted_date(cursor, title, current_accepted_date, new_accepted_date):
    print(f"Updating accepted_date for {title} from {current_accepted_date} to {new_accepted_date}")
    cursor.execute('UPDATE completed_problems SET accepted_date = ? WHERE title = ?', (new_accepted_date, title))

def update_review_times(cursor, title, current_review_times):
    print(f"Updating review_times for {title} to {current_review_times}")
    cursor.execute('UPDATE completed_problems SET review_times = ? WHERE title = ?', (current_review_times, title))

def update_review_next(cursor, title, current_review_next, next_review_next):
    print(f"Updating review_next for {title} from {current_review_next} to {next_review_next}")
    cursor.execute('UPDATE completed_problems SET review_next = ? WHERE title = ?', (next_review_next, title))

def update_review_latest(cursor, title, current_review_latest, next_review_latest):
    print(f"Updating review_latest for {title} from {current_review_latest} to {next_review_latest}")
    cursor.execute('UPDATE completed_problems SET review_latest = ? WHERE title = ?', (next_review_latest, title))

def process_submission(cursor, submission):
    title = submission['title']
    time_stamp = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d')

    cursor.execute('SELECT accepted_date, review_next, review_latest, review_times FROM completed_problems WHERE title = ?', (title,))
    existing = cursor.fetchone()

    if existing:
        accepted_date, review_next, review_latest, review_times = existing
        print(f"{title} already exists in the database.")

        if accepted_date and accepted_date > time_stamp: 
            print(f"Backtrace {title}")
            update_accepted_date(cursor, title, accepted_date, time_stamp)
            if review_latest and review_latest > time_stamp:
                review_times += 1
                update_review_times(cursor, title, review_times)
                next_review_next = (datetime.strptime(review_latest, '%Y-%m-%d') + timedelta(days=2 * (review_times + 1))).strftime('%Y-%m-%d')
                update_review_next(cursor, title, review_next, next_review_next)
        elif accepted_date and accepted_date < time_stamp: 
            print(f"{title} is a revise submission")
            if review_latest and review_latest < time_stamp:
                review_times += 1
                update_review_times(cursor, title, review_times)
                update_review_latest(cursor, title, review_latest, time_stamp)
                next_review_next = (datetime.strptime(time_stamp, '%Y-%m-%d') + timedelta(days=2 * (review_times + 1))).strftime('%Y-%m-%d')
                update_review_next(cursor, title, review_next, next_review_next)
        elif accepted_date and accepted_date == time_stamp: 
            print(f"{title} is a today submission")

    else:  
        accepted_date = time_stamp
        review_latest = time_stamp
        review_next = (datetime.strptime(time_stamp, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        review_times = 0
        cursor.execute('INSERT INTO completed_problems (title, accepted_date, review_next, review_latest, review_times) VALUES (?, ?, ?, ?, ?)', 
                       (title, accepted_date, review_next, review_latest, review_times))
        print(f"Inserted a new problem: {title} | accepted_date: {accepted_date} | review_next: {review_next}")

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='update', help='Responds with Parkle\'s LeetCode to-do-list')
async def update(ctx):
    submissions = fetch_submissions()
    if submissions:
        conn = sqlite3.connect('submissions.db')
        cursor = conn.cursor()

        for submission in submissions:
            print(f"Processing submission: {submission['title']}")
            process_submission(cursor, submission)
            conn.commit()

        today = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        cursor.execute('SELECT title FROM completed_problems WHERE accepted_date = ?', (today,))
        new_problems = [f"{row[0]}: {get_problem_link(convert_to_slug(row[0]))}" for row in cursor.fetchall()]

        cursor.execute('SELECT title FROM completed_problems WHERE review_next <= ? AND review_latest != ?', (today, today))
        to_review_problems = [f"{get_problem_link(convert_to_slug(row[0]))}" for row in cursor.fetchall()]

        cursor.execute('SELECT title FROM completed_problems WHERE review_latest = ? AND accepted_date != ?', (today, today))
        reviewed_problems = [f"{row[0]}" for row in cursor.fetchall()]

        message = f"\(￣︶￣*\)\nToday's Summary ({current_time})\n"
        message += f"Completed {len(new_problems)} New Problem(s):\n" + "\n".join(new_problems) + "\n"
        message += f"{len(to_review_problems)} Problem(s) to Review:\n" + "\n".join(to_review_problems) + "\n"
        message += f"{len(reviewed_problems)} Reviewed Problems:\n" + "\n".join(reviewed_problems)
        print(message)
        conn.close()
        MAX_MESSAGE_LENGTH = 2000
        while len(message) > MAX_MESSAGE_LENGTH:
            part = message[:MAX_MESSAGE_LENGTH]
            await ctx.send(part)
            message = message[MAX_MESSAGE_LENGTH:]

        if message:
            await ctx.send(message)
    else:
        print("Can't fetch submission, no update!")
        await ctx.send("You have just requested, please wait a few more minute 👌!")

bot.run(TOKEN)