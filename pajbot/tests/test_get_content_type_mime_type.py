def test_get_content_type_mime_type() -> None:
    from pajbot.utils import get_content_type_mime_type

    from requests import Response

    def response(content_type: str) -> Response:
        r = Response()
        r.headers["Content-Type"] = content_type
        return r

    assert get_content_type_mime_type(response("text/plain; charset=utf-8")) == "text/plain"
    assert get_content_type_mime_type(response("TEXT/PLAIN; charset=utf-8")) == "text/plain"
    assert get_content_type_mime_type(response("application/json")) == "application/json"
    assert get_content_type_mime_type(response("invalid")) == "invalid"
    assert get_content_type_mime_type(response("")) == ""
