import json
import ssl

import requests
import urllib3

from websocket import create_connection
from typing import Callable

import logging

from clio import strs

_logger = logging.getLogger(__name__)


class RouterClient:
    def __init__(self, url: str, api_token: str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.url = url
        self._ws = "ws" + url[4:]
        self._api_token = api_token

    def _header(self):
        return {"Authorization": f"Token {self._api_token}"}

    def subscribe(self, queue: str, desc: dict, callback: Callable):
        ws = create_connection(
            f"{self._ws}/subscribe/{queue}", sslopt={"certs_reqs": ssl.CERT_NONE}, header=self._header()
        )
        ws.send(json.dumps(desc))
        try:
            while r := ws.recv():
                callback(**json.loads(r))
        finally:
            ws.close()

    def call(self, function: str, args: str, args_type: str = "json", raw=False):
        queue = function.split(".", 1)[0]
        args = {
            "function": function,
            "args": args,
            "args_type": args_type,
        }
        result = requests.get(f"{self.url}/call/{queue}", data=strs.to_json(args), verify=False, headers=self._header())
        if result.status_code != 200:
            raise Exception(f"[{result.status_code}]: {result.reason}")
        else:
            result = result.text
            if raw:
                return result

            try:
                result = strs.from_json(result)
            except Exception:
                raise Exception(f"unhandled result: {result}")

            if result["type"] == "text":
                return result["result"]
            elif result["type"] == "err":
                raise Exception(result["result"])
            else:
                raise Exception(f"unknown result type: {result}")

    def respond(self, queue: str, caller_id: str, response: str):
        result = requests.get(
            f"{self.url}/respond/{queue}",
            params={"CallerID": caller_id},
            data=response,
            verify=False,
            headers=self._header(),
        )
        if result.status_code != 200:
            raise Exception(f"[{result.status_code}]: {result.reason}")
