from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple, Union, cast

from sdkite.http._stringescape import stringescape_dumps, stringescape_loads
from sdkite.http.engine_requests import HTTPEngineRequests
from sdkite.http.model import HTTPHeaderDict, HTTPRequest, HTTPResponse
from sdkite.utils import identity

if sys.version_info < (3, 8):  # pragma: no cover
    from backports.cached_property import cached_property
    from typing_extensions import TypedDict
else:  # pragma: no cover
    from functools import cached_property
    from typing import TypedDict

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Iterator
else:  # pragma: no cover
    from collections.abc import Iterable, Iterator


class _RecordedRequest(TypedDict):
    method: str
    url: str
    headers: Dict[str, str]
    body: bytes


class _RecordedResponse(TypedDict):
    status_code: int
    reason: str
    headers: Dict[str, str]
    body: List[bytes]


class HTTPResponseReplay(HTTPResponse):
    def __init__(self, recorded_response: _RecordedResponse) -> None:
        self.recorded_response = recorded_response

    @property
    def raw(self) -> object:
        raise ValueError("The 'raw' attribute is not available with the replay engine")

    @property
    def status_code(self) -> int:
        return self.recorded_response["status_code"]

    @property
    def reason(self) -> str:
        return self.recorded_response["reason"]

    @cached_property
    def headers(self) -> HTTPHeaderDict:
        return HTTPHeaderDict(self.recorded_response["headers"])

    @cached_property
    def data_stream(self) -> Iterator[bytes]:
        return iter(self.recorded_response["body"])

    @property
    def data_bytes(self) -> bytes:
        try:
            parts = [next(self.data_stream)]
        except StopIteration:
            raise ValueError(
                "The data_xxx attributes can be only accessed once with the replay engine"
            ) from None
        parts.extend(self.data_stream)
        return b"".join(parts)

    @property
    def data_str(self) -> str:
        return self.data_bytes.decode()

    @cached_property
    def data_json(self) -> object:
        return json.loads(self.data_bytes)

    def replace(
        self,
        *,
        status_code: Optional[int] = None,
        reason: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[bytes, Iterable[bytes]]] = None,
    ) -> "HTTPResponseReplay":
        recorded_response = cast(_RecordedResponse, deepcopy(self.recorded_response))
        if status_code is not None:
            recorded_response["status_code"] = status_code
        if reason is not None:
            recorded_response["reason"] = reason
        if headers is not None:
            recorded_response["headers"] = dict(headers)
        if body is not None:
            if isinstance(body, bytes):
                body = [body]
            recorded_response["body"] = list(body)
        return HTTPResponseReplay(recorded_response)


def _default_recording_compute_basename(request: HTTPRequest, _: HTTPResponse) -> str:
    return re.sub(
        "[^a-zA-Z0-9]", "_", f"{time.time():.0f} {request.method.lower()} {request.url}"
    )


class HTTPEngineReplay:
    def __init__(
        self,
        paths: Iterable[Path],
        *,
        recording: bool = False,
        replay_request_modifier: Callable[
            [HTTPRequest],
            HTTPRequest,
        ] = identity,
        replay_response_modifier: Callable[
            [HTTPResponseReplay],
            HTTPResponseReplay,
        ] = identity,
        recording_request_modifier: Callable[
            [HTTPRequest],
            HTTPRequest,
        ] = identity,
        recording_response_modifier: Callable[
            [HTTPResponseReplay],
            HTTPResponseReplay,
        ] = identity,
        recording_compute_basename: Callable[
            [HTTPRequest, HTTPResponseReplay],
            str,
        ] = _default_recording_compute_basename,
    ) -> None:
        # load all recorded items
        self.recorded: List[
            Tuple[_RecordedRequest, _RecordedResponse]
        ] = []  # sorted by priority
        for path_dir in paths:
            for path_item in path_dir.iterdir():
                if path_item.is_file() and path_item.suffix == ".json":
                    with path_item.open() as path_item_fp:
                        item = json.load(path_item_fp)
                    item["request"]["body"] = stringescape_loads(
                        item["request"]["body"]
                    )
                    item["response"]["body"] = [
                        stringescape_loads(part) for part in item["response"]["body"]
                    ]
                    self.recorded.append((item["request"], item["response"]))
            self.recording_path_dir = path_dir  # will get last item
        self.recorded.reverse()

        # set recording options
        self.recording = recording
        self.engine: Optional[Callable[[HTTPRequest], HTTPResponse]] = None

        # other attributes
        self.replay_request_modifier = replay_request_modifier
        self.replay_response_modifier = replay_response_modifier
        self.recording_request_modifier = recording_request_modifier
        self.recording_response_modifier = recording_response_modifier
        self.recording_compute_basename = recording_compute_basename

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        # exhausting body to be able to deepcopy later
        request = replace(
            request,
            body=request.body
            if isinstance(request.body, bytes)
            else b"".join(request.body),
        )

        lookup_request = self.replay_request_modifier(deepcopy(request))
        recorded_request = _RecordedRequest(
            method=lookup_request.method,
            url=lookup_request.url,
            headers=dict(lookup_request.headers),
            body=lookup_request.body
            if isinstance(lookup_request.body, bytes)
            else b"".join(lookup_request.body),
        )

        # recording mode
        if self.recording:
            # perform request
            if self.engine is None:
                self.engine = HTTPEngineRequests()

            real_request = self.recording_request_modifier(deepcopy(request))
            with self.engine(real_request) as real_response:
                received_response = HTTPResponseReplay(
                    _RecordedResponse(
                        status_code=real_response.status_code,
                        reason=real_response.reason,
                        headers=dict(real_response.headers),
                        body=list(real_response.data_stream)
                        if real_request.stream_response
                        else [real_response.data_bytes],
                    )
                )
            response = self.recording_response_modifier(received_response)

            # save recorded response
            recorded_basename = self.recording_compute_basename(request, response)
            recorded_path = self.recording_path_dir / f"{recorded_basename}.json"
            with recorded_path.open("w") as recorded_fp:
                json.dump(
                    {
                        "request": {
                            **recorded_request,
                            "body": stringescape_dumps(recorded_request["body"]),
                        },
                        "response": {
                            **response.recorded_response,
                            "body": [
                                stringescape_dumps(part)
                                for part in response.recorded_response["body"]
                            ],
                        },
                    },
                    recorded_fp,
                    indent=2,
                )
                recorded_fp.write("\n")

        # replay recorded response
        else:
            for req, resp in self.recorded:
                if req == recorded_request:
                    response = HTTPResponseReplay(resp)
                    break
            else:
                raise ValueError(
                    f"No response have been recorded for request: {recorded_request}"
                )

        return self.replay_response_modifier(response)
