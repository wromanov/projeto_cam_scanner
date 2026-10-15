# Inventário observado de dependências

## Plataforma e método

- Python: 3.14.0, CPython, Windows 11 x64 (`AMD64`, build 26100).
- Fonte: metadata e `pip freeze --all` do ambiente `.venv` já existente do projeto, consultados sem instalar ou atualizar pacotes.
- Esse inventário descreve o ambiente observado; não é um lock validado nem prova de instalação limpa.
- SHA-256 de wheels/sdists não está disponível na metadata instalada. Não foram inventados hashes. Um lock com hashes precisa ser gerado a partir dos artefatos aprovados, em etapa autorizada.

## Dependências diretas de runtime

| Distribuição | Versão observada | Uso direto |
|---|---:|---|
| `av` | 19.0.1 | Decodificar um frame RTSP via PyAV/FFmpeg. |
| `onvif-python` | 0.4.4 | Modelos e bindings ONVIF/WSDL já fornecidos pela biblioteca. |
| `openpyxl` | 3.1.5 | Leitura e escrita XLSX. |
| `Pillow` | 12.3.0 | Decodificação, orientação e thumbnail JPEG sem metadados. |
| `requests` | 2.34.2 | Sessões HTTP diretamente usadas pelos adapters e transporte governado. |
| `rich` | 15.0.0 | Indicadores de progresso no terminal. |
| `zeep` | 4.3.3 | Cliente SOAP chamado diretamente pela fachada ONVIF. |

`httpx` foi removido do manifesto: não há import de `httpx` no código do produto. `lxml` é requerido por Zeep e não é importado diretamente pelo aplicativo; será coletado com as DLLs nativas pelo spec ONEDIR.

## Transitivas observadas

| Dependência de | Distribuição transitiva | Versão observada |
|---|---|---:|
| `onvif-python` | `pyreadline3` | 3.5.6 |
| `requests` | `certifi` | 2026.7.22 |
| `requests` | `charset-normalizer` | 3.5.2 |
| `requests` | `idna` | 3.20 |
| `requests` | `urllib3` | 2.8.0 |
| `openpyxl` | `et-xmlfile` | 2.0.0 |
| `zeep` | `attrs` | 26.1.0 |
| `zeep` | `isodate` | 0.7.2 |
| `zeep` | `lxml` | 6.1.3 |
| `zeep` | `platformdirs` | 4.12.3 |
| `zeep` | `requests-file` | 3.0.1 |
| `zeep` | `requests-toolbelt` | 1.0.0 |
| `rich` | `markdown-it-py` | 4.2.0 |
| `rich` | `Pygments` | 2.21.0 |
| `markdown-it-py` | `mdurl` | 1.2.0 |

## Ferramentas de desenvolvimento e packaging observadas

- `pytest==9.1.1`, `ruff==0.16.10`, `pyinstaller==6.22.3`.
- Transitivas relevantes no Windows: `altgraph==0.17.5`, `packaging==26.3`, `pefile==2024.8.26`, `pyinstaller-hooks-contrib==2026.8`, `pywin32-ctypes==0.2.3`, `setuptools==84.0.0`, `colorama==0.4.6`, `iniconfig==2.3.1`, `pluggy==1.6.0`.
- O manifesto exige `setuptools>=75` e `wheel` como build backend. Build e instalação não foram executados.

## Preparação futura do bundle

`cam_scanner.spec` usa paths absolutos derivados do próprio spec, inclui WSDL ONVIF e bundle de certificados `certifi`, reúne DLLs de PyAV/lxml/Pillow e declara os módulos importados dinamicamente por ONVIF, Zeep, Pillow, openpyxl e Rich. Python 3.14 fornece `tomllib` na biblioteca padrão. Isso é inventário e preparação estática: imports, DLLs, certificados e execução do artefato só serão comprovados pelo build/smoke P12, ainda não autorizado.
