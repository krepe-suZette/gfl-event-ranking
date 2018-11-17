import pymysql
import datetime
import json

config = json.load(open("config.json", "r"))

conn = pymysql.connect(**config["mysql"])
cur = conn.cursor()

today = datetime.date.today()
sql = (
    "INSERT INTO ranking (date, user_key, event_name, score, per, ranking, comment, vaild) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
)

event_name = config['event_name']
today = input('오늘 날짜 입력: ')

rank2input = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
args = [(today, f"inRanking{n:0>3}", event_name, input(f'{n:>3}등 입력: '), 0, n, "수동 입력", 0) for n in rank2input]

cur.executemany(sql, args)
conn.commit()

print("")
