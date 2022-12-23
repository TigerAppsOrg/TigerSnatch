# ----------------------------------------------------------------------
# activedirectory.py
# Contains ActiveDirectory, a class used to communicate with the Users API
# from the Princeton OIT.
# Adapted from https://github.com/vr2amesh/COS333-API-Code-Examples
# ----------------------------------------------------------------------

import requests
import json
import base64
from config import CONSUMER_KEY, CONSUMER_SECRET
from time import time


class ActiveDirectory:
    def __init__(self, db):
        self.configs = Configs()
        self._db = db

    # wrapper function for _getJSON with the users endpoint.

    def get_user(self, netid):
        return self._getJSON(self.configs.USERS, uid=netid)

    """
    This function allows a user to make a request to 
    a certain endpoint, with the BASE_URL of 
    https://api.princeton.edu:443/active-directory/1.0.5

    The parameters kwargs are keyword arguments. It
    symbolizes a variable number of arguments 
    """

    def _getJSON(self, endpoint, **kwargs):
        tic = time()
        req = requests.get(
            self.configs.BASE_URL + endpoint,
            params=kwargs if "kwargs" not in kwargs else kwargs["kwargs"],
            headers={"Authorization": "Bearer " + self.configs.ACCESS_TOKEN},
        )
        text = req.text

        self._db._add_system_log(
            "activedirectory",
            {
                "message": "ActiveDirectory API query",
                "response_time": time() - tic,
                "endpoint": endpoint,
                "args": kwargs,
            },
            print_=False,
        )

        # Check to see if the response failed due to invalid credentials
        text = self._updateConfigs(text, endpoint, **kwargs)

        return json.loads(text)

    def _updateConfigs(self, text, endpoint, **kwargs):
        if text.startswith("<ams:fault"):
            self.configs._refreshToken(grant_type="client_credentials")

            # Redo the request with the new access token
            req = requests.get(
                self.configs.BASE_URL + endpoint,
                params=kwargs if "kwargs" not in kwargs else kwargs["kwargs"],
                headers={"Authorization": "Bearer " + self.configs.ACCESS_TOKEN},
            )
            text = req.text

        return text


class Configs:
    def __init__(self):
        self.CONSUMER_KEY = CONSUMER_KEY
        self.CONSUMER_SECRET = CONSUMER_SECRET
        self.BASE_URL = "https://api.princeton.edu:443/active-directory/1.0.5"
        self.USERS = "/users"
        self.REFRESH_TOKEN_URL = "https://api.princeton.edu:443/token"
        self._refreshToken(grant_type="client_credentials")

    def _refreshToken(self, **kwargs):
        req = requests.post(
            self.REFRESH_TOKEN_URL,
            data=kwargs,
            headers={
                "Authorization": "Basic "
                + base64.b64encode(
                    bytes(self.CONSUMER_KEY + ":" + self.CONSUMER_SECRET, "utf-8")
                ).decode("utf-8")
            },
        )
        text = req.text
        response = json.loads(text)
        self.ACCESS_TOKEN = response["access_token"]


if __name__ == "__main__":
    from database import Database

    api = ActiveDirectory()
    db = Database()
    all_users = db._db.users.find({})

    i = 1
    for user in all_users:
        netid = user["netid"]
        print(f"processing user {netid} ({i})")
        i += 1
        data = api.get_user(netid)

        if not data:
            print("no data found for user", netid)
            db._db.users.update_one({"netid": netid}, {"$set": {"year": None}})
            continue

        data = data[0]
        pustatus = data["pustatus"]
        if pustatus == "graduate":
            year = "Grad"
        elif pustatus == "undergraduate":
            year = data["department"].split(" ")[-1]
        elif pustatus == "fac" or pustatus == "stf":
            year = "Faculty"
        else:
            year = None

        print("year set as", year)
        db._db.users.update_one({"netid": netid}, {"$set": {"year": year}})
