import abc
from typing import List
import re

class CommitMessageGenerator(abc.ABC):
    """
    Abstract base class for commit message generators.
    This allows us to easily swap in an AI-based generator in a future version.
    """
    @abc.abstractmethod
    def generate(self, staged_files: List[str], diff_content: str) -> str:
        """
        Analyzes the staged files and diff to generate a commit message.
        """
        pass

class RuleBasedCommitGenerator(CommitMessageGenerator):
    """
    Generates Conventional Commits using basic heuristics and rules based on 
    the names of the changed files and the diff content.
    """
    def generate(self, staged_files: List[str], diff_content: str) -> str:
        if not staged_files:
            return "chore: update repository"

        file_count = len(staged_files)
        
        # Heuristics based on file paths
        has_tests = any("test" in f.lower() for f in staged_files)
        has_docs = any(f.lower().endswith(".md") or "docs/" in f.lower() for f in staged_files)
        has_config = any(f.endswith(".json") or f.endswith(".toml") or f.endswith(".gitignore") or f.endswith(".txt") for f in staged_files)
        has_python = any(f.endswith(".py") for f in staged_files)

        # Determine prefix
        prefix = "chore"
        if has_tests and not has_python:
            prefix = "test"
        elif has_docs and not has_python:
            prefix = "docs"
        elif has_python:
            # If python files changed, look at the diff for clues
            diff_lower = diff_content.lower()
            if "bug" in diff_lower or "fix" in diff_lower or "error" in diff_lower:
                prefix = "fix"
            elif "refactor" in diff_lower or "clean" in diff_lower:
                prefix = "refactor"
            else:
                prefix = "feat"

        # Determine subject
        if file_count == 1:
            subject = f"update {staged_files[0]}"
            if has_tests:
                subject = f"add/update tests in {staged_files[0]}"
            elif has_docs:
                subject = f"update documentation in {staged_files[0]}"
        elif file_count < 4:
            # Join up to 3 file names
            file_names = [f.split('/')[-1] for f in staged_files]
            subject = f"update {', '.join(file_names)}"
        else:
            # Generic message for many files
            if prefix == "docs":
                subject = f"update {file_count} documentation files"
            elif prefix == "test":
                subject = f"update {file_count} test files"
            elif prefix == "feat" or prefix == "fix":
                subject = f"modify {file_count} project files"
            else:
                subject = f"update {file_count} repository files"

        return f"{prefix}: {subject}"
