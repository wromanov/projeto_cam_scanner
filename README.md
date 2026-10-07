# CAM SCANNER

CLI para Windows voltada ao inventário de câmeras IP. A versão inicial prevista é `0.1.0`; o alvo operacional futuro é `1.0.0`.

## Estado atual

Este diretório contém somente a Engineering Foundation aprovada, documentos de continuidade e scaffold estrutural. Coleta ONVIF, adapters de fabricantes, snapshots, leitura/escrita operacional de XLSX e processamento MULTI ainda não estão implementados.

## Desenvolvimento

- Python 3.14.x em `venv`;
- instalação de desenvolvimento: `pip install -e .[dev]`;
- entrypoint previsto: `cam-scanner` ou `python -m cam_scanner`;
- configuração em `config/settings.toml`;
- dados de entrada e saída em `input/` e `output/`; logs em `logs/`.

Não armazene credenciais ou planilhas de entrada com credenciais no Git. A planilha MULTI é um artefato sensível.

## Governança

Comece por [`docs/continuity/START_HERE.md`](docs/continuity/START_HERE.md). O root deste checkout depende do ambiente; código de aplicação não contém paths absolutos de máquina.
