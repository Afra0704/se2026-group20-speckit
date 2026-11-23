"""Standalone OAuth command; 002 can later register the same helper in Flask."""
import argparse
import os
from pathlib import Path

from .google_authorization import AuthError, _read_client, authorize, validate_paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare Guided Notes Desktop OAuth credentials")
    parser.add_argument("command", choices=["authorize-sheets", "check-config"])
    parser.add_argument("--client", default=os.environ.get("NOTES_GOOGLE_CLIENT_SECRETS"))
    parser.add_argument("--token", default=os.environ.get("NOTES_GOOGLE_TOKEN"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args(argv)
    try:
        if args.command == "check-config":
            client, _ = validate_paths(args.client, args.token, args.repo_root)
            _read_client(client)
            print("Configuration paths and Desktop client are valid; Google access has not been tested.")
        else:
            authorize(args.client, args.token, repo_root=args.repo_root, interactive=True)
            print("Google authorization is ready; worksheet access still requires verification.")
        return 0
    except AuthError as error:
        print(f"Authorization unavailable: {error.code}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
