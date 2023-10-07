from aiohttp import ClientResponse


class FortniteException(Exception):

    pass


class HTTPException(FortniteException):

    def __init__(self, resp: ClientResponse, data: dict) -> None:
        self.response = resp
        self.data = data

        self.url: str = str(resp.url)
        self.method: str = resp.method
        self.status: int = resp.status
        self.reason: str = resp.reason

        self.error_code: str = data.get('errorCode', '[error code not found]')
        self.error_message: str = data.get('errorMessage', '[error message not found]')

    def __str__(self) -> str:
        return f'{self.method.upper()} {self.url} responded with {self.status} {self.reason}' \
               f' - {self.error_message} ({self.error_code})'


class BadRequest(HTTPException):

    pass


class Unauthorized(HTTPException):

    pass


class Forbidden(HTTPException):

    pass


class NotFound(HTTPException):

    pass


class TooManyRequests(HTTPException):

    pass


class ServerError(HTTPException):

    pass
