# Dependency Extractor

**[EN]** A command-line tool to extract subsets of a software project based on its source code dependencies.
**[PT-BR]** Uma ferramenta de linha de comando para extrair subconjuntos de um projeto de software com base em suas dependências de código-fonte.

Ideal para isolar uma funcionalidade, criar um exemplo mínimo reproduzível ou migrar partes de um código de forma segura e automatizada.

## Visão Geral

Muitas vezes, precisamos compartilhar ou analisar apenas uma parte específica de um grande projeto. Fazer isso manualmente, copiando e colando arquivos e tentando adivinhar suas dependências, é um processo lento e propenso a erros.

O `Dependency Extractor` automatiza esse processo. Você fornece um ou mais arquivos de ponto de entrada (ex: `main.py` ou `MyController.cs`), e a ferramenta:

1.  Analisa recursivamente todos os arquivos de código-fonte locais dos quais eles dependem, respeitando a profundidade de análise configurada.
2.  Identifica as dependências de pacotes externos (Python Pip e C# NuGet).
3.  Agrupa todos os arquivos necessários em uma nova pasta ou em um arquivo `.zip`, preservando a estrutura de diretórios original.
4.  Gera um relatório detalhado sobre o processo de extração.

## Principais Funcionalidades

-   **Análise de Dependências:** Suporta análise recursiva completa (padrão) ou apenas de dependências diretas (nível 1).
-   **Suporte Multi-Linguagem:** Entende `import` em Python e a resolução de tipos em C#.
-   **Múltiplos Diretórios de Projeto:** Busque por dependências em múltiplas pastas-fonte, ideal para monorepos ou projetos com estrutura complexa.
-   **Filtros Flexíveis:** Ignore arquivos e diretórios específicos (como `venv`, `__pycache__`, `*.log`) para manter a extração limpa.
-   **Saída Flexível:** Salve o resultado como uma estrutura de pastas ou como um arquivo `.zip` pronto para compartilhar.
-   **Relatório Detalhado:** Gera um arquivo `summary-report.md` com o resumo da extração, lista de arquivos e dependências externas.
-   **Feedback Visual:** Exibe barras de progresso durante as operações demoradas de indexação e análise.
-   **Logging Configurável:** Controle o nível de detalhe dos logs com as opções `--log-level` e `--verbose`/`-v`.
-   **Configuração via JSON:** Gerencie configurações complexas de forma fácil e reproduzível através de um arquivo de configuração.

## Instalação

A ferramenta é construída em Python e requer algumas bibliotecas. O método recomendado para instalação é usando um ambiente virtual (`venv`).

1.  **Clone ou baixe o projeto** para a sua máquina.

2.  **Crie o ambiente virtual:** Na pasta raiz do projeto, execute o comando:
    ```bash
    python -m venv .venv
    ```

3.  **Ative o ambiente virtual:**
    * **Windows (CMD/PowerShell):**
        ```bash
        .venv\Scripts\activate
        ```
    * **Linux ou macOS:**
        ```bash
        source .venv/bin/activate
        ```
    Seu terminal deverá agora mostrar `(.venv)` no início da linha de comando.

4.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

## Como Usar

A ferramenta pode ser configurada inteiramente via linha de comando ou através de um arquivo JSON.

### Interface de Linha de Comando (CLI)

```
> python main.py --help

 Usage: main.py [OPTIONS] [SOURCE_FILES]...

 [EN] Dependency Extractor: A tool to extract a project subset from source
 files.
 [PT-BR] Extrator de Dependências: Uma ferramenta para extrair um subconjunto
 de projeto a partir de arquivos de origem.

 Arguments:
  [SOURCE_FILES]...  [EN] Source files to start from. / [PT-BR] Arquivos de
                     origem para iniciar.

 Options:
  -d, --project-dir DIRECTORY     [EN] Project directory to search. Can be used
                                  multiple times. / [PT-BR] Diretório do
                                  projeto para busca. Pode ser usado múltiplas
                                  vezes.
  --ignore-dir TEXT               [EN] Directory name to ignore. / [PT-BR]
                                  Nome de diretório para ignorar.
  --ignore-file TEXT              [EN] File name/pattern to ignore. / [PT-BR]
                                  Nome/padrão de arquivo para ignorar.
  -o, --output-dir DIRECTORY      [EN] Destination directory. / [PT-BR]
                                  Diretório de destino.
  -z, --zip DIRECTORY             [EN] Create a zip file. / [PT-BR] Cria um
                                  arquivo zip.
  -c, --config FILE               [EN] Path to a JSON configuration file. /
                                  [PT-BR] Caminho para um arquivo de
                                  configuração JSON.
  --no-recursion / --recursion    [EN] Extract direct dependencies only
                                  (level 1). / [PT-BR] Extrai apenas as
                                  dependências diretas (nível 1).
  --report / --no-report          [EN] Generate a summary report file. /
                                  [PT-BR] Gera um arquivo de relatório
                                  resumido.
  --log-level TEXT                [EN] Set the log level, overrides JSON
                                  config. / [PT-BR] Define o nível de log,
                                  sobrescreve a config JSON.
  -v, --verbose                   [EN] Enable DEBUG logging, overrides
                                  everything. / [PT-BR] Ativa o log DEBUG,
                                  sobrescreve tudo.
  --help                          Show this message and exit.
```

### Exemplo de Uso com Arquivo de Configuração

Usar um arquivo JSON é a forma mais recomendada para configurações complexas, pois permite salvá-las e reutilizá-las.

**`job.json` de exemplo:**
```json
{
  "project_dirs": [
    "D:\\Projetos\\MeuProjeto\\backend\\src",
    "D:\\Projetos\\MeuProjeto\\backend\\libs"
  ],
  "source_files": [
    "D:\\Projetos\\MeuProjeto\\backend\\src\\Controllers\\PedidoController.cs"
  ],
  "output_dir": "D:\\Extracoes\\feature-pedido",
  "zip_file": "D:\\Extracoes\\feature-pedido.zip",
  "ignore_dirs": [
    "obj",
    "bin",
    "__pycache__",
    "Testes"
  ],
  "ignore_files": [
    "*.user",
    "*.log"
  ],
  "no_recursion": false,
  "verbose": true,
  "generate_report": true
}
```

**Comando para executar:**
```bash
python main.py -c job.json
```

## A Saída

Após a execução, a ferramenta produzirá:

1.  **Uma pasta de destino** (se `-o`/`--output-dir` for usado) com todos os arquivos de código-fonte necessários, mantendo a estrutura de pastas relativa.
2.  **Um arquivo `.zip`** (se `-z`/`--zip` for usado) contendo a mesma estrutura de arquivos.
3.  **Arquivos de dependência externa:** `requirements.txt` (para Python) e `csharp_packages.txt` (para C#) são gerados automaticamente na saída.
4.  **Relatório de Extração (`summary-report.md`):** Se habilitado, este arquivo é gerado na saída e contém um resumo completo do processo.

## Como Funciona

-   **Análise de Código Estática:** A ferramenta não executa seu código.
    -   Para **Python**, ela usa a Árvore de Sintaxe Abstrata (`AST`) para encontrar de forma segura todas as declarações `import`.
    -   Para **C#**, ela primeiro realiza uma fase de **indexação** multithreaded para mapear todos os tipos do projeto. Em seguida, ela analisa o código em busca de usos desses tipos (como `new Tipo()`, herança, etc.) para resolver as dependências.
-   **Resolução de Dependências:** A busca por arquivos é feita seguindo uma abordagem de busca em largura (BFS) a partir dos arquivos de origem, respeitando o limite de profundidade (`--no-recursion`).