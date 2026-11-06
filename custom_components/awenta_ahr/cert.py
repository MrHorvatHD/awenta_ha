"""Self-signed certificate for the local unit server.

The units do not validate the server certificate, but they do require a TLS handshake, so the integration creates a
long-lived self-signed certificate for `ahr.awenta.pl` (the name the units connect to) on first use.
"""
import datetime
import os

CERT_FILE = "awenta_ahr_cert.pem"
KEY_FILE = "awenta_ahr_key.pem"
HOSTNAME = "ahr.awenta.pl"


def _expired_soon(cert_path):
    from cryptography import x509

    with open(cert_path, "rb") as handle:
        cert = x509.load_pem_x509_certificate(handle.read())
    end = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)
    return end - datetime.datetime.now(datetime.timezone.utc) < datetime.timedelta(days=30)


def ensure_certificate(directory):
    """Return (cert_path, key_path), creating the pair when missing or about to expire. Blocking: run in an executor."""
    cert_path = os.path.join(directory, CERT_FILE)
    key_path = os.path.join(directory, KEY_FILE)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        try:
            if not _expired_soon(cert_path):
                return cert_path, key_path
        except Exception:  # noqa: BLE001 - unreadable pair: regenerate
            pass

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOSTNAME)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(HOSTNAME)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    os.makedirs(directory, exist_ok=True)
    with open(key_path, "wb") as handle:
        handle.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                       serialization.NoEncryption()))
    os.chmod(key_path, 0o600)
    with open(cert_path, "wb") as handle:
        handle.write(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path
