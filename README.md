# CAM SCANNER

CLI para Windows voltada ao inventário de câmeras IP. A versão do pacote preparado para homologação P12 é `1.0.0`.

## Estado vigente — 2026-10-19

O pacote portátil CAM Scanner `1.0.0` para Windows 11 24H2 x64 foi construído e passou na validação offline P12. `PREP12-09=CLEARED_IN_P12`; o executável, manifesto e resultados estão em [`docs/continuity/PROJECT_STATE.md`](docs/continuity/PROJECT_STATE.md) e [`docs/continuity/CONTINUITY_RECORD.md`](docs/continuity/CONTINUITY_RECORD.md). O ONEDIR tem 265 arquivos e 119.94 MiB.

CLI, instalação em pasta protegida, SINGLE com IP inválido, falha controlada sem dados graváveis, fixture ONVIF/MULTI em loopback, exportação XLSX com snapshot e integridade SHA-256 passaram. Gates 2/3/4/V e regressão integral (373 passed, 0 failed/skipped/deselected) são evidência PRE-P12 já aprovada e não foram repetidos nesta atividade. RTSP/PyAV permanece fail-closed.

Nenhuma câmera real foi acessada. Homologação operacional READ_ONLY e publicação/Gate 5 seguem pendentes de autorização separada; esta atualização não declara homologação concluída. Worktree e alterações preexistentes foram preservados; sem commit, push, merge, reset ou clean.

## Histórico da slice inicial (P1)

O estado abaixo descreve a situação anterior ao fechamento documentado de P1 em P1-CHECKPOINT-01; consulte o estado vigente acima.

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
