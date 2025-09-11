from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, FilePath, DirectoryPath, validator

class AppSettings(BaseModel):
    """
    [EN] Defines and validates all application settings using Pydantic.
    [PT-BR] Define e valida todas as configurações da aplicação usando Pydantic.
    """
    source_files: List[FilePath] = Field(..., description="[EN] One or more source files to start the extraction from. / [PT-BR] Um ou mais arquivos de origem para iniciar a extração.")
    project_dirs: List[DirectoryPath] = Field(..., description="[EN] A list of project directories to search for dependencies. / [PT-BR] Uma lista de diretórios de projeto para procurar por dependências.")
    ignore_dirs: List[str] = Field(default_factory=list, description="[EN] Directory names to ignore during discovery (e.g., 'venv', '__pycache__'). / [PT-BR] Nomes de diretório a serem ignorados durante a descoberta (ex: 'venv', '__pycache__').")
    ignore_files: List[str] = Field(default_factory=list, description="[EN] File names/patterns to ignore during discovery (e.g., '.DS_Store', '*.log'). / [PT-BR] Nomes/padrões de arquivo a serem ignorados durante a descoberta (ex: '.DS_Store', '*.log').")
    output_dir: Optional[Path] = Field(None, description="[EN] Destination directory for the extracted files. / [PT-BR] Diretório de destino para os arquivos extraídos.")
    zip_file: Optional[Path] = Field(None, description="[EN] Creates a zip archive with the specified name. / [PT-BR] Cria um arquivo zip com o nome especificado.")
    no_recursion: bool = Field(False, description="[EN] If True, extracts only the direct dependencies of the source files. / [PT-BR] Se True, extrai apenas as dependências diretas dos arquivos de origem.")
    log_level: str = Field("INFO", description="[EN] Logging level (DEBUG, INFO, WARNING, ERROR). / [PT-BR] Nível de log (DEBUG, INFO, WARNING, ERROR).")
    verbose: bool = Field(False, description="[EN] Enable detailed (DEBUG level) logging. / [PT-BR] Ativa o log detalhado (nível DEBUG).")
    generate_report: bool = Field(True, description="[EN] If True, generates a summary report file. / [PT-BR] Se True, gera um arquivo de relatório resumido.")

    @validator('log_level')
    def validate_log_level(cls, value):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_value = value.upper()
        if upper_value not in valid_levels:
            msg = f"[EN] Invalid log level '{value}'. Must be one of {valid_levels} / [PT-BR] Nível de log inválido '{value}'. Deve ser um de {valid_levels}"
            raise ValueError(msg)
        return upper_value