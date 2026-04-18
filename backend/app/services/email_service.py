import json


class EmailService:
    def draft_missing_info_email(self, candidate: dict) -> str:
        parsed = candidate.get("parsed_json")
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}

        name = (
            candidate.get("full_name")
            or (parsed.get("personal_info") or {}).get("full_name")
            or "Candidate"
        )

        missing_info = candidate.get("missing_info")
        if not missing_info:
            missing_info = parsed.get("missing_info")

        if isinstance(missing_info, dict):
            missing_fields = missing_info.get("missing_fields") or []
        elif isinstance(missing_info, list):
            missing_fields = missing_info
        else:
            missing_fields = []

        missing_fields = [str(item).strip() for item in missing_fields if str(item).strip()]

        if not missing_fields:
            return (
                f"Dear {name},\n\n"
                "Thank you for your application. We have all the necessary information to proceed with your application.\n\n"
                "Best regards,\nRecruitment Team"
            )

        missing_text = "\n".join(f"- {field}" for field in missing_fields)
        return (
            f"Dear {name},\n\n"
            "Thank you for your application. We noticed that the following information is missing from your application:\n"
            f"{missing_text}\n\n"
            "Please provide this information at your earliest convenience to proceed with your application.\n\n"
            "Best regards,\nRecruitment Team"
        )

