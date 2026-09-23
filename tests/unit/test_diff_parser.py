import pytest
from src.domain.diff_parser import DiffParser


def test_is_code_file_allowed_extensions():
    """허용된 확장자(.py, .java 등) 검증"""
    assert DiffParser.is_code_file("src/main.py") is True
    assert DiffParser.is_code_file("UserService.java") is True
    assert DiffParser.is_code_file("script.js") is True


def test_is_code_file_excluded_patterns():
    """제외 패턴(.md, lock 파일, gradle 등) 필터링 검증"""
    assert DiffParser.is_code_file("README.md") is False
    assert DiffParser.is_code_file("package-lock.json") is False
    assert DiffParser.is_code_file("build.gradle") is False
    assert DiffParser.is_code_file(".gitignore") is False


def test_parse_raw_diff():
    """raw_diff 파싱 및 필터링 동작 검증"""
    sample_diff = """diff --git a/src/main.py b/src/main.py
index 1234567..89abcdef 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
+print("Hello World")
diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,1 +1,2 @@
+# Title
"""

    compact_diff, target_files = DiffParser.parse(sample_diff)

    # README.md는 제외되고 main.py만 대상 파일로 선택되었는지 확인
    assert target_files == ["src/main.py"]
    assert "File: src/main.py" in compact_diff
    assert "README.md" not in compact_diff
    assert 'print("Hello World")' in compact_diff