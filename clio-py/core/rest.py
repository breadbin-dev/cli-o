import requests

content_json = {"Content-Type": "application/json"}


def read_response(response, type=...):
    if response.status_code // 100 != 2:
        try:
            if (not response.reason) and response.text:
                response.reason = response.text
        except Exception:
            pass
        response.raise_for_status()
    if type is ... or type == "json":
        return response.json()
    if type == "text":
        return response.text
    raise Exception(f"Unknown type: {type}")


class Rest:
    def __init__(self, url, headers=..., additional_headers=None, proxies=None, auth=None, verify=True):
        self.url = url
        self._session = requests.Session()
        self._session.auth = auth
        self._session.verify = verify

        if headers is ...:
            headers = content_json

        if additional_headers is not None:
            headers = {**headers, **additional_headers}

        self._headers = headers
        self._proxies = proxies

    def get_headers(self):
        return self._headers

    def get(self, item, params=None, type=...):
        return read_response(
            self._session.get(
                f"{self.url}{item}",
                params=params,
                headers=self.get_headers(),
                proxies=self._proxies,
            ),
            type=type,
        )

    def post(self, item, data, params=None, headers=..., url=..., type=...):
        if headers is ...:
            headers = self.get_headers()

        if url is ...:
            url = self.url

        return read_response(
            self._session.post(
                f"{url}{item}",
                json=data,
                params=params,
                headers=headers,
                proxies=self._proxies,
            ),
            type=type,
        )

    def put(self, item, data, params=None):
        return read_response(
            self._session.put(
                f"{self.url}{item}",
                json=data,
                params=params,
                headers=self.get_headers(),
                proxies=self._proxies,
            )
        )

    def delete(self, item, data=None, params=None):
        return read_response(
            self._session.delete(
                f"{self.url}{item}",
                json=data,
                params=params,
                headers=self.get_headers(),
                proxies=self._proxies,
            )
        )
