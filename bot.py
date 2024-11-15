import discord
import os
from dotenv import load_dotenv
import requests
import sqlite3
from discord.ext import tasks
from datetime import datetime, timedelta
import re

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ACCOUNT_USER = os.getenv('ACCOUNT_USER')

def create_table_if_not_exists(cursor):
    """Creates the completed_problems table if it doesn't already exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completed_problems (
            id INTEGER PRIMARY KEY,
            title TEXT UNIQUE,
            accepted_date TEXT,
            review_next TEXT,
            review_latest TEXT,
            review_times INTEGER
        )
    ''')

def clear_database(cursor):
    """Clears all data from the completed_problems table."""
    cursor.execute('DELETE FROM completed_problems')
    print("Database cleared.")

def convert_to_slug(title):
    title_slug = title.lower()
    title_slug = re.sub(r'[^a-z0-9\s-]', '', title_slug)  
    title_slug = re.sub(r'\s+', '-', title_slug) 
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

def get_problem_link(title_slug):
    return f"https://leetcode.com/problems/{title_slug}"

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

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    @tasks.loop(minutes=1)
    async def my_background_task(self):
        await self.wait_until_ready()
        # Check if it's exactly 9 AM or 9 PM
        channel = self.get_channel(CHANNEL_ID)  # channel ID goes here
        submissions = fetch_submissions()
        if submissions:
            conn = sqlite3.connect('submissions.db')
            cursor = conn.cursor()

            create_table_if_not_exists(cursor)
            # clear_database(cursor)

            for submission in submissions:
                print(f"Processing submission: {submission['title']}")
                process_submission(cursor, submission)

            today = datetime.now().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_problems = []
            to_review_problems = []
            reviewed_problems = []

            # Fetching problems in separate queries
            cursor.execute('SELECT title FROM completed_problems WHERE accepted_date = ?', (today,))
            new_problems = [f"{row[0]}: {get_problem_link(convert_to_slug(row[0]))}" for row in cursor.fetchall()]

            cursor.execute('SELECT title FROM completed_problems WHERE review_next <= ? AND review_latest != ?', (today, today))
            to_review_problems = [f"{row[0]}: {get_problem_link(convert_to_slug(row[0]))}" for row in cursor.fetchall()]

            cursor.execute('SELECT title FROM completed_problems WHERE review_latest = ? AND accepted_date != ?', (today, today))
            reviewed_problems = [f"{row[0]}: {get_problem_link(convert_to_slug(row[0]))}" for row in cursor.fetchall()]

            # Constructing the message to send
            message = f"Today's Summary ({current_time})\n"
            message += f"Completed {len(new_problems)} New Problem(s):\n" + "\n".join(new_problems) + "\n"
            message += f"{len(to_review_problems)} Problem(s) to Review:\n" + "\n".join(to_review_problems) + "\n"
            message += f"{len(reviewed_problems)} Reviewed Problems:\n" + "\n".join(reviewed_problems)
            print(message)
        else:
            print("Can't fetch submission, no update!")
            message = "Can't fetch submission, no update!"
        # Sending the message to the channel
        await channel.send(message)


client = MyClient(intents=discord.Intents.default())
client.run(BOT_TOKEN)