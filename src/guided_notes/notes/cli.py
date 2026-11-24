"""Standalone OAuth command; 002 can later register the same helper in Flask."""
import argparse
import json
import os
from pathlib import Path

from .google_authorization import AuthError, _read_client, authorize, validate_paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare Guided Notes Desktop OAuth credentials")
    parser.add_argument("command", choices=["authorize-sheets", "check-config", "inspect-sheet"])
    parser.add_argument("--client", default=os.environ.get("NOTES_GOOGLE_CLIENT_SECRETS"))
    parser.add_argument("--token", default=os.environ.get("NOTES_GOOGLE_TOKEN"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--url", help="Google Sheets URL for read-only inspection")
    parser.add_argument("--sheet-id", type=int, help="Numeric worksheet id; defaults to URL gid")
    args = parser.parse_args(argv)
    try:
        if args.command == "check-config":
            client, _ = validate_paths(args.client, args.token, args.repo_root)
            _read_client(client)
            print("Configuration paths and Desktop client are valid; Google access has not been tested.")
        elif args.command == "authorize-sheets":
            authorize(args.client, args.token, repo_root=args.repo_root, interactive=True)
            print("Google authorization is ready; worksheet access still requires verification.")
        else:
            return inspect_sheet(args)
        return 0
    except AuthError as error:
        print(f"Authorization unavailable: {error.code}")
        return 1


def inspect_sheet(args):
    """Read-only local teacher diagnostic; never emits question/answer content."""
    from .recognition import RecognitionError, recognize
    from .sheets_gateway import GatewayError, SheetsGateway, build_google_service, parse_sheets_url
    try:
        spreadsheet_id, gid = parse_sheets_url(args.url)
        sheet_id = args.sheet_id if args.sheet_id is not None else gid
        if type(sheet_id) is not int or sheet_id < 0:
            raise GatewayError("INVALID_REQUEST", http_status=400)
        credentials = authorize(args.client, args.token, repo_root=args.repo_root)
        sheet = SheetsGateway(build_google_service(credentials)).read_sheet(spreadsheet_id, sheet_id)
        result = recognize(sheet)
        print(json.dumps({"read_only": True, "sheet_id": sheet_id,
            "question_count": result.question_count, "answer_item_count": result.answer_item_count,
            "questions": [{"number": q.display_number, "kind": q.kind,
                "answer_anchors": [item.answer_range.anchor for item in q.items]} for q in result.questions]},
            ensure_ascii=True))
        return 0
    except GatewayError as error:
        print(f"Sheet inspection unavailable: {error.code}")
        return 1
    except RecognitionError as error:
        print(json.dumps({"read_only": True, "errors": [
            {"code": issue.code, "sheet_id": issue.sheet_id, "question_number": issue.question_number}
            for issue in error.issues]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
