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

**To visit API Store*
1. Connect to vpn.princeton.edu using GlobalProtect VPN.
2. Navigate to https://api-store.princeton.edu/store/
3. Login with TigerSnatch credentials for access to MobileApp API.

**Things for Shannon to Remember**
- Data on course page is read from DB. If it has been more than 5 mins since course page was last visited, then API is queried and this course's data is updated in DB. Notifs script directly queries API for new enrollment/cap and checks if spots are available; does not update DB.
