# Wechat-Moments-Scraper
## Usages
A program used to scrape and collect WeChat Moments data from your friends.
Possible use cases include
- Data analysis of user activity (Possibly in violation of TOS)
- Stalking your friends through their Moments activity
- Producing fancy graphs to demonstrate your superior friend circle

## Running the program
### Important: Can only be used on Windows. Also, please read the Bugs section before making the decision to run the program.
The program was not originally designed to be used by anyone other than myself. Therefore, it is very user-unfriendly. Steps for running with Postgres database follow:
1. Download and unzip the repository
2. Set up a PostgreSQL database (Refer to Youtube for the thousands of tutorials available)
3. Open `scraperV2.py` and edit user settings with your credentials
	- Must Change
		- `HOSTNAME`: Your database IP
		- `DATABASE`: Database name
		- `USERNAME`: Database login username
		- `PWD`: Database login password
		- `PORT_ID`: The port of the database
	- Optional
		- `MAX_PYQ`: Number of posts the scraper will aim for. I suggest setting the value to ~500 for the initial scrape and 0 after that.
		- `SCRAPER_NAME`: Your scraper username, intended to track progress of multiple scraping machines.
		- `UPDATE_FREQ`: Uploads data to the database every x posts scraped.
		- `SCROLL_DIST`: How far the program scrolls after each post. Keep it at its default value.
		- `PROCESS_ALL`: Processes all posts in the database to generate users. Don't change this.
4. Open WeChat Moments and scroll to the top.
5. Open a Terminal window and make sure the Moments window is fully visible. Run the command `python3 scraperV2.py` and let the program run.
6. The program will (should) automatically stop when it hits the week mark, where the date data is considered too inaccurate to be useful.

## Data structure
1. Posts
![image](https://user-images.githubusercontent.com/60602265/214553654-b23a00f4-c214-4bec-952a-3fe2b984cff0.png)

2. Users
![image](https://user-images.githubusercontent.com/60602265/214553769-734a08df-1df0-4875-ae07-059d1a0a80b6.png)

# Bugs
The program is full of bugs. The approach of reading application memory does not work very well, as the data is provided in lines instead of sections. This makes data processing incredibly tedious, and I am convinced that the raw data of the moments posts cannot be separated into their correct sections without the use of AI. The current code misses or reads but does not index a lot of posts. It also misplaces text in different sections (i.e. `content` in `likes`).

A much better approach would be to emulate an android phone. There are many repositories that accomplish the task through that approach already.

As my visual approach appears to be a dead end, there would probably be no more updates.

## Credits:
  - https://github.com/HYLZ-2019/FriendsOfFriends used as the base.
