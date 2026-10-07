# Execution Plan — P0-A03 e sequência P0–P12

## P0-A03 — Foundation Remediation & Continuity Reconciliation

**DELIVERY_UNIT** = atividade/checkpoint conforme PM-01 e padrão adotado no projeto; não declarar sprint.

Escopo autorizado: reconciliar os findings F-01…F-08 decididos pelo usuário, corrigir o contrato estrutural de `CameraResult`, atualizar testes estruturais e reconciliar roadmap/plano/continuidade. Não inclui implementação funcional. Git somente leitura.

Critérios de saída: F-03/F-05/F-06/F-07 remediados; F-01/F-02/F-04/F-08 corretamente registrados; contratos de segurança preservados; continuidade coerente e retomável; validações estruturais aplicáveis aprovadas; sem implementação funcional e sem escrita Git; PROJECT_STATE e handoff atualizados; Agent Handoff Gate avaliado.

P0-A02 permanece historicamente `CHANGES_REQUIRED`, com findings F-01…F-08. As decisões posteriores pertencem a P0-A03; não converter a review anterior em PASS. Esta atividade não concede aprovação Foundation, Project Opening Gate, autorização de P1 ou autorização Git.

## P1 — SINGLE Minimum Vertical Slice (planejada; não autorizada)

```text
DELIVERY_UNIT = definir conforme PM-01 e padrão já adotado no projeto
SLICE = SINGLE Minimum Vertical Slice
CANONICAL_FLOW = Main Menu
→ SINGLE
→ terminal credentials
→ CameraTarget
→ InventoryService
→ CameraCollector
→ ONVIF read-only
→ CameraResult
→ TerminalUI
→ post-query menu
P1_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
```

Critérios mínimos de DONE: aplicação inicia; menu principal funciona; SINGLE solicita IP, username e password via `getpass()` no terminal; realiza consulta ONVIF real somente leitura; obtém Manufacturer, Model, Serial e Firmware quando disponíveis; normaliza em `CameraResult` e exibe no terminal; erros esperados não mostram traceback ao operador; menu oferece `[1] pesquisar nova câmera`, `[2] ir para MULTI`, `[3] sair`; não altera configuração da câmera; testes aplicáveis passam; validação operacional ocorre em Python 3.14.x; integração da slice no fluxo canônico é demonstrada.

`P1_PLANNED != P1_AUTHORIZED`. `DEFINITION_OF_READY` deve passar antes da implementação material. `DEFINITION_OF_DONE` exige implementação, validação de módulo, integração canônica, validação de integração/fluxo acumulado/regressão quando aplicáveis, invariantes, aceite, documentação e PROJECT_STATE reconciliados, delivery unit atualizada e blockers resolvidos.

## Roadmap executável e integração

O roadmap normativo está em [`ROADMAP.md`](ROADMAP.md). Sequência: P0 Foundation; P1 SINGLE mínimo; P2 expansão de inventário SINGLE; P3 snapshot SINGLE sem XLSX; P4 MULTI + XLSX + snapshot embedded; P5 concorrência/robustez; P6 Axis; P7 Hikvision; P8 Samsung/Hanwha; P9 Dahua; P10 Panasonic; P11 Bosch; P12 hardening/regressão/packaging.

Para cada slice: `IMPLEMENT → MODULE_VALIDATE → INTEGRATE_INTO_CANONICAL_FLOW → INTEGRATION_VALIDATE → VALIDATE_ACCUMULATED_FLOW → REGRESSION_VALIDATE → RECONCILE_PROJECT_STATE → CLOSE`. Adiamento de integração exige registro explícito de motivo, dependência, owner, target slice, risco e decisão de usuário ou justificativa de não necessidade. Não acumular módulos isolados para integração big-bang.

## Baseline e evidências da P0-A03

Root ativo: `C:\Users\walac\desenvolvimento\projeto_cam_scanner`. Estado Git observado antes da edição: repositório existe, branch `master`, zero commits, `HEAD` inválido/não criado. Não executar stage, commit, push, reset, checkout, clean, tag ou release.

Binding Continuity 3.0: evidência de validação na P0-A02 com PowerShell `Test-Json -Schema` contra o schema canônico; não atribuir esta evidência à P0-A01. Python 3.14.x não foi validado nesta atividade; a baseline oficial permanece 3.14.x e P1 não pode fechar sem validação nela. O root WORK ausente é fato ambiental; HOME é o root ativo válido.

## P12 — gate de build operacional

Antes de build operacional/release, validar `TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER`. A lacuna atual de `packaging/build.ps1` foi aceita e deferida a P12; não expandir script nesta atividade salvo correção de referência factual inconsistente.
