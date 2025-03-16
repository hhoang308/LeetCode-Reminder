# Result
![image](https://github.com/user-attachments/assets/574f6441-bffc-4e8e-a1c7-6f977e1663b7)
# Purpose
This bot is created to remind you to revise the exercises you have done on leetcode after a period of time.
# How it works
I used [this API](https://github.com/alfaarghya/alfa-leetcode-api) to get 20 latest accepted submission. The example data I got when query this API is included in the file _submission_data.txt_. Then I parse it and save it in SQL Lite database. After a while, the bot will automatically reload the data, update the database and perform the search. Currently I set it to 12 hours because I want a reminder after waking up to know what exercises I need to do today and one before going to bed to encourage myself that I did a good job.
# How to use this 
I recommend you to use a virtual machine for convenience, I'm using google cloud now.
### Step 1: Install Python
python --version
### Step 2: Install requirement.txt
sudo apt install python3-pip

pip3 install -r requirements.txt
### Step 3: Log in to Discord Developer Portal
### Step 4: Create .env
ACCOUNT_USER in here is huyhoang3082001
![image](https://github.com/user-attachments/assets/e80aeaf1-18f2-4f65-b8bc-27be9c8153d3)
BOT_TOKEN will get from Discord Developer Portal -> Bot -> Token (you can click Reset Token)
```
BOT_TOKEN=
ACCOUNT_USER=
```
### Step 5: Run it as a service
### Step 6: Change time zone (optional)
