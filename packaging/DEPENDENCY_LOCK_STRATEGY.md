# Estratégia candidata de lock — PREP12-10

**Estado corrente (2026-10-19):** o par de locks foi gerado e validado tecnicamente: `requirements/locks/windows-py314-hashed.txt` e `requirements/locks/pylock.windows-py314.toml`. Os 36/36 pins e hashes correspondem; a reprodução offline instalou 36/36 e `pip check` e imports passaram. O Architect aceitou o critério técnico de lock e reprodução (`ACCEPT`). PREP12-10 permanece sem `CLEARED` enquanto Gate 2/V aguarda regressão sem skip e reavaliação.

## Escopo

- Alvo: CPython 3.14, Windows x64 (`AMD64`). O lock é específico desta combinação; outras plataformas e versões de Python precisam de resolução própria.
- Entrada direta: [`requirements/locks/windows-py314.in`](../requirements/locks/windows-py314.in), com as dependências de runtime e dev já fixadas em `pyproject.toml`, mais a proposta explícita de ferramentas de lock/build.
- Saídas pretendidas: `requirements/locks/pylock.windows-py314.toml`, contendo versões transitivas e hashes SHA-256 dos wheels resolvidos, e `requirements/locks/windows-py314-hashed.txt`, instalável com `pip install --require-hashes`.
- `httpx` não entra no conjunto: não há import dele em `src/`. `requests` permanece direto porque adapters, transporte e captura de snapshot o importam. `lxml` deve ser resolvido como transitiva de Zeep, sem declaração direta do aplicativo.
- PyInstaller deve permanecer no conjunto de packaging; o lock transitivo precisa registrar também `pyinstaller-hooks-contrib` e demais dependências que o resolver selecionar.

## Resolução e hashes

O comando preparado usa o `pip lock` bootstrapped com o venv descartável, sem instalar dependências do produto:

```powershell
$basePython = 'C:\Users\walacedelgado\AppData\Local\Programs\Python\Python314\python.exe'
if (-not (Test-Path -LiteralPath $basePython)) { throw 'Python 3.14 validado não encontrado.' }
& $basePython --version
if ($LASTEXITCODE -ne 0) { throw 'Falha ao validar o executável Python.' }
$activityTemp = Join-Path (Get-Location).Path ('_tmp_PREP12_10_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $activityTemp | Out-Null
$env:TEMP = $activityTemp
$env:TMP = $activityTemp
$resolverVenv = Join-Path $activityTemp 'resolver-venv'
& $basePython -m venv $resolverVenv
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o resolver venv descartável.' }
$python = Join-Path $resolverVenv 'Scripts\python.exe'
& $python --version
if ($LASTEXITCODE -ne 0) { throw 'Falha ao validar o Python do resolver venv.' }
& $python -m pip lock `
  --only-binary=:all: `
  --no-cache-dir `
  --requirement requirements/locks/windows-py314.in `
  --output requirements/locks/pylock.windows-py314.toml
if ($LASTEXITCODE -ne 0) { throw 'Resolução do lock falhou; não usar saída parcial.' }
```

`--only-binary=:all:` impede que a resolução construa dependências a partir de sdist. O arquivo gerado deve ser inspecionado para confirmar que cada distribuição tem versão, URL e SHA-256; o resolver deve falhar se algum wheel compatível não existir. A versão do comando usada nesta tentativa foi `pip 25.2`; a ajuda local identifica `pip lock` como experimental, portanto o formato e o gerador precisam de revisão explícita antes de adoção.

O TOML de `pip lock` não substitui o artefato de instalação exigido pelo critério `pip install --require-hashes`. Quando um índice aprovado estiver acessível, escolher e registrar uma versão específica de `pip-tools` antes de instalá-la somente no resolver venv. Não preencher a versão sem confirmar a origem permitida e a disponibilidade do artefato. O relatório de instalação registra hashes dos artefatos da ferramenta e de suas dependências:

```powershell
$pipToolsVersion = '<versão aprovada e fixada>'
if ($pipToolsVersion -notmatch '^\d+(\.\d+){1,3}([a-zA-Z0-9.+-]*)?$') { throw 'Fixe uma versão aprovada de pip-tools antes de instalar.' }
$pipToolsInstallReport = Join-Path $activityTemp 'pip-tools-install-report.json'
& $python -m pip install --only-binary=:all: --report $pipToolsInstallReport "pip-tools==$pipToolsVersion"
if ($LASTEXITCODE -ne 0) { throw 'Instalação isolada de pip-tools falhou.' }
```

Com a ferramenta isolada instalada, gerar também o requirements lock:

```powershell
if (-not (Test-Path -LiteralPath $python)) { throw 'Resolver venv descartável não encontrado.' }
& $python -m piptools compile `
  --generate-hashes `
  --allow-unsafe `
  --pip-args="--only-binary=:all:" `
  --resolver=backtracking `
  --output-file requirements/locks/windows-py314-hashed.txt `
  requirements/locks/windows-py314.in
if ($LASTEXITCODE -ne 0) { throw 'Geração do requirements lock falhou.' }
```

`--allow-unsafe` é necessário para que `pip`, `setuptools` e `wheel`, já fixados na entrada, também apareçam no arquivo hasheado. `--only-binary=:all:` impede seleção de sdist e exige wheels compatíveis com Windows/CPython 3.14. A revisão deve confirmar que cada pacote, inclusive os três `unsafe`, tem versão e hashes SHA-256 dos artefatos selecionados e origem registrada. Depois da geração dos dois locks, criar um venv de reprodução independente do resolvedor no mesmo diretório exclusivo:

```powershell
$reproductionVenv = Join-Path $activityTemp 'reproduction-venv'
& $basePython -m venv $reproductionVenv
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o venv limpo de reprodução.' }
$reproductionPython = Join-Path $reproductionVenv 'Scripts\python.exe'
& $reproductionPython -m pip install --require-hashes --only-binary=:all: -r requirements/locks/windows-py314-hashed.txt
if ($LASTEXITCODE -ne 0) { throw 'Instalação reproduzida a partir do lock falhou.' }
& $reproductionPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'pip check falhou no venv reproduzido.' }
```

Em seguida comparar o grafo instalado com o lock TOML e executar imports e testes aplicáveis. Registrar a versão de `pip-tools` e os hashes da ferramenta no relatório da geração; ela é tooling do resolvedor, não dependência runtime/dev/build do produto.

## Evidência e limites desta preparação

- O Python executável foi confirmado como `3.14.0` antes da resolução.
- A tentativa de gerar o lock falhou ao resolver `av==19.0.1`: o índice retornou “No matching distribution found” com lista vazia. A rede/índice disponível neste sandbox não forneceu as versões; por isso não há arquivo `pylock.windows-py314.toml` nem hashes inventados.
- Não houve instalação ou atualização de pacote. Diretórios temporários criados pelo `pip lock` foram preservados.
- `setuptools==84.0.0` foi observado no venv reutilizado. `pip==25.2` também é a ferramenta observada. As versões em `windows-py314.in` são proposta isolada de resolução, não aprovação de mudança de versão; `pyproject.toml` permanece sem alteração e ainda declara `setuptools>=75` e `wheel` sem pin.
- A resolução e a inspeção de hashes ainda precisam ser repetidas em PowerShell local com acesso ao índice aprovado. Validação em ambiente limpo, `pip check`, regressão integral e build continuam gates separados e exigem autorização própria.

## Decisão de gate

PREP12-10 permanece **OPEN** até existir lock transitivo com hashes, revisão das versões/tooling candidatas e aprovação formal. Este artefato descreve a estratégia e fixa sua entrada, mas não declara reprodução garantida.

## Investigação de `av==19.0.1` — 2026-10-16

- O executável Python 3.14.0 do venv de validação reporta `av==19.0.1` instalado; `pip cache list av` não encontrou wheel local.
- A página oficial do [PyPI para av 19.0.1](https://pypi.org/project/av/19.0.1/) lista `av-19.0.1-cp312-abi3-win_amd64.whl`, compatível com CPython 3.14 pelo ABI estável `abi3`, e informa SHA-256 `906fc3db09288319a75ea23ffefb59961c7dbe0d1c074601507a89de7d8593d8`. A especificação [PyPA sobre extensões binárias](https://packaging.python.org/en/latest/guides/packaging-binary-extensions/) descreve `abi3` como ABI estável entre versões minor de CPython.
- `pip lock` 25.2 foi executado sem instalação, com `--only-binary=:all:`, `--no-cache-dir` e `--index-url https://pypi.org/simple`. O resolver continuou retornando `No matching distribution found` para `av==19.0.1`; nenhum arquivo `pylock.windows-py314.toml` foi produzido. O resultado aponta para uma limitação de resolução/rede do shell ou do índice efetivamente consultado, não para ausência da release no PyPI público. A causa exata do acesso do resolver permanece não determinada.
- A versão fixada não foi alterada e não houve instalação. A geração do lock transitivo segue pendente até um ambiente autorizado conseguir resolver a entrada e todas as transitivas, registrar seus hashes, revisar tooling/versões e reproduzir a instalação em ambiente limpo.
- Os diretórios temporários reportados pelo `pip lock` foram preservados.

## PREP12-10 — tentativa em venv isolado e bloqueio do índice (2026-10-16)

- O worktree confirmado é `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_pre_p12_remediation`, branch `feature/pre-p12-unified-remediation`, HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e`. O Python 3.14.0 base é AMD64 / `win-amd64`.
- Um resolver venv novo foi criado em `_tmp_PREP12_10_venv_f7619b781f1b49719a7d236faa951a7d\resolver-venv` e validado como Python 3.14.0 x64. O único pacote bootstrapped nele foi pip 25.2; nenhuma dependência do produto foi instalada nesse ambiente nem em qualquer ambiente preexistente.
- `pip config debug` no resolver mostrou `PIP_NO_INDEX='1'`; não havia `pip.ini` global, do venv ou do usuário. `pip index versions pip-tools -vv` informou que os índices foram ignorados e zero locais foram consultados. `pip install pip-tools` falhou com `No matching distribution found`; nenhum pacote foi instalado. O valor `PIP_NO_INDEX` não foi removido nem sobrescrito.
- `pip cache list av` e `pip cache list pip-tools` não encontraram wheels locais; o cache HTTP existente não foi interpretado como prova de disponibilidade de artefatos. A evidência não demonstra incompatibilidade ou ausência de `av==19.0.1`. A release pública lista `av-19.0.1-cp312-abi3-win_amd64.whl` e hash SHA-256 `906fc3db09288319a75ea23ffefb59961c7dbe0d1c074601507a89de7d8593d8`; consultar [PyPI av 19.0.1](https://pypi.org/project/av/19.0.1/). A resolução local está bloqueada pela política efetiva de não consultar índices, e não deve ser contornada.
- Não foi gerado lock nem executada reprodução limpa. PREP12-10 continua OPEN até um índice autorizado ficar disponível no ambiente, ou um wheelhouse aprovado e íntegro ser fornecido. Depois disso gerar e correlacionar os dois formatos, instalar a partir de `windows-py314-hashed.txt` em venv novo, verificar dependências/imports/testes e solicitar aceite independente.
