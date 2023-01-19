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
MAX_PYQ = 1
SCRAPER_NAME = "Middleclicker"

HOSTNAME = ""
DATABASE = "Posts"
USERNAME = "middleclicker"
PWD = ""
PORT_ID = 5432
conn = None
cur = None


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
    # NOTE: the number of seconds since 1970-01-01
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


# Hook into WeChat's process
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

all_pyq = []
all_pyq_contents = set()

last_content_cnt = 0
has_updated = False

start_date = datetime.now().strftime("20%y-%m-%d")

class GetOutOfLoop( Exception ):
    pass

try:
    conn = psycopg2.connect(host=HOSTNAME, dbname=DATABASE, user=USERNAME, port=PORT_ID)
    cur = conn.cursor()

    build_table = ''' CREATE TABLE IF NOT EXISTS posts
    (
        uuid        int PRIMARY KEY NOT NULL,
        name        text NOT NULL,
        content     text,
        media       int,
        date        date,
        likes       text,
        like_count  int NOT NULL,
        comments    text,
        comment_count int NOT NULL,
        scraped_date timestamp NOT NULL,
        contributor  text NOT NULL,
        count       int   
    );'''
    insert_script = "INSERT INTO posts (uuid, name, content, media, date, likes, like_count, comments, comment_count, scraped_date, contributor, count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"

    cur.execute(build_table)

    sql = 'SELECT COUNT(*) FROM posts;'
    data = []
    cur.execute(sql, data)
    results = cur.fetchone()
    total_posts = results[0]

    print("Collecting Data")
    while True:
        # 如果按Esc关闭朋友圈页面，这里就会崩掉然后结束
        try:
            pyq_win = app['朋友圈']
        except:
            break
        try:
            pyqs = pyq_win.wrapper_object().descendants(depth=4)
            for x in pyqs:
                try:
                    pyq_info = []
                    classname = x.friendly_class_name()
                    if (classname == "ListItem"):
                        # 这是一条朋友圈
                        processed_pyq = replace_emoji(x.window_text()).split('\n')
                        author = processed_pyq[0]
                        pyq_contents = "".join(processed_pyq[1:len(processed_pyq) - 3])
                        # 这他妈是啥。。。
                        if "包含" in processed_pyq[1] or "视频" in processed_pyq[1]:  # 没有文案，只有图片 or 视频
                            media = processed_pyq[1]
                            time = processed_pyq[2]
                            pyq_contents = "NA"
                        elif "包含" in processed_pyq[len(processed_pyq) - 3] or "视频" in processed_pyq[
                            len(processed_pyq) - 3]:
                            media = processed_pyq[len(processed_pyq) - 3]
                            time = processed_pyq[len(processed_pyq) - 2]
                        elif processed_pyq[len(processed_pyq) - 2] == "Tape":
                            media = "Tape"
                            time = processed_pyq[len(processed_pyq) - 3]
                        elif "包含" in processed_pyq[len(processed_pyq) - 4] or "视频" in processed_pyq[
                            len(processed_pyq) - 4]:  # 有文案，图片，地点
                            media = processed_pyq[len(processed_pyq) - 4]
                            time = processed_pyq[len(processed_pyq) - 2]
                            pyq_contents = "".join(processed_pyq[1:len(processed_pyq) - 4])
                        else:
                            media = "NA"
                            time = processed_pyq[len(processed_pyq) - 2]

                        if (pyq_contents in all_pyq_contents):
                            # 已经爬过这一条了
                            last_content_cnt += 1
                            continue
                        last_content_cnt = 0
                        all_pyq_contents.add(pyq_contents)

                        processed_time = calc_time(time)
                        if processed_time == -1:
                            raise GetOutOfLoop

                        print(pyq_contents, media, processed_time)

                        uuid_time = processed_time.split('-')[0] + ":" + processed_time.split('-')[1] + ":" + \
                                    processed_time.split('-')[2]

                        pyq_info.append(generate_uuid(pyq_contents, author, uuid_time))
                        pyq_info.append(author)
                        pyq_info.append(pyq_contents)
                        pyq_info.append(process_raw_media(media))
                        pyq_info.append(processed_time)

                        try:
                            hasComment = False
                            hasLikes = False
                            edits = DFS(x, 6)
                            for e in edits:
                                if (e.friendly_class_name() == "Edit"):
                                    hasLikes = True
                                    likes = replace_emoji(e.window_text())
                                if (e.friendly_class_name() == "ListBox"):
                                    pinglun = []
                                    hasComment = True
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
                        pyq_info.append(total_posts) # Dont question it, idk lol

                        all_pyq.append(pyq_info)
                except Exception as e:
                    print(e)
                    pass
        except GetOutOfLoop:
            pass
        except Exception:
            pass

        if (len(all_pyq) < MAX_PYQ):
            # 向下滚动
            cords = pyq_win.rectangle()
            pywinauto.mouse.scroll(wheel_dist=-5, coords=(cords.left + 10, cords.bottom - 10))
        elif len(all_pyq) == MAX_PYQ and not has_updated:
            print("Finished Data Collection, entering monitoring mode")
            for e in all_pyq[len(all_pyq) - 10:len(all_pyq)]:
                try:
                    cur.execute(insert_script, e)
                except psycopg2.IntegrityError:
                    conn.rollback()
                else:
                    conn.commit()
        else:
            t.sleep(1)
            cords = pyq_win.rectangle()
            mouse.click(coords=(cords.left + 50, cords.top + 10))  # Refresh
        if len(all_pyq) % 10 == 0:
            for e in all_pyq[len(all_pyq)-10:len(all_pyq)]:
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

# CSV Mode
# unsuccessful = []
# filename = start_time + ".csv"
# with open(filename, 'w', newline='') as file:
#    header = ['uuid', 'author', 'content', 'media', 'time', 'likes', 'comments', 'scraped_date', 'contributor']
#    writer = csv.DictWriter(file, fieldnames = header)
#    writer.writeheader()
#    for pyq in all_pyq:
#        try:
#            writer.writerow(pyq)
#        except:
#            unsuccessful.append(pyq)

# if len(unsuccessful) > 0:
#    print("------------Unsuccessful Items------------")
#    for item in unsuccessful:
#        print(item)
# else:
#    print("------------Successfully wrote all data into file------------")

# print("Merging CSVs...")
# merge_csv.merge("combined.csv", filename)
