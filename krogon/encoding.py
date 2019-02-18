from base64 import b64encode


def to_base64(plain_text: str) -> str:
    return b64encode(plain_text.encode('utf-8')).decode('utf-8')
