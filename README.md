# Purpose
This bot is created to remind you to revise the exercises you have done on leetcode after a period of time.
# How it works
I used [this API](https://github.com/alfaarghya/alfa-leetcode-api) to get 20 latest accepted submission. The example data I got when query this API is included in the file _submission_data.txt_. Then I parse it and save it in SQL Lite database. After a while, the bot will automatically reload the data, update the database and perform the search. Currently I set it to 12 hours because I want a reminder after waking up to know what exercises I need to do today and one before going to bed to encourage myself that I did a good job.
# How to use this 
I recommend you to use a virtual machine for convenience, I'm using google cloud now.
### Step 1: Install Python
### Step 2: Install requirement.txt
### Step 3: Log in to Discord Developer Portal
### Step 4: Copy Channel ID
### Step 5: Create .env
```
BOT_TOKEN=
ACCOUNT_USER=
CHANNEL_ID=
```
### Step 6: Run it as a service
