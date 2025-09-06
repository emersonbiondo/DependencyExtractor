#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dependency Extractor

A command-line tool to recursively extract a subset of a source code project.
It starts from a single entry file, traces its local dependencies, identifies
external packages, and bundles the result into a directory or a zip archive.
Supports both Python and C# projects.
"""

import ast
import logging
import re
import shutil
import sys
import argparse
import zipfile
from pathlib import Path
from typing import Set, List, Optional, Union

# No Python 3.10+, isso é mais robusto. Para versões anteriores,
# uma lista manual seria necessária para máxima compatibilidade.
# In Python 3.10+, this is more robust. For older versions, a manual
# list would be needed for maximum compatibility.
try:
    from sys import stdlib_module_names
except ImportError:
    # Lista parcial para compatibilidade com Python < 3.10
    # Partial list for compatibility with Python < 3.10
    stdlib_module_names = {"os", "sys", "re", "collections", "math", "datetime", "json", "typing"}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DependencyExtractor:
    """
    Encapsulates the logic for recursively extracting a project subset.

    This class handles the analysis of source files, discovery of both local
    and external dependencies, and the final packaging of the results into
    either a directory structure or a zip archive.
    """

    def __init__(self, source_file_path: str, project_root_path: str):
        """
        Initializes the extractor.

        Args:
            source_file_path (str): The absolute or relative path to the entry source file.
            project_root_path (str): The absolute or relative path to the project's root directory.

        Raises:
            FileNotFoundError: If the source file does not exist.
            NotADirectoryError: If the project root is not a valid directory.
        """
        self.source_path = Path(source_file_path).resolve()
        self.project_root = Path(project_root_path).resolve()

        if not self.source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {self.source_path}")
        if not self.project_root.is_dir():
            raise NotADirectoryError(f"Project root not found: {self.project_root}")

        # files_to_copy: Set of resolved paths for files identified as dependencies.
        self.files_to_copy: Set[Path] = set()
        # files_to_process: A queue of files to be analyzed.
        self.files_to_process: List[Path] = [self.source_path]
        # external_python_deps: A set of identified external Python packages.
        self.external_python_deps: Set[str] = set()
        # external_csharp_deps: A set of identified external C# NuGet packages.
        self.external_csharp_deps: Set[str] = set()

    def run_extraction(self, destination: str, zip_output: bool = False) -> None:
        """
        Executes the main extraction workflow.

        This method orchestrates the dependency collection and the final output generation.

        Args:
            destination (str): The path to the output directory or the destination zip file.
            zip_output (bool): If True, creates a zip archive. Otherwise, creates a directory.
        """
        self._collect_local_dependencies()
        self._collect_external_csharp_dependencies()

        destination_path = Path(destination)
        if zip_output:
            self._create_zip_archive(destination_path)
        else:
            self._copy_files_to_dir(destination_path)

        msg_en = "Extraction process completed successfully."
        msg_pt = "Processo de extração concluído com sucesso."
        logging.info(f"{msg_en} / {msg_pt}")

    def _collect_local_dependencies(self) -> None:
        """Recursively analyzes files in the queue to find all local source dependencies."""
        logging.info("Starting recursive analysis of local dependencies...")
        while self.files_to_process:
            current_file = self.files_to_process.pop(0)
            if current_file in self.files_to_copy:
                continue

            logging.info(f"  Analyzing: {current_file.relative_to(self.project_root)}")
            self.files_to_copy.add(current_file)

            try:
                content = current_file.read_text(encoding='utf-8')
                dependencies: Set[Path] = set()
                if current_file.suffix.lower() == '.py':
                    dependencies = self._parse_python_dependencies(content)
                elif current_file.suffix.lower() == '.cs':
                    dependencies = self._parse_csharp_dependencies(content)

                for dep_path in dependencies:
                    if dep_path not in self.files_to_copy:
                        self.files_to_process.append(dep_path)
            except Exception as e:
                logging.warning(f"  Could not parse {current_file.name}: {e}")

    def _parse_python_dependencies(self, content: str) -> Set[Path]:
        """
        Parses Python code content to find local and external dependencies.

        Args:
            content (str): The source code of a Python file.

        Returns:
            Set[Path]: A set of resolved absolute paths to local Python dependencies.
        """
        local_deps: Set[Path] = set()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            module_name: Optional[str] = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
            elif isinstance(node, ast.ImportFrom) and node.level == 0:  # Absolute imports only
                module_name = node.module
            
            if not module_name:
                continue

            resolved_paths = self._resolve_module_path(module_name)
            if resolved_paths:
                local_deps.update(resolved_paths)
            # If not resolved locally and not in stdlib, it's external.
            # Se não resolveu localmente e não é da bibl. padrão, é externo.
            elif module_name.split('.')[0] not in stdlib_module_names:
                self.external_python_deps.add(module_name.split('.')[0])
        return local_deps

    def _parse_csharp_dependencies(self, content: str) -> Set[Path]:
        """
        Parses C# code content to find local dependencies based on 'using' statements.

        Args:
            content (str): The source code of a C# file.

        Returns:
            Set[Path]: A set of resolved absolute paths to local C# dependencies.
        """
        local_deps: Set[Path] = set()
        pattern = re.compile(r'^\s*using\s+([\w\.]+);', re.MULTILINE)
        for match in pattern.finditer(content):
            namespace = match.group(1)
            # Heuristic to ignore common system namespaces
            if namespace.startswith('System') or namespace.startswith('Microsoft'):
                continue
            
            resolved_paths = self._resolve_module_path(namespace)
            if resolved_paths:
                local_deps.update(resolved_paths)
        return local_deps

    def _resolve_module_path(self, name: str) -> Optional[Set[Path]]:
        """
        Tries to find a file or package corresponding to a module/namespace name.

        Args:
            name (str): The name of the module or namespace (e.g., 'my_app.utils').

        Returns:
            Optional[Set[Path]]: A set of resolved file paths, or None if not found.
        """
        path_str = str(Path(*name.split('.')))
        
        # Check for a single file (.py or .cs)
        for ext in ['.cs', '.py']:
            potential_file = self.project_root / (path_str + ext)
            if potential_file.is_file():
                return {potential_file.resolve()}
        
        # Check for a Python package directory (contains __init__.py)
        potential_dir = self.project_root / path_str
        if (potential_dir / '__init__.py').is_file():
            # For packages, add all Python files within that directory recursively
            return set(potential_dir.rglob('*.py'))
        
        return None

    def _collect_external_csharp_dependencies(self) -> None:
        """Scans the project for .csproj files and extracts NuGet package references."""
        logging.info("Scanning for .csproj files to find external C# packages...")
        pattern = re.compile(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', re.IGNORECASE)
        for csproj_file in self.project_root.rglob('*.csproj'):
            logging.info(f"  Reading packages from: {csproj_file.name}")
            content = csproj_file.read_text(encoding='utf-8')
            for match in pattern.finditer(content):
                package, version = match.groups()
                self.external_csharp_deps.add(f"{package}=={version}")

    def _create_zip_archive(self, zip_path: Path) -> None:
        """
        Creates a zip archive with all collected files and dependency lists.

        Args:
            zip_path (Path): The path for the output zip file.
        """
        logging.info(f"Creating zip archive at: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.files_to_copy:
                arcname = file_path.relative_to(self.project_root)
                zf.write(file_path, arcname)
                logging.info(f"  Adding {arcname} to zip.")

            if self.external_python_deps:
                req_content = "\n".join(sorted(list(self.external_python_deps)))
                zf.writestr('requirements.txt', req_content)
                logging.info("  Adding requirements.txt to zip.")

            if self.external_csharp_deps:
                pkg_content = "\n".join(sorted(list(self.external_csharp_deps)))
                zf.writestr('csharp_packages.txt', pkg_content)
                logging.info("  Adding csharp_packages.txt to zip.")

    def _copy_files_to_dir(self, dir_path: Path) -> None:
        """
        Copies all collected files and dependency lists to a target directory.

        Args:
            dir_path (Path): The path to the destination directory.
        """
        logging.info(f"Copying files to directory: {dir_path}")
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir(parents=True)

        for file_path in self.files_to_copy:
            relative_path = file_path.relative_to(self.project_root)
            dest_file = dir_path / relative_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_file)
            logging.info(f"  Copied {relative_path}")

        if self.external_python_deps:
            (dir_path / 'requirements.txt').write_text("\n".join(sorted(list(self.external_python_deps))), encoding='utf-8')
            logging.info("  Created requirements.txt")

        if self.external_csharp_deps:
            (dir_path / 'csharp_packages.txt').write_text("\n".join(sorted(list(self.external_csharp_deps))), encoding='utf-8')
            logging.info("  Created csharp_packages.txt")

def main() -> None:
    """
    Parses command-line arguments and runs the dependency extraction process.
    """
    parser = argparse.ArgumentParser(
        description="Dependency Extractor: A tool to extract a project subset based on dependencies.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source_file", help="The path to the source file to start the extraction from.")
    parser.add_argument("--project-root", "-r", required=True, help="The root directory of the project.")
    
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--output-dir", "-o", default="./extracted_project", help="Destination directory for the extracted files. (Default: ./extracted_project)")
    output_group.add_argument("--zip", "-z", help="Creates a zip archive with the specified name (e.g., my_project.zip).")
    
    args = parser.parse_args()
    
    try:
        extractor = DependencyExtractor(
            source_file_path=args.source_file,
            project_root_path=args.project_root
        )
        if args.zip:
            extractor.run_extraction(destination=args.zip, zip_output=True)
        else:
            extractor.run_extraction(destination=args.output_dir, zip_output=False)

    except (FileNotFoundError, NotADirectoryError) as e:
        logging.critical(str(e))
        sys.exit(1)
    except Exception as e:
        logging.critical(f"A critical error stopped the execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()