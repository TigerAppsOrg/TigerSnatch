# Guide for TigerSnatch Development

**To start developing**
1. Create a virtual environment for the app's dependencies. 
    - With conda, do `conda create --name <name>` and activate the environment.
2. Install the requirements outlined in `requirements.txt`.
    - Do `pip install -r requirements.txt`
3. Also install `black`, a Python formatter. 
    - Do `conda install -c conda-forge black=21.7b0` (it will take a while). 
5. Edit `config.py` to hard-code config variables. Copy the hard-coded values from Heroku (under Settings > Reveal Config Vars).

**Our dev workflow**

For non-minor changes:
1. Make a new dev branch.
2. Make code changes on this branch. Test your changes (on desktop & mobile view) locally and with our auto-enabled review apps (a review app is created when you make a commit to your opened PR).
3. If edits were made to `.py` files, do `black .` in the main directory to format the Python code.
    - Your commits must pass our automatic `black` formatting checks (done for PRs).
4. Open a pull request to merge the dev branch into main. In your PR's body, describe the PR's goals, overview of changes made (with images), how you tested these changes, and future work/potential issues. 
5. Ask for code review (required to complete PR).
6. Don't forget to pull changes from main into dev before merging PR.

**To run the app locally**
1. If you haven't already, follow the steps above to install dependencies and create a config file.
2. Start the Flask server: `python _exec_server.py <port_num>`
2. Navigate to `localhost:<port_num>` in your browser.

**To edit JS/CSS files**
- After editing a JS or CSS file, up the version number of the file. This ensures the browser downloads the newest version of the file (and doesn't used the cached version).
    - e.g. For `app.x.y.js`, the version number is `x.y`. Change `x` to `x+1` for major changes, `y` to `y+1` for minor changes.

**To interact with the DB**
1. Install the MongoDB Compass Desktop app for easier visual interaction.
2. In the app, enter the connection string for either the production or staging app.
    - Connection string is found in Heroku config vars.
    - It is **highly** recommended to use staging DB for development.

**To deploy the app**
- Pushes to main are auto-deployed to the production app. **Do NOT push to main unless an urgent fix is necessary.** Always develop on another branch.
- To deploy to staging app, you can manually deploy a specific branch in Heroku.
- When you open a PR and make a commit, a review app (with url `tigersnatch-pr-*.herokuapp.com`) is automatically created with your commit deployed.

**To simulate one run of the notifications script**
1. If needed, first manually fill a course section using the Admin panel and then subscribe to that section.
    - Be sure to visit the section's course page before doing this to force a data update for that course.
2. Run `python send_notifs.py` (locally) or `heroku run python src/send_notifs.py -a <app_name>` (on a specific app).

**To view Heroku logs**
- Do `heroku logs --tail -a <app_name>`
- Use Papertrail in Heroku (stores more logs & logs are search-able)

**To visit API Store**
1. Connect to vpn.princeton.edu using GlobalProtect VPN.
2. Navigate to https://api-store.princeton.edu/store/
3. Login with TigerSnatch credentials for access to MobileApp API.

**How to add a Release Note**
1. Write down a title for your product update, the date it was deployed, and any short tags to describe this update (e.g. What type of update is it - new feature, bug fix, feature enhancement? On which page is this feature located? How important is this update for your users - high, medium, low?)  
2. Open `RELEASE_NOTES.md` and `release_notes_metadata.json`. `RELEASE_NOTES.md` is the human-readable version of our release notes in the Github Repo. This file contains the "body" of each release note, written in markdown. `release_notes_metadata.json` stores the metadata for each release note: the title, date, and tags. In both files, release notes are organized in reverse chronological order (i.e. release notes should be in the same order in both files!)
    - In `release_notes_metadata.json`, follow the existing format to add metadata about your new note, i.e. your note's metadata is contained in an object within an ordered (reverse chron.) list: 
        ```
        {
            "title": [title], 
            "date": [MM / DD / YY], 
            "tags": {
                [tag type]: [tag value],
                ...
            }
        }
        ```
        - NOTE: Each note's metadata must include a title, the date, and 1+ tags.
        - NOTE: Tags can be of any type/value. If you are to edit/add a new type, then make sure to this type has been assigned its own badge color in `about.html` (or else the tag won't be rendered):
            ```
            {% if [tag type] in note["tags"] %}
                <span class="badge rounded-pill" [color]>{{ note["tags"][[tag type]] }}</span>
            ```
    - In `RELEASE_NOTES.md`, follow the existing format to add the body of your new release note in the appropriate order (reverse chron.), i.e. 
        ```
        <!-- NOTE  -->
        Title - MM / DD / YY

        <!-- BODY  -->
        Body of note, written in markdown. To add images, use HTML: <img src="static/release_notes_pics/image_file" width="100%"/>
        ```
        - NOTE: Any images for release notes should be saved in `static/release_notes_pics` folder. 
        - NOTE: The `<!-- NOTE  -->` and `<!-- BODY  -->` delimiters (in that order) must be included for each note.
3. Double-check that you correctly formatted your release note and its metadata. Double-check that the Release Notes section is properly rendered on the About page. If you do not correctly carry out step 2 above, all release notes may fail to display on the About page. Push your changes to the TigerSnatch repo.
- Note that anything written above the first note in `RELEASE_NOTES.md` will not appear on the About page. **To see how `RELEASE_NOTES.md` and `release_notes_metadata.json` are parsed to construct the Release Notes section on the About page, check out `get_release_notes()` in `app_helper.py`.**  

**Things for Shannon to Remember**
- Data on course page is read from DB. If it has been more than 5 mins since course page was last visited, then API is queried and this course's data is updated in DB. Notifs script directly queries API for new enrollment/cap and checks if spots are available; does not update DB.
