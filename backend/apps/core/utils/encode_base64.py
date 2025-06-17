import base64


def encode_base64(base64_string) -> str:
    if not base64_string:
        return ""
    try:
        token = base64_string.split(' ')[1]
        data = base64.b64decode(token).decode()
        return data
    except Exception as err:
        return ""
