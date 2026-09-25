"""Generate and validate the project-local CA and localhost TLS certificate."""

from __future__ import annotations

import argparse
import ipaddress
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_CERTIFICATE = "vgu-buddy-local-ca.crt"
CA_PRIVATE_KEY = "vgu-buddy-local-ca-key.pem"
SERVER_CERTIFICATE = "localhost.crt"
SERVER_PRIVATE_KEY = "localhost-key.pem"
EXPECTED_FILES = frozenset(
    {CA_CERTIFICATE, CA_PRIVATE_KEY, SERVER_CERTIFICATE, SERVER_PRIVATE_KEY}
)


class LocalTlsError(RuntimeError):
    """Raised when local TLS material is incomplete or invalid."""


def _private_key_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _validate_existing(directory: Path, now: datetime) -> None:
    present = {path.name for path in directory.iterdir() if path.is_file()}
    if not EXPECTED_FILES.issubset(present):
        raise LocalTlsError(
            "Local TLS directory is incomplete; remove it and regenerate safely."
        )

    try:
        ca_certificate = x509.load_pem_x509_certificate(
            (directory / CA_CERTIFICATE).read_bytes()
        )
        ca_key = serialization.load_pem_private_key(
            (directory / CA_PRIVATE_KEY).read_bytes(), password=None
        )
        server_certificate = x509.load_pem_x509_certificate(
            (directory / SERVER_CERTIFICATE).read_bytes()
        )
        server_key = serialization.load_pem_private_key(
            (directory / SERVER_PRIVATE_KEY).read_bytes(), password=None
        )
        san = server_certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
        ca_subject_key_identifier = ca_certificate.extensions.get_extension_for_class(
            x509.SubjectKeyIdentifier
        ).value
        ca_authority_key_identifier = ca_certificate.extensions.get_extension_for_class(
            x509.AuthorityKeyIdentifier
        ).value
        server_certificate.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        server_authority_key_identifier = (
            server_certificate.extensions.get_extension_for_class(
                x509.AuthorityKeyIdentifier
            ).value
        )
    except (OSError, TypeError, ValueError, x509.ExtensionNotFound) as error:
        raise LocalTlsError("Local TLS material is invalid.") from error

    ca_certificate_key = ca_certificate.public_key()
    server_certificate_key = server_certificate.public_key()
    if (
        not isinstance(ca_key, ec.EllipticCurvePrivateKey)
        or not isinstance(server_key, ec.EllipticCurvePrivateKey)
        or not isinstance(ca_certificate_key, ec.EllipticCurvePublicKey)
        or not isinstance(server_certificate_key, ec.EllipticCurvePublicKey)
    ):
        raise LocalTlsError("Local TLS material is invalid.")

    if (
        ca_certificate.not_valid_after_utc <= now
        or server_certificate.not_valid_after_utc <= now
        or server_certificate.issuer != ca_certificate.subject
        or ca_key.public_key().public_numbers() != ca_certificate_key.public_numbers()
        or server_key.public_key().public_numbers()
        != server_certificate_key.public_numbers()
        or "localhost" not in san.get_values_for_type(x509.DNSName)
        or ca_authority_key_identifier.key_identifier
        != ca_subject_key_identifier.digest
        or server_authority_key_identifier.key_identifier
        != ca_subject_key_identifier.digest
    ):
        raise LocalTlsError("Local TLS material is invalid or expired.")


def configure_local_tls(directory: Path, *, now: datetime | None = None) -> bool:
    """Create local-only TLS material once, or validate an existing complete bundle."""
    current_time = now or datetime.now(UTC)
    if directory.exists():
        if not directory.is_dir():
            raise LocalTlsError("Local TLS output must be a directory.")
        _validate_existing(directory, current_time)
        return False

    directory.mkdir(parents=True)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "VGU Buddy Local CA")])
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(current_time - timedelta(minutes=5))
        .not_valid_after(current_time + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_key = ec.generate_private_key(ec.SECP256R1())
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_certificate.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(current_time - timedelta(minutes=5))
        .not_valid_after(current_time + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("::1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    files = {
        CA_CERTIFICATE: ca_certificate.public_bytes(serialization.Encoding.PEM),
        CA_PRIVATE_KEY: _private_key_bytes(ca_key),
        SERVER_CERTIFICATE: server_certificate.public_bytes(serialization.Encoding.PEM),
        SERVER_PRIVATE_KEY: _private_key_bytes(server_key),
    }
    try:
        for name, content in files.items():
            path = directory / name
            path.write_bytes(content)
            if name.endswith("-key.pem"):
                os.chmod(path, 0o600)
    except OSError as error:
        raise LocalTlsError("Local TLS material could not be written.") from error
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure trusted local HTTPS material."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".local/tls"),
        help="Output directory (default: .local/tls).",
    )
    arguments = parser.parse_args()
    try:
        created = configure_local_tls(arguments.output_dir.resolve())
    except LocalTlsError:
        print("Error: local TLS material could not be configured.", file=sys.stderr)
        return 1
    print("Local TLS material created." if created else "Local TLS material is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
