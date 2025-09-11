import json
import logging
from pathlib import Path
from typing import List, Optional

import typer
from pydantic import ValidationError
from rich.logging import RichHandler

from .settings import AppSettings
from .extractor import DependencyExtractor

def setup_logging(log_level: str):
    """
    [EN] Configures the application's logger.
    [PT-BR] Configura o logger da aplicação.
    """
    logging.basicConfig(
        level=log_level.upper(),
        format='%(message)s',
        datefmt='[%X]',
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
    )

log = logging.getLogger("rich")
app = typer.Typer(help="[EN] Dependency Extractor: A tool to extract a project subset from source files.\n[PT-BR] Extrator de Dependências: Uma ferramenta para extrair um subconjunto de projeto a partir de arquivos de origem.")

@app.command()
def main(
    source_files: Optional[List[Path]] = typer.Argument(None, help="[EN] Source files to start from. / [PT-BR] Arquivos de origem para iniciar."),
    project_dirs: Optional[List[Path]] = typer.Option(None, "-d", "--project-dir", help="[EN] Project directory to search. Can be used multiple times. / [PT-BR] Diretório do projeto para busca. Pode ser usado múltiplas vezes."),
    ignore_dir: Optional[List[str]] = typer.Option(None, "--ignore-dir", help="[EN] Directory name to ignore. / [PT-BR] Nome de diretório para ignorar."),
    ignore_file: Optional[List[str]] = typer.Option(None, "--ignore-file", help="[EN] File name/pattern to ignore. / [PT-BR] Nome/padrão de arquivo para ignorar."),
    output_dir: Optional[Path] = typer.Option(None, "-o", "--output-dir", help="[EN] Destination directory. / [PT-BR] Diretório de destino."),
    zip_file: Optional[Path] = typer.Option(None, "-z", "--zip", help="[EN] Create a zip file. / [PT-BR] Cria um arquivo zip."),
    config: Optional[Path] = typer.Option(None, "-c", "--config", help="[EN] Path to a JSON configuration file. / [PT-BR] Caminho para um arquivo de configuração JSON."),
    no_recursion: Optional[bool] = typer.Option(None, "--no-recursion", help="[EN] Extract direct dependencies only (level 1). / [PT-BR] Extrai apenas as dependências diretas (nível 1)."),
    log_level: Optional[str] = typer.Option(None, "--log-level", help="[EN] Set the log level, overrides JSON config. / [PT-BR] Define o nível de log, sobrescreve a config JSON."),
    verbose: Optional[bool] = typer.Option(None, "-v", "--verbose", help="[EN] Enable DEBUG logging, overrides everything. / [PT-BR] Ativa o log DEBUG, sobrescreve tudo.")
):
    """
    [EN] Dependency Extractor: A tool to extract a project subset from source files.
    [PT-BR] Extrator de Dependências: Uma ferramenta para extrair um subconjunto de projeto a partir de arquivos de origem.
    """
    config_data = {}
    if config and config.is_file():
        # [EN] This initial log must happen before setup_logging to be visible.
        # [PT-BR] Este log inicial deve acontecer antes de setup_logging para ser visível.
        print(f"INFO: [EN] Loading configuration from: {config} / [PT-BR] Carregando configuração de: {config}")
        try:
            config_data = json.loads(config.read_text('utf-8'))
        except json.JSONDecodeError:
            print(f"CRITICAL: [EN] Error decoding JSON from: {config} / [PT-BR] Erro ao decodificar JSON de: {config}")
            raise typer.Exit(1)
            
    # --- [EN] Updated Log Logic / [PT-BR] Lógica de Log Atualizada ---
    # 1. [EN] Determine verbosity (CLI has priority over JSON) / [PT-BR] Determina a verbosidade (CLI tem prioridade sobre JSON)
    is_verbose = verbose if verbose is not None else config_data.get("verbose", False)
    
    # 2. [EN] Determine final log level based on precedence / [PT-BR] Determina o nível de log final com base na precedência
    if is_verbose:
        final_log_level = "DEBUG"
    elif log_level:  # [EN] If --log-level was passed on the CLI / [PT-BR] Se --log-level foi passado na CLI
        final_log_level = log_level
    else: # [EN] Use from JSON or the ultimate default 'INFO' / [PT-BR] Usa o do JSON ou o padrão 'INFO'
        final_log_level = config_data.get("log_level", "INFO")

    setup_logging(final_log_level)
    log = logging.getLogger("rich")
    # --- [EN] End of Updated Log Logic / [PT-BR] Fim da Lógica de Log Atualizada ---

    final_settings_data = {
        "source_files": source_files or config_data.get("source_files"),
        "project_dirs": project_dirs or config_data.get("project_dirs"),
        "ignore_dirs": ignore_dir or config_data.get("ignore_dirs", []),
        "ignore_files": ignore_file or config_data.get("ignore_files", []),
        "output_dir": output_dir or config_data.get("output_dir"),
        "zip_file": zip_file or config_data.get("zip_file"),
        "no_recursion": no_recursion if no_recursion is not None else config_data.get("no_recursion", False),
        "log_level": final_log_level,
        "verbose": is_verbose,
    }
    final_settings_data = {k: v for k, v in final_settings_data.items() if v is not None}

    try:
        settings = AppSettings(**final_settings_data)
    except ValidationError as e:
        log.critical(f"[EN] Configuration error:\n{e}\n[PT-BR] Erro de configuração:\n{e}")
        raise typer.Exit(1)

    if not settings.output_dir and not settings.zip_file:
        log.warning("[EN] No output specified. Nothing to do. / [PT-BR] Nenhuma saída especificada. Nada a fazer.")
        raise typer.Exit()
        
    try:
        extractor = DependencyExtractor(settings)
        extractor.run()
    except Exception as e:
        log.critical(f"[EN] A critical error stopped execution: {e} / [PT-BR] Um erro crítico interrompeu a execução: {e}", exc_info=True)
        raise typer.Exit(1)