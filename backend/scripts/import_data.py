#!/usr/bin/env python3
"""
GhostQA Data Import Script

This script imports data from a GhostQA export zip file into the current system.
Use this to migrate data from one GhostQA installation to another.

Usage:
    python import_data.py <export_file.zip> [options]

Examples:
    python import_data.py ghostqa_export_20240115.zip
    python import_data.py backup.zip --strategy overwrite
    python import_data.py backup.zip --strategy skip --only users,projects
    python import_data.py backup.zip --dry-run

Conflict Strategies:
    skip      - Skip files that already exist (default)
    overwrite - Overwrite existing files
    backup    - Backup existing files before overwriting
"""

import os
import sys
import json
import zipfile
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Dict, List, Tuple
from enum import Enum


# Get the backend directory path
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "app" / "data"

# Data categories
DATA_CATEGORIES = [
    "projects",
    "features",
    "traditional",
    "folders",
    "users",
    "organizations",
    "org_members",
    "project_members",
    "org_invites",
    "reports",
    "results",
    "agent_knowledge",
]


class ConflictStrategy(Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    BACKUP = "backup"


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def validate_export_file(zip_path: Path) -> Tuple[bool, dict, str]:
    """
    Validate the export file and extract metadata.

    Returns:
        Tuple of (is_valid, metadata, error_message)
    """
    if not zip_path.exists():
        return False, {}, f"File not found: {zip_path}"

    if not zipfile.is_zipfile(zip_path):
        return False, {}, f"Invalid zip file: {zip_path}"

    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Check for metadata file
            if "_export_metadata.json" not in zipf.namelist():
                return False, {}, "Missing export metadata - not a valid GhostQA export"

            # Read metadata
            metadata_content = zipf.read("_export_metadata.json").decode('utf-8')
            metadata = json.loads(metadata_content)

            # Validate metadata structure
            required_fields = ["export_version", "export_timestamp", "categories_exported"]
            for field in required_fields:
                if field not in metadata:
                    return False, {}, f"Invalid metadata: missing {field}"

            return True, metadata, ""

    except zipfile.BadZipFile:
        return False, {}, "Corrupted zip file"
    except json.JSONDecodeError:
        return False, {}, "Invalid metadata JSON"
    except Exception as e:
        return False, {}, f"Error reading export file: {e}"


def analyze_conflicts(
    zip_path: Path,
    metadata: dict,
    only_categories: Optional[Set[str]] = None
) -> Dict[str, List[str]]:
    """
    Analyze which files would conflict with existing data.

    Returns:
        Dictionary mapping categories to lists of conflicting file paths
    """
    conflicts = {}

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for name in zipf.namelist():
            if name == "_export_metadata.json":
                continue

            if not name.startswith("data/"):
                continue

            # Get relative path
            rel_path = name[5:]  # Remove "data/" prefix

            if not rel_path:
                continue

            # Get category from path
            parts = rel_path.split("/")
            category = parts[0]

            # Skip if not in requested categories
            if only_categories and category not in only_categories:
                continue

            # Check if file exists
            target_path = DATA_DIR / rel_path
            if target_path.exists():
                if category not in conflicts:
                    conflicts[category] = []
                conflicts[category].append(rel_path)

    return conflicts


def create_backup(backup_dir: Path, file_path: Path) -> bool:
    """Create a backup of a file before overwriting."""
    try:
        backup_path = backup_dir / file_path.relative_to(DATA_DIR)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        return True
    except Exception as e:
        print(f"    Warning: Failed to backup {file_path}: {e}")
        return False


def import_data(
    zip_path: Path,
    strategy: ConflictStrategy = ConflictStrategy.SKIP,
    only_categories: Optional[Set[str]] = None,
    dry_run: bool = False
) -> dict:
    """
    Import data from a GhostQA export file.

    Args:
        zip_path: Path to the export zip file
        strategy: How to handle file conflicts
        only_categories: Optional set of categories to import (None = all)
        dry_run: If True, only simulate the import

    Returns:
        Dictionary with import statistics
    """
    print(f"\n{'='*60}")
    print("GhostQA Data Import")
    print(f"{'='*60}")
    print(f"Source: {zip_path}")
    print(f"Target: {DATA_DIR}")
    print(f"Strategy: {strategy.value}")
    if only_categories:
        print(f"Categories: {', '.join(only_categories)}")
    if dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***")

    # Validate export file
    print(f"\n{'='*60}")
    print("Validating export file...")
    print(f"{'='*60}\n")

    is_valid, metadata, error = validate_export_file(zip_path)
    if not is_valid:
        print(f"  Error: {error}")
        return {"success": False, "error": error}

    print(f"  Export version  : {metadata.get('export_version', 'unknown')}")
    print(f"  Export date     : {metadata.get('export_timestamp', 'unknown')}")
    print(f"  Source system   : {metadata.get('source_system', 'unknown')}")
    print(f"  Categories      : {', '.join(metadata.get('categories_exported', []))}")

    if "statistics" in metadata and "total" in metadata["statistics"]:
        total_stats = metadata["statistics"]["total"]
        print(f"  Total files     : {total_stats.get('file_count', 'unknown')}")
        print(f"  Total size      : {total_stats.get('size_human', 'unknown')}")

    # Analyze conflicts
    print(f"\n{'='*60}")
    print("Analyzing conflicts...")
    print(f"{'='*60}\n")

    conflicts = analyze_conflicts(zip_path, metadata, only_categories)
    total_conflicts = sum(len(files) for files in conflicts.values())

    if total_conflicts > 0:
        print(f"  Found {total_conflicts} conflicting file(s):")
        for category, files in conflicts.items():
            print(f"    {category}: {len(files)} file(s)")
        print(f"\n  Strategy '{strategy.value}' will be applied to conflicts.")
    else:
        print("  No conflicts found.")

    # Create backup directory if needed
    backup_dir = None
    if strategy == ConflictStrategy.BACKUP and total_conflicts > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BACKEND_DIR / f"backup_before_import_{timestamp}"
        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Backup directory: {backup_dir}")

    # Import data
    print(f"\n{'='*60}")
    print("Importing data...")
    print(f"{'='*60}\n")

    stats = {
        "success": True,
        "files_imported": 0,
        "files_skipped": 0,
        "files_overwritten": 0,
        "files_backed_up": 0,
        "errors": [],
        "by_category": {}
    }

    # Filter categories to import
    categories_to_import = set(metadata.get("categories_exported", []))
    if only_categories:
        categories_to_import = categories_to_import & only_categories

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for name in zipf.namelist():
            if name == "_export_metadata.json":
                continue

            if not name.startswith("data/"):
                continue

            rel_path = name[5:]  # Remove "data/" prefix

            if not rel_path:
                continue

            # Check if it's a directory entry
            if name.endswith("/"):
                target_dir = DATA_DIR / rel_path
                if not dry_run and not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                continue

            # Get category
            parts = rel_path.split("/")
            category = parts[0]

            # Skip if not in requested categories
            if category not in categories_to_import and category in DATA_CATEGORIES:
                continue

            # Initialize category stats
            if category not in stats["by_category"]:
                stats["by_category"][category] = {
                    "imported": 0,
                    "skipped": 0,
                    "overwritten": 0
                }

            target_path = DATA_DIR / rel_path
            file_exists = target_path.exists()

            # Handle conflicts based on strategy
            if file_exists:
                if strategy == ConflictStrategy.SKIP:
                    stats["files_skipped"] += 1
                    stats["by_category"][category]["skipped"] += 1
                    continue

                elif strategy == ConflictStrategy.BACKUP:
                    if not dry_run:
                        create_backup(backup_dir, target_path)
                    stats["files_backed_up"] += 1

                stats["files_overwritten"] += 1
                stats["by_category"][category]["overwritten"] += 1
            else:
                stats["by_category"][category]["imported"] += 1

            # Extract file
            if not dry_run:
                try:
                    # Ensure parent directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract file
                    with zipf.open(name) as src:
                        with open(target_path, 'wb') as dst:
                            dst.write(src.read())

                    stats["files_imported"] += 1
                except Exception as e:
                    stats["errors"].append(f"{rel_path}: {e}")
                    print(f"    Error importing {rel_path}: {e}")
            else:
                stats["files_imported"] += 1

    # Print category summary
    print("  Import summary by category:")
    for category in sorted(stats["by_category"].keys()):
        cat_stats = stats["by_category"][category]
        imported = cat_stats["imported"]
        skipped = cat_stats["skipped"]
        overwritten = cat_stats["overwritten"]
        total = imported + skipped + overwritten
        print(f"    {category:20} : {total:4} files "
              f"(new: {imported}, skipped: {skipped}, overwritten: {overwritten})")

    # Final summary
    print(f"\n{'='*60}")
    print("Import Complete!" + (" (DRY RUN)" if dry_run else ""))
    print(f"{'='*60}")
    print(f"  Files imported    : {stats['files_imported']}")
    print(f"  Files skipped     : {stats['files_skipped']}")
    print(f"  Files overwritten : {stats['files_overwritten']}")
    if stats["files_backed_up"] > 0:
        print(f"  Files backed up   : {stats['files_backed_up']}")
    if stats["errors"]:
        print(f"  Errors            : {len(stats['errors'])}")
    print(f"{'='*60}\n")

    if stats["errors"]:
        print("Errors encountered:")
        for error in stats["errors"][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(stats["errors"]) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more errors")

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import GhostQA data from an export zip file"
    )
    parser.add_argument(
        "export_file",
        help="Path to the GhostQA export zip file"
    )
    parser.add_argument(
        "--strategy", "-s",
        choices=["skip", "overwrite", "backup"],
        default="skip",
        help="How to handle conflicting files (default: skip)"
    )
    parser.add_argument(
        "--only", "-o",
        help="Comma-separated list of categories to import (default: all)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Simulate the import without making changes"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    zip_path = Path(args.export_file)
    strategy = ConflictStrategy(args.strategy)

    only_categories = None
    if args.only:
        only_categories = {cat.strip().lower() for cat in args.only.split(",")}
        invalid = only_categories - set(DATA_CATEGORIES)
        if invalid:
            print(f"Warning: Unknown categories will be ignored: {', '.join(invalid)}")
            only_categories = only_categories & set(DATA_CATEGORIES)

    # Validate file exists
    if not zip_path.exists():
        print(f"Error: File not found: {zip_path}")
        sys.exit(1)

    # Confirm before proceeding (unless dry-run or forced)
    if not args.dry_run and not args.force:
        print(f"\nThis will import data from: {zip_path}")
        print(f"Into target directory: {DATA_DIR}")
        print(f"Conflict strategy: {strategy.value}")
        response = input("\nProceed with import? [y/N]: ").strip().lower()
        if response != 'y':
            print("Import cancelled.")
            sys.exit(0)

    try:
        result = import_data(
            zip_path=zip_path,
            strategy=strategy,
            only_categories=only_categories,
            dry_run=args.dry_run
        )

        if result["success"]:
            if not args.dry_run and result["files_imported"] > 0:
                print("Note: You may need to restart the GhostQA server for changes to take effect.")
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\nError during import: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
