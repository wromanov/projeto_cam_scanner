# Execution Plan — P0-A03 e sequência P0–P12

## P0-A03 — Foundation Remediation & Continuity Reconciliation

**DELIVERY_UNIT** = atividade/checkpoint conforme PM-01 e padrão adotado no projeto; não declarar sprint.

Escopo autorizado: reconciliar os findings F-01…F-08 decididos pelo usuário, corrigir o contrato estrutural de `CameraResult`, atualizar testes estruturais e reconciliar roadmap/plano/continuidade. Não inclui implementação funcional. Git somente leitura.

Critérios de saída: F-03/F-05/F-06/F-07 remediados; F-01/F-02/F-04/F-08 corretamente registrados; contratos de segurança preservados; continuidade coerente e retomável; validações estruturais aplicáveis aprovadas; sem implementação funcional e sem escrita Git; PROJECT_STATE e handoff atualizados; Agent Handoff Gate avaliado.

P0-A02 permanece historicamente `CHANGES_REQUIRED`, com findings F-01…F-08. As decisões posteriores pertencem a P0-A03; não converter a review anterior em PASS. Esta atividade não concede aprovação Foundation, Project Opening Gate, autorização de P1 ou autorização Git.

## P1 — SINGLE Minimum Vertical Slice (CLOSED)

```text
DELIVERY_UNIT = definir conforme PM-01 e padrão já adotado no projeto
SLICE = SINGLE Minimum Vertical Slice
IMPLEMENTED_BASELINE_P1_A01 = Main Menu
→ SINGLE
→ terminal credentials
→ CameraTarget
→ InventoryService
→ CameraCollector
→ vendor-first routing + ONVIF read-only fallback/complement + preauth discovery (P1-A04)
→ CameraResult
→ TerminalUI
→ post-query menu
CURRENT_COLLECTION_STRATEGY = VENDOR_FIRST_WHEN_KNOWN
ONVIF_ROLE = GENERIC_FALLBACK + COMPLEMENT + PREAUTH_DISCOVERY
IMPLEMENTATION_ADAPTATION_REQUIRED = NO (P1-A04)
P1_IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_P1_A01_AND_P1_A04_ACTIVITY_PAYLOAD
P1_CONTRACT_STATUS = APPROVED
CAMERA_RESULT_FIELD_COUNT = 14
TYPING_DECISIONS_PENDING = NONE
P1_STATUS = CLOSED
P1_A02_HISTORICAL_RESULT = BLOCKED_AUTHENTICATION
CURRENT_STRATEGY_REAL_CAMERA_VALIDATION = PARTIAL_SUCCESS (P1-A05; details in PROJECT_STATE and continuity record)
```

Fluxo integrado em P1-A04: descoberta READ_ONLY pré-autenticação quando necessária → resolução do fabricante → adapter nativo registrado quando conhecido → ONVIF como complemento/fallback → `SUCCESS | PARTIAL_SUCCESS | FAILED`. Credenciais de XLSX são individuais por linha/câmera e `TRY_ALL_VENDOR_LOGINS = PROHIBITED`. O contrato P1 contém os requisitos completos e preserva os 14 campos atuais de `CameraResult` até eventual contrato futuro. P1 foi fechada em P1-CHECKPOINT-01 após validação operacional real READ_ONLY com evidência pré-auth preservada como `PARTIAL_SUCCESS`; autenticação ONVIF bem-sucedida não é obrigatória nesse cenário.

O contrato P1 está em [`../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`](../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md). O usuário aprovou preservar os dez campos existentes e acrescentar somente `error_code`, `error_message`, `collection_method` e `duration`, totalizando 14. As tipagens e regras canônicas dos quatro campos estão fechadas em P1-C01-R2. P1-A04 e P1-A05 estão concluídas conforme seus payloads autorizados.

Critérios mínimos de DONE: aplicação inicia; menu principal funciona; SINGLE solicita IP, username e password via `getpass()` no terminal; realiza consulta ONVIF somente leitura; obtém Manufacturer, Model, Serial e Firmware quando disponíveis; normaliza em `CameraResult` e exibe no terminal; erros esperados não mostram traceback ao operador; menu oferece `[1] pesquisar nova câmera`, `[2] ir para MULTI`, `[3] sair`; não altera configuração da câmera; testes aplicáveis passam; validação operacional ocorre em Python 3.14.x; integração da slice no fluxo canônico é demonstrada; consulta READ_ONLY contra câmera real autorizada é evidenciada.

`DEFINITION_OF_DONE` foi satisfeito em P1-CHECKPOINT-01. Próxima atividade: definição/contrato de P2; `P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`.

## P1-A03 — Collection Strategy Documentation Reconciliation

Concluída documentalmente em 2026-10-07 após checkpoint local do baseline P1-A01/P1-A02 (`d64ff9799d5d84c22a33ab7c24f589cbe619e3a6`). O usuário aprovou `VENDOR_FIRST_WHEN_KNOWN`; detalhes no contrato P1. P1-A02 continua como evidência histórica `BLOCKED` sob a premissa anterior; sua retomada para habilitar autenticação ONVIF foi supersedida. Nenhum código foi alterado nesta atividade. P1 continua `NOT_READY` até adaptação e validação.

```text
P1-A03 = COMPLETED_WITH_FINDINGS
NEXT_ACTIVITY = P1-A04 — Implementar adaptação da estratégia de coleta revisada
NEXT_ACTIVITY_READINESS = READY_FOR_ACTIVITY_DEFINITION
NEXT_ACTIVITY_AUTHORIZATION = NOT_GRANTED; autorização de implementação específica necessária
```

## P1-A04 — SINGLE vendor-first strategy adaptation

P1-A04 implementou no fluxo canônico a descoberta ONVIF READ_ONLY pré-autenticação, resolução estrutural de fabricante, consulta prioritária a um adapter registrado e fallback ONVIF genérico. O registry inicia vazio; os placeholders dos fabricantes não são registrados nem tratados como adapters funcionais. Evidência pré-autenticação válida preserva `PARTIAL_SUCCESS` quando a autenticação ONVIF falha. A entrada SINGLE existente foi mantida; o contrato não exige novo prompt de fabricante nessa slice. Validação contra câmera real não foi executada sem authority operacional específica.

```text
P1-A04_IMPLEMENTATION = COMPLETE
CANONICAL_FLOW = PASS
VENDOR_FIRST_ROUTING = PASS
PREAUTH_FINGERPRINT = PASS (estrutural e sintético)
ONVIF_AUTH_FAILURE_SEMANTICS = PASS (evidência preservada como PARTIAL_SUCCESS)
CAMERA_RESULT_FIELD_COUNT = 14
PYTHON = 3.14.0
PYTEST = PASS (51 tests)
RUFF = PASS
CLI_SMOKE = PASS (main menu and exit)
REAL_CAMERA_VALIDATION = NOT_RUN_NO_ACTIVITY_AUTHORITY
P1_STATUS = NOT_READY
NEXT_ACTIVITY = P1-A05 — Validar estratégia revisada READ_ONLY em target autorizado
NEXT_ACTIVITY_AUTHORIZATION = NOT_GRANTED
GIT_WRITES = NONE
```

## P1-A05 — Validação operacional READ_ONLY e fechamento

O payload executor autorizado registra target `10.143.36.33`, descoberta pré-auth aprovada e fabricante Hikvision. A coleta autenticada ONVIF retornou `AUTH_ERROR`; tratamento da falha, semântica `PARTIAL_SUCCESS` e segurança de senha passaram. Chamadas mutantes: zero. Finding de interoperabilidade ONVIF Digest: aberto, não bloqueante segundo o DoD revisado. P1 fechada; próxima atividade é definir o contrato P2. Implementação P2 não autorizada.

```text
P1_A05 = PASS
REAL_CAMERA_RESULT = PARTIAL_SUCCESS
PREAUTH_DISCOVERY = PASS
MANUFACTURER_RESOLUTION = HIKVISION
ONVIF_AUTHENTICATED_COLLECTION = AUTH_ERROR
AUTH_FAILURE_SEMANTICS = PASS
PARTIAL_SUCCESS_SEMANTICS = PASS
PASSWORD_SECURITY = PASS
MUTATING_CALLS = 0
ONVIF_DIGEST_INTEROPERABILITY = OPEN_NON_BLOCKING
P1_CLOSURE = PASS
P1_STATUS = CLOSED
NEXT_PHASE = P2
NEXT_ACTIVITY = Definition/contract of P2 per canonical roadmap
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
```

## ARCH-ALIGN-01 — Reconciliation documental da direção arquitetural

Concluída em 2026-10-08 com base em [`ARCH_AUDIT_01_REPORT.md`](../../audit/ARCH_AUDIT_01_REPORT.md), publicado no HEAD inicial `27582e1a3e26d861a94ece15c5d50a7348a8482f`. A auditoria foi preservada. A direção aprovada para evolução após P1 é `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, mantendo o monólito modular e os componentes existentes. A estratégia `VENDOR_FIRST_WHEN_KNOWN` permanece o baseline histórico/implementado da P1; sua substituição documental não declara mudança no código nem invalida o fechamento da P1.

```text
ARCHITECTURE_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE
DECISION_STATUS = DIRECTION_APPROVED
P2_STATUS = PLANNING / CONTRACT PENDING
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
ONVIF_DIGEST_ROOT_CAUSE = UNDETERMINED
```

P2-A01 — **Contrato arquitetural da P2** — foi aprovado documentalmente em 2026-10-09. O contrato define seleção híbrida determinística; identidade `IDENTITY_V1`; domínio mínimo; autenticação e limites por câmera; fallback; budgets; proveniência e status; TLS/destinos; PoC mínima Hikvision ISAPI e critérios T01–T15. A aprovação não autoriza implementação nem encerra a fase P2.

A política futura deve considerar fabricante conhecido/identificado, adapter funcional disponível, operações READ_ONLY suportadas, campos necessários, evidências existentes, mecanismo de autenticação disponível, limites de tempo/requisições e risco de autenticações adicionais. O coletor nativo permanece preferencial quando fabricante, capacidade e escopo de credenciais justificarem. A evolução preserva o monólito modular e seus componentes `ApplicationController`, `SingleWorkflow`, `MultiWorkflow`, `InventoryService`, `CameraTarget`, `CameraResult`, `AdapterRegistry`, `TerminalUI`, `ExcelReader` e `ExcelWriter`; contratos tipados internos podem ser avaliados no contrato P2, sem implementação autorizada nesta atividade.

Escopo planejado de P2: (A) contrato da política híbrida; (B) correção de preservação de evidências; (C) correção de resolução de fabricante/fingerprint; (D) diagnóstico por etapa/operação; (E) seleção controlada de autenticação ONVIF; (F) contratos de proveniência e merge; (G) PoC mínima Hikvision ISAPI integrada a SINGLE; (H) validação operacional posterior, com autorização independente; (I) expansão incremental do inventário e rede. Apenas a prova mínima Hikvision é antecipada de P7; o adapter Hikvision completo continua em P7. Ordem P3–P12 preservada. A PoC está planejada e não autorizada para implementação.

Achados materiais rastreados ao relatório original, sem duplicá-lo: F01 (HIGH, bug confirmado: perda de evidência); F02 (HIGH, bug confirmado: fingerprint falso/ordem-dependente); F03 (HIGH, limitação confirmada: diagnóstico por etapa/contexto de tentativas); F04 (MEDIUM, seleção ONVIF não explícita; causa Digest real não determinada); F05 (MEDIUM, capability nativa planejada, sem adapter funcional); F06 (MEDIUM, merge/proveniência limitado); F07 (MEDIUM, budgets/deadline/retries não conectados e porta fixa); F08 (MEDIUM, lacuna de domínio/contrato para inventário e tentativas); F09 (MEDIUM, dependências sem versões reproduzíveis e `httpx` ausente no ambiente auditado); F10 (MEDIUM, registry sem validação de capability e contrato genérico); F11 (MEDIUM, risco de fronteira de transporte/trust, sem exploração demonstrada); F12 (LOW, divergência documental SHA). A PoC é capability planejada; riscos e hipóteses permanecem distinguidos de bugs confirmados. O 401 Digest não está declarado resolvido.

Invariantes da direção: `READ_ONLY = MANDATORY`; credenciais limitadas à própria câmera; `NO_CREDENTIAL_SPRAYING`; `NO_PASSWORD_OUTPUT`; `NO_MUTATING_CAMERA_OPERATIONS`. ONVIF discovery não é obrigatória se fabricante conhecido e caminho nativo válido cobrirem os campos necessários. Nenhuma conta ONVIF deve ser provisionada em massa como pré-requisito. Nenhum detalhe pendente da P2 está aprovado implicitamente por esta direção.

```text
PREVIOUS = VENDOR_FIRST_WHEN_KNOWN
APPROVED_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE
SOURCE = docs/audit/ARCH_AUDIT_01_REPORT.md
P1_STATUS = CLOSED
P2_STATUS = CONTRACT_PENDING
NEXT_ACTIVITY = P2-A01 — Contrato arquitetural da P2
NEXT_ACTIVITY_READINESS = READY_FOR_ACTIVITY_DEFINITION
NEXT_ACTIVITY_AUTHORIZATION = NOT_GRANTED; separate activity authority required; implementation NOT_GRANTED
```

## P2-A01 — Hybrid Collection Architecture Contract (estado inicial da proposta; supersedido por P2-A01-R1)

Concluída como proposta documental no baseline `d8d2d02c9a659391fd80a7b4590f6767ab625cba` (`master`, igual a `origin/master` na entrada). O contrato está em [`../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`](../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md). Preserva P1 e a direção híbrida aprovada, registra F01–F03, política de seleção, diagnóstico, evidências/proveniência, auth/fallback, transporte, budgets, PoC ISAPI, aceites T01–T15 e sequência incremental.

```text
P2_A01_DOCUMENT = CREATED_AND_ROOT_REVIEWED
CONTRACT_STATUS = PENDING_APPROVAL
MATERIAL_DECISIONS_PENDING = D01,D02,D03,D04,D05,D06
D07 = DEFERRED; NOT_MATERIAL_TO_P2_A01
P1_STATUS = CLOSED
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
GIT_WRITES = NONE
NEXT_ACTIVITY = USER REVIEW / APPROVAL OF P2-A01 CONTRACT
NEXT_ACTIVITY_AUTHORIZATION = REVIEW_ONLY
```

O DoD desta atividade documental foi satisfeito como proposta revisada. A aprovação do contrato e qualquer implementação continuam decisões separadas do usuário. Não executar câmeras reais nem testes nesta atividade; a baseline informada de 51 testes é histórica e não foi reexecutada.

## Roadmap executável e integração

O roadmap normativo está em [`ROADMAP.md`](ROADMAP.md). Sequência preservada: P0 Foundation; P1 SINGLE mínimo fechado sob seu contrato; P2 contrato/política híbrida, correções, PoC ISAPI mínima e expansão incremental; P3 snapshot SINGLE sem XLSX; P4 MULTI + XLSX + snapshot embedded; P5 concorrência/robustez; P6 Axis; P7 adapter Hikvision completo; P8 Samsung/Hanwha; P9 Dahua; P10 Panasonic; P11 Bosch; P12 hardening/regressão/packaging.

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
NEXT_ACTIVITY_AT_THAT_TIME = Retomar P1-A02 após confirmar autenticação e permissão ONVIF da conta autorizada
```

## P1-A02 — Real Camera READ_ONLY Validation

O usuário autorizou a validação READ_ONLY para `10.143.36.33`. Três execuções do fluxo SINGLE retornaram `AUTH_ERROR`, confirmado pelo log sanitizado. O fluxo de erro e o menu pós-consulta funcionaram, sem dados do dispositivo. P1 permanece `NOT_READY`; retomar esta atividade após confirmar autenticação e permissão ONVIF da conta autorizada. Credenciais devem ser fornecidas localmente pelo prompt `getpass()`.

```text
P1-A02 = BLOCKED
TARGET_AUTHORIZED = YES
TARGET_IP = 10.143.36.33
REAL_CAMERA_VALIDATION = BLOCKED_AUTHENTICATION
NEXT_ACTIVITY_AT_THAT_TIME = Retomar P1-A02 após confirmar autenticação e permissão ONVIF da conta autorizada
```

## P2-A01-R1 — Reconciliation of Human Contract Approval (2026-10-09)

O usuário aprovou D01 (`APPROVED_WITH_REVISION`) e D02–D06 (`APPROVED_WITH_ADJUSTMENTS`); D00 já estava aprovada. O contrato em [`../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`](../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md) foi reconciliado integralmente, incluindo perfil `IDENTITY_V1`, fallback, coleta complementar, proveniência, casos A–G, PoC ISAPI e critérios T01–T15. F01–F03 permanecem preservados. D07 continua `DEFERRED`.

```text
ACTIVITY = P2 CONTRACT APPROVAL RECONCILIATION
DECISIONS_D01_D06 = APPROVED
CONTRACT_STATUS = APPROVED
P0_STATUS = CLOSED
P1_STATUS = CLOSED
P2_PHASE_STATUS = OPEN
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
DEPENDENCY_CHANGES = NONE
REAL_CAMERA_CALLS = NONE
GIT_WRITES = NONE
NEXT_ACTIVITY = P2 planning/execution authority as a separate user decision
```
