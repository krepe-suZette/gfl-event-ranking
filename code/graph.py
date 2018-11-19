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
import shutil

config = json.load(open("config.json", "r"))

conn = pymysql.connect(**config["mysql"])
cur = conn.cursor()

matplotlib.rc("font", family="KoPubDotum", size=16)

event_name = config["event_name"]
Y_TICKS = 50000
Y_LIMIT = 700000
Y_LIMIT_ADV = 50000


# 작성시 끝부분에 \n 써주세요. 
PER_INFO = {
    10: "황금계 황금요정x1, 랜덤특성 황금요정x2\n",
    20: "황금요정x2\n",
    30: "",
    40: "9A-91 전장\n",
    50: "황금요정x1\n"
}


def __init__():
    os.makedirs(f'../data/{event_name}/raw', exist_ok=True)
    os.makedirs(f'../data/{event_name}/interpolate', exist_ok=True)
    os.makedirs(f'../data/{event_name}/in100', exist_ok=True)
    os.makedirs(f'../image/{event_name}/per_score', exist_ok=True)
    os.makedirs(f'../image/{event_name}/date_score', exist_ok=True)
    return


# 구글 설문으로 받아온거를 리스트 형태로 반환
# /data/이벤트명/raw_google/날짜.csv 형태로 저장 필요
# 파일이 없으면 빈 리스트 반환
def load_raws_from_google(date: datetime.date) -> list:
    if not os.path.exists(f"../data/{event_name}/raw_google/{date}.csv"):
        return []
    with open(f"../data/{event_name}/raw_google/{date}.csv", 'r', encoding='utf-8') as f:
        ret = []
        rdr = csv.reader(f)
        for num, row in enumerate(rdr):
            if num == 0:
                continue
            timestamp, score, per, rate, comment = row
            score, per = int(score), int(per)
            rate = int(rate) if rate else 0
            # if per == 0:
            #     continue
            ret.append((per, score))
    return ret


def write_csv(path, rows):
    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f)
        for row in rows:
            wr.writerow(row)
    return


# 정렬. [(per, score), (...), ...] 형태로 넣을것
# 이상한 값은 제거해서 돌려줌
def sort_rows(rows: list):
    sorted_rows = sorted(list(set(rows)), key=lambda x: x[0])
    sorted_rows = sorted(sorted_rows, reverse=True, key=lambda x: x[1])
    # except_set = set()
    sorted_rows_len = len(sorted_rows)
    except_list = []
    for num, row in enumerate(sorted_rows):
        if num == 0:
            if row[0] <= sorted_rows[num + 1][0]:
                continue
            else:
                except_list.append(row)
        elif num < sorted_rows_len - 1:
            # 내 양쪽 값이 같은지 확인
            if sorted_rows[num - 1][0] <= sorted_rows[num + 1][0]:
                # 내 값이 양쪽 사이에 있는지 확인
                if sorted_rows[num - 1][0] <= row[0] <= sorted_rows[num + 1][0]:
                    # 사이에 있는게 맞다면 통과
                    continue
                else:
                    # 사이에 없다면 자기 자신을 문제목록에 추가
                    except_list.append(row)
            # 양쪽부터 문제가 있는 경우
            else:
                if sorted_rows[num - 1][0] > row[0]:
                    except_list.append(row)
                else:
                    pass
        else:
            if sorted_rows[num - 1][0] <= row[0]:
                continue
            else:
                except_list.append(row)
    for row in except_list:
        sorted_rows.remove(row)
    return sorted_rows


# DB로부터 데이터 가공 및 저장

def raw(date):
    sql = (
        "SELECT per, score FROM ranking "
        "WHERE event_name = %s AND date = %s AND vaild > -1 "
        "ORDER BY score DESC"
    )
    cur.execute(sql, (event_name, date))
    rows = list(cur.fetchall())
    rows += load_raws_from_google(date)
    rows = sort_rows(rows)
    if len(rows) == 0:
        print(f">>> raw: SKIP {date}")
        return
    write_csv(f'../data/{event_name}/raw/{date}.csv', rows)
    print(f">>> raw: {date} : {len(rows)}")
    return


def interpolate(date, gets=[]):
    st = time.time()
    if not os.path.exists(f"../data/{event_name}/raw/{date}.csv"):
        print(f">>> int: SKIP {date}")
        return
    with open(f"../data/{event_name}/raw/{date}.csv", 'r', encoding='utf-8') as f:
        rows_dict = {}
        rdr = csv.reader(f)
        for row in rdr:
            per, score = int(row[0]), int(row[1])
            if per not in rows_dict or score < rows_dict.get(per, 0):
                rows_dict[per] = score
    rows = sorted([(n, m) for n, m in rows_dict.items()])
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
    with open(f"../data/{event_name}/interpolate/{date}.csv", "w", encoding='utf-8', newline='') as f:
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
        'WHERE event_name = %s AND user_key = %s AND vaild > -1'
    )
    for rk in get_list:
        cur.execute(sql, (event_name, 'inRanking{0:0>3}'.format(rk)))
        rows = cur.fetchall()
        if len(rows) == 0:
            print(f">>> in100: SKIP")
            return
        with open(f"../data/{event_name}/in100/{rk:0>3}.csv", "w", encoding='utf-8', newline='') as f:
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
    plt.yticks(range(0, Y_LIMIT + 1, Y_TICKS))
    plt.ylim(-1000, Y_LIMIT + Y_LIMIT_ADV)
    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.94, top=0.92)
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()


def preset_ds():
    dtmin = datetime.datetime(2018, 11, 16, hour=1)
    dtmax = dtmin + datetime.timedelta(days=16)
    dttk = [datetime.datetime(2018, 11, 17) + datetime.timedelta(days=n) for n in range(0, 15, 1)]
    dttkif = [f"{n.month:0>2}-{n.day:0>2}" for n in dttk]

    plt.figure(figsize=(16, 9), dpi=120)
    plt.xlabel("date")
    plt.ylabel("score")
    plt.xticks(dttk, dttkif)
    plt.yticks(range(0, Y_LIMIT + 1, Y_TICKS))
    plt.xlim(dtmin, dtmax)
    plt.ylim(-1000, Y_LIMIT + Y_LIMIT_ADV)
    plt.subplots_adjust(left=0.10, bottom=0.08, right=0.88, top=0.92)
    plt.grid(True, which='major', linestyle='-', linewidth='1', alpha=0.5)
    plt.grid(True, which='minor', linestyle='-', linewidth='0.5', alpha=0.1)
    plt.minorticks_on()


# 가로줄 그리는 함수
def draw_axhline(line, text):
    plt.axhline(line, color='r', linewidth=1, alpha=0.5)
    plt.text(100, line, text, ha="right", va="bottom", alpha=0.5, size=14)
    return


def draw_axvspan(rows, score_min, score_max, **kwargs):
    range_list = []
    for row in rows:
        if score_min <= row[1] <= score_max:
            range_list.append(row[0])
    range_list.sort()
    if len(range_list) > 2:
        plt.axvspan(range_list[0], range_list[-1], **kwargs)


# figure 에 받은 데이터로 그래프 그리기

def ps_scatter(date, **kwargs):
    with open(f"../data/{event_name}/raw/{date}.csv", 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        x, y = list(zip(*rdr))
        x = [int(n) for n in x]
        y = [int(n) for n in y]
    plt.scatter(x, y, **kwargs)
    draw_axvspan(zip(x, y), 459, 459, color='gray', alpha=0.2)
    # plt.show()


def ps_plot(date, annotate=[], **kwargs):
    with open(f"../data/{event_name}/interpolate/{date}.csv", 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        x, y = list(zip(*rdr))
        x = [int(n) for n in x]
        y = [int(n) for n in y]
    plt.plot(x, y, **kwargs)

    for i in annotate:
        if i == 0:
            text = f"{y[i]}점\n100등"
        else:
            text = f"{PER_INFO.get(i, '')}{y[i]}점\n{i}%"
        plt.annotate(text, xy=(i + 2, y[i] + 5000))


def ds_plot(gets=[0, 10, 30, 50], **kwargs):
    file_list = glob.glob(f"../data/{event_name}/interpolate/*.csv")
    data = dict([(n, []) for n in gets])
    for file_name in sorted(file_list):
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
        with open(f"../data/{event_name}/in100/{rank:0>3}.csv", 'r', encoding='utf-8') as f:
            rdr = csv.reader(f)
            x, y = list(zip(*rdr))
            x = [datetime.datetime.strptime(n, "%Y-%m-%d") for n in x]
            y = [int(n) for n in y]
            plt.plot(x, y, label=f"{rank}등", **kwargs)
            plt.text(x[-1], y[-1] + 5000, f"{y[-1]}", size=8, ha="center", va="bottom", alpha=0.5)


# 별도 저장한 데이터 파일로부터 그래프 생성

def draw_per_score(date, gets=[0, 10, 20, 40, 50]):
    st = time.time()

    # 그래프 기초 설정
    preset_ps()
    plt.title(f"소녀전선 한국서버 <허수미궁+> {date} 분포 그래프")

    # 점, 그래프 그리기
    ps_scatter(date, marker='s', label="전체 표본")
    ps_plot(date, annotate=gets, label="예상 점수 그래프")
    # 가로선 그리기
    draw_axhline(200000, '황금요정 확정지급 점수\n200,000점')
    draw_axhline(400000, '최고등급 보상 확정지급 점수\n400,000점')

    # 범례
    plt.legend(loc=1)
    plt.figtext(0.10, 0.04, "36베이스 - 소녀전선 데이터베이스 https://girlsfrontline.kr", ha="left", va="top", alpha=0.5, size=12)
    plt.figtext(0.94, 0.04, "구글 설문 및 36베이스 카카오톡 봇으로 표본 조사중입니다. 많이 참여해주세요.", ha="right", va="top", alpha=0.5, size=12)

    # 저장
    # plt.show()
    plt.savefig(f'../image/{event_name}/per_score/{date}.png')
    print(f">>> {time.time() - st} secs.")
    return


def draw_date_score():
    # dir_name 에는 보간값 있는 폴더 이름 적기
    st = time.time()

    # 프리셋 적용
    preset_ds()
    plt.title(f"소녀전선 한국서버 <허수미궁+> 등급컷 변화 그래프")

    # 점, 그래프 그리기
    ds_plot_in100([1, 10, 50, 100], marker='o', mfc='w')
    ds_plot([5, 10, 15, 20, 30, 40, 50], marker='o', mfc='w')
    # 가로선 그리기
    draw_axhline(200000, '황금요정 확정지급 점수\n200,000점')
    draw_axhline(400000, '최고등급 보상 확정지급 점수\n400,000점')

    # 범례
    plt.legend(bbox_to_anchor=(1, 0.5), loc="center left")
    plt.figtext(0.10, 0.04, "36베이스 - 소녀전선 데이터베이스 https://girlsfrontline.kr", ha="left", va="top", alpha=0.5, size=12)
    plt.figtext(0.88, 0.04, "구글 설문 및 36베이스 카카오톡 봇으로 표본 조사중입니다. 많이 참여해주세요.", ha="right", va="top", alpha=0.5, size=12)

    # 저장
    # plt.show()
    plt.savefig(f'../image/{event_name}/date_score/{datetime.date.today()}.png')
    shutil.copy(f'../image/{event_name}/date_score/{datetime.date.today()}.png', "../docs/recent.png")
    print(f">>> {time.time() - st} secs.")
    return


# 날짜별로 데이터 파일 만들기

def make_data(td=15):
    date_list = [datetime.date(2018, 11, 17) + datetime.timedelta(days=n) for n in range(0, td)]
    for date in date_list:
        raw(date)
        interpolate(date)
    data_in100()


if __name__ == "__main__":
    # __init__()
    st = time.time()
    make_data(3)

    for fn in glob.glob("../data/kr_deepdive/interpolate/*.csv"):
        date = os.path.splitext(os.path.split(fn)[1])[0]
        draw_per_score(date)
    draw_date_score()
    print(f"total {time.time() - st} secs.")
