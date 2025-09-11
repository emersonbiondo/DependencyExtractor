import ast
import re
from pathlib import Path
from typing import List, Set, Tuple, Optional, Callable

try:
    from sys import stdlib_module_names
except ImportError:
    # [EN] Partial list for compatibility with Python < 3.10
    # [PT-BR] Lista parcial para compatibilidade com Python < 3.10
    stdlib_module_names = {"os", "sys", "re", "collections", "math", "datetime", "json", "typing"}


def index_single_csharp_file(file_path: Path) -> List[Tuple[str, Path]]:
    """
    [EN] Extracts type definitions from a single C# file.
    [PT-BR] Extrai definições de tipo de um único arquivo C#.
    """
    type_def_pattern = re.compile(r'\b(?:public|internal|private|protected)?\s*(?:partial|static|abstract)?\s*(class|interface|enum|struct)\s+([a-zA-Z0-9_]+)')
    found_types = []
    try:
        content = file_path.read_text(encoding='utf-8')
        for match in type_def_pattern.finditer(content):
            type_name = match.group(2)
            found_types.append((type_name, file_path))
    except Exception:
        # [EN] Silently ignore files that cannot be read.
        # [PT-BR] Ignora silenciosamente arquivos que não podem ser lidos.
        pass
    return found_types


def parse_csharp_dependencies(content: str, type_map: dict, is_ignored_func: Callable[[Path], bool]) -> Set[Path]:
    """
    [EN] Finds all referenced local C# types within a file's content.
    [PT-BR] Encontra todos os tipos C# locais referenciados no conteúdo de um arquivo.
    """
    dependencies: Set[Path] = set()
    potential_type_pattern = re.compile(r'(?:new\s+|:\s*|typeof\s*\(|<|\[)\s*([A-Z][a-zA-Z0-9_]+)')
    for match in potential_type_pattern.finditer(content):
        type_name = match.group(1)
        if type_name in type_map:
            file_path = type_map[type_name]
            if not is_ignored_func(file_path):
                dependencies.add(file_path)
    return dependencies


def resolve_python_module(name: str, project_dirs: List[Path]) -> Optional[Path]:
    """
    [EN] Resolves a Python module name to a file path within any project directory.
    [PT-BR] Resolve um nome de módulo Python para um caminho de arquivo dentro de qualquer diretório do projeto.
    """
    path_str = name.replace('.', '/')
    for base_dir in project_dirs:
        potential_file = base_dir / f"{path_str}.py"
        if potential_file.is_file():
            return potential_file.resolve()
        
        potential_dir = base_dir / path_str
        if potential_dir.is_dir() and (potential_dir / '__init__.py').is_file():
            return (potential_dir / '__init__.py').resolve()
    return None

def parse_python_dependencies(content: str, project_dirs: List[Path], is_ignored_func: Callable[[Path], bool]) -> Tuple[Set[Path], Set[str]]:
    """
    [EN] Parses a Python file to find local and external dependencies.
    [PT-BR] Analisa um arquivo Python para encontrar dependências locais e externas.
    """
    local_deps: Set[Path] = set()
    external_deps: Set[str] = set()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return local_deps, external_deps

    for node in ast.walk(tree):
        modules_to_check = []
        if isinstance(node, ast.Import):
            modules_to_check.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # [EN] Note: Simplified to handle absolute imports for now. Relative import logic can be more complex.
            # [PT-BR] Nota: Simplificado para lidar com imports absolutos por enquanto. A lógica para imports relativos pode ser mais complexa.
            modules_to_check.append(node.module)

        for module_name in modules_to_check:
            resolved_path = resolve_python_module(module_name, project_dirs)
            if resolved_path:
                if not is_ignored_func(resolved_path):
                    local_deps.add(resolved_path)
            elif module_name.split('.')[0] not in stdlib_module_names:
                external_deps.add(module_name.split('.')[0])
    return local_deps, external_deps