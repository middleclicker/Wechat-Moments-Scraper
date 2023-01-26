# Wechat-Moments-Scraper
Scraper for wechat moments. (700+ line behemoth)

To the CS Teacher: You better give me full marks for the assignment.

## CAN ONLY BE USED ON WINDOWS ##

# Usage
1. Setup an SQL database and edit the connection variables at the top of Scraper.py.
2. Edit user settings.
  - MAX_PYQ: Number of posts the scraper will aim for
  - SCRAPER_NAME: Your username
  - UPDATE_FREQ: Updates database every x posts
  - SCROLL_DIST: How far the program scrolls after each post
  - PROCESS_ALL: Processes all posts in database to generate users. Set to False if you don't want that.
  
  - TODO (Don't change these):
    - REFRESH_DELAY
    - RANDOMIZED_SCROLL
    - RANDOMIZED_REFRESH_DELAY
3. Open Wechat Moments and run the program. Do not move anything. Wait for the program to fully finish.
4. Consider giving the repository a star~

# Data
1. Posts
  
![image](https://user-images.githubusercontent.com/60602265/214553654-b23a00f4-c214-4bec-952a-3fe2b984cff0.png)

2. Users
  
![image](https://user-images.githubusercontent.com/60602265/214553769-734a08df-1df0-4875-ae07-059d1a0a80b6.png)

# Bugs
The program will have bugs, I probably didn't do enough testing. The code also looks like gibberish.

Create an issue if you find one.

# Todo
- ~~Fix different content cases~~ Added comments, fixed logic errors
- ~~Add data processing module~~ Added
- Comment and like count are still broken for some reason... I'm not sure why
- User update function isn't working properly. Delete user database before running program.
- Code Cleanup (Rename functions, recode some parts, etc.)
- Scroll Randomization
- User stats dialogue generator

# Credits:
  - https://github.com/HYLZ-2019/FriendsOfFriends used as base.
