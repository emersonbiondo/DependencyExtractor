#!/usr/-bin/env python3
# -*- coding: utf-8 -*-

"""
Dependency Extractor (Advanced, Multithreaded, Multi-Source, Bilingual)

[EN] A high-reliability tool to extract project subsets from one or more source files.
[PT-BR] Uma ferramenta de alta confiabilidade para extrair subconjuntos de projetos a partir de um ou mais arquivos de origem.
"""
import concurrent.futures
import json
import ast
import logging
import re
import shutil
import sys
import argparse
import zipfile
from pathlib import Path
from typing import Set, List, Optional, Dict, Any, Tuple

# [EN] In Python 3.10+, this is more robust. For older versions, a manual
#      list would be needed for maximum compatibility.
# [PT-BR] No Python 3.10+, isto é mais robusto. Para versões anteriores,
#         uma lista manual seria necessária para máxima compatibilidade.
try:
    from sys import stdlib_module_names
except ImportError:
    # [EN] Partial list for compatibility with Python < 3.10
    # [PT-BR] Lista parcial para compatibilidade com Python < 3.10
    stdlib_module_names = {"os", "sys", "re", "collections", "math", "datetime", "json", "typing"}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DependencyExtractor:
    """
    [EN] Encapsulates the advanced logic for recursively extracting a project subset.
    [PT-BR] Encapsula a lógica avançada para extrair recursivamente um subconjunto de projeto.
    """
    def __init__(self, source_file_paths: List[str], project_root_path: str):
        self.project_root = Path(project_root_path).resolve()
        if not self.project_root.is_dir():
            msg = f"[EN] Project root not found: {self.project_root} / [PT-BR] Diretório raiz do projeto não encontrado: {self.project_root}"
            raise NotADirectoryError(msg)

        self.files_to_process: List[Path] = []
        for path_str in source_file_paths:
            source_path = Path(path_str).resolve()
            if not source_path.is_file():
                msg = f"[EN] Source file not found: {source_path} / [PT-BR] Arquivo de origem não encontrado: {source_path}"
                raise FileNotFoundError(msg)
            self.files_to_process.append(source_path)

        self.files_to_copy: Set[Path] = set()
        self.external_python_deps: Set[str] = set()
        self.external_csharp_deps: Set[str] = set()
        self.csharp_type_to_path_map: Dict[str, Path] = {}
        self.is_csharp_project = any(p.suffix.lower() == '.cs' for p in self.files_to_process)


    def run_extraction(self, output_dir: Optional[str] = None, zip_file: Optional[str] = None) -> None:
        if self.is_csharp_project:
            self._build_csharp_type_index_multithreaded()

        self._collect_local_dependencies()
        self._collect_external_csharp_dependencies()

        if not self.files_to_copy:
            msg = "[EN] No local source files were found or collected. Halting output generation. / [PT-BR] Nenhum arquivo de código-fonte local foi encontrado ou coletado. Interrompendo a geração de saída."
            logging.warning(msg)
            return

        if output_dir:
            self._copy_files_to_dir(Path(output_dir))
        if zip_file:
            self._create_zip_archive(Path(zip_file))

        msg = "[EN] Extraction process completed successfully. / [PT-BR] Processo de extração concluído com sucesso."
        logging.info(msg)

    def _index_single_file(self, file_path: Path) -> List[Tuple[str, Path]]:
        type_def_pattern = re.compile(r'\b(?:public|internal|private|protected)?\s*(?:partial|static|abstract)?\s*(class|interface|enum|struct)\s+([a-zA-Z0-9_]+)')
        found_types = []
        try:
            content = file_path.read_text(encoding='utf-8')
            matches = type_def_pattern.finditer(content)
            for match in matches:
                type_name = match.group(2)
                found_types.append((type_name, file_path))
        except Exception:
            # [EN] Ignore files that cannot be read
            # [PT-BR] Ignora arquivos que não podem ser lidos
            pass
        return found_types

    def _build_csharp_type_index_multithreaded(self) -> None:
        logging.info("[EN] Indexing C# project files using multiple threads... / [PT-BR] Indexando arquivos de projeto C# usando múltiplas threads...")
        
        cs_files = list(self.project_root.rglob('*.cs'))
        logging.info(f"[EN] Found {len(cs_files)} C# files to index. / [PT-BR] Encontrados {len(cs_files)} arquivos C# para indexar.")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self._index_single_file, cs_files)
            
            for file_results in results:
                for type_name, file_path in file_results:
                    if type_name not in self.csharp_type_to_path_map:
                        self.csharp_type_to_path_map[type_name] = file_path
        
        msg = f"[EN] Indexing complete. Found {len(self.csharp_type_to_path_map)} unique C# types. / [PT-BR] Indexação completa. Encontrados {len(self.csharp_type_to_path_map)} tipos C# únicos."
        logging.info(msg)
    
    def _collect_local_dependencies(self) -> None:
        logging.info("[EN] Starting recursive analysis of local dependencies... / [PT-BR] Iniciando análise recursiva de dependências locais...")
        while self.files_to_process:
            current_file = self.files_to_process.pop(0)
            if current_file in self.files_to_copy:
                continue
            logging.info(f"[EN]   Analyzing: {current_file.relative_to(self.project_root)} / [PT-BR]   Analisando: {current_file.relative_to(self.project_root)}")
            self.files_to_copy.add(current_file)
            try:
                content = current_file.read_text(encoding='utf-8')
                dependencies: Set[Path] = set()
                if current_file.suffix.lower() == '.py':
                    dependencies = self._parse_python_dependencies(content)
                elif current_file.suffix.lower() == '.cs':
                    dependencies = self._parse_csharp_dependencies_with_index(content)
                
                for dep_path in dependencies:
                    if dep_path not in self.files_to_copy:
                        self.files_to_process.append(dep_path)
            except Exception as e:
                msg = f"[EN] Could not parse {current_file.name}: {e} / [PT-BR] Não foi possível analisar {current_file.name}: {e}"
                logging.warning(f"  {msg}")

    def _parse_csharp_dependencies_with_index(self, content: str) -> Set[Path]:
        dependencies: Set[Path] = set()
        potential_type_pattern = re.compile(r'\b([A-Z][a-zA-Z0-9_<>]+)\b')
        potential_types = set(match.group(1) for match in potential_type_pattern.finditer(content))
        for type_name in potential_types:
            base_type_name = type_name.split('<')[0]
            if base_type_name in self.csharp_type_to_path_map:
                file_path = self.csharp_type_to_path_map[base_type_name]
                dependencies.add(file_path)
        return dependencies

    def _parse_python_dependencies(self, content: str) -> Set[Path]:
        local_deps: Set[Path] = set()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            module_name: Optional[str] = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                module_name = node.module
            
            if not module_name:
                continue
                
            resolved_paths = self._resolve_python_module_path(module_name)
            if resolved_paths:
                local_deps.update(resolved_paths)
            elif module_name.split('.')[0] not in stdlib_module_names:
                self.external_python_deps.add(module_name.split('.')[0])
        return local_deps

    def _resolve_python_module_path(self, name: str) -> Optional[Set[Path]]:
        path_str = str(Path(*name.split('.')))
        for ext in ['.py']:
            potential_file = self.project_root / (path_str + ext)
            if potential_file.is_file():
                return {potential_file.resolve()}
        potential_dir = self.project_root / path_str
        if (potential_dir / '__init__.py').is_file():
            return set(potential_dir.rglob('*.py'))
        return None

    def _collect_external_csharp_dependencies(self) -> None:
        if not self.is_csharp_project: return
        logging.info("[EN] Scanning for .csproj files to find external C# packages... / [PT-BR] Procurando por arquivos .csproj para encontrar pacotes C# externos...")
        pattern = re.compile(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', re.IGNORECASE)
        for csproj_file in self.project_root.rglob('*.csproj'):
            content = csproj_file.read_text(encoding='utf-8')
            for match in pattern.finditer(content):
                package, version = match.groups()
                self.external_csharp_deps.add(f"{package}=={version}")

    def _create_zip_archive(self, zip_path: Path) -> None:
        logging.info(f"[EN] Creating zip archive at: {zip_path} / [PT-BR] Criando arquivo zip em: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.files_to_copy:
                arcname = file_path.relative_to(self.project_root)
                zf.write(file_path, arcname)
            if self.external_python_deps:
                req_content = "\n".join(sorted(list(self.external_python_deps)))
                zf.writestr('requirements.txt', req_content)
            if self.external_csharp_deps:
                pkg_content = "\n".join(sorted(list(self.external_csharp_deps)))
                zf.writestr('csharp_packages.txt', pkg_content)

    def _copy_files_to_dir(self, dir_path: Path) -> None:
        logging.info(f"[EN] Copying files to directory: {dir_path} / [PT-BR] Copiando arquivos para o diretório: {dir_path}")
        if dir_path.exists(): shutil.rmtree(dir_path)
        dir_path.mkdir(parents=True)
        for file_path in self.files_to_copy:
            relative_path = file_path.relative_to(self.project_root)
            dest_file = dir_path / relative_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_file)
        if self.external_python_deps:
            (dir_path / 'requirements.txt').write_text("\n".join(sorted(list(self.external_python_deps))), encoding='utf-8')
        if self.external_csharp_deps:
            (dir_path / 'csharp_packages.txt').write_text("\n".join(sorted(list(self.external_csharp_deps))), encoding='utf-8')

def main() -> None:
    parser = argparse.ArgumentParser(
        description="[EN] Dependency Extractor: A tool to extract a project subset from one or more source files.\n[PT-BR] Dependency Extractor: Uma ferramenta para extrair um subconjunto de projeto a partir de um ou mais arquivos de origem.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source_files", nargs='*', help="[EN] One or more source files to start the extraction from. Can be omitted if using a config file.\n[PT-BR] Um ou mais arquivos de origem para iniciar a extração. Pode ser omitido se usar um arquivo de configuração.")
    parser.add_argument("-r", "--project-root", help="[EN] The root directory of the project.\n[PT-BR] O diretório raiz do projeto.")
    parser.add_argument("-o", "--output-dir", help="[EN] Destination directory for the extracted files.\n[PT-BR] Diretório de destino para os arquivos extraídos.")
    parser.add_argument("-z", "--zip", help="[EN] Creates a zip archive with the specified name.\n[PT-BR] Cria um arquivo zip com o nome especificado.")
    parser.add_argument("-c", "--config", help="[EN] Path to a JSON configuration file.\n[PT-BR] Caminho para um arquivo de configuração JSON.")
    
    args = parser.parse_args()
    
    config: Dict[str, Any] = {}
    if args.config:
        logging.info(f"[EN] Loading configuration from: {args.config} / [PT-BR] Carregando configuração de: {args.config}")
        try:
            config = json.loads(Path(args.config).read_text(encoding='utf-8'))
        except FileNotFoundError:
            msg = f"[EN] Configuration file not found: {args.config} / [PT-BR] Arquivo de configuração não encontrado: {args.config}"
            logging.critical(msg); sys.exit(1)
        except json.JSONDecodeError:
            msg = f"[EN] Error decoding JSON from config file: {args.config} / [PT-BR] Erro ao decodificar JSON do arquivo de configuração: {args.config}"
            logging.critical(msg); sys.exit(1)

    source_files = args.source_files or config.get("source_files")
    if not source_files and "source_file" in config:
        source_files = [config["source_file"]]

    project_root = args.project_root or config.get("project_root")
    output_dir = args.output_dir or config.get("output_dir")
    zip_file = args.zip or config.get("zip")

    if not source_files or not project_root:
        msg = "[EN] Parameters 'source_files' and 'project_root' are required. / [PT-BR] Os parâmetros 'source_files' e 'project_root' são obrigatórios."
        logging.critical(msg); sys.exit(1)
    if not output_dir and not zip_file:
        msg = "[EN] No output specified. Nothing to do. Use -o/--output-dir or -z/--zip. / [PT-BR] Nenhuma saída especificada. Nada a fazer. Use -o/--output-dir ou -z/--zip."
        logging.warning(msg); sys.exit(0)

    try:
        extractor = DependencyExtractor(
            source_file_paths=source_files,
            project_root_path=project_root
        )
        extractor.run_extraction(output_dir=output_dir, zip_file=zip_file)
    except (FileNotFoundError, NotADirectoryError) as e:
        logging.critical(str(e)); sys.exit(1)
    except Exception as e:
        msg = f"[EN] A critical error stopped the execution: {e} / [PT-BR] Um erro crítico interrompeu a execução: {e}"
        logging.critical(msg, exc_info=True); sys.exit(1)

if __name__ == "__main__":
    main()