from googleapiclient.errors import HttpError
from typing import Callable
import krogon.either as E


def on_http404(return_result: E.Either) -> Callable[[Exception], E.Either]:
    def handle(ex: E.TryCatchError):
        if not (hasattr(ex.caught_error, 'resp') and hasattr(ex.caught_error.resp, 'status')):
            return E.Failure(ex)

        http_error: HttpError = ex.caught_error
        if http_error.resp.status == 404:
            return return_result
        else:
            return E.Failure(ex)

    return handle
