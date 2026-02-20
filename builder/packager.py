"""Packaging module — compiles the Viewer into a branded standalone .exe."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable


class Packager:
    """Produces a branded, standalone GuidWire Viewer executable."""

    def build(
        self,
        tree_json_path: str | Path,
        logo_path: str | Path,
        company_name: str,
        output_dir: str | Path,
        progress_callback: Callable[[str], None] | None = None,
    ) -> Path:
        """Build a standalone viewer .exe for the given tree and branding.

        Args:
            tree_json_path: Path to the validated tree.json produced by TreeBuilder.
            logo_path: Path to the company logo image (any Pillow-supported format).
            company_name: Company name embedded into config.json and the exe name.
            output_dir: Directory where the finished .exe will be placed.
            progress_callback: Optional callable(message) for progress updates.

        Returns:
            Path to the produced .exe file.

        Raises:
            FileNotFoundError: If required source files are missing.
            RuntimeError: If PyInstaller fails.
        """
        from PIL import Image

        def _log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        tree_json_path = Path(tree_json_path)
        logo_path = Path(logo_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Locate the viewer source directory relative to this file
        viewer_src = Path(__file__).parent.parent / "viewer"
        if not viewer_src.exists():
            raise FileNotFoundError(f"Viewer source directory not found: {viewer_src}")

        with tempfile.TemporaryDirectory(prefix="guidewire_build_") as tmp_str:
            tmp = Path(tmp_str)
            work_dir = tmp / "viewer"

            _log("Copying viewer source to temporary working directory…")
            shutil.copytree(str(viewer_src), str(work_dir))

            assets_dir = work_dir / "assets"
            assets_dir.mkdir(exist_ok=True)

            # Inject tree.json
            _log("Injecting tree.json…")
            shutil.copy2(str(tree_json_path), str(assets_dir / "tree.json"))

            # Process and inject logo
            _log("Processing logo image…")
            img = Image.open(str(logo_path)).convert("RGBA")
            img.thumbnail((300, 300), Image.LANCZOS)
            img.save(str(assets_dir / "logo.png"), format="PNG")

            # Write config.json
            _log("Writing config.json…")
            config = {"company_name": company_name}
            (assets_dir / "config.json").write_text(
                json.dumps(config, indent=2), encoding="utf-8"
            )

            # Run PyInstaller
            safe_name = "".join(
                c if c.isalnum() or c in ("_", "-") else "_"
                for c in company_name
            )
            exe_name = f"GuidWire_{safe_name}"
            main_script = work_dir / "main.py"

            _log(f"Running PyInstaller to build '{exe_name}'…")
            dist_dir = tmp / "dist"
            build_dir = tmp / "build"

            cmd = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onefile",
                "--windowed",
                "--name",
                exe_name,
                "--distpath",
                str(dist_dir),
                "--workpath",
                str(build_dir),
                "--specpath",
                str(tmp),
                "--add-data",
                f"{assets_dir}{os.pathsep}assets",
                str(main_script),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(work_dir),
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"PyInstaller failed with exit code {result.returncode}.\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

            # Find and move the produced exe
            candidates = list(dist_dir.glob(f"{exe_name}*"))
            if not candidates:
                raise RuntimeError(
                    f"PyInstaller succeeded but no output executable found in {dist_dir}"
                )

            exe_file = candidates[0]
            destination = output_dir / exe_file.name
            shutil.move(str(exe_file), str(destination))

            _log(f"Build complete → {destination}")
            return destination
