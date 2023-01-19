import csv
import json
import re

fileName = "combined.csv"


def findUser(to_search, phrase, keyword):
    '''
    :param to_search: List with dictionary to search
    :param phrase: Phrase to search for
    :param keyword: Keyword to search for
    :return: Index of phrase in list
    '''
    for i in range(0, len(to_search)):
        if phrase == to_search[i][keyword]:
            return i
    return -1


def isEnglish(char):
    '''
    :param char: Character
    :return: If the character is in the English alphabet
    '''
    if re.match(r'^[a-zA-Z0-9]*$', char):
        return True
    return False


def isChinese(char):
    '''
    :param char: Character
    :return: If the character is Chinese
    '''
    if re.match(r'[\u4e00-\u9fff]+', char):
        return True
    return False


def getRawData(row):
    '''
    :param row: Retrieve raw data from CSV row
    :return: UUID, Username, Post content, Post media, Post time, Post likes, Post comments
    '''
    uuid = row[0]
    user = row[1]
    content = row[2]
    raw_media = row[3]
    raw_time = row[4]
    likes = row[5]
    comments = processComments(row[6])
    raw_scraped_date = row[7].split(':')
    scraped_date = raw_scraped_date[0] + "/" + raw_scraped_date[1] + "/" + raw_scraped_date[2]
    contributor = row[8]

    return uuid, user, content, raw_media, raw_time, likes, comments, scraped_date, contributor


def getLengthData(processed_likes, comments, content):
    if content == "NA":
        chinese_characters = []
        english_characters = []
        emojis = []
    else:
        english_characters, chinese_characters, emojis = processChineseEnglish(content)

    post_likes = len(processed_likes)
    post_comments = len(comments)
    chinese_length = len(chinese_characters)
    english_length = len(english_characters)
    emoji_length = len(emojis)
    content_length = chinese_length + english_length + emoji_length  # Switch to len(content) for more accurate reading

    return post_likes, post_comments, chinese_length, english_length, emoji_length, content_length


def processChineseEnglish(content):
    english = []
    chinese = []
    symbols = []
    word = ""
    symbol = ""
    for i in range(0, len(content)):
        char = content[i]
        if isEnglish(char) and symbol == "":
            word += char
        else:
            if word:
                english.append(word)
                word = ""
            if isChinese(char) and not symbol:  # I think there are chinese symbols?
                chinese.append(char)
            elif char == ']' and symbol:
                symbol += char
                symbols.append(symbol)
                symbol = ""
            elif char == '[' and not symbol:
                symbol += char
            elif symbol:
                symbol += char

    return english, chinese, symbols


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


def process_time(raw_time):
    '''
    :param raw_time: Raw time "sec:min:hour:day:month:year"
    :return: date "day/month/year" and time if available
    '''
    split_time = raw_time.split(':')
    date = split_time[3] + "/" + split_time[4] + "/" + split_time[5]
    if split_time[1] != "NA":
        time = split_time[2] + ":" + split_time[1]  # hour : minute (just for the sake of graphing)
    else:
        time = "NA"

    return date, time


def processComments(comments):
    '''
    :param comments: Raw comments ['abc', 'efd', ...]
    :return: Processed comment list
    '''
    raw_comments = comments[1:len(comments) - 1]  # Removed brackets
    new_comment = False
    processed_comments = []
    start = 0
    for i in range(0, len(raw_comments)):
        if raw_comments[i] == "'":
            if new_comment == False:
                start = i + 1
                new_comment = True
                # print(f"Set start variable to position {start} with next char {raw_comments[i+1]}")
            else:
                if i == len(raw_comments) - 1:
                    processed_comments.append(raw_comments[start:i])
                    return processed_comments
                if raw_comments[i + 1] == ',':
                    processed_comments.append(raw_comments[start:i])
                    # print(raw_comments[start:i])
                    new_comment = False

    return processed_comments


def initPost(uuid, user, date, time, content, media, likes, comments, post_likes, post_comments):
    postDickshonary = {}
    postDickshonary["UUID"] = uuid
    postDickshonary["User"] = user
    postDickshonary["Date"] = date
    postDickshonary["Time"] = time
    postDickshonary["Content"] = content
    postDickshonary["Media"] = media
    postDickshonary["Likes"] = likes
    postDickshonary["Comments"] = comments
    postDickshonary["Like Count"] = post_likes
    postDickshonary["Comment Count"] = post_comments
    return postDickshonary


def initUser(user, post_likes, post_comments, content_length, chinese_length, english_length, emoji_length):
    dickshonary = {}
    dickshonary["User"] = user
    dickshonary["Total Posts"] = 1
    dickshonary["Total Likes"] = post_likes
    dickshonary["Total Comments"] = post_comments
    dickshonary["Total Likes Given"] = 0
    dickshonary["Total Comments Given"] = 0
    dickshonary["Total Content Length"] = content_length
    dickshonary["Total Media"] = media
    dickshonary["Chinese Content Length"] = chinese_length
    dickshonary["English Content Length"] = english_length
    dickshonary["Emoji Content Length"] = emoji_length
    dickshonary["Posts"] = []
    return dickshonary


def initGlobal():
    overview_dick = {}
    overview_dick["Global Posts"] = 0
    overview_dick["Global Likes"] = 0
    overview_dick["Global Comments"] = 0
    overview_dick["Global Content Length"] = 0
    overview_dick["Global Media"] = 0
    overview_dick["Global Chinese Content Length"] = 0
    overview_dick["Global English Content Length"] = 0
    overview_dick["Global Emoji Content Length"] = 0
    return overview_dick


def updateUser(userTally, index, post_likes, post_comments, content_length, media, chinese_length,
               english_length, emoji_length, postDictionary, likes, comments):
    userTally[index]["Total Posts"] += 1
    userTally[index]["Total Likes"] += post_likes
    userTally[index]["Total Comments"] += post_comments
    userTally[index]["Total Content Length"] += content_length
    userTally[index]["Total Media"] += media
    userTally[index]["Chinese Content Length"] += chinese_length
    userTally[index]["English Content Length"] += english_length
    userTally[index]["Emoji Content Length"] += emoji_length
    userTally[index]["Posts"].append(postDictionary)

    if len(likes) == 0:
        return userTally

    for i in range(0, len(likes)):
        like = likes[i]
        likerIndex = findUser(userTally, like, "User")
        if likerIndex == -1:
            userTally.append(initUser(like, 0, 0, 0, 0, 0, 0))  # Help initiliaze the user
        userTally[findUser(userTally, like, "User")]["Total Likes Given"] += 1

    if len(comments) == 0:
        return userTally

    for i in range(0, len(comments)):
        comment = comments[i].split(" : ")[0]
        commentIndex = findUser(userTally, comment, "User")
        if commentIndex == -1:
            userTally.append(initUser(comment, 0, 0, 0, 0, 0, 0))
        userTally[commentIndex]["Total Comments Given"] += 1

    return userTally


def updateGlobal(overview_dick, post_likes, post_comments, content_length, media, chinese_length, english_length,
                 emoji_length):
    overview_dick["Global Posts"] += 1
    overview_dick["Global Likes"] += post_likes
    overview_dick["Global Comments"] += post_comments
    overview_dick["Global Content Length"] += content_length
    overview_dick["Global Media"] += media
    overview_dick["Global Chinese Content Length"] += chinese_length
    overview_dick["Global English Content Length"] += english_length
    overview_dick["Global Emoji Content Length"] += emoji_length
    return overview_dick

def initScraperDict():
    scraperDictionary = {}
    scraperDictionary["Scraper Count"] = 0
    scraperDictionary["Scrapers"] = []
    scraperDictionary["Scraped Dates"] = {} # Kinda useless... I still haven't figured out timeseries
    return scraperDictionary

def initScraper(contributor, posts_contributed):
    scraper = {}
    scraper["Contributor"] = contributor
    scraper["Posts Contributed"] = posts_contributed
    return scraper

Json_File = {}
Users = []
Global_Dictionary = initGlobal()
Scraper_Dictionary = initScraperDict()

with open(fileName) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        User_Posts = []
        User_Dictionary = {}
        Post_Dictionary = {}
        if line_count > 0:
            uuid, user, content, raw_media, raw_time, likes, comments, scraped_date, contributor = getRawData(row)
            date, time = process_time(raw_time)
            media = process_raw_media(raw_media)
            post_like_count, post_comment_count, post_chinese_len, post_eng_len, post_emoji_len, content_len = getLengthData(
                likes.split('，'), comments, content)
            Post_Dictionary = initPost(uuid, user, date, time, content, media, likes, comments, post_like_count,
                                       post_comment_count)
            User_Posts.append(Post_Dictionary)
            userIndex = findUser(Users, user, "User")
            if userIndex == -1:
                User_Dictionary = initUser(user, post_like_count, post_comment_count, content_len, post_chinese_len, post_eng_len,
                                           post_emoji_len)
                User_Dictionary["Posts"] = User_Posts
                Users.append(User_Dictionary)
            else:
                Users = updateUser(Users, userIndex, post_like_count, post_comment_count, content_len, media,
                                   post_chinese_len, post_eng_len, post_emoji_len, Post_Dictionary, likes.split('，'),
                                   comments)

            scraperIndex = findUser(Scraper_Dictionary["Scrapers"], contributor, "Contributor")
            if scraperIndex == -1:
                Scraper_Dictionary["Scrapers"].append(initScraper(contributor, 1))
                Scraper_Dictionary["Scraper Count"] += 1
            else:
                Scraper_Dictionary["Scrapers"][scraperIndex]["Posts Contributed"] += 1

            if scraped_date in Scraper_Dictionary["Scraped Dates"]:
                Scraper_Dictionary["Scraped Dates"][scraped_date] += 1
            else:
                Scraper_Dictionary["Scraped Dates"][scraped_date] = 1

            Global_Dictionary = updateGlobal(Global_Dictionary, post_like_count, post_comment_count, content_len, media,
                                             post_chinese_len, post_eng_len, post_emoji_len)

        line_count += 1

Json_File["Users"] = Users
Json_File["Global"] = Global_Dictionary
Json_File["Scraper Stats"] = Scraper_Dictionary
with open("data_overview.json", "w") as fp:
    json.dump(Json_File, fp, indent=4)

