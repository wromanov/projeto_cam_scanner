# CAM SCANNER

CLI para Windows voltada ao inventário de câmeras IP. A versão inicial prevista é `0.1.0`; o alvo operacional futuro é `1.0.0`.

## Estado atual

A slice SINGLE consulta Manufacturer, Model, SerialNumber e FirmwareVersion por ONVIF `GetDeviceInformation`, somente leitura. O menu e a navegação pós-consulta estão integrados. MULTI, adapters de fabricantes, snapshots e leitura/escrita operacional de XLSX continuam fora desta slice.

A validação sintética da integração está implementada. A validação operacional com câmera real depende de um target e credenciais autorizados; sem essa evidência, P1 permanece aberta.

## Desenvolvimento

- Python 3.14.x em `venv`;
- instalação de desenvolvimento: `pip install -e .[dev]`;
- entrypoint: `cam-scanner` ou `python -m cam_scanner`;
- configuração em `config/settings.toml`;
- dados de entrada e saída em `input/` e `output/`; logs em `logs/`.

Não armazene credenciais ou planilhas de entrada com credenciais no Git. A planilha MULTI é um artefato sensível.

## Governança

Comece por [`docs/continuity/START_HERE.md`](docs/continuity/START_HERE.md). O root deste checkout depende do ambiente; código de aplicação não contém paths absolutos de máquina.
