import shutil
import zipfile
import logging
from pathlib import Path
from typing import Set, Callable, Optional

log = logging.getLogger("rich")

def create_zip_archive(zip_path: Path, files_to_copy: Set[Path], get_relative_path_func: Callable[[Path], str], 
                       py_deps: Set[str], cs_deps: Set[str], report_content: Optional[str] = None) -> None:
    """
    [EN] Creates a zip archive of the collected files.
    [PT-BR] Cria um arquivo zip com os arquivos coletados.
    """
    log.info(f"[EN] Creating zip archive at: {zip_path} / [PT-BR] Criando arquivo zip em: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_copy:
            arcname = get_relative_path_func(file_path)
            zf.write(file_path, arcname)
        if py_deps:
            zf.writestr('requirements.txt', "\n".join(sorted(list(py_deps))))
        if cs_deps:
            zf.writestr('csharp_packages.txt', "\n".join(sorted(list(cs_deps))))
        if report_content:
            zf.writestr('summary-report.md', report_content)


def copy_files_to_dir(dir_path: Path, files_to_copy: Set[Path], get_relative_path_func: Callable[[Path], str], 
                      py_deps: Set[str], cs_deps: Set[str], report_content: Optional[str] = None) -> None:
    """
    [EN] Copies the collected files to a destination directory.
    [PT-BR] Copia os arquivos coletados para um diretório de destino.
    """
    log.info(f"[EN] Copying files to directory: {dir_path} / [PT-BR] Copiando arquivos para o diretório: {dir_path}")
    if dir_path.exists():
        shutil.rmtree(dir_path)
    dir_path.mkdir(parents=True)
    
    for file_path in files_to_copy:
        relative_path_str = get_relative_path_func(file_path)
        dest_file = dir_path / relative_path_str
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest_file)
    if py_deps:
        (dir_path / 'requirements.txt').write_text("\n".join(sorted(list(py_deps))), encoding='utf-8')
    if cs_deps:
        (dir_path / 'csharp_packages.txt').write_text("\n".join(sorted(list(cs_deps))), encoding='utf-8')
    if report_content:
        (dir_path / 'summary-report.md').write_text(report_content, encoding='utf-8')