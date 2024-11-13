import sqlite3
import json
from datetime import datetime, timedelta

def clear_database(cursor):
    """Clears all data from the completed_problems table."""
    cursor.execute('DELETE FROM completed_problems')
    print("Database cleared.")

#Cập nhật lần đầu tiên làm bài này
def update_accepted_date(cursor, title, current_accepted_date, new_accepted_date):
    #Trường hợp nếu như bài này đã ôn tập rồi, do chỉ duyệt từ mới nhất đến cũ nhật nên có khả năng bị lặp và phải cập nhật lại
    print(f"Updating accepted_date for {title} from {current_accepted_date} to {new_accepted_date}")
    cursor.execute('UPDATE completed_problems SET accepted_date = ? WHERE title = ?', (new_accepted_date, title))

#Cập nhật ngày cuối cùng làm bài này
def update_review_times(cursor, title, current_review_times):
    print(f"Updating review_times for {title} to {current_review_times}")
    cursor.execute('UPDATE completed_problems SET review_times = ? WHERE title = ?', (current_review_times, title))

#Cập nhật thời gian cần ôn tập tiếp theo
def update_review_next(cursor, title, current_review_next, next_review_next):
    #Trường hợp 1: Bài này là bài ôn tập <-> bài này đã làm từ ít nhất là hôm qua
    #Trường hợp 2: Bài này là bài mới làm hôm nay <-> accepted_date == today
    #Trường hợp 3: Cập nhật lại giống trong trường hợp của update_accepted_date() -> cái này nên được cập nhật cùng lúc với review_latest luôn chứ ?
    print(f"Updating review_next for {title} from {current_review_next} to {next_review_next}")
    cursor.execute('UPDATE completed_problems SET review_next = ? WHERE title = ?', (next_review_next, title))

def update_review_latest(cursor, title, current_review_latest, next_review_latest):
    print(f"Updating review_latest for {title} from {current_review_latest} to {next_review_latest}")
    cursor.execute('UPDATE completed_problems SET review_latest = ? WHERE title = ?', (next_review_latest, title))

def process_submission(cursor, submission):
    title = submission['title']
    time_stamp = datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d')

    # Kiểm tra xem bài tập đã tồn tại trong cơ sở dữ liệu
    cursor.execute('SELECT accepted_date, review_next, review_latest, review_times FROM completed_problems WHERE title = ?', (title,))
    existing = cursor.fetchone()

    if existing:
        accepted_date, review_next, review_latest, review_times = existing
        print(f"{title} already exists in the database.")
        
        # Cập nhật accepted_date
        if accepted_date and accepted_date > time_stamp: #Backtrace lại các bài đã làm rồi
            print(f"Backtrace {title}")
            update_accepted_date(cursor, title, accepted_date, time_stamp)
            if review_latest and review_latest > time_stamp:
                review_times += 1
                update_review_times(cursor, title, review_times)
                next_review_next = (datetime.strptime(review_latest, '%Y-%m-%d') + timedelta(days=2 * (review_times + 1))).strftime('%Y-%m-%d')
                update_review_next(cursor, title, review_next, next_review_next)
        elif accepted_date and accepted_date < time_stamp: #Bài ôn tập
            print(f"{title} is a revise submission")
            if review_latest and review_latest < time_stamp:
                review_times += 1
                update_review_times(cursor, title, review_times)
                update_review_latest(cursor, title, review_latest, time_stamp)
                next_review_next = (datetime.strptime(time_stamp, '%Y-%m-%d') + timedelta(days=2 * (review_times + 1))).strftime('%Y-%m-%d')
                update_review_next(cursor, title, review_next, next_review_next)
        elif accepted_date and accepted_date == time_stamp: #Bài mới làm hôm nay
            print(f"{title} is a today submission")

    else:  # Vấn đề chưa tồn tại -> thêm mới
        accepted_date = time_stamp
        review_latest = time_stamp
        review_next = (datetime.strptime(time_stamp, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        review_times = 0
        cursor.execute('INSERT INTO completed_problems (title, accepted_date, review_next, review_latest, review_times) VALUES (?, ?, ?, ?, ?)', 
                       (title, accepted_date, review_next, review_latest, review_times))
        print(f"Inserted a new problem: {title} | accepted_date: {accepted_date} | review_next: {review_next}")

# Ví dụ sử dụng các hàm trên:
def process_file(input_file):
    with open(input_file, 'r') as file:
        data = file.read()
        submissions = json.loads(data).get("submission", [])
    
    conn = sqlite3.connect('submissions.db')
    cursor = conn.cursor()

    # clear_database(cursor)
    
    for submission in submissions:
        print(f"Processing submission: {submission['title']}")
        process_submission(cursor, submission)
    
    conn.commit()
    conn.close()

def print_notice():
    print("Print Notification:")
    
    conn = sqlite3.connect('submissions.db')
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')

    # Query for new problems (accepted today)
    cursor.execute('SELECT title FROM completed_problems WHERE accepted_date = ?', (today,))
    new_problems = [row[0] for row in cursor.fetchall()]
    
    # Query for problems to review (review_next <= today and review_latest != today)
    cursor.execute('SELECT title FROM completed_problems WHERE review_next <= ? AND review_latest != ?', (today, today))
    to_review_problems = [row[0] for row in cursor.fetchall()]
    
    # Query for reviewed problems (review_latest == today and accepted_date != today)
    cursor.execute('SELECT title FROM completed_problems WHERE review_latest = ? AND accepted_date != ?', (today, today))
    reviewed_problems = [row[0] for row in cursor.fetchall()]
    
    conn.close()

    # Printing the categories
    print("\nNew Problems (Accepted Today):")
    if new_problems:
        for title in new_problems:
            print(f"- {title}")
    else:
        print("No new problems today.")
    
    print("\nProblems to Review (Review Date <= Today, but not reviewed today):")
    if to_review_problems:
        for title in to_review_problems:
            print(f"- {title}")
    else:
        print("No problems to review today.")
    
    print("\nReviewed Problems (Reviewed Today, but not accepted today):")
    if reviewed_problems:
        for title in reviewed_problems:
            print(f"- {title}")
    else:
        print("No problems reviewed today.")

# Thực thi
input_file = 'submissions_data.txt'
process_file(input_file)
print_notice()
