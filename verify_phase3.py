#!/usr/bin/env python3
"""Phase 3 Test Suite Setup and Verification Script

This script:
1. Verifies all Phase 3 implementation files exist
2. Runs pytest with coverage reporting for watchlist functionality
3. Validates code quality (ruff, mypy)
4. Generates coverage report

Usage:
    python verify_phase3.py                 # Run all tests
    python verify_phase3.py --coverage      # Run with coverage report
    python verify_phase3.py --lint          # Run linting only
    python verify_phase3.py --type-check    # Run type checking only
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


class Phase3Verifier:
    """Verification suite for Phase 3 implementation."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize verifier with repository root."""
        self.repo_root = repo_root or Path(__file__).parent
        self.component_dir = self.repo_root / "custom_components" / "marinetraffic_tracker"
        self.tests_dir = self.repo_root / "tests"

    def verify_files_exist(self) -> bool:
        """Verify all Phase 3 implementation files exist."""
        print("=" * 70)
        print("Phase 3 File Verification")
        print("=" * 70)

        files_to_check = {
            "Production Files": [
                self.component_dir / "const.py",
                self.component_dir / "config_flow.py",
                self.component_dir / "coordinator.py",
                self.component_dir / "sensor.py",
                self.component_dir / "entity.py",
                self.component_dir / "device_tracker.py",
                self.component_dir / "strings.json",
                self.component_dir / "translations" / "en.json",
            ],
            "Test Files": [
                self.tests_dir / "test_watchlist.py",
                self.tests_dir / "test_config_flow.py",
                self.tests_dir / "test_sensor_attributes.py",
                self.tests_dir / "test_entity_registry_defaults.py",
                self.tests_dir / "test_vessel_device_info.py",
            ],
        }

        all_exist = True
        for category, files in files_to_check.items():
            print(f"\n{category}:")
            for file_path in files:
                exists = file_path.exists()
                status = "✅" if exists else "❌"
                print(f"  {status} {file_path.relative_to(self.repo_root)}")
                if not exists:
                    all_exist = False

        return all_exist

    def run_pytest(self, coverage: bool = False) -> bool:
        """Run pytest tests."""
        print("\n" + "=" * 70)
        print("Running Pytest Test Suite")
        print("=" * 70)

        cmd = ["python", "-m", "pytest", "tests/", "-v"]

        if coverage:
            cmd.extend([
                "--cov=custom_components/marinetraffic_tracker",
                "--cov-report=term-missing",
                "--cov-report=html",
            ])

        print(f"\nCommand: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=self.repo_root)
        return result.returncode == 0

    def run_ruff_check(self) -> bool:
        """Run ruff linting."""
        print("\n" + "=" * 70)
        print("Running Ruff Linting")
        print("=" * 70)

        cmd = ["python", "-m", "ruff", "check", "custom_components", "tests"]
        print(f"\nCommand: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=self.repo_root)
        return result.returncode == 0

    def run_mypy_check(self) -> bool:
        """Run mypy type checking."""
        print("\n" + "=" * 70)
        print("Running Mypy Type Checking")
        print("=" * 70)

        cmd = [
            "python", "-m", "mypy",
            "custom_components/marinetraffic_tracker",
        ]
        print(f"\nCommand: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=self.repo_root)
        return result.returncode == 0

    def run_watchlist_tests_only(self) -> bool:
        """Run only watchlist-related tests."""
        print("\n" + "=" * 70)
        print("Running Watchlist Tests Only")
        print("=" * 70)

        cmd = [
            "python", "-m", "pytest",
            "tests/test_watchlist.py",
            "tests/test_config_flow.py::*watchlist*",
            "tests/test_sensor_attributes.py::*Watchlist*",
            "tests/test_entity_registry_defaults.py::*watchlist*",
            "tests/test_vessel_device_info.py::*Watchlist*",
            "-v", "--tb=short",
        ]

        print(f"\nCommand: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=self.repo_root)
        return result.returncode == 0

    def generate_summary(self, results: dict[str, bool]) -> None:
        """Generate verification summary."""
        print("\n" + "=" * 70)
        print("PHASE 3 VERIFICATION SUMMARY")
        print("=" * 70)

        for check, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")

        all_passed = all(results.values())
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ ALL PHASE 3 VERIFICATION CHECKS PASSED")
        else:
            print("❌ SOME VERIFICATION CHECKS FAILED - SEE DETAILS ABOVE")
        print("=" * 70)

        return all_passed


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 3 Test Suite Setup and Verification"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run linting only",
    )
    parser.add_argument(
        "--type-check",
        action="store_true",
        help="Run type checking only",
    )
    parser.add_argument(
        "--watchlist-only",
        action="store_true",
        help="Run watchlist tests only",
    )
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="Verify files only (no tests)",
    )

    args = parser.parse_args()

    verifier = Phase3Verifier()
    results: dict[str, bool] = {}

    # Always check files exist
    results["Files Exist"] = verifier.verify_files_exist()

    if args.files_only:
        verifier.generate_summary(results)
        return 0 if results["Files Exist"] else 1

    if args.lint:
        results["Ruff Linting"] = verifier.run_ruff_check()
    elif args.type_check:
        results["Mypy Type Checking"] = verifier.run_mypy_check()
    elif args.watchlist_only:
        results["Watchlist Tests"] = verifier.run_watchlist_tests_only()
    else:
        # Full test suite with optional coverage
        results["Pytest Tests"] = verifier.run_pytest(coverage=args.coverage)
        results["Ruff Linting"] = verifier.run_ruff_check()
        results["Mypy Type Checking"] = verifier.run_mypy_check()

    verifier.generate_summary(results)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
