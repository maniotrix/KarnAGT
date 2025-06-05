#!/usr/bin/env python3
"""
Comprehensive Type Checking Script
Runs mypy with detailed error reporting and suggestions
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_mypy_check() -> Tuple[bool, List[str]]:
    """Run mypy type checking and return results"""
    print("🔍 Running MyPy Type Checking...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "app/",
                "--config-file=mypy.ini",
                "--show-error-codes",
                "--show-column-numbers",
                "--no-error-summary",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        errors = []
        if result.stdout:
            errors.extend(result.stdout.strip().split("\n"))
        if result.stderr:
            errors.extend(result.stderr.strip().split("\n"))

        # Filter out empty lines
        errors = [error for error in errors if error.strip()]

        success = result.returncode == 0
        return success, errors

    except Exception as e:
        return False, [f"Failed to run mypy: {e}"]


def categorize_errors(errors: List[str]) -> dict:
    """Categorize errors by type for better understanding"""
    categories = {
        "missing_imports": [],
        "attribute_errors": [],
        "type_mismatches": [],
        "missing_type_annotations": [],
        "incompatible_returns": [],
        "other": [],
    }

    for error in errors:
        if "import" in error.lower() and (
            "cannot" in error.lower() or "missing" in error.lower()
        ):
            categories["missing_imports"].append(error)
        elif (
            "has no attribute" in error
            or "Item" in error
            and "has no attribute" in error
        ):
            categories["attribute_errors"].append(error)
        elif "incompatible type" in error.lower() or "expected" in error.lower():
            categories["type_mismatches"].append(error)
        elif "missing type annotation" in error.lower() or "untyped" in error.lower():
            categories["missing_type_annotations"].append(error)
        elif "incompatible return" in error.lower():
            categories["incompatible_returns"].append(error)
        else:
            categories["other"].append(error)

    return categories


def print_error_summary(categories: dict):
    """Print categorized error summary with suggestions"""

    print("\n📊 Error Summary by Category:")
    print("=" * 60)

    total_errors = sum(len(errors) for errors in categories.values())

    if total_errors == 0:
        print("🎉 No type errors found! Your code is type-safe!")
        return

    for category, errors in categories.items():
        if not errors:
            continue

        print(f"\n🔴 {category.replace('_', ' ').title()}: {len(errors)} errors")
        print("-" * 40)

        # Show first few errors as examples
        for error in errors[:3]:
            print(f"  • {error}")

        if len(errors) > 3:
            print(f"  ... and {len(errors) - 3} more")

        # Provide suggestions based on error category
        print(f"\n💡 Suggestions for {category.replace('_', ' ')}:")

        if category == "missing_imports":
            print("  - Install missing type stubs: pip install types-<package>")
            print(
                "  - Add to mypy.ini: [mypy-<package>.*] ignore_missing_imports = true"
            )

        elif category == "attribute_errors":
            print("  - Check for typos in attribute names")
            print("  - Add __getattr__ method for dynamic attributes")
            print("  - Use typing.Protocol for duck typing")

        elif category == "type_mismatches":
            print("  - Check function signatures and return types")
            print("  - Use Union types for multiple possible types")
            print("  - Cast values when necessary: cast(TargetType, value)")

        elif category == "missing_type_annotations":
            print("  - Add type hints to function parameters and return values")
            print("  - Use 'from __future__ import annotations' for forward references")

        elif category == "incompatible_returns":
            print("  - Ensure all return paths return the same type")
            print("  - Use Optional[Type] for functions that might return None")


def print_common_fixes():
    """Print common type checking fixes"""
    print("\n🔧 Common Type Error Fixes:")
    print("=" * 60)

    fixes = [
        ("Missing imports", "pip install types-requests types-redis types-psycopg2"),
        ("Dynamic attributes", "Use __getattr__ or typing.Any"),
        ("Optional values", "Use Optional[Type] or Type | None"),
        ("Multiple types", "Use Union[Type1, Type2] or Type1 | Type2"),
        ("Forward references", "Use 'from __future__ import annotations'"),
        ("Any type", "Use typing.Any for unknown types temporarily"),
        ("Ignore line", "Add # type: ignore[error-code] comment"),
        ("Protocol typing", "Use typing.Protocol for structural typing"),
    ]

    for issue, fix in fixes:
        print(f"  {issue:20} → {fix}")


def run_pylance_check():
    """Check if Pylance settings are configured"""
    print("\n🔍 Checking Pylance Configuration...")

    vscode_settings = Path(".vscode/settings.json")
    if vscode_settings.exists():
        print("  ✅ VS Code settings found")
        with open(vscode_settings) as f:
            content = f.read()
            if "typeCheckingMode" in content and "strict" in content:
                print("  ✅ Pylance strict mode enabled")
            else:
                print("  ⚠️  Pylance strict mode not found in settings")
    else:
        print("  ⚠️  VS Code settings not found")
        print("     Create .vscode/settings.json with Pylance configuration")


def main():
    """Main type checking function"""
    print("🚀 Comprehensive Type Checking")
    print("=" * 60)

    # Check if mypy is installed
    try:
        subprocess.run(
            [sys.executable, "-m", "mypy", "--version"], capture_output=True, check=True
        )
        print("✅ MyPy is installed")
    except subprocess.CalledProcessError:
        print("❌ MyPy not found. Install with: pip install mypy")
        return False

    # Run type checking
    success, errors = run_mypy_check()

    if success:
        print("🎉 Type checking passed! No errors found.")
        run_pylance_check()
        return True

    # Categorize and display errors
    categories = categorize_errors(errors)
    print_error_summary(categories)
    print_common_fixes()
    run_pylance_check()

    print(f"\n📈 Total Errors: {sum(len(errors) for errors in categories.values())}")
    print("\n🎯 Focus on fixing attribute errors and type mismatches first!")

    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
