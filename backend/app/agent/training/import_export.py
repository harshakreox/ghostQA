"""
Knowledge Import/Export

Utilities for sharing training data between environments,
teams, and applications.
"""

import json
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KnowledgeImportExport:
    """
    Import and export knowledge base data.

    Supports:
    - Full knowledge base export
    - Selective export by domain
    - Pattern-only export
    - Community knowledge packs
    """

    def __init__(self, data_dir: str = "data/agent_knowledge"):
        """Initialize import/export utility"""
        self.data_dir = Path(data_dir)

    def export_full(self, output_path: str, include_training: bool = False) -> Dict[str, Any]:
        """
        Export entire knowledge base.

        Args:
            output_path: Output file path (.json or .zip)
            include_training: Include raw training batches

        Returns:
            Export summary
        """
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "type": "full_export",
            "selectors": {},
            "patterns": {},
            "recovery": {},
            "global_patterns": {}
        }

        # Export selectors
        selectors_dir = self.data_dir / "selectors"
        if selectors_dir.exists():
            for file in selectors_dir.glob("*.json"):
                with open(file, 'r') as f:
                    domain = file.stem
                    export_data["selectors"][domain] = json.load(f)

        # Export patterns
        patterns_dir = self.data_dir / "patterns"
        if patterns_dir.exists():
            for file in patterns_dir.glob("*.json"):
                with open(file, 'r') as f:
                    export_data["patterns"][file.stem] = json.load(f)

        # Export recovery strategies
        recovery_dir = self.data_dir / "recovery"
        if recovery_dir.exists():
            for file in recovery_dir.glob("*.json"):
                with open(file, 'r') as f:
                    export_data["recovery"][file.stem] = json.load(f)

        # Export global patterns
        global_dir = self.data_dir / "global"
        if global_dir.exists():
            for file in global_dir.glob("*.json"):
                with open(file, 'r') as f:
                    export_data["global_patterns"][file.stem] = json.load(f)

        # Include training data if requested
        if include_training:
            export_data["training_batches"] = []
            training_dir = self.data_dir / "training"
            if training_dir.exists():
                for file in training_dir.glob("batch_*.json"):
                    with open(file, 'r') as f:
                        export_data["training_batches"].append(json.load(f))

        # Calculate stats
        stats = {
            "domains": len(export_data["selectors"]),
            "total_elements": sum(
                len(d.get("pages", {}).get("elements", {}))
                for d in export_data["selectors"].values()
                if isinstance(d, dict)
            ),
            "patterns": len(export_data["patterns"]),
            "global_patterns": len(export_data["global_patterns"])
        }
        export_data["stats"] = stats

        # Save
        output_file = Path(output_path)
        if output_path.endswith(".zip"):
            self._save_as_zip(export_data, output_file)
        else:
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)

        logger.info(f"Exported knowledge to {output_path}: {stats}")
        return stats

    def export_domain(self, domain: str, output_path: str) -> Dict[str, Any]:
        """
        Export knowledge for a specific domain.

        Args:
            domain: Domain to export
            output_path: Output file path

        Returns:
            Export summary
        """
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "type": "domain_export",
            "domain": domain,
            "selectors": {},
            "patterns": [],
            "recovery": {}
        }

        # Load domain selectors
        selector_file = self.data_dir / "selectors" / f"{domain.replace('.', '_')}.json"
        if selector_file.exists():
            with open(selector_file, 'r') as f:
                export_data["selectors"] = json.load(f)

        # Load domain recovery
        recovery_file = self.data_dir / "recovery" / f"{domain.replace('.', '_')}_recovery.json"
        if recovery_file.exists():
            with open(recovery_file, 'r') as f:
                export_data["recovery"] = json.load(f)

        # Save
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        return {
            "domain": domain,
            "elements": len(export_data["selectors"].get("pages", {}))
        }

    def export_patterns_only(self, output_path: str) -> Dict[str, Any]:
        """
        Export only action patterns (useful for sharing common workflows).

        Args:
            output_path: Output file path

        Returns:
            Export summary
        """
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "type": "patterns_export",
            "patterns": {},
            "global_patterns": {}
        }

        # Export patterns
        patterns_dir = self.data_dir / "patterns"
        if patterns_dir.exists():
            for file in patterns_dir.glob("*.json"):
                with open(file, 'r') as f:
                    export_data["patterns"][file.stem] = json.load(f)

        # Export global patterns
        global_dir = self.data_dir / "global"
        if global_dir.exists():
            for file in global_dir.glob("*.json"):
                with open(file, 'r') as f:
                    export_data["global_patterns"][file.stem] = json.load(f)

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        return {
            "patterns": len(export_data["patterns"]),
            "global_patterns": len(export_data["global_patterns"])
        }

    def import_knowledge(
        self,
        import_path: str,
        merge: bool = True,
        filter_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Import knowledge from an export file.

        Args:
            import_path: Path to import file
            merge: Merge with existing or replace
            filter_domains: Only import specific domains

        Returns:
            Import summary
        """
        import_file = Path(import_path)

        if import_path.endswith(".zip"):
            import_data = self._load_from_zip(import_file)
        else:
            with open(import_file, 'r') as f:
                import_data = json.load(f)

        stats = {
            "domains_imported": 0,
            "elements_imported": 0,
            "patterns_imported": 0,
            "skipped": 0
        }

        # Import selectors
        for domain, domain_data in import_data.get("selectors", {}).items():
            if filter_domains and domain not in filter_domains:
                stats["skipped"] += 1
                continue

            target_file = self.data_dir / "selectors" / f"{domain.replace('.', '_')}.json"
            target_file.parent.mkdir(parents=True, exist_ok=True)

            if merge and target_file.exists():
                with open(target_file, 'r') as f:
                    existing = json.load(f)
                domain_data = self._merge_domain_data(existing, domain_data)

            with open(target_file, 'w') as f:
                json.dump(domain_data, f, indent=2)

            stats["domains_imported"] += 1

        # Import patterns
        for pattern_name, pattern_data in import_data.get("patterns", {}).items():
            target_file = self.data_dir / "patterns" / f"{pattern_name}.json"
            target_file.parent.mkdir(parents=True, exist_ok=True)

            if merge and target_file.exists():
                with open(target_file, 'r') as f:
                    existing = json.load(f)
                pattern_data = self._merge_patterns(existing, pattern_data)

            with open(target_file, 'w') as f:
                json.dump(pattern_data, f, indent=2)

            stats["patterns_imported"] += 1

        # Import global patterns
        for pattern_name, pattern_data in import_data.get("global_patterns", {}).items():
            target_file = self.data_dir / "global" / f"{pattern_name}.json"
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with open(target_file, 'w') as f:
                json.dump(pattern_data, f, indent=2)

        # Import recovery strategies
        for recovery_name, recovery_data in import_data.get("recovery", {}).items():
            target_file = self.data_dir / "recovery" / f"{recovery_name}.json"
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with open(target_file, 'w') as f:
                json.dump(recovery_data, f, indent=2)

        logger.info(f"Imported knowledge from {import_path}: {stats}")
        return stats

    def _merge_domain_data(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge domain data, preferring higher confidence selectors"""
        merged = existing.copy()

        for page, page_data in new_data.get("pages", {}).items():
            if page not in merged.get("pages", {}):
                merged.setdefault("pages", {})[page] = page_data
            else:
                # Merge elements
                existing_page = merged["pages"][page]
                for elem_key, elem_data in page_data.get("elements", {}).items():
                    if elem_key not in existing_page.get("elements", {}):
                        existing_page.setdefault("elements", {})[elem_key] = elem_data
                    else:
                        # Merge selectors
                        existing_selectors = {
                            s["value"]: s
                            for s in existing_page["elements"][elem_key].get("selectors", [])
                        }
                        for sel in elem_data.get("selectors", []):
                            sel_value = sel.get("value")
                            if sel_value not in existing_selectors:
                                existing_page["elements"][elem_key].setdefault("selectors", []).append(sel)
                            elif sel.get("confidence", 0) > existing_selectors[sel_value].get("confidence", 0):
                                # Update with higher confidence
                                idx = next(
                                    i for i, s in enumerate(existing_page["elements"][elem_key]["selectors"])
                                    if s.get("value") == sel_value
                                )
                                existing_page["elements"][elem_key]["selectors"][idx] = sel

        return merged

    def _merge_patterns(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge pattern data"""
        merged = existing.copy()

        if isinstance(new_data, list):
            existing_ids = {p.get("id") for p in merged if isinstance(p, dict)}
            for pattern in new_data:
                if pattern.get("id") not in existing_ids:
                    merged.append(pattern)
        elif isinstance(new_data, dict):
            for key, value in new_data.items():
                if key not in merged:
                    merged[key] = value

        return merged

    def _save_as_zip(self, data: Dict[str, Any], output_path: Path):
        """Save export as zip file"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("knowledge.json", json.dumps(data, indent=2))

    def _load_from_zip(self, import_path: Path) -> Dict[str, Any]:
        """Load import from zip file"""
        with zipfile.ZipFile(import_path, 'r') as zf:
            with zf.open("knowledge.json") as f:
                return json.load(f)

    # ==================== Community Packs ====================

    def create_community_pack(
        self,
        name: str,
        description: str,
        domains: List[str],
        output_path: str,
        author: str = "Anonymous"
    ) -> Dict[str, Any]:
        """
        Create a shareable community knowledge pack.

        Args:
            name: Pack name
            description: What this pack covers
            domains: Domains to include
            output_path: Output file path
            author: Pack author

        Returns:
            Pack summary
        """
        pack_data = {
            "pack_info": {
                "name": name,
                "description": description,
                "author": author,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "pack_id": hashlib.md5(f"{name}_{datetime.utcnow()}".encode()).hexdigest()[:12]
            },
            "selectors": {},
            "patterns": {},
            "global_patterns": {}
        }

        # Export specified domains
        for domain in domains:
            selector_file = self.data_dir / "selectors" / f"{domain.replace('.', '_')}.json"
            if selector_file.exists():
                with open(selector_file, 'r') as f:
                    pack_data["selectors"][domain] = json.load(f)

        # Include relevant patterns
        patterns_dir = self.data_dir / "patterns"
        if patterns_dir.exists():
            for file in patterns_dir.glob("*.json"):
                with open(file, 'r') as f:
                    pack_data["patterns"][file.stem] = json.load(f)

        # Include global patterns
        global_dir = self.data_dir / "global"
        if global_dir.exists():
            for file in global_dir.glob("*.json"):
                with open(file, 'r') as f:
                    pack_data["global_patterns"][file.stem] = json.load(f)

        # Save as zip
        self._save_as_zip(pack_data, Path(output_path))

        return {
            "pack_id": pack_data["pack_info"]["pack_id"],
            "name": name,
            "domains": len(pack_data["selectors"]),
            "patterns": len(pack_data["patterns"])
        }

    def install_community_pack(self, pack_path: str, merge: bool = True) -> Dict[str, Any]:
        """
        Install a community knowledge pack.

        Args:
            pack_path: Path to pack file
            merge: Merge with existing knowledge

        Returns:
            Installation summary
        """
        return self.import_knowledge(pack_path, merge=merge)
