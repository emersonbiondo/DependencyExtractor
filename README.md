# Dependency Extractor

Uma ferramenta de linha de comando para extrair subconjuntos de projetos de código-fonte baseados em suas dependências. Ideal para isolar uma funcionalidade, criar um exemplo mínimo reproduzível ou migrar partes de um código.

---

## Visão Geral

Muitas vezes, precisamos compartilhar ou analisar apenas uma parte específica de um grande projeto. Fazer isso manualmente, copiando e colando arquivos e tentando adivinhar suas dependências, é um processo lento e propenso a erros.

O `Dependency Extractor` automatiza esse processo. Você fornece um único arquivo de ponto de entrada (ex: `main.py` ou `MyController.cs`) e a ferramenta:
1.  Analisa recursivamente todos os arquivos de código-fonte locais dos quais ele depende.
2.  Identifica as dependências de pacotes externos (Pip/NuGet).
3.  Agrupa todos os arquivos necessários em uma nova pasta ou em um arquivo `.zip`, preservando a estrutura de diretórios original.

## Principais Funcionalidades

* **Análise Recursiva de Dependências:** Mapeia a árvore de dependências completa a partir de um único arquivo.
* **Suporte a Python e C#:** Entende `import`s em Python e `using`s em C#.
* **Definição Explícita da Raiz do Projeto:** Você define o escopo da busca, garantindo que a resolução de dependências seja precisa.
* **Geração de Lista de Dependências Externas:** Cria automaticamente um `requirements.txt` para Python e um `csharp_packages.txt` para C#.
* **Saída Flexível:** Salve o resultado como uma estrutura de pastas ou como um arquivo `.zip` pronto para compartilhar.

## Requisitos

* Python 3.8 ou superior.

## Como Usar

O script é executado a partir da linha de comando com os seguintes argumentos:

```bash
python DependencyExtractor.py --help
```
```
usage: DependencyExtractor.py [-h] -r PROJECT_ROOT [-o OUTPUT_DIR | -z ZIP] source_file

Dependency Extractor: A tool to extract a project subset based on dependencies.

positional arguments:
  source_file           The path to the source file to start the extraction from.

options:
  -h, --help            show this help message and exit
  -r PROJECT_ROOT, --project-root PROJECT_ROOT
                        The root directory of the project.
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Destination directory for the extracted files. (Default: ./extracted_project)
  -z ZIP, --zip ZIP     Creates a zip archive with the specified name (e.g., my_project.zip).

```

### **Exemplo 1: Extrair uma funcionalidade Python para um diretório**

Imagine a seguinte estrutura de projeto:
```
/meu_projeto_py/
├── main.py             # importa 'utils.database'
├── requirements.txt    # contém 'requests'
└── utils/
    ├── __init__.py
    └── database.py     # importa 'requests'
```

**Comando:**
```bash
python DependencyExtractor.py /meu_projeto_py/main.py \
    -r /meu_projeto_py \
    -o ./extracao_python
```

**Resultado:** A pasta `./extracao_python` será criada com o seguinte conteúdo:
```
/extracao_python/
├── main.py
├── requirements.txt  # Gerado com 'requests'
└── utils/
    ├── __init__.py
    └── database.py
```

### **Exemplo 2: Extrair um Controller C# para um arquivo Zip**

Imagine a seguinte estrutura de projeto:
```
/meu_projeto_cs/
├── MeuProjeto.csproj   # contém '<PackageReference Include="Dapper" ...>'
└── Controllers/
    └── UserController.cs   # usa 'MeuProjeto.Services'
└── Services/
    └── UserService.cs      # usa 'Dapper'
```

**Comando:**
```bash
python DependencyExtractor.py "/meu_projeto_cs/Controllers/UserController.cs" \
    -r "/meu_projeto_cs" \
    -z "user_feature.zip"
```

**Resultado:** O arquivo `user_feature.zip` será criado. Ao descompactá-lo, você terá:
```
/
├── csharp_packages.txt   # Gerado com 'Dapper==2.0.123'
└── Controllers/
    └── UserController.cs
└── Services/
    └── UserService.cs
```

## Como Funciona

* **Análise de Código Estática:** A ferramenta não executa seu código.
    * Para **Python**, ela usa a árvore de sintaxe abstrata (`AST`) para encontrar de forma segura todas as declarações `import` e `from ... import`.
    * Para **C#**, ela usa expressões regulares para encontrar declarações `using` e para extrair referências de pacotes dos arquivos `.csproj`.
* **Resolução de Módulos:** Todos os módulos/namespaces são resolvidos em relação à pasta `--project-root` que você fornece.
* **Diferenciação de Dependências:** Módulos que não são encontrados localmente e não pertencem à biblioteca padrão do Python são considerados dependências externas. Para C#, os pacotes são lidos diretamente dos arquivos `.csproj`.