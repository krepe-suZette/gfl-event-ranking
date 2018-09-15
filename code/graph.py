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


def data_in100():
    st = time.time()
    get_list = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    sql = (
        'SELECT date, score FROM ranking '
        'WHERE user_key = %s AND vaild > -1'
    )
    for rk in get_list:
        cur.execute(sql, 'inRanking{0:0>3}'.format(rk))
        rows = cur.fetchall()
        with open(f"../data/in100/{rk:0>3}.csv", "w", encoding='utf-8', newline='') as f:
            wr = csv.writer(f)
            for row in rows:
                wr.writerow(row)
    print(f">>> in100: {time.time() - st} secs.")
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


def ds_plot(gets=[0, 10, 30, 50], **kwargs):
    file_list = glob.glob("../data/interpolate/*.csv")
    data = dict([(n, []) for n in gets])
    for file_name in file_list:
        with open(file_name, 'r', encoding='utf-8') as f:
            rdr = csv.reader(f)
            date = os.path.splitext(os.path.split(file_name)[1])[0]
            x, y = list(zip(*rdr))
            x = [int(n) for n in x]
            y = [int(n) for n in y]
            for per in gets:
                data[per].append((datetime.datetime.strptime(date, "%Y-%m-%d"), y[per]))
    for per in gets:
        x, y = list(zip(*data[per]))
        plt.plot(x, y, label=f"{per}%", **kwargs)
        plt.text(x[-1], y[-1] + 5000, f"{y[-1]}", size=8, ha="center", va="bottom", alpha=0.5)


def ds_plot_in100(gets=[], **kwargs):
    for rank in gets:
        with open(f"../data/in100/{rank:0>3}.csv", 'r', encoding='utf-8') as f:
            rdr = csv.reader(f)
            x, y = list(zip(*rdr))
            x = [datetime.datetime.strptime(n, "%Y-%m-%d") for n in x]
            y = [int(n) for n in y]
            plt.plot(x, y, label=f"{rank}등", **kwargs)
            plt.text(x[-1], y[-1] + 5000, f"{y[-1]}", size=8, ha="center", va="bottom", alpha=0.5)


# 별도 저장한 데이터 파일로부터 그래프 생성

def draw_per_score(date, gets=[0, 10, 30, 50]):
    st = time.time()

    # 그래프 기초 설정
    preset_ps()
    plt.title(f"소녀전선 한국서버 <돌풍구출> {date} 분포 그래프")

    # 점, 그래프 그리기
    ps_scatter(date, marker='s', label="전체 표본")
    ps_plot(date, annotate=gets, label="예상 점수 그래프")
    # 가로선 그리기
    plt.axhline(270000, color='r', linewidth=1, alpha=0.5)
    plt.axhline(88888, color='r', linewidth=1, alpha=0.5)
    plt.text(100, 270000, '4더미 무전투 점수 최대치\n270,000점', ha="right", va="bottom", alpha=0.5, size=14)
    plt.text(100, 88888, '폭죽요정 확정 지급 점수\n88,888점', ha="right", va="bottom", alpha=0.5, size=14)

    # 범례
    plt.legend()
    plt.figtext(0.94, 0.04, "36베이스 카카오톡 봇으로 표본 조사중입니다. 많이 참여해주세요.", ha="right", va="top", alpha=0.5, size=12)

    # 저장
    # plt.show()
    plt.savefig(f'../image/per_score/{date}.png')
    print(f">>> {time.time() - st} secs.")
    return


def draw_date_score(gets=[0, 10, 30, 50]):
    # dir_name 에는 보간값 있는 폴더 이름 적기
    st = time.time()

    # 프리셋 적용
    preset_ds()
    plt.title(f"소녀전선 한국서버 <돌풍구출> 등급컷 변화 그래프")

    # 점, 그래프 그리기
    ds_plot_in100([1, 10, 50, 100], marker='o', mfc='w')
    ds_plot([10, 20, 30, 40, 50], marker='o', mfc='w')
    # 가로선 그리기
    plt.axhline(270000, color='r', linewidth=1, alpha=0.5)
    plt.axhline(88888, color='r', linewidth=1, alpha=0.5)
    plt.text(datetime.date(2018, 9, 21), 270000, '4더미 무전투 점수 최대치\n270,000점', ha="right", va="bottom", alpha=0.5, size=14)
    plt.text(datetime.date(2018, 9, 21), 88888, '폭죽요정 확정 지급 점수\n88,888점', ha="right", va="bottom", alpha=0.5, size=14)

    # 범례
    plt.legend(bbox_to_anchor=(1, 0.5), loc="center left")
    plt.figtext(0.88, 0.04, "36베이스 카카오톡 봇으로 표본 조사중입니다. 많이 참여해주세요.", ha="right", va="top", alpha=0.5, size=12)

    # 저장
    # plt.show()
    plt.savefig(f'../image/date_score/{datetime.date.today()}.png')
    print(f">>> {time.time() - st} secs.")
    return


# 날짜별로 데이터 파일 만들기

def make_data(td=21):
    date_list = [datetime.date(2018, 9, 1) + datetime.timedelta(days=n) for n in range(0, td)]
    for date in date_list:
        interpolate(date)
        raw(date)
    data_in100()


if __name__ == "__main__":
    st = time.time()
    make_data()

    for fn in glob.glob("../data/interpolate/*.csv"):
        date = os.path.splitext(os.path.split(fn)[1])[0]
        draw_per_score(date)
    draw_date_score()
    print(f"total {time.time() - st} secs.")
