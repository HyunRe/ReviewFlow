import re
from typing import List, Tuple

ALLOWED_EXTENSIONS = {".java", ".py", ".js", ".ts", ".go", ".kt", ".sql"}
EXCLUDED_PATTERNS = [
    r"package-lock\.json$", r"yarn\.lock$", r"gradlew.*",
    r"build\.gradle.*", r"pom\.xml$", r"\.gitignore$", r".*\.md$"
]


class DiffParser:
    @staticmethod
    def is_code_file(filename: str) -> bool:
        for pattern in EXCLUDED_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return False
        return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

    @classmethod
    def parse(cls, raw_diff: str) -> Tuple[str, List[str]]:
        if not raw_diff:
            return "", []

        file_diffs = re.split(r'(^diff --git a/.* b/.*$)', raw_diff, flags=re.MULTILINE)
        filtered_chunks, target_files = [], []

        i = 1
        while i < len(file_diffs):
            header = file_diffs[i]
            body = file_diffs[i + 1] if i + 1 < len(file_diffs) else ""
            match = re.search(r'b/(.+)$', header)

            if match:
                filename = match.group(1).strip()
                if cls.is_code_file(filename):
                    target_files.append(filename)
                    clean_body = re.sub(r'^(index|---|Signal|\+\+\+).*\n?', '', body, flags=re.MULTILINE)
                    filtered_chunks.append(f"File: {filename}\n{clean_body.strip()}")
            i += 2

        compact_diff = "\n\n".join(filtered_chunks)
        return compact_diff, target_files