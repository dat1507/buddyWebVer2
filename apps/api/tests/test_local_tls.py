"""Local HTTPS bootstrap tests for OPS-002."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cryptography import x509

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "generate_local_tls.py"


def test_local_tls_generator_creates_valid_idempotent_bundle(tmp_path: Path) -> None:
    output = tmp_path / "tls"

    first = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0
    assert first.stdout == "Local TLS material created.\n"
    assert second.returncode == 0
    assert second.stdout == "Local TLS material is valid.\n"
    assert "PRIVATE KEY" not in first.stdout + first.stderr + second.stdout + second.stderr

    ca_certificate = x509.load_pem_x509_certificate(
        (output / "vgu-buddy-local-ca.crt").read_bytes()
    )
    server_certificate = x509.load_pem_x509_certificate((output / "localhost.crt").read_bytes())
    san = server_certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    ca_ski = ca_certificate.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    ca_aki = ca_certificate.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
    server_certificate.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
    server_aki = server_certificate.extensions.get_extension_for_class(
        x509.AuthorityKeyIdentifier
    ).value
    assert server_certificate.issuer == ca_certificate.subject
    assert "localhost" in san.get_values_for_type(x509.DNSName)
    assert ca_aki.key_identifier == ca_ski.digest
    assert server_aki.key_identifier == ca_ski.digest


def test_local_tls_generator_rejects_partial_bundle_without_details(tmp_path: Path) -> None:
    output = tmp_path / "tls"
    output.mkdir()
    (output / "localhost.crt").write_text("incomplete", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Error: local TLS material could not be configured.\n"
