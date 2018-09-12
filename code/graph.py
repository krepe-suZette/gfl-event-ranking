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
import os
import glob

config = json.load(open("config.json", "r"))

conn = pymysql.connect(**config)
cur = conn.cursor()

matplotlib.rc("font", family="Noto Sans CJK KR", size=16)


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
        print(f"SKIP {date}")
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
    xy = dict(zip(range(0, 101), iy1))

    # 저장
    json.dump(xy, open(f"../json/{date}.json", "w"), indent=2)

    print(f">>> {time.time() - st} secs.")
    return


def draw_per_score(file_name, gets=[0, 10, 30, 50]):
    st = time.time()

    # 파일 열기
    xy = json.load(open(file_name, 'r'))
    fn = os.path.splitext(os.path.split(file_name)[1])[0]
    x, y = list(zip(*[(int(x), y) for x, y in xy.items()]))

    # 그래프 기초 설정
    plt.figure(figsize=(16, 9), dpi=120)
    plt.ylabel("score")
    plt.xlabel("percent")
    plt.yticks(range(0, 1000001, 50000))
    plt.ylim(-1000, 1010000)
    plt.xticks(range(0, 101, 5))
    plt.title(f"소녀전선 한국서버 <돌풍구출> {fn} 분포 그래프")

    # 점, 그래프 그리기
    # plt.scatter(x, y1, s=10, c='black', label='point')
    plt.plot(x, y, label='예상 점수 그래프')
    # 가로선 그리기
    plt.axhline(270000, color='r', linewidth=1)
    plt.axhline(88888, color='r', linewidth=1)
    plt.text(100, 270000, '4더미 무전투 점수 최대치 (270,000점)', ha="right", va="bottom")
    plt.text(100, 88888, '폭죽요정 확정 지급 점수 (88,888점)', ha="right", va="bottom")
    # 설명 그리기
    # plt.annotate(f"100등 : {int(xy[0])}점", xy=(0, int(xy[0])))
    for i in gets:
        plt.annotate(f"{i}%: 약 {int(xy[str(i)])}점", xy=(i + 2, int(xy[str(i)]) + 5000))

    plt.subplots_adjust(left=0.08, bottom=0.08, right=0.96, top=0.92)
    plt.legend()
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()
    print(f">>> {time.time() - st} secs.")
    # plt.show()
    plt.savefig(f'../image/per_score/{fn}.png')


def make_json(td=10):
    date_list = [datetime.date(2018, 9, 1) + datetime.timedelta(days=n) for n in range(0, td)]
    for date in date_list:
        interpolate(date)
        pass


if __name__ == "__main__":
    st = time.time()
    make_json(10)

    for fn in glob.glob("../json/*.json"):
        draw_per_score(fn)
    print(f"total {time.time() - st} secs.")
