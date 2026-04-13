"""
WearPark — Génération CA + certificats de devices simulés
==========================================================
Remplace gen_certs.sh — fonctionne sur Windows, Mac, Linux.

Usage:
    pip install cryptography
    python gen_certs.py                              # CNs par défaut
    python gen_certs.py sim-001 sim-002 sim-003      # CNs spécifiques

Résultat dans ./certs/ :
    ca.pem                              CA publique  (à donner au backend)
    ca.key                              Clé privée CA (garder secret)
    devices/<cn>/client.crt             Certificat du device
    devices/<cn>/client.key             Clé privée du device
    devices/<cn>/.env                   .env prêt pour le simulateur
"""

import sys
import datetime
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    print("[ERROR] Librairie manquante. Installez-la avec:")
    print("        pip install cryptography")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUT_DIR      = Path("./certs")
CA_DAYS      = 3650
DEVICE_DAYS  = 1825
KEY_SIZE     = 2048

DEFAULT_DEVICE_KEYS = [
    "device-test",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=KEY_SIZE)


def save_private_key(key, path: Path) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def save_certificate(cert, path: Path) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ca_subject() -> x509.Name:
    return x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "CA"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Quebec"),
        x509.NameAttribute(NameOID.LOCALITY_NAME,            "Montreal"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "WearPark"),
        x509.NameAttribute(NameOID.COMMON_NAME,              "WearPark-SimCA"),
    ])


def device_subject(cn: str) -> x509.Name:
    return x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "CA"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Quebec"),
        x509.NameAttribute(NameOID.LOCALITY_NAME,            "Montreal"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "WearPark"),
        x509.NameAttribute(NameOID.COMMON_NAME,              cn),
    ])


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Génération CA
# ---------------------------------------------------------------------------

def generate_ca(out_dir: Path):
    ca_key_path  = out_dir / "ca.key"
    ca_cert_path = out_dir / "ca.pem"

    if ca_key_path.exists() and ca_cert_path.exists():
        print("[WARN] CA déjà existante — réutilisée.")
        print("       Supprimez ca.key + ca.pem pour en recréer une.")
        ca_key = serialization.load_pem_private_key(
            ca_key_path.read_bytes(), password=None
        )
        ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
        return ca_key, ca_cert

    print("[INFO] Génération de la CA...")
    ca_key = generate_private_key()

    subject = ca_subject()
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc())
        .not_valid_after(now_utc() + datetime.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    save_private_key(ca_key,  ca_key_path)
    save_certificate(ca_cert, ca_cert_path)
    print(f"[OK]   CA générée → {ca_cert_path}")
    return ca_key, ca_cert


# ---------------------------------------------------------------------------
# Génération certificat device
# ---------------------------------------------------------------------------

def generate_device_cert(cn: str, ca_key, ca_cert, out_dir: Path) -> None:
    device_dir = out_dir / "devices" / cn
    device_dir.mkdir(parents=True, exist_ok=True)

    key_path  = device_dir / "client.key"
    cert_path = device_dir / "client.crt"

    print(f"[INFO] Certificat pour device: {cn}")

    device_key = generate_private_key()

    cert = (
        x509.CertificateBuilder()
        .subject_name(device_subject(cn))
        .issuer_name(ca_cert.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc())
        .not_valid_after(now_utc() + datetime.timedelta(days=DEVICE_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    save_private_key(device_key, key_path)
    save_certificate(cert, cert_path)

    # Vérifier le CN extrait
    extracted_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    print(f"[OK]   CN extrait du cert: '{extracted_cn}'")

    # Générer le .env pour le simulateur
    abs_out = out_dir.resolve()
    env_content = f"""# WearPark Simulator — Device: {cn}
# Généré le {now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC

TCP_HOST=127.0.0.1
TCP_PORT=9000
TLS_ENABLED=true
TLS_CA_CERT_PATH={abs_out / "ca.pem"}
TLS_CLIENT_CERT_PATH={abs_out / "devices" / cn / "client.crt"}
TLS_CLIENT_KEY_PATH={abs_out / "devices" / cn / "client.key"}
TLS_REQUIRE_CLIENT_CERT=true
SAMPLE_RATE_HZ=50
"""
    (device_dir / ".env").write_text(env_content, encoding="utf-8")
    print(f"[OK]   .env → {device_dir / '.env'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    device_keys = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_DEVICE_KEYS

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ca_key, ca_cert = generate_ca(OUT_DIR)

    for cn in device_keys:
        generate_device_cert(cn, ca_key, ca_cert, OUT_DIR)

    # Résumé
    abs_out = OUT_DIR.resolve()
    first   = device_keys[0]
    print()
    print("=" * 60)
    print(f"  Certificats dans: {abs_out}")
    print("=" * 60)
    print(f"  CA publique pour le backend:")
    print(f"    {abs_out / 'ca.pem'}")
    print()
    print(f"  Devices générés:")
    for cn in device_keys:
        print(f"    • {cn} → {abs_out / 'devices' / cn}/")
    print()
    print(f"  Exemple simulateur:")
    print(f"    python simulator.py \\")
    print(f"      --date 2024-03-15 --attacks 5 \\")
    print(f"      --tls \\")
    print(f"      --ca-cert {abs_out / 'ca.pem'} \\")
    print(f"      --client-cert {abs_out / 'devices' / first / 'client.crt'} \\")
    print(f"      --client-key {abs_out / 'devices' / first / 'client.key'}")
    print()
    print("  IMPORTANT: Insérer les device_keys en DB avant de connecter.")
    print("=" * 60)


if __name__ == "__main__":
    main()