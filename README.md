# Dependency Extractor

Uma ferramenta de linha de comando para extrair subconjuntos de projetos de código-fonte baseados em suas dependências. Ideal para isolar uma funcionalidade, criar um exemplo mínimo reproduzível ou migrar partes de um código.

---

## Visão Geral

Muitas vezes, precisamos compartilhar ou analisar apenas uma parte específica de um grande projeto. Fazer isso manualmente, copiando e colando arquivos e tentando adivinhar suas dependências, é um processo lento e propenso a erros.

O `Dependency Extractor` automatiza esse processo. Você fornece um ou mais arquivos de ponto de entrada (ex: `main.py` ou `MyController.cs`) e a ferramenta:
1.  Analisa recursivamente todos os arquivos de código-fonte locais dos quais eles dependem.
2.  Identifica as dependências de pacotes externos (Pip/NuGet).
3.  Agrupa todos os arquivos necessários em uma nova pasta ou em um arquivo `.zip`, preservando la estrutura de diretórios original.

## Principais Funcionalidades

* **Análise Recursiva de Dependências:** Mapeia a árvore de dependências completa a partir de um único arquivo.
* **Múltiplos Pontos de Entrada:** Inicie a extração a partir de um ou mais arquivos de origem simultaneamente.
* **Suporte a Python e C#:** Entende `import`s em Python e `using`s/tipos em C#.
* **Definição Explícita da Raiz do Projeto:** Você define o escopo da busca, garantindo que a resolução de dependências seja precisa.
* **Geração de Lista de Dependências Externas:** Cria automaticamente um `requirements.txt` para Python e um `csharp_packages.txt` para C#.
* **Saída Flexível:** Salve o resultado como uma estrutura de pastas ou como um arquivo `.zip` pronto para compartilhar.
* **Configuração via JSON:** Gerencie configurações complexas de forma fácil e reproduzível através de um arquivo de configuração.

## Requisitos

* Python 3.8 ou superior.

## Como Usar

O script agora aceita um ou mais arquivos de origem diretamente na linha de comando, ou pode ser configurado via um arquivo JSON.

```bash
python DependencyExtractor.py --help
```
```
usage: DependencyExtractor.py [-h] [-r PROJECT_ROOT] [-o OUTPUT_DIR] [-z ZIP] [-c CONFIG] [source_files ...]

Dependency Extractor: A tool to extract a project subset from one or more source files.

positional arguments:
  source_files          One or more source files to start the extraction from. Can be omitted if using a config file.

options:
  -h, --help            show this help message and exit
  -r PROJECT_ROOT, --project-root PROJECT_ROOT
                        The root directory of the project.
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Destination directory for the extracted files.
  -z ZIP, --zip ZIP     Creates a zip archive with the specified name.
  -c CONFIG, --config CONFIG
                        Path to a JSON configuration file.

```

### **Exemplo 1: Linha de Comando com Múltiplos Arquivos**

Imagine que você quer extrair uma feature que envolve um Controller e um Service específicos.
```
/meu_projeto_cs/
├── MeuProjeto.csproj
├── Controllers/
│   └── PedidoController.cs   # Depende de PedidoService
└── Services/
    ├── PedidoService.cs      # Depende de Repositories.PedidoRepository
    └── ClienteService.cs
└── Repositories/
    └── PedidoRepository.cs
```

**Comando:**
```bash
python DependencyExtractor.py "/meu_projeto_cs/Controllers/PedidoController.cs" "/meu_projeto_cs/Services/ClienteService.cs" -r "/meu_projeto_cs" -o "./feature_extraida"

```

**Resultado:** A pasta ./feature_extraida será criada contendo PedidoController.cs, PedidoService.cs, PedidoRepository.cs (pois é dependência de PedidoService) e ClienteService.cs, unificando as dependências de todos os pontos de entrada.

### **Exemplo 2: Arquivo de Configuração JSON com Múltiplos Arquivos**

Para execuções complexas e reproduzíveis, você pode definir múltiplos arquivos de origem no seu arquivo de configuração usando a chave "source_files".
Arquivo job.json:
```
{
  "source_files": [
    "/meu_projeto_cs/Controllers/PedidoController.cs",
    "/meu_projeto_cs/Services/ClienteService.cs"
  ],
  "project_root": "/meu_projeto_cs",
  "zip": "feature_completa.zip"
}
```

**Comando:**
```bash
python DependencyExtractor.py -c job.json
```

**Resultado:** Um arquivo feature_completa.zip será criado com todos os arquivos de código-fonte necessários para PedidoController e ClienteService.

## Como Funciona

* **Análise de Código Estática:** A ferramenta não executa seu código.
    * Para **Python**, ela usa a árvore de sintaxe abstrata (`AST`) para encontrar de forma segura todas as declarações `import` e `from ... import`.
    * Para **C#**, ela primeiro realiza uma fase de **indexação** multithreaded, mapeando todos os tipos (classes, enums, etc.) do projeto para seus respectivos arquivos. Em seguida, ela analisa o código em busca de usos desses tipos para resolver as dependências com alta confiabilidade, independentemente da estrutura de pastas.
* **Resolução de Módulos:** Todos os módulos/namespaces são resolvidos em relação à pasta `--project-root` que você fornece.
* **Diferenciação de Dependências:** Módulos que não são encontrados localmente e não pertencem à biblioteca padrão do Python são considerados dependências externas. Para C#, os pacotes são lidos diretamente dos arquivos `.csproj`.