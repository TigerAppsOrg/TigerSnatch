# Guide for TigerSnatch Development

**To start developing**
1. Create a virtual environment for the app's dependencies.
    - With conda, do `conda create --name <name>` and activate the environment.
2. Install the requirements outlined in `requirements.txt`.
    - Do `pip install -r requirements.txt`
3. Edit `config.py` to hard-code config variables. Copy the hard-coded values from Heroku (under Settings > Reveal Config Vars).

**To run the app locally**
1. If you haven't already, follow the steps above to install dependencies and create a config file.
2. Start the Flask server: `python _exec_server.py <port_num>`
2. Navigate to `localhost:<port_num>` in your browser.


**To edit JS/CSS files**
1. Change the version number of the minified JS/CSS files, to make these file stored in the browser cache are updated. 
    - e.g. If the filename is `app.min.x.y.js` , change to `x+1` for major changes, `y+1` for minor changes.
    - Be sure to update to the new filename in `script` and/or `stylesheet` tags everywhere. You can use global find-and-replace in VSCode (cmd-shift-F) to accomplish this.
2. To update the minified files:
    - To update the minified JS file, run `closure-compiler --js app.js --js_output_file app.min.x.y.js` in the terminal.
    - To update the minified CSS file, use an online tool to unminify (before editing) and minify (after editing) the CSS and copy the minified code into the CSS file.
    - Again, be sure to update the version number and the relevant `script` and/or `stylesheet` tags everywhere (see #1).

**To interact with the DB**
1. Install the MongoDB Compass Desktop app for easier visual interaction.
2. In the app, enter the connection string for either the production or staging app.
    - Connection string is found in Heroku config vars.
    - It is **highly** recommended to use staging DB for development.

**To deploy the app**
- Pushes to main are auto-deployed to the production app. **Do NOT push to main unless an urgent fix is necessary.** Always develop on another branch.
- To deploy to staging app, you can manually deploy a specific branch in Heroku.

**To simulate one run of the notifications script**
1. If needed, first manually fill a course section using the Admin panel and then subscribe to that section.
    - Be sure to visit the section's course page before doing this to force a data update for that course.
2. Run `python send_notifs.py` (locally) or `heroku run python src/send_notifs.py -a <app_name>` (on a specific app).

**To view Heroku logs**
- Use command: `heroku logs --tail -a <app_name>`

**To visit API Store**
1. Connect to vpn.princeton.edu using GlobalProtect VPN.
2. Navigate to https://api-store.princeton.edu/store/
3. Login with TigerSnatch credentials for access to MobileApp API.

**Things for Shannon to Remember**
- Data on course page is read from DB. If it has been more than 5 mins since course page was last visited, then API is queried and this course's data is updated in DB. Notifs script directly queries API for new enrollment/cap and checks if spots are available; does not update DB.

**How to add a Release Note**

1. Write down a title for your product update, the date it was deployed, and any short tags to describe this update (e.g. What type of update is it - new feature, bug fix, feature enhancement? On which page is this feature located? How important is this update for your users - high, medium, low?)  
2. Open `RELEASE_NOTES.md` and `release_notes_metadata.json`. `RELEASE_NOTES.md` is the human-readable version of our release notes in the Github Repo. This file contains the "body" of each release note. `release_notes_metadata.json` stores the metadata for each release note: the title, date, and tags. In both files, release notes are organized in reverse chronological order (i.e. release notes should be in the same order in both files!)
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
    - In `RELEASE_NOTES.md`, follow the existing format to add the body of your new release note in the appropriate order (reverse chron.), i.e. 
        ```
        <!-- NOTE  -->
        Title - MM / DD / YY

        <!-- BODY  -->
        Body of note, written in markdown. To add images, use HTML: <img src="static/release_notes_pics/image_file" width="100%"/>
        ```
3. Double-check that you correctly formatted your release note and its metadata. Double-check that the Release Notes section is properly rendered on the About page. If you do not correctly carry out step 2 above, all release notes may fail to display on the About page. Note that anything written above the first note in `RELEASE_NOTES.md` will not appear on the About page. **To see how `RELEASE_NOTES.md` and `release_notes_metadata.json` are parsed to construct the Release Notes section on the About page, check out `get_release_notes()` in `app_helper.py`.**  
