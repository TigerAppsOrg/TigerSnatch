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
from database import Database
from time import time


class ActiveDirectory:
    def __init__(self):
        self.configs = Configs()
        self._db = Database()

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
    api = ActiveDirectory()
    print(api.get_user("ntyp"))
