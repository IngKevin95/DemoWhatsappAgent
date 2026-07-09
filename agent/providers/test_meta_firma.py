import hashlib
import hmac

from .meta import ProveedorMeta


def test_validar_firma():
    p = ProveedorMeta()
    p.app_secret = "secreto"
    cuerpo = b'{"a":1}'
    firma_valida = "sha256=" + hmac.new(b"secreto", cuerpo, hashlib.sha256).hexdigest()

    assert p.validar_firma(cuerpo, firma_valida) is True
    assert p.validar_firma(cuerpo, "sha256=deadbeef") is False
    assert p.validar_firma(cuerpo, None) is False
    assert p.validar_firma(cuerpo, "sinPrefijo") is False


if __name__ == "__main__":
    test_validar_firma()
    print("ok")
