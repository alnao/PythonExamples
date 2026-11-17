"""Token JWT firmati con HS256, solo con la libreria standard (niente pyjwt e niente bundling con Docker).

- sign(payload, secret, minutes): crea un token con iat ed exp
- verify(token, secret): controlla formato, algoritmo, firma e scadenza; restituisce il payload o solleva InvalidToken
"""

import base64
import hashlib
import hmac
import json
import time


class InvalidToken(Exception):
    pass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(signing_input: str, secret: str) -> str:
    return _b64encode(hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest())


def sign(payload: dict, secret: str, minutes: int = 60) -> str:
    now = int(time.time())
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64encode(json.dumps({**payload, "iat": now, "exp": now + minutes * 60}, separators=(",", ":")).encode())
    return f"{header}.{body}.{_signature(f'{header}.{body}', secret)}"


def verify(token: str, secret: str) -> dict:
    try:
        header_b64, body_b64, signature = token.split(".")
        header = json.loads(_b64decode(header_b64))
        payload = json.loads(_b64decode(body_b64))
    except (ValueError, AttributeError) as e:
        raise InvalidToken(f"token non valido: {e}")
    if header.get("alg") != "HS256":
        raise InvalidToken("algoritmo non ammesso")  # niente "none" o algoritmi diversi
    if not hmac.compare_digest(signature, _signature(f"{header_b64}.{body_b64}", secret)):
        raise InvalidToken("firma non valida")
    if not isinstance(payload.get("exp"), (int, float)) or payload["exp"] < time.time():
        raise InvalidToken("token scaduto")
    return payload
