import json
import math
import re
from datetime import datetime

import demoji
import pinyin
import psutil
import psycopg2
import pywinauto
from pywinauto import mouse
from pywinauto.application import Application

# User Settings
MAX_PYQ = 1000 # its fine the week limit thing will take care of this
SCRAPER_NAME = "Middleclicker"
REFRESH_DELAY = 1
UPDATE_FREQ = 1
SCROLL_DIST = 5
PROCESS_ALL = True

# TODO: I dont know if wechat has bot detection...
RANDOMIZED_SCROLL = False
RANDOMIZED_REFRESH_DELAY = False

HOSTNAME = ""
DATABASE = "Posts"
USERNAME = "scraper"
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


def calc_time(raw_date):
    now = int(math.floor(datetime.now().timestamp()))
    if "刚刚" in raw_date:
        return datetime.fromtimestamp(now).strftime("20%y-%m-%d")
    elif "分钟前" in raw_date:
        return datetime.fromtimestamp(now - int(raw_date[0:raw_date.index("分钟前")]) * 60).strftime("20%y-%m-%d")
    elif "小时前" in raw_date:
        return datetime.fromtimestamp(now - int(raw_date[0:raw_date.index("小时前")]) * 60 * 60).strftime("20%y-%m-%d")
    elif "天" in raw_date:
        if raw_date[0:raw_date.index("天")] == "昨":
            return datetime.fromtimestamp(now - 1 * 24 * 60 * 60).strftime("20%y-%m-%d")
        else:
            return datetime.fromtimestamp(now - int(raw_date[0:raw_date.index("天")]) * 24 * 60 * 60).strftime("20%y"
                                                                                                              "-%m-%d")
    else:
        return -1  # Stop the program when it reaches the start of the week. Accuracy too low.


# Not perfect, whatever.
def generate_uuid(post_content, post_author):
    total = 1
    res = post_content + post_author
    for i in pinyin.get(res, format="numerical"):
        total += ord(i) * 33
    return total


def process_raw_media(raw_media):
    """
    :param raw_media: Raw media "包含2张图片", "视频", "NA"
    :return: Number of media pieces
    """
    if "图" in raw_media:  # 包含1张图片
        return [int(s) for s in re.findall(r'-?\d+\.?\d*', raw_media)][0]
    elif "视频" in raw_media:  # 视频
        return 1
    else:  # NA
        return 0


def isEnglish(char):
    """
    :param char: Character
    :return: If the character is in the English alphabet
    """
    if re.match(r'^[a-zA-Z0-9]*$', char):
        return True
    return False


def isChinese(char):
    """
    :param char: Character
    :return: If the character is Chinese
    """
    if re.match(r'[\u4e00-\u9fff]+', char):
        return True
    return False


def processChineseEnglish(post_content):
    english_words = []
    chinese_words = []
    post_symbols = []
    word = ""
    symbol = ""
    for i in range(0, len(post_content)):
        char = post_content[i]
        if isEnglish(char) and symbol == "":
            word += char
        else:
            if word:
                english_words.append(word)
                word = ""
            if isChinese(char) and not symbol:  # I think there are chinese symbols?
                chinese_words.append(char)
            elif char == ']' and symbol:
                symbol += char
                post_symbols.append(symbol)
                symbol = ""
            elif char == '[' and not symbol:
                symbol += char
            elif symbol:
                symbol += char

    return english_words, chinese_words, post_symbols


def findUserNestedList(username, nested_list):
    if len(nested_list) == 0:
        return -1
    for i in range(0, len(nested_list)):
        if nested_list[i][0] == username:
            return i
    return -1


def generateFreqLikes(raw_likes):
    results = {}
    if len(raw_likes) == 0:
        return results
    raw_likes = raw_likes.split('，')  # What the fuck is this comma
    for like in raw_likes:
        results[like] = 1
    return results


def generateFreqComments(comments):
    results = {}
    if len(comments) == 0:
        return results
    comments = comments[1:len(comments) - 1]
    com_start = 0
    is_comment = False
    for i in range(0, len(comments)):
        if is_comment:
            if comments[i] == '"':
                is_comment = False
            elif comments[i + 1:i + 4] == " : ":  # To account for motherfuckers who use colons in their comments
                name = comments[com_start:i + 1].split("回复")[0]  # a 回复 b : efg or a : efg
                if name[len(name) - 1] == ' ':
                    name = name[:-1]
                # print(name)
                if name in results:
                    results[name] += 1
                else:
                    results[name] = 1
        else:
            if comments[i] == '"':
                is_comment = True
                com_start = i + 1
    return results


def updateFreq(prevDict, curDict):
    if not prevDict:
        return curDict
    if not curDict:
        return prevDict
    for e in curDict:  # Loops through key
        if e in prevDict:
            prevDict[e] += curDict[e]
        else:
            prevDict[e] = curDict[e]
    return prevDict


def updateActiveDates(prevDict, curDate):
    if not prevDict:
        return {curDate: 1}
    if curDate in prevDict:
        prevDict[curDate] += 1
    else:
        prevDict[curDate] = 1
    return prevDict


def initUser(name, total_posts, total_media, total_words, total_word_count_eng, total_word_count_chn, total_emoji_count,
             total_likes_recieved, total_comments_recieved, total_likes_given, total_comments_given, frequent_likes,
             frequent_likes_to, frequent_commenters, frequent_comments_to, active_dates):
    user = []
    user.append(name)
    user.append(total_posts)
    user.append(total_media)
    user.append(total_words)
    user.append(total_word_count_eng)
    user.append(total_word_count_chn)
    user.append(total_emoji_count)
    user.append(total_likes_recieved)
    user.append(total_comments_recieved)
    user.append(total_likes_given)
    user.append(total_comments_given)
    user.append(frequent_likes)
    user.append(frequent_likes_to)
    user.append(frequent_commenters)
    user.append(frequent_comments_to)
    user.append(active_dates)
    return user


def logScrapeStatistics(initialPostCount, endPostCount, initialUserCount, endUserCount, usersUpdated):
    print("-------------------")
    print(f"Initial Post Count: {initialPostCount}")
    print(f"End Post Count: {endPostCount}")
    print(f"Posts Contributed: {endPostCount - initialPostCount}")
    print(f"Initial User Count: {initialUserCount}")
    print(f"End User Count: {endUserCount}")
    print(f"Added Users: {endUserCount - initialUserCount}")
    print(f"Updated Users: {usersUpdated}")
    print("-------------------")


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

    # Create data storage tables
    build_posts_table = ''' CREATE TABLE IF NOT EXISTS posts
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
    build_user_table = ''' CREATE TABLE IF NOT EXISTS users
    (
        name                    text            PRIMARY KEY NOT NULL,
        total_posts             int             NOT NULL,
        total_media             int             NOT NULL,
        total_words             int             NOT NULL,
        total_word_count_eng    int             NOT NULL,
        total_word_count_chn    int             NOT NULL,
        total_emoji_count       int             NOT NULL,
        total_likes_recieved    int             NOT NULL,
        total_comments_recieved int             NOT NULL,
        total_likes_given       int             NOT NULL,
        total_comments_given    int             NOT NULL,
        frequent_likes          jsonb,
        frequent_likes_to       jsonb,
        frequent_commenters     jsonb,
        frequent_comments_to    jsonb,
        active_dates            jsonb,
        count                   int
    );'''
    posts_insert_script = ''' INSERT INTO posts 
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
    user_insert_script = ''' INSERT INTO users
    (
        name,
        total_posts,
        total_media,
        total_words,
        total_word_count_eng,
        total_word_count_chn,
        total_emoji_count,
        total_likes_recieved,
        total_comments_recieved,
        total_likes_given,
        total_comments_given,
        frequent_likes,
        frequent_likes_to,
        frequent_commenters,
        frequent_comments_to,
        active_dates,
        count
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);'''
    get_post_count = '''SELECT COUNT(*) FROM posts;'''
    get_posts = '''SELECT * FROM posts ORDER BY count ASC'''
    get_user_count = '''SELECT COUNT(*) FROM users;'''
    cur.execute(build_posts_table)
    cur.execute(build_user_table)
    cur.execute(get_post_count)
    initialPostCount = cur.fetchone()[0]

    all_pyq = []
    pyq_uuids = []
    pk_list = []
    has_updated = False
    last_content_cnt = 0

    # ------------Data Collection------------
    print("Collecting Data")

    # Data structure:
    # pyq_info:
    #   0: UUID
    #   1: Author
    #   2: Content
    #   3: Media Count
    #   4: Time
    #   5: Likes
    #   6: Comments
    #   7: Scraped Time
    #   8: Scraper Name

    while True:
        try:
            pyq_win = app['朋友圈']
        except:
            pass
        try:
            pyqs = pyq_win.wrapper_object().descendants(depth=4)
            for pyq in pyqs:
                try:
                    pyq_info = []
                    if pyq.friendly_class_name() == "ListItem":  # Post detected
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
                        if processed_time == -1:  # Posts are older than a week
                            raise GetOutOfLoop

                        uuid = generate_uuid(pyq_contents, author)

                        if uuid in pyq_uuids: # how the fuck do duplicates still get in???
                            last_content_cnt += 1
                            continue
                        pyq_uuids.append(pyq_contents)

                        pyq_info.append(uuid)
                        pyq_info.append(author)
                        pyq_info.append(pyq_contents)
                        pyq_info.append(process_raw_media(media))
                        pyq_info.append(processed_time)

                        try:
                            hasComment = False
                            hasLikes = False

                            edits = DFS(pyq, 6)
                            likes = []
                            pinglun = []
                            for e in edits:
                                if e.friendly_class_name() == "Edit":
                                    hasLikes = True

                                    likes = replace_emoji(e.window_text())
                                if e.friendly_class_name() == "ListBox":
                                    hasComment = True

                                    pinglun = []
                                    comments = e.children()
                                    for com in comments:
                                        if com.friendly_class_name() == "ListItem":
                                            pinglun.append(replace_emoji(com.window_text()))

                            if hasLikes:
                                pyq_info.append(likes)
                                pyq_info.append(len(likes.split('，')))
                            else:
                                pyq_info.append("NA")
                                pyq_info.append(0)
                            if hasComment:
                                pyq_info.append(pinglun)
                                pyq_info.append(len(pinglun))
                            else:
                                pyq_info.append("NA")
                                pyq_info.append(0)
                        except:
                            pass

                        pyq_info.append(datetime.now())
                        pyq_info.append(SCRAPER_NAME)

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
        if post_count < MAX_PYQ:
            pywinauto.mouse.scroll(wheel_dist=-SCROLL_DIST, coords=scroll) # Scroll down
        # elif post_count >= MAX_PYQ and not has_updated:
        #     print("Uploading Data")
        #     # TODO: Count returning weird numbers... i actually have no idea why this is happening
        #     # TODO: The amount of duplicates is insane...
        #     for e in all_pyq:
        #         cur.execute(get_post_count)
        #         total_posts = cur.fetchone()[0]
        #         try:
        #             if e[0] not in pk_list:
        #                 new_e = e
        #                 new_e.append(total_posts + 1)
        #                 if len(new_e) > 12:
        #                     print(new_e)
        #                     continue
        #                 cur.execute(posts_insert_script, new_e)
        #                 pk_list.append(new_e[0])
        #         except psycopg2.IntegrityError:  # Ignore duplicated key error
        #             conn.rollback()
        #         else:
        #             conn.commit()
        #     break
        else:
            break

        if post_count % UPDATE_FREQ == 0:
            for e in all_pyq[post_count - UPDATE_FREQ:post_count]:
                cur.execute(get_post_count)
                total_posts = cur.fetchone()[0]
                try:
                    if e[0] not in pk_list:
                        new_e = e
                        new_e.append(total_posts + 1)
                        if len(new_e) > 12:
                            print(new_e)
                            continue
                        cur.execute(posts_insert_script, new_e)
                        pk_list.append(new_e[0])
                except psycopg2.IntegrityError:  # Ignore duplicated key error
                    conn.rollback()
                else:
                    conn.commit()

    # ------------Data Processing------------
    print("Processing Data")
    if PROCESS_ALL:
        cur.execute(get_posts)
        all_db_posts = cur.fetchall()
        all_users = []
        for row in all_db_posts:
            name = row[1]
            content = row[2]
            english, chinese, symbols = processChineseEnglish(content)
            post_likes = generateFreqLikes(row[5])
            post_comments = generateFreqComments(row[5])
            userIndex = findUserNestedList(name, all_users)
            if userIndex == -1:
                total_posts = 1
                total_media = row[3]
                total_word_count_eng = len(english)
                total_word_count_chn = len(chinese)
                total_emoji_count = len(symbols)
                total_words = total_word_count_chn + total_word_count_chn + total_emoji_count  # Emoji counts cuz i say so
                total_likes_recieved = row[6]
                total_comments_recieved = row[8]
                total_likes_given = 0
                total_comments_given = 0
                frequent_likes = generateFreqLikes(row[5])
                frequent_likes_to = {}
                frequent_commenters = generateFreqComments(row[7])
                frequent_comments_to = {}
                active_dates = {row[4].strftime("20%y-%m-%d"): 1}
            else:
                # >= 11 jsonb
                user = all_users[userIndex]
                total_posts = user[1] + 1
                total_media = user[2] + row[3]
                total_word_count_eng = user[4] + len(english)
                total_word_count_chn = user[5] + len(chinese)
                total_emoji_count = user[6] + len(symbols)
                total_words = user[3] + len(english) + len(chinese) + len(symbols)
                total_likes_recieved = user[7] + row[6]
                total_comments_recieved = user[8] + row[8]
                total_likes_given = user[9]
                total_comments_given = user[10]
                frequent_likes = updateFreq(json.loads(user[11]), post_likes)
                frequent_likes_to = json.loads(user[12])
                frequent_commenters = updateFreq(json.loads(user[13]), post_comments)
                frequent_comments_to = json.loads(user[14])
                active_dates = updateActiveDates(json.loads(user[15]), row[4].strftime("20%y-%m-%d"))
                all_users.pop(userIndex)

            all_users.append(initUser(
                name=name,
                total_posts=total_posts,
                total_media=total_media,
                total_words=total_words,
                total_word_count_eng=total_word_count_eng,
                total_word_count_chn=total_word_count_chn,
                total_emoji_count=total_emoji_count,
                total_likes_recieved=total_likes_recieved,
                total_likes_given=total_likes_given,
                total_comments_recieved=total_comments_recieved,
                total_comments_given=total_comments_given,
                frequent_likes=json.dumps(frequent_likes),
                frequent_likes_to=json.dumps(frequent_likes_to),
                frequent_commenters=json.dumps(frequent_commenters),
                frequent_comments_to=json.dumps(frequent_comments_to),
                active_dates=json.dumps(active_dates)
            ))

            for u in post_likes:
                likerIndex = findUserNestedList(u, all_users)
                if likerIndex == -1:
                    all_users.append(initUser(
                        name=u,
                        total_posts=0,
                        total_media=0,
                        total_words=0,
                        total_word_count_eng=0,
                        total_word_count_chn=0,
                        total_emoji_count=0,
                        total_likes_recieved=0,
                        total_likes_given=1,
                        total_comments_recieved=0,
                        total_comments_given=0,
                        frequent_likes=json.dumps({}),
                        frequent_likes_to=json.dumps({name: 1}),
                        frequent_commenters=json.dumps({}),
                        frequent_comments_to=json.dumps({}),
                        active_dates=json.dumps({})
                    ))
                else:
                    all_users[likerIndex][8] += 1
                    updated_likers = json.loads(all_users[likerIndex][12])
                    if name in updated_likers:
                        updated_likers[name] += 1
                    else:
                        updated_likers[name] = 1
                    all_users[likerIndex][12] = json.dumps(updated_likers)
            for u in post_comments:
                commentorIndex = findUserNestedList(u, all_users)
                if commentorIndex == -1:
                    all_users.append(initUser(
                        name=u,
                        total_posts=0,
                        total_media=0,
                        total_words=0,
                        total_word_count_eng=0,
                        total_word_count_chn=0,
                        total_emoji_count=0,
                        total_likes_recieved=0,
                        total_likes_given=0,
                        total_comments_recieved=0,
                        total_comments_given=1,
                        frequent_likes=json.dumps({}),
                        frequent_likes_to=json.dumps({}),
                        frequent_commenters=json.dumps({}),
                        frequent_comments_to=json.dumps({name: 1}),
                        active_dates=json.dumps({})
                    ))
                else:
                    all_users[commentorIndex][9] += 1
                    updated_commenters = json.loads(all_users[commentorIndex][12])
                    if name in updated_commenters:
                        updated_commenters[name] += 1
                    else:
                        updated_commenters[name] = 1
                    all_users[commentorIndex][13] = json.dumps(updated_commenters)

        usersUpdated = 0
        print("Uploading User Data")
        for e in all_users:
            cur.execute(get_user_count)
            total_users = cur.fetchone()[0]
            initialUserCount = total_users
            try:
                # NOTE: USE SINGLE QUOTES
                new_e = e
                new_e.append(total_users + 1)
                # print(new_e)
                cur.execute(f'''SELECT EXISTS(SELECT 1 FROM users WHERE name='{new_e[0]}');''')
                if not cur.fetchone()[0]: # If user already exists
                    usersUpdated += 1
                    cur.execute(f'''DELETE FROM users WHERE name='{new_e[0]}';''')
                cur.execute(user_insert_script, new_e)
            except psycopg2.IntegrityError:  # Ignore duplicated key error
                conn.rollback()
            except Exception as exception:
                print(exception)
                pass
            else:
                conn.commit()

        cur.execute(get_post_count)
        endPostCount = cur.fetchone()[0]
        cur.execute(get_user_count)
        endUserCount = cur.fetchone()[0]
        logScrapeStatistics(initialPostCount, endPostCount, initialUserCount, endUserCount, usersUpdated)
except Exception as error:
    print(error)
    pass
finally:
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()
