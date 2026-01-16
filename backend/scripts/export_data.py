#!/usr/bin/env python3
"""
GhostQA Data Export Script

This script exports all data from the GhostQA system into a compressed zip file
for migration to another system.

Usage:
    python export_data.py [--output OUTPUT_PATH] [--exclude CATEGORY1,CATEGORY2]

Examples:
    python export_data.py
    python export_data.py --output /path/to/backup.zip
    python export_data.py --exclude reports,results
"""

import os
import sys
import json
import zipfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Set

# Get the backend directory path
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "app" / "data"

# Data categories that can be exported
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


def get_file_count(directory: Path) -> int:
    """Count JSON files in a directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.json")))


def get_dir_size(directory: Path) -> int:
    """Get total size of directory in bytes."""
    if not directory.exists():
        return 0
    total = 0
    for path in directory.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def create_export_metadata(categories: List[str], exclude: Set[str]) -> dict:
    """Create metadata about the export."""
    metadata = {
        "export_version": "1.0",
        "export_timestamp": datetime.now().isoformat(),
        "ghostqa_version": "1.0.0",
        "source_system": os.environ.get("COMPUTERNAME", "unknown"),
        "categories_exported": [],
        "categories_excluded": list(exclude),
        "statistics": {}
    }

    total_files = 0
    total_size = 0

    for category in categories:
        if category in exclude:
            continue

        category_dir = DATA_DIR / category
        file_count = get_file_count(category_dir)
        dir_size = get_dir_size(category_dir)

        metadata["categories_exported"].append(category)
        metadata["statistics"][category] = {
            "file_count": file_count,
            "size_bytes": dir_size,
            "size_human": format_size(dir_size)
        }

        total_files += file_count
        total_size += dir_size

    metadata["statistics"]["total"] = {
        "file_count": total_files,
        "size_bytes": total_size,
        "size_human": format_size(total_size)
    }

    return metadata


def export_data(
    output_path: Optional[str] = None,
    exclude_categories: Optional[Set[str]] = None
) -> str:
    """
    Export all GhostQA data to a zip file.

    Args:
        output_path: Custom output path for the zip file
        exclude_categories: Set of category names to exclude from export

    Returns:
        Path to the created zip file
    """
    exclude = exclude_categories or set()

    # Generate default output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = BACKEND_DIR / f"ghostqa_export_{timestamp}.zip"
    else:
        output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("GhostQA Data Export")
    print(f"{'='*60}")
    print(f"Source: {DATA_DIR}")
    print(f"Output: {output_path}")

    if exclude:
        print(f"Excluding: {', '.join(exclude)}")

    print(f"\n{'='*60}")
    print("Scanning data directories...")
    print(f"{'='*60}\n")

    # Create metadata
    metadata = create_export_metadata(DATA_CATEGORIES, exclude)

    # Print statistics
    for category in metadata["categories_exported"]:
        stats = metadata["statistics"][category]
        print(f"  {category:20} : {stats['file_count']:5} files ({stats['size_human']})")

    print(f"\n  {'TOTAL':20} : {metadata['statistics']['total']['file_count']:5} files "
          f"({metadata['statistics']['total']['size_human']})")

    if metadata["statistics"]["total"]["file_count"] == 0:
        print("\nWarning: No data files found to export!")
        return None

    print(f"\n{'='*60}")
    print("Creating export archive...")
    print(f"{'='*60}\n")

    # Create the zip file
    files_exported = 0
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add metadata file
        metadata_json = json.dumps(metadata, indent=2, default=str)
        zipf.writestr("_export_metadata.json", metadata_json)

        # Export each category
        for category in metadata["categories_exported"]:
            category_dir = DATA_DIR / category

            if not category_dir.exists():
                continue

            print(f"  Exporting {category}...")

            # Walk through all files in the category directory
            for file_path in category_dir.rglob("*"):
                if file_path.is_file():
                    # Calculate relative path from data directory
                    rel_path = file_path.relative_to(DATA_DIR)

                    # Add file to zip with preserved directory structure
                    zipf.write(file_path, f"data/{rel_path}")
                    files_exported += 1

        # Export any root-level files in data directory (like .gitkeep, marker files)
        for file_path in DATA_DIR.glob("*"):
            if file_path.is_file():
                zipf.write(file_path, f"data/{file_path.name}")

    # Get final zip file size
    zip_size = output_path.stat().st_size

    print(f"\n{'='*60}")
    print("Export Complete!")
    print(f"{'='*60}")
    print(f"  Files exported : {files_exported}")
    print(f"  Archive size   : {format_size(zip_size)}")
    print(f"  Output file    : {output_path}")
    print(f"{'='*60}\n")

    return str(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export GhostQA data to a zip file for migration"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for the zip file (default: ghostqa_export_<timestamp>.zip)"
    )
    parser.add_argument(
        "--exclude", "-e",
        help="Comma-separated list of categories to exclude (e.g., reports,results)"
    )
    parser.add_argument(
        "--list-categories", "-l",
        action="store_true",
        help="List available data categories and exit"
    )

    args = parser.parse_args()

    if args.list_categories:
        print("\nAvailable data categories:")
        for category in DATA_CATEGORIES:
            category_dir = DATA_DIR / category
            count = get_file_count(category_dir)
            size = format_size(get_dir_size(category_dir))
            print(f"  - {category:20} ({count} files, {size})")
        return

    exclude = set()
    if args.exclude:
        exclude = {cat.strip().lower() for cat in args.exclude.split(",")}
        invalid = exclude - set(DATA_CATEGORIES)
        if invalid:
            print(f"Warning: Unknown categories will be ignored: {', '.join(invalid)}")
            exclude = exclude & set(DATA_CATEGORIES)

    try:
        result = export_data(
            output_path=args.output,
            exclude_categories=exclude
        )
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\nError during export: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
