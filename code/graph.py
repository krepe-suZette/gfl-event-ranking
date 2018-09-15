import numpy as np
import matplotlib
import matplotlib.pylab as plt
import matplotlib.font_manager as fm
import scipy
import scipy.interpolate as spi
import pymysql
import datetime
import time
import json
import csv
import os
import glob

config = json.load(open("config.json", "r"))

conn = pymysql.connect(**config)
cur = conn.cursor()

matplotlib.rc("font", family="KoPubDotum", size=16)


# DB로부터 데이터 가공 및 저장

def raw(date):
    sql = (
        "SELECT per, score FROM ranking "
        "WHERE date = %s AND vaild > -1 "
        "ORDER BY score DESC"
    )
    cur.execute(sql, date)
    rows = cur.fetchall()
    if len(rows) == 0:
        print(f">>> raw: SKIP {date}")
        return
    with open(f'../data/raw/{date}.csv', 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f)
        for row in rows:
            wr.writerow(row)
    return


def interpolate(date, gets=[]):
    st = time.time()
    sql = (
        "SELECT per, MIN(score) FROM ranking "
        "WHERE date = %s AND vaild > -1 "
        "GROUP BY per;"
    )
    cur.execute(sql, date)
    rows = cur.fetchall()
    if len(rows) < 10:
        print(f">>> int: SKIP {date}")
        return
    elif len(rows) < 28:
        k = 1
    else:
        k = 2

    # y1: min, y2: max
    if rows[-1][0] == 100:
        x, y1 = list(zip(*rows[:-1], (100, 1, 1)))
    else:
        x, y1 = list(zip(*rows, (100, 1, 1)))

    # 보간
    ipo1 = spi.splrep(x, y1, k=k)
    iy1 = (int(n) for n in spi.splev(range(0, 101), ipo1))

    # 저장
    with open(f"../data/interpolate/{date}.csv", "w", encoding='utf-8', newline='') as f:
        wr = csv.writer(f)
        for row in zip(range(0, 101), iy1):
            wr.writerow(row)

    print(f">>> int: {time.time() - st} secs.")
    return


# 프리셋

def preset_ps():
    plt.figure(figsize=(16, 9), dpi=120)
    plt.xlabel("percent")
    plt.ylabel("score")
    plt.xticks(range(0, 101, 5))
    plt.yticks(range(0, 1050001, 50000))
    plt.ylim(-1000, 1100000)
    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.94, top=0.92)
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()


def preset_ds():
    dtmin = datetime.datetime(2018, 8, 25, hour=1)
    dtmax = dtmin + datetime.timedelta(days=28)
    dttk = [datetime.datetime(2018, 8, 26) + datetime.timedelta(days=n) for n in range(0, 27, 2)]
    dttkif = [f"{n.month:0>2}-{n.day:0>2}" for n in dttk]

    plt.figure(figsize=(16, 9), dpi=120)
    plt.xlabel("date")
    plt.ylabel("score")
    plt.xticks(dttk, dttkif)
    plt.yticks(range(0, 1050001, 50000))
    plt.xlim(dtmin, dtmax)
    plt.ylim(-1000, 1100000)
    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.88, top=0.92)
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()


# figure 에 받은 데이터로 그래프 그리기

def ps_scatter(date, **kwargs):
    with open(f"../data/raw/{date}.csv", 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        x, y = list(zip(*rdr))
        x = [int(n) for n in x]
        y = [int(n) for n in y]
    plt.scatter(x, y, **kwargs)
    # plt.show()


def ps_plot(date, annotate=[], **kwargs):
    with open(f"../data/interpolate/{date}.csv", 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        x, y = list(zip(*rdr))
        x = [int(n) for n in x]
        y = [int(n) for n in y]
    plt.plot(x, y, **kwargs)

    for i in annotate:
        plt.annotate(f"{i}%: 약 {y[i]}점", xy=(i + 2, y[i] + 5000))


# 별도 저장한 데이터 파일로부터 그래프 생성

def draw_per_score(file_name, gets=[0, 10, 30, 50]):
    st = time.time()
    fn = os.path.splitext(os.path.split(file_name)[1])[0]

    # 그래프 기초 설정
    plt.figure(figsize=(16, 9), dpi=120)
    plt.ylabel("score")
    plt.xlabel("percent")
    plt.yticks(range(0, 1000001, 50000))
    plt.ylim(-1000, 1010000)
    plt.xticks(range(0, 101, 5))
    plt.title(f"소녀전선 한국서버 <돌풍구출> {fn} 분포 그래프")

    # 점, 그래프 그리기
    # ps_scatter(fn, marker='s')
    ps_plot(fn, annotate=gets, label="예상 점수 그래프")
    # 가로선 그리기
    plt.axhline(270000, color='r', linewidth=1)
    plt.axhline(88888, color='r', linewidth=1)
    plt.text(100, 270000, '4더미 무전투 점수 최대치 (270,000점)', ha="right", va="bottom")
    plt.text(100, 88888, '폭죽요정 확정 지급 점수 (88,888점)', ha="right", va="bottom")

    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.94, top=0.92)
    plt.legend()
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()
    # plt.show()
    plt.savefig(f'../image/per_score/{fn}.png')
    print(f">>> {time.time() - st} secs.")
    return


def draw_date_score(dir_name, gets=[0, 10, 30, 50]):
    # dir_name에는 보간값 있는 json 폴더 이름 적기
    # WIP
    return


# 날짜별로 데이터 파일 만들기

def make_data(td=21):
    date_list = [datetime.date(2018, 9, 1) + datetime.timedelta(days=n) for n in range(0, td)]
    for date in date_list:
        interpolate(date)
        raw(date)


if __name__ == "__main__":
    st = time.time()
    make_data()

    for fn in glob.glob("../data/interpolate/*.csv"):
        draw_per_score(fn)
    print(f"total {time.time() - st} secs.")
