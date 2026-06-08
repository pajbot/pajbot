from requests import Response


def get_content_type_mime_type(response: Response) -> str:
    return response.headers["Content-Type"].partition(";")[0].strip().lower()
