import concurrent.futures
import logging
import re
from collections import deque
from pathlib import Path
from typing import Dict, Set, Tuple

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from .settings import AppSettings
from .parsers import (index_single_csharp_file, parse_csharp_dependencies,
                      parse_python_dependencies)
from .file_system import create_zip_archive, copy_files_to_dir
from .report import ReportGenerator

log = logging.getLogger("rich")

class DependencyExtractor:
    # __init__, _is_ignored, _get_relative_path_str... (código existente sem alterações)
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.project_dirs = [p.resolve() for p in self.settings.project_dirs]
        self.ignore_dirs = set(self.settings.ignore_dirs)
        self.ignore_files = set(self.settings.ignore_files)
        self.files_to_process: deque[Tuple[Path, int]] = deque((p.resolve(), 0) for p in self.settings.source_files)
        self.files_to_copy: Set[Path] = set()
        self.external_python_deps: Set[str] = set()
        self.external_csharp_deps: Set[str] = set()
        self.csharp_type_to_path_map: Dict[str, Path] = {}
        self.is_csharp_project = any(p.suffix.lower() == '.cs' for p in self.settings.source_files)
        log.debug(f"[EN] Extractor initialized with settings: {settings.model_dump_json(indent=2)} / [PT-BR] Extrator inicializado com as configurações: {settings.model_dump_json(indent=2)}")

    def _is_ignored(self, path: Path) -> bool:
        for part in path.parts:
            if part in self.ignore_dirs:
                log.debug(f"[EN] Ignoring '{path}' because directory '{part}' is in ignore list. / [PT-BR] Ignorando '{path}' porque o diretório '{part}' está na lista de ignorados.")
                return True
        for pattern in self.ignore_files:
            if path.match(pattern):
                log.debug(f"[EN] Ignoring '{path}' because it matches file pattern '{pattern}'. / [PT-BR] Ignorando '{path}' porque corresponde ao padrão de arquivo '{pattern}'.")
                return True
        return False

    def run(self) -> None:
        """
        [EN] Executes the entire extraction process.
        [PT-BR] Executa todo o processo de extração.
        """
        log.info("[EN] Starting extraction process... / [PT-BR] Iniciando processo de extração...")
        if self.is_csharp_project:
            self._build_csharp_type_index()
        
        self._collect_local_dependencies()
        self._collect_external_csharp_dependencies()

        if not self.files_to_copy:
            log.warning("[EN] No local source files found or collected. Halting output generation. / [PT-BR] Nenhum arquivo de código-fonte local foi encontrado ou coletado. Interrompendo a geração de saída.")
            return

        report_content = None
        if self.settings.generate_report:
            log.info("[EN] Generating summary report... / [PT-BR] Gerando relatório resumido...")
            reporter = ReportGenerator(self.settings, self.files_to_copy, self.external_python_deps, self.external_csharp_deps)
            report_content = reporter.generate_markdown()

        if self.settings.output_dir:
            copy_files_to_dir(self.settings.output_dir, self.files_to_copy, self._get_relative_path_str, self.external_python_deps, self.external_csharp_deps, report_content)
        
        if self.settings.zip_file:
            create_zip_archive(self.settings.zip_file, self.files_to_copy, self._get_relative_path_str, self.external_python_deps, self.external_csharp_deps, report_content)

        log.info("[EN] Extraction process completed successfully. / [PT-BR] Processo de extração concluído com sucesso.")

    def _build_csharp_type_index(self) -> None:
        """
        [EN] Indexes all C# types in the project directories using multiple threads.
        [PT-BR] Indexa todos os tipos C# nos diretórios do projeto usando múltiplas threads.
        """
        log.info("[EN] Indexing C# project files... / [PT-BR] Indexando arquivos de projeto C#...")
        all_cs_files = [cs_file for proj_dir in self.project_dirs for cs_file in proj_dir.rglob('*.cs') if not self._is_ignored(cs_file)]
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%")) as progress:
            task = progress.add_task("[EN] Indexing... / [PT-BR] Indexando...", total=len(all_cs_files))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(index_single_csharp_file, file): file for file in all_cs_files}
                for future in concurrent.futures.as_completed(futures):
                    file_results = future.result()
                    for type_name, file_path in file_results:
                        if type_name not in self.csharp_type_to_path_map:
                            self.csharp_type_to_path_map[type_name] = file_path
                    progress.update(task, advance=1)
        
        log.info(f"[EN] Indexing complete. Found {len(self.csharp_type_to_path_map)} unique C# types. / [PT-BR] Indexação completa. Encontrados {len(self.csharp_type_to_path_map)} tipos C# únicos.")

    def _collect_local_dependencies(self) -> None:
        """
        [EN] Recursively analyzes the file queue to find all local dependencies.
        [PT-BR] Analisa recursivamente a fila de arquivos para encontrar todas as dependências locais.
        """
        log.info("[EN] Starting analysis of local dependencies... / [PT-BR] Iniciando análise de dependências locais...")
        processed_files: Set[Path] = set()

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("({task.completed} of {task.total} files)")) as progress:
            task = progress.add_task("[EN] Analyzing... / [PT-BR] Analisando...", total=len(self.files_to_process))
            
            while self.files_to_process:
                current_file, current_depth = self.files_to_process.popleft()
                progress.update(task, description=f"[EN] Analyzing: {current_file.name} / [PT-BR] Analisando: {current_file.name}")

                if current_file in processed_files or self._is_ignored(current_file):
                    progress.update(task, advance=1)
                    continue
                
                processed_files.add(current_file)
                self.files_to_copy.add(current_file)
                log.debug(f"[EN]   Analyzing (depth {current_depth}): {self._get_relative_path_str(current_file)} / [PT-BR]   Analisando (nível {current_depth}): {self._get_relative_path_str(current_file)}")

                if self.settings.no_recursion and current_depth >= 1:
                    log.debug(f"[EN] Stopping recursion at depth {current_depth}. / [PT-BR] Parando a recursão no nível {current_depth}.")
                    progress.update(task, advance=1)
                    continue

                try:
                    content = current_file.read_text(encoding='utf-8', errors='ignore')
                    new_deps: Set[Path] = set()
                    if current_file.suffix.lower() == '.py':
                        local_deps, ext_deps = parse_python_dependencies(content, self.project_dirs, self._is_ignored)
                        new_deps.update(local_deps)
                        self.external_python_deps.update(ext_deps)
                    elif current_file.suffix.lower() == '.cs':
                        new_deps.update(parse_csharp_dependencies(content, self.csharp_type_to_path_map, self._is_ignored))
                    
                    for dep_path in new_deps:
                        if dep_path not in processed_files and dep_path not in [item[0] for item in self.files_to_process]:
                            self.files_to_process.append((dep_path, current_depth + 1))
                    
                    progress.update(task, total=len(processed_files) + len(self.files_to_process))
                except Exception as e:
                    log.warning(f"[EN] Could not parse {current_file.name}: {e} / [PT-BR] Não foi possível analisar {current_file.name}: {e}")
                
                progress.update(task, advance=1)
    
    def _get_relative_path_str(self, file_path: Path) -> str:
        for proj_dir in self.project_dirs:
            if file_path.is_relative_to(proj_dir):
                return str(file_path.relative_to(proj_dir))
        return str(file_path)

    def _collect_external_csharp_dependencies(self) -> None:
        if not self.is_csharp_project: return
        log.info("[EN] Scanning for external dependencies in .csproj files... / [PT-BR] Procurando por dependências externas em arquivos .csproj...")
        pattern = re.compile(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', re.IGNORECASE)
        
        for proj_dir in self.project_dirs:
            for csproj_file in proj_dir.rglob('*.csproj'):
                if self._is_ignored(csproj_file): continue
                log.debug(f"[EN] Analyzing project file: '{csproj_file.name}' / [PT-BR] Analisando arquivo de projeto: '{csproj_file.name}'")
                content = csproj_file.read_text(encoding='utf-8')
                for match in pattern.finditer(content):
                    package, version = match.groups()
                    self.external_csharp_deps.add(f"{package}=={version}")