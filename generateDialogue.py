import psycopg2
import json
HOSTNAME = ""
DATABASE = "Posts"
USERNAME = "scraper"
PWD = ""
PORT_ID = 5432
USER = ""
conn = None
cur = None
def procFreqLikes(raw_likes, connecting_word):
    if connecting_word == 0:
        connecting_word = "来自"
    else:
        connecting_word = "给到"
    raw_likes = sorted(raw_likes.items(), key=lambda x:x[1])
    if len(raw_likes) < 3:
        return ".." # （少于三项，暂不支持此数据）
    return f'''{raw_likes[len(raw_likes)-1][0]}，{raw_likes[len(raw_likes)-2][0]}和{raw_likes[len(raw_likes)-3][0]}''', f'''{raw_likes[len(raw_likes)-1][1]}次{connecting_word}{raw_likes[len(raw_likes)-1][0]}，{raw_likes[len(raw_likes)-2][1]}次{connecting_word}{raw_likes[len(raw_likes)-2][0]}，{raw_likes[len(raw_likes)-3][1]}次{connecting_word}{raw_likes[len(raw_likes)-3][0]}'''

try:
    conn = psycopg2.connect(host=HOSTNAME, dbname=DATABASE, user=USERNAME, port=PORT_ID)
    cur = conn.cursor()

    cur.execute(f'''SELECT * FROM users WHERE name='{USER}';''')
    user = cur.fetchall()[0]

    print(f'''
    {user[0]}在数据库中有{user[1]}条朋友圈。Ta总共发了{user[2]}张图片和视频，朋友圈配文总长为{user[3]}，其中含有{user[4]}个英文单词，{user[5]}个中文汉字和{user[6]}个表情。Ta总共收到了{user[7]}个赞和{user[8]}个评论（包括自己）。Ta总共点了{user[9]}次赞，评论{user[10]}次。
    Ta最常收到{procFreqLikes(user[11], 0)[0]}的点赞，其中{procFreqLikes(user[11], 0)[1]}。Ta也经常给{procFreqLikes(user[12], 1)[0]}点赞，其中{procFreqLikes(user[12], 1)[1]}。
    {procFreqLikes(user[13], 0)[0]}经常给Ta评论，其中{procFreqLikes(user[13], 0)[1]}。Ta也经常给{procFreqLikes(user[14], 1)[0]}评论，其中{procFreqLikes(user[14], 1)[1]}。''')
except Exception as e:
    print(e)
    pass
