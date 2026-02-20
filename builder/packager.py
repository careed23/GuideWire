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
                "--paths",
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
                timeout=600,
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

    def build_library_viewer(
        self,
        content_dir: str | Path,
        company_name: str,
        output_dir: str | Path,
        progress_callback: Callable[[str], None] | None = None,
    ) -> Path:
        """Build a standalone offline library viewer executable.

        Unlike :meth:`build`, the content folder (``*_Content/``) is **not**
        embedded inside the exe; it must be placed next to the exe at runtime.
        Only a small ``viewer_config.json`` (containing the content folder
        name) is embedded so the viewer knows where to look.

        Args:
            content_dir: Path to the ``*_Content`` folder produced by
                         :class:`LibraryBuilder` (used only to verify it
                         exists and to read its name).
            company_name: Company / project name; used in the exe filename.
            output_dir: Directory where the finished exe will be placed.
            progress_callback: Optional callable(message) for progress updates.

        Returns:
            Path to the produced exe file.

        Raises:
            FileNotFoundError: If the content folder or viewer source is missing.
            RuntimeError: If PyInstaller fails.
        """

        def _log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        content_dir = Path(content_dir)
        if not content_dir.exists():
            raise FileNotFoundError(f"Content directory not found: {content_dir}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        viewer_src = Path(__file__).parent.parent / "viewer"
        if not viewer_src.exists():
            raise FileNotFoundError(f"Viewer source directory not found: {viewer_src}")

        safe_name = "".join(
            c if c.isalnum() or c in ("_", "-") else "_" for c in company_name
        )
        content_folder_name = content_dir.name
        exe_name = f"GuidWire_{safe_name}_LibraryViewer"

        with tempfile.TemporaryDirectory(prefix="guidewire_lib_build_") as tmp_str:
            tmp = Path(tmp_str)
            work_dir = tmp / "viewer"

            _log("Copying viewer source to temporary working directory…")
            shutil.copytree(str(viewer_src), str(work_dir))

            assets_dir = work_dir / "assets"
            assets_dir.mkdir(exist_ok=True)

            # Embed a small config so the viewer knows the content folder name
            _log("Writing viewer_config.json…")
            (assets_dir / "viewer_config.json").write_text(
                json.dumps({"content_folder": content_folder_name}, indent=2),
                encoding="utf-8",
            )

            main_script = work_dir / "library_main.py"
            dist_dir = tmp / "dist"
            build_dir = tmp / "build"

            _log(f"Running PyInstaller to build '{exe_name}'…")
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
                "--paths",
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
                timeout=600,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"PyInstaller failed with exit code {result.returncode}.\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )

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
