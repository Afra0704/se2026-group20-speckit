"""Local fixture for exercising 002 before the live 001 adapter is available."""


def get_demo_catalog(_teacher, import_id, import_version):
    if import_id != "demo" or import_version not in (1, 2):
        return None
    return {
        "import_id": import_id,
        "import_version": import_version,
        "questions": [
            {
                "question_id": f"demo-q{question}",
                "display_number": str(question if import_version == 1 else question + 3),
                "kind": "question_set" if question == 2 else "single",
                "items": [
                    {
                        "item_id": f"demo-item-{question}-{item}",
                        "blank_id": f"demo-blank-{question}-{item}",
                        "subitem_label": str(item) if question == 2 else None,
                    }
                    for item in range(1, 3 if question == 2 else 2)
                ],
            }
            for question in range(1, 4)
        ],
    }
