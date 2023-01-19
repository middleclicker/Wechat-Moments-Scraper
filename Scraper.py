import math
import re
import sys
import time as t
from datetime import datetime

import demoji
import pinyin
import psutil
import psycopg2
import pywinauto
from pywinauto import mouse
from pywinauto.application import Application

# User Settings
MAX_PYQ = 50
SCRAPER_NAME = "Middleclicker"
REFRESH_DELAY = 1
UPDATE_FREQ = 5
SCROLL_DIST = 5

# TODO: I dont know if wechat has bot detection...
RANDOMIZED_SCROLL = False
RANDOMIZED_REFRESH_DELAY = False

HOSTNAME = ""
DATABASE = "Posts"
USERNAME = ""
PWD = ""
PORT_ID = 5432
conn = None
cur = None


# Helper Classes
class GetOutOfLoop(Exception):
    pass


# Helper Functions
def DFS(win, layers):
    children = []
    last_layer = [win]
    new_layer = []
    for cnt in range(layers):
        for c in last_layer:
            gs = c.children()
            for g in gs:
                new_layer.append(g)
        for x in new_layer:
            children.append(x)
        last_layer = new_layer
        new_layer = []
    return children


def replace_emoji(text):
    dem = demoji.findall(text)
    for item in dem.items():
        text = text.replace(item[0], "[" + item[1] + "]")
    return text


def calc_time(input):
    now = int(math.floor(datetime.now().timestamp()))
    if "刚刚" in input:
        return datetime.fromtimestamp(now).strftime("20%y-%m-%d")
    elif "分钟前" in input:
        return datetime.fromtimestamp(now - int(input[0:input.index("分钟前")]) * 60).strftime("20%y-%m-%d")
    elif "小时前" in input:
        return datetime.fromtimestamp(now - int(input[0:input.index("小时前")]) * 60 * 60).strftime("20%y-%m-%d")
    elif "天" in input:
        if input[0:input.index("天")] == "昨":
            return datetime.fromtimestamp(now - 1 * 24 * 60 * 60).strftime("20%y-%m-%d")
        else:
            return datetime.fromtimestamp(now - int(input[0:input.index("天")]) * 24 * 60 * 60).strftime("20%y-%m-%d")
    else:
        return -1  # Stop the program when it reaches the start of the week. Accuracy too low.


# Not perfect, whatever.
def generate_uuid(content, author, date):
    total = 1
    res = content + author + date
    for i in pinyin.get(res, format="numerical"):
        total += ord(i) * 33
    return total


def process_raw_media(raw_media):
    '''
    :param raw_media: Raw media "包含2张图片", "视频", "NA"
    :return: Number of media pieces
    '''
    if "图" in raw_media:  # 包含1张图片
        return [int(s) for s in re.findall(r'-?\d+\.?\d*', raw_media)][0]
    elif "视频" in raw_media:  # 视频
        return 1
    else:  # NA
        return 0


try:
    # ------------Wechat PID Hook------------
    PID = 0
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name'])
        except psutil.NoSuchProcess:
            pass
        else:
            if 'WeChat.exe' == pinfo['name']:
                PID = pinfo['pid']

    app = Application(backend='uia').connect(process=PID)

    # ------------Database------------
    conn = psycopg2.connect(host=HOSTNAME, dbname=DATABASE, user=USERNAME, port=PORT_ID)
    cur = conn.cursor()

    # Create data storage table
    build_table = ''' CREATE TABLE IF NOT EXISTS posts
    (
        uuid            int             PRIMARY KEY NOT NULL,
        name            text            NOT NULL,
        content         text,
        media           int,
        date            date,
        likes           text,
        like_count      int             NOT NULL,
        comments        text,
        comment_count   int             NOT NULL,
        scraped_date    timestamptz     NOT NULL,
        contributor     text            NOT NULL,
        count           int   
    );'''
    insert_script = ''' INSERT INTO posts 
    (
        uuid, 
        name, 
        content, 
        media, 
        date, 
        likes, 
        like_count, 
        comments, 
        comment_count, 
        scraped_date, 
        contributor, 
        count
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);'''
    cur.execute(build_table)

    # Get number of posts
    data = []
    cur.execute('SELECT COUNT(*) FROM posts;', data)
    results = cur.fetchone()
    total_posts = results[0]

    all_pyq = []
    pyq_uuids = set()

    has_updated = False
    last_content_cnt = 0

    # ------------Data Collection------------
    print("Collecting Data")
    while True:
        try:
            pyq_win = app['朋友圈']
        except:
            break
        try:
            pyqs = pyq_win.wrapper_object().descendants(depth=4)
            for pyq in pyqs:
                try:
                    pyq_info = []
                    if (pyq.friendly_class_name() == "ListItem"):  # Post detected
                        processed_pyq = replace_emoji(pyq.window_text()).split('\n')

                        lineCount = len(processed_pyq)

                        author = processed_pyq[0]
                        pyq_contents = "".join(processed_pyq[1:lineCount - 3])

                        if "包含" in processed_pyq[lineCount - 3] or "视频" in processed_pyq[lineCount - 3]:
                            # 文案：      有/无
                            # 图片 / 视频：有
                            # 地点：      无
                            # 嵌入链接：   无

                            # 文案：有
                            # ['middleclicker', 'abc', 'efg', '包含2张图片 / 视频', '1分钟前', '']
                            # ['middleclicker', 'abc', '包含2张图片 / 视频', '1分钟前', '']
                            media = processed_pyq[lineCount - 3]
                            time = processed_pyq[lineCount - 2]

                            # 文案：无
                            # ['middleclicker', '包含2张图片 / 视频', '1分钟前', '']
                            if "包含" in processed_pyq[1] or "视频" in processed_pyq[1]:
                                pyq_contents = "NA"
                        elif "包含" in processed_pyq[lineCount - 4] or "视频" in processed_pyq[lineCount - 4]:
                            # 文案：      有/无
                            # 图片 / 视频：有
                            # 地点：      有
                            # 嵌入链接：   无

                            # 文案：有
                            # ['middleclicker', 'abc', 'efg', '包含2张图片 / 视频', '深圳国际交流监狱', '1分钟前', '']
                            media = processed_pyq[lineCount - 4]
                            time = processed_pyq[lineCount - 2]

                            # 文案：无
                            # ['middleclicker', '包含2张图片 / 视频', '深圳国际交流监狱', '1分钟前', '']
                            if "包含" in processed_pyq[1] or "视频" in processed_pyq[1]:
                                pyq_contents = "NA"
                        elif "前" in processed_pyq[lineCount - 3]:
                            # 文案：      有/无
                            # 图片 / 视频：无
                            # 地点：      有/无，无所谓，还没记录地点
                            # 嵌入链接：   有

                            # 文案：有
                            # ['middleclicker', 'abc', '来点问题！', '1分钟前', 'Tape / QQMusic / Whatever', '']
                            # ['middleclicker', 'abc', '来点问题！', '深圳国际交流监狱', '1分钟前', 'Tape / QQMusic / Whatever', '']
                            media = processed_pyq[lineCount - 2]
                            time = processed_pyq[lineCount - 3]

                            # 文案：无
                            # ['middleclicker', '来点问题！', '1分钟前', 'Tape / QQ Music / Whatever', '']
                            if "包含" in processed_pyq[2] or "视频" in processed_pyq[2]:
                                pyq_contents = "NA"
                        else:
                            # 文案：      有
                            # 图片 / 视频：无
                            # 地点：      有/无
                            # 嵌入链接：   无
                            # ['middleclicker', 'abc', 'efg', '1分钟前', '']
                            media = "NA"
                            time = processed_pyq[lineCount - 2]

                        processed_time = calc_time(time)
                        if processed_time == -1:
                            raise GetOutOfLoop

                        uuid_time = processed_time.split('-')[0] + ":" + processed_time.split('-')[1] + ":" + \
                                    processed_time.split('-')[2]
                        uuid = generate_uuid(pyq_contents, author, uuid_time)

                        if (uuid in pyq_uuids):
                            last_content_cnt += 1
                            continue
                        pyq_uuids.add(pyq_contents)

                        pyq_info.append(uuid)
                        pyq_info.append(author)
                        pyq_info.append(pyq_contents)
                        pyq_info.append(process_raw_media(media))
                        pyq_info.append(processed_time)

                        try:
                            hasComment = False
                            hasLikes = False

                            edits = DFS(pyq, 6)
                            for e in edits:
                                if (e.friendly_class_name() == "Edit"):
                                    hasLikes = True

                                    likes = replace_emoji(e.window_text())
                                if (e.friendly_class_name() == "ListBox"):
                                    hasComment = True

                                    pinglun = []
                                    comments = e.children()
                                    for com in comments:
                                        if (com.friendly_class_name() == "ListItem"):
                                            pinglun.append(replace_emoji(com.window_text()))

                            if not hasLikes:
                                pyq_info.append("NA")
                                pyq_info.append(0)
                            else:
                                pyq_info.append(likes)
                                pyq_info.append(len(likes.split('，')))
                            if not hasComment:
                                pyq_info.append("NA")
                                pyq_info.append(0)
                            else:
                                pyq_info.append(pinglun)
                                pyq_info.append(len(pinglun))
                        except:
                            pass

                        pyq_info.append(datetime.now())
                        pyq_info.append(SCRAPER_NAME)

                        total_posts += 1
                        pyq_info.append(total_posts)  # Until I figure out how to use grafana properly

                        all_pyq.append(pyq_info)
                except Exception as e:
                    print(e)
                    pass
        except GetOutOfLoop:
            pass
        except Exception:
            pass

        post_count = len(all_pyq)
        refresh = (pyq_win.rectangle().left + 50, pyq_win.rectangle().top + 10)
        scroll = (pyq_win.rectangle().left + 10, pyq_win.rectangle().bottom - 10)
        if post_count < MAX_PYQ:  # Scroll Down
            pywinauto.mouse.scroll(wheel_dist=-SCROLL_DIST, coords=scroll)
        elif post_count == MAX_PYQ and not has_updated:
            print("Finished Data Collection, entering monitoring mode")
            for e in all_pyq[post_count - UPDATE_FREQ:post_count]:
                try:
                    cur.execute(insert_script, e)
                except psycopg2.IntegrityError:  # Ignore duplicated key error
                    conn.rollback()
                else:
                    conn.commit()
        else:
            # Active monitoring mode
            t.sleep(REFRESH_DELAY)
            mouse.click(coords=refresh)  # Refresh
        if post_count % UPDATE_FREQ == 0:
            for e in all_pyq[post_count - 10:post_count]:
                try:
                    cur.execute(insert_script, e)
                except psycopg2.IntegrityError:
                    conn.rollback()
                else:
                    conn.commit()
except Exception as error:
    print(error)
finally:
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()
