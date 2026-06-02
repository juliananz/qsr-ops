"""
scripts/hash_pin.py
Generate a salted PIN hash for pasting into .streamlit/secrets.toml.

Usage
-----
  # Step 1 — generate a salt (run once, paste into [auth] salt = "..."):
  python scripts/hash_pin.py --gen-salt

  # Step 2 — hash a PIN for one user (repeat for each person):
  python scripts/hash_pin.py

The script never prints or logs the raw PIN.
"""
import argparse
import getpass
import hashlib
import secrets
import sys

_PBKDF2_ITERS = 200_000


def gen_salt() -> str:
    return secrets.token_hex(32)


def hash_pin(pin: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), _PBKDF2_ITERS)
    return dk.hex()


def main() -> None:
    parser = argparse.ArgumentParser(description="PIN hash helper for qsr-ops auth")
    parser.add_argument(
        "--gen-salt",
        action="store_true",
        help="Generate a new random salt and exit (do this once, then store it in secrets.toml)",
    )
    args = parser.parse_args()

    if args.gen_salt:
        salt = gen_salt()
        print("\nGenerated salt (add to secrets.toml under [auth]):")
        print(f'salt = "{salt}"')
        print(
            "\nKeep this value secret and constant — changing it invalidates ALL stored hashes."
        )
        return

    # --- Hash a PIN for one user ---
    print("Hash a PIN for one user")
    print("=" * 40)

    salt = input("Enter salt (from secrets.toml [auth] salt = ...): ").strip()
    if not salt:
        print("Error: salt cannot be empty.", file=sys.stderr)
        sys.exit(1)

    username = input("Enter username (e.g. paulina): ").strip()
    if not username:
        print("Error: username cannot be empty.", file=sys.stderr)
        sys.exit(1)

    pin = getpass.getpass("Enter 4-digit PIN (input is hidden): ").strip()
    if not pin.isdigit() or len(pin) != 4:
        print("Error: PIN must be exactly 4 digits.", file=sys.stderr)
        sys.exit(1)

    h = hash_pin(pin, salt)

    print(f"\nAdd this line to [auth.users] in secrets.toml:")
    print(f'{username} = "{h}"')


if __name__ == "__main__":
    main()
