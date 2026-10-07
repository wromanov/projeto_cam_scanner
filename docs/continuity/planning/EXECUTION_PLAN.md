# Execution Plan — P0-A03 e sequência P0–P12

## P0-A03 — Foundation Remediation & Continuity Reconciliation

**DELIVERY_UNIT** = atividade/checkpoint conforme PM-01 e padrão adotado no projeto; não declarar sprint.

Escopo autorizado: reconciliar os findings F-01…F-08 decididos pelo usuário, corrigir o contrato estrutural de `CameraResult`, atualizar testes estruturais e reconciliar roadmap/plano/continuidade. Não inclui implementação funcional. Git somente leitura.

Critérios de saída: F-03/F-05/F-06/F-07 remediados; F-01/F-02/F-04/F-08 corretamente registrados; contratos de segurança preservados; continuidade coerente e retomável; validações estruturais aplicáveis aprovadas; sem implementação funcional e sem escrita Git; PROJECT_STATE e handoff atualizados; Agent Handoff Gate avaliado.

P0-A02 permanece historicamente `CHANGES_REQUIRED`, com findings F-01…F-08. As decisões posteriores pertencem a P0-A03; não converter a review anterior em PASS. Esta atividade não concede aprovação Foundation, Project Opening Gate, autorização de P1 ou autorização Git.

## P1 — SINGLE Minimum Vertical Slice (autorizada; implementação integrada; validação operacional pendente)

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
P1_IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_P1_A01
P1_CONTRACT_STATUS = APPROVED
CAMERA_RESULT_FIELD_COUNT = 14
TYPING_DECISIONS_PENDING = NONE
P1_STATUS = NOT_READY
REAL_CAMERA_VALIDATION = BLOCKED_AUTHENTICATION
```

O contrato aprovado está em [`../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`](../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md). O usuário aprovou preservar os dez campos existentes e acrescentar somente `error_code`, `error_message`, `collection_method` e `duration`, totalizando 14. As tipagens e regras canônicas dos quatro campos estão fechadas no contrato P1-C01-R2. A autorização de implementação foi concedida no payload executor de P1-A01.

Critérios mínimos de DONE: aplicação inicia; menu principal funciona; SINGLE solicita IP, username e password via `getpass()` no terminal; realiza consulta ONVIF somente leitura; obtém Manufacturer, Model, Serial e Firmware quando disponíveis; normaliza em `CameraResult` e exibe no terminal; erros esperados não mostram traceback ao operador; menu oferece `[1] pesquisar nova câmera`, `[2] ir para MULTI`, `[3] sair`; não altera configuração da câmera; testes aplicáveis passam; validação operacional ocorre em Python 3.14.x; integração da slice no fluxo canônico é demonstrada; consulta READ_ONLY contra câmera real autorizada é evidenciada.

`P1_PLANNED != P1_AUTHORIZED`. `DEFINITION_OF_READY` deve passar antes da implementação material. `DEFINITION_OF_DONE` exige implementação, validação de módulo, integração canônica, validação de integração/fluxo acumulado/regressão quando aplicáveis, invariantes, aceite, documentação e PROJECT_STATE reconciliados, delivery unit atualizada e blockers resolvidos.

## Roadmap executável e integração

O roadmap normativo está em [`ROADMAP.md`](ROADMAP.md). Sequência: P0 Foundation; P1 SINGLE mínimo; P2 expansão de inventário SINGLE; P3 snapshot SINGLE sem XLSX; P4 MULTI + XLSX + snapshot embedded; P5 concorrência/robustez; P6 Axis; P7 Hikvision; P8 Samsung/Hanwha; P9 Dahua; P10 Panasonic; P11 Bosch; P12 hardening/regressão/packaging.

Para cada slice: `IMPLEMENT → MODULE_VALIDATE → INTEGRATE_INTO_CANONICAL_FLOW → INTEGRATION_VALIDATE → VALIDATE_ACCUMULATED_FLOW → REGRESSION_VALIDATE → RECONCILE_PROJECT_STATE → CLOSE`. Adiamento de integração exige registro explícito de motivo, dependência, owner, target slice, risco e decisão de usuário ou justificativa de não necessidade. Não acumular módulos isolados para integração big-bang.

## Baseline e evidências históricas da P0-A03

Root ativo: `C:\Users\walac\desenvolvimento\projeto_cam_scanner`. Estado Git observado antes da edição: repositório existe, branch `master`, zero commits, `HEAD` inválido/não criado. Não executar stage, commit, push, reset, checkout, clean, tag ou release.

Binding Continuity 3.0: evidência de validação na P0-A02 com PowerShell `Test-Json -Schema` contra o schema canônico; não atribuir esta evidência à P0-A01. Python 3.14.x não foi validado nesta atividade; a baseline oficial permanece 3.14.x e P1 não pode fechar sem validação nela. O root WORK ausente é fato ambiental; HOME é o root ativo válido.

## P12 — gate de build operacional

Antes de build operacional/release, validar `TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER`. A lacuna atual de `packaging/build.ps1` foi aceita e deferida a P12; não expandir script nesta atividade salvo correção de referência factual inconsistente.

## P0-A04 — Foundation Review Recheck

Escopo: leitura, validações existentes e atualização de estado/continuidade. Sem implementação funcional, mudança arquitetural ou escrita Git. Critérios de saída: conferir F-01…F-08, registrar evidências e limites, emitir resultado da revisão e reconciliar continuidade. Resultado e critérios verificados em [`../FOUNDATION_REVIEW_P0_A04.md`](../FOUNDATION_REVIEW_P0_A04.md). Próxima decisão e autorização em PROJECT_STATE; os fatos ambientais da seção P0-A03 acima são históricos.

## P1-C01-R1 — CameraResult Contract Reconciliation (documental)

Registro histórico de P1-C01-R1: contrato documental somente, sem código. A decisão explícita do usuário aprovou os quatro novos campos, preservando os dez existentes, sem extension bag ou password. P1-C01-R2 fechou posteriormente as tipagens; a autorização de implementação foi concedida depois em P1-A01.

## P1-C01-R2 — Typing Contract Closure (documental)

Decisões de tipo, vocabulário, nulabilidade, regras de sucesso/falha, sanitização e duração foram persistidas no contrato P1. `CollectionStatus` existente é reutilizado. O estado histórico de autorização foi supersedido pelo payload executor da P1-A01.

## P1-A01 — SINGLE Minimum Vertical Slice Implementation

O fluxo CLI → ApplicationController → menu → SingleWorkflow → entrada protegida → InventoryService → Generic ONVIF collector → `GetDeviceInformation` → CameraResult → terminal → decisão de navegação foi integrado e validado com cliente ONVIF falso em Python 3.14.0. Validações sintéticas acumuladas e regressão aplicável passaram; pytest e Ruff passaram. A consulta real READ_ONLY não foi executada porque nenhum target e credencial autorizados foram fornecidos.

```text
P1-A01_IMPLEMENTATION = COMPLETE
CANONICAL_FLOW_INTEGRATED = YES
SYNTHETIC_INTEGRATION_VALIDATION = PASS
REAL_CAMERA_VALIDATION = BLOCKED_NO_AUTHORIZED_TARGET
P1_STATUS = NOT_READY
NEXT_ACTIVITY = Retomar P1-A02 após confirmar autenticação e permissão ONVIF da conta autorizada
```

## P1-A02 — Real Camera READ_ONLY Validation

O usuário autorizou a validação READ_ONLY para `10.143.36.33`. Três execuções do fluxo SINGLE retornaram `AUTH_ERROR`, confirmado pelo log sanitizado. O fluxo de erro e o menu pós-consulta funcionaram, sem dados do dispositivo. P1 permanece `NOT_READY`; retomar esta atividade após confirmar autenticação e permissão ONVIF da conta autorizada. Credenciais devem ser fornecidas localmente pelo prompt `getpass()`.

```text
P1-A02 = BLOCKED
TARGET_AUTHORIZED = YES
TARGET_IP = 10.143.36.33
REAL_CAMERA_VALIDATION = BLOCKED_AUTHENTICATION
NEXT_ACTIVITY = Retomar P1-A02 após confirmar autenticação e permissão ONVIF da conta autorizada
```
