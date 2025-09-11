from datetime import datetime
from pathlib import Path
from typing import Set, List
from .settings import AppSettings

class ReportGenerator:
    """
    [EN] Generates a Markdown summary report of the extraction process.
    [PT-BR] Gera um relatório resumido em Markdown do processo de extração.
    """
    def __init__(self, settings: AppSettings, files_copied: Set[Path],
                 py_deps: Set[str], cs_deps: Set[str]):
        self.settings = settings
        self.files_copied = sorted(list(files_copied))
        self.py_deps = sorted(list(py_deps))
        self.cs_deps = sorted(list(cs_deps))
        self.report_content = ""

    def _get_relative_path_str(self, file_path: Path) -> str:
        """
        [EN] Calculates the relative path of a file based on the project_dirs list.
        [PT-BR] Calcula o caminho relativo de um arquivo com base na lista project_dirs.
        """
        for proj_dir in self.settings.project_dirs:
            if file_path.is_relative_to(proj_dir):
                return str(file_path.relative_to(proj_dir))
        return str(file_path)

    def generate_markdown(self) -> str:
        """
        [EN] Constructs the full report in Markdown format.
        [PT-BR] Constrói o relatório completo em formato Markdown.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # --- Header ---
        self.report_content += "# Dependency Extraction Report\n\n"
        self.report_content += f"**[EN] Report generated on:** {now} / **[PT-BR] Relatório gerado em:** {now}\n\n"

        # --- Summary ---
        self.report_content += "## [EN] Summary / [PT-BR] Resumo\n\n"
        self.report_content += f"- **[EN] Source Files / [PT-BR] Arquivos de Origem:** `{[str(p.name) for p in self.settings.source_files]}`\n"
        self.report_content += f"- **[EN] Total Files Copied / [PT-BR] Total de Arquivos Copiados:** `{len(self.files_copied)}`\n"
        self.report_content += f"- **[EN] Python Dependencies Found / [PT-BR] Dependências Python Encontradas:** `{len(self.py_deps)}`\n"
        self.report_content += f"- **[EN] C# Dependencies Found / [PT-BR] Dependências C# Encontradas:** `{len(self.cs_deps)}`\n"

        # --- Copied Files ---
        self.report_content += "\n## [EN] Extracted Files / [PT-BR] Arquivos Extraídos\n\n"
        if self.files_copied:
            self.report_content += "<details>\n<summary>[EN] Click to expand / [PT-BR] Clique para expandir</summary>\n\n"
            self.report_content += "```\n"
            for file_path in self.files_copied:
                self.report_content += f"- {self._get_relative_path_str(file_path)}\n"
            self.report_content += "```\n\n</details>\n"
        else:
            self.report_content += "[EN] No files were extracted. / [PT-BR] Nenhum arquivo foi extraído.\n"

        # --- External Dependencies ---
        self.report_content += "\n## [EN] External Dependencies / [PT-BR] Dependências Externas\n\n"
        if self.py_deps:
            self.report_content += "### Python (`requirements.txt`)\n\n```\n"
            self.report_content += "\n".join(self.py_deps)
            self.report_content += "\n```\n"
        if self.cs_deps:
            self.report_content += "### C# (`csharp_packages.txt`)\n\n```\n"
            self.report_content += "\n".join(self.cs_deps)
            self.report_content += "\n```\n"
        if not self.py_deps and not self.cs_deps:
            self.report_content += "[EN] No external dependencies found. / [PT-BR] Nenhuma dependência externa foi encontrada.\n"
            
        return self.report_content