# PROJECT_STATE — projeto_cam_scanner

```text
PROJECT_ID = projeto_cam_scanner
PROJECT_ROOT_HOME = ambiente atual, root C:\Users\walac\desenvolvimento\projeto_cam_scanner
PROJECT_ROOT_WORK = não existe neste computador
CURRENT_PHASE = P0 — Project Opening + Foundation
CURRENT_ACTIVITY = P0-A03-G1 — Governed Git Checkpoint Publication; concluída com findings
CURRENT_DELIVERY_UNIT = activity/checkpoint conforme PM-01 (sem sprint declarada)
DELIVERY_UNIT_STATUS = COMPLETED_WITH_FINDINGS
LAST_COMPLETED_ACTIVITY = P0-A03-G1 — Governed Git Checkpoint Publication
PREVIOUS_COMPLETED_ACTIVITY = P0-A02 — Foundation Review (CHANGES_REQUIRED; BLOCKED_FOR_FORMAL_CLOSURE)
POLICY_INTERNALIZATION_GATE = PASS_WITH_FINDINGS (conforme payload; não reexecutado neste checkpoint)
ENGINEERING_FOUNDATION = 10/10 ITEMS APPROVED (conforme payload do usuário)
FOUNDATION_REVIEW = P0-A02 COMPLETED; CHANGES_REQUIRED; findings F-01..F-08
P0_A02_COMPLETION = 90%
P0_A02_STATUS = BLOCKED_FOR_FORMAL_CLOSURE
FOUNDATION_REVIEW_APPROVAL_RECOMMENDATION = DO_NOT_APPROVE_YET
FOUNDATION_APPROVAL = NOT_GRANTED
PROJECT_OPENING_GATE = NOT_READY
AGENT_HANDOFF_GATE = PASS
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
GIT_WRITE_AUTHORIZATION = NOT_GRANTED_FOR_FUTURE_ACTIONS; P0-A03-G1 authorization consumed
GIT_REPOSITORY = YES
GIT_BRANCH = master
GIT_COMMITS = 2 (initial foundation checkpoint + continuity update)
GIT_HEAD = CURRENT_GOVERNED_CHECKPOINT
CURRENT_GOVERNED_CHECKPOINT = CURRENT_REPOSITORY_HEAD
GIT_REMOTE = origin (https://github.com/wromanov/projeto_cam_scanner.git)
GIT_UPSTREAM = origin/master
WORKING_TREE = CLEAN
CHAT_HISTORY_REQUIRED_FOR_RESUMPTION = NO
```

## Identidade e objetivo

CLI para Windows para consultar câmeras IP e produzir inventário. Root escolhido: `C:\Users\walac\desenvolvimento\projeto_cam_scanner`, que existe e corresponde ao root HOME declarado. O root WORK `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner` não existe. Código da aplicação não pode conter paths absolutos de máquina.

## Escopo funcional aprovado

- Menu principal: `[1] SINGLE`, `[2] MULTI`, `[3] EXIT`.
- SINGLE solicita IP e username no terminal, password por `getpass()`, consulta exatamente uma câmera e mostra o resultado. Depois oferece nova pesquisa, MULTI ou saída. Não importa nem gera XLSX automaticamente.
- MULTI solicita XLSX de entrada com IP/USERNAME/PASSWORD, processa em lote, mostra progresso percentual e gera XLSX consolidado com snapshot.
- Famílias: Axis, Hikvision, Samsung/Samsung Techwin/Hanwha, Dahua, Panasonic e Bosch.
- Acesso READ_ONLY; coleta ONVIF-first; manufacturer adapter como fallback.
- Fallback de snapshot: ONVIF_HTTP → VENDOR_HTTP → RTSP_FRAME.
- P0-A03 autoriza somente remediação estrutural/documental; nenhuma coleta funcional.

## Engineering Foundation aprovada (fonte de entrada: payload fornecido pelo usuário)

| ID | Decisões persistidas |
|---|---|
| EF-STACK-01 | Python 3.14.x; venv, pip, pyproject.toml; onvif-python, httpx, openpyxl, Pillow, Rich, PyAV, pytest, Ruff e tomllib; sem framework CLI e sem FFmpeg externo obrigatório; Windows primário. |
| EF-ARCH-01 | Modular monolith CLI; ports/adapters leves; ApplicationController controla navegação; SingleWorkflow/MultiWorkflow compartilham InventoryService/CameraCollector; CameraTarget comum; CameraResult sem password; ONVIF-first; ManufacturerNormalizer + AdapterRegistry; adapters Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic e Bosch; SnapshotService separado; ExcelReader/ExcelWriter isolados; TerminalUI/ProgressReporter isolam Rich; PARTIAL_SUCCESS suportado; READ_ONLY estrutural; sem banco, event bus ou framework DI. |
| EF-CONCURRENCY-01 | ThreadPoolExecutor futuro; max_workers padrão 8, configurável 1..32; no máximo 2 RTSP concorrentes; paralelismo por câmera e nenhum intra-câmera por padrão; falha individual não aborta lote; ordem da entrada preservada; Ctrl+C graceful; parciais preservados quando possível; SUCCESS/PARTIAL_SUCCESS/FAILED/CANCELLED. |
| EF-RESILIENCE-01 | Connect 3s; request 7s; budget ONVIF 15s; fabricante 10s; snapshot HTTP 10s; RTSP open 8s; primeiro frame 5s; soft deadline/câmera 45s; ICMP não obrigatório; 1 retry e backoff 1s só para falha transitória; sem retry para auth failure ou connection refused. |
| EF-SECURITY-01 | SINGLE usa getpass; password só em memória durante coleta; nunca em output/log/CameraResult/temporário/telemetria; `CameraTarget.password` repr=False; sanitização obrigatória; sem criptografia XLSX proprietária V1; XLSX MULTI é sensível. |
| EF-SNAPSHOT-01 | Ordem ONVIF_HTTP → VENDOR_HTTP → RTSP_FRAME; captura de um frame; thumbnail 320×180; JPEG quality 75; proporção preservada sem crop/stretch; metadata removida; temporários no OS temp com prefixo `cam_scanner_`; keep=false; stale cleanup 24h; apagar snapshot após uso/incorporação; sem upload/processamento externo. |
| EF-XLSX-01 | Entrada obrigatória IP/USERNAME/PASSWORD; cabeçalhos case-insensitive e ordem física livre; extras ignoradas; vazias ignoradas; linha inválida vira FAILED sem abortar lote; IP duplicado permitido com warning. Saída INVENTARIO e RESUMO; colunas na ordem aprovada do payload; missing=N/A; sem password; ordem de entrada; header congelado; autofilter; sem gráficos V1. |
| EF-LOGGING-01 | stdlib logging; um arquivo por execução; RUN_ID; INFO default, DEBUG suportado; IP/hostname podem aparecer; username não por default; password/auth headers/URL com credencial/conteúdo snapshot nunca; sanitização; sem stack trace no terminal; stack inesperado somente no log sanitizado; retenção 30 dias; máximo 10 MB; sem logging externo ou telemetria. |
| EF-CONFIG-01 | Paths relativos ao runtime/application root; TOML por tomllib; `config/settings.toml` e `settings.example.toml`; credenciais proibidas; ausente usa defaults seguros; inválida fail fast; chave desconhecida warning+ignore; EffectiveConfig; input/output/logs; input externo permitido; temporários OS temp; XLSX sensível fora do Git. |
| EF-PACKAGING-01 | Python 3.14.x + venv; entrypoint `cam-scanner` e `python -m cam_scanner`; PyInstaller ONEDIR; Windows 11 x64; sem Python no destino; console YES; sem installer; portable; SemVer; inicial 0.1.0; release operacional alvo 1.0.0; `packaging/cam_scanner.spec` e `packaging/build.ps1`; publicação separadamente autorizada. |

## Roadmap e execução

O roadmap P0–P12 está em [`planning/ROADMAP.md`](planning/ROADMAP.md); sequência e DoD em [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md). P1 é SINGLE Minimum Vertical Slice, planejada e sem autorização de implementação.

## Estado Git, validação e risco

O checkpoint governado foi publicado em `origin/master`; consulte o HEAD corrente em runtime, sem depender de hash persistido neste documento. A P0-A03-G1 criou o commit `chore(project): establish governed foundation baseline` e um commit documental para reconciliar esta continuidade. Nenhuma credencial real foi persistida. O Continuity 3.0 binding foi validado na P0-A02 usando PowerShell `Test-Json -Schema` contra o schema canônico; esta evidência não pertence à P0-A01. Python 3.14.x não foi validado; a baseline permanece 3.14.x e P1 exige validação operacional nessa versão. O root WORK não existe neste computador; HOME permanece root válido.
As verificações sintáticas/imports foram executadas com Python 3.12.14 do runtime local; o alvo da Foundation é Python 3.14.x e não está instalado neste ambiente.

## Gates, readiness e autorização

P0-A02 executou a Foundation Review e permaneceu `CHANGES_REQUIRED`; P0-A03 não promoveu essa review nem concedeu Foundation Approval. A aprovação 10/10 da Engineering Foundation permanece como decisão reportada pelo usuário, distinta do resultado da review.

```text
PROJECT_STATE_UPDATE = PASS
ACTIVITY_COMPLETE = YES (P0-A03-G1 outputs completos com findings registrados)
ACTIVITY_COMPLETION_PERCENT = 100% (exclusivamente P0-A03-G1)
P0_A03_STATUS = COMPLETED_WITH_FINDINGS
P0_A03_G1_STATUS = COMPLETED_WITH_FINDINGS
P0_A03_G1_COMPLETION = 100%
P0_A03_G1_GIT_CHECKPOINT = PUBLISHED; LOCAL_HEAD = CURRENT_GOVERNED_CHECKPOINT; UPSTREAM = origin/master
FOUNDATION_REVIEW_RECHECK_READINESS = READY
FOUNDATION_APPROVAL = NOT_GRANTED_BY_P0_A03
PROJECT_OPENING_GATE = NOT_YET_PASS
SAFE_RESUME_POINT = pacote de continuidade reconciliado; próxima atividade é recheck da Foundation Review; P1 não autorizada
NEXT_ACTIVITY = P0-A04 — Foundation Review recheck
NEXT_ACTIVITY_READINESS = READY
NEXT_ACTIVITY_AUTHORIZATION = revisão/recheck somente; implementação P1 e novas escritas Git não autorizadas
LAST_VALIDATED_INTEGRATED_BASELINE = NONE (nenhuma slice funcional integrada; scaffold somente)
OPEN_DECISIONS = executar Foundation Review e determinar Project Opening Gate
BLOCKERS = Foundation Review recheck e Project Opening Gate ainda pendentes; não impedem encerramento da remediação P0-A03
KNOWN_RISKS = Python 3.14.x não validado; baseline de governança reside fora do root do projeto
DEFERRED_ITEMS = validação runtime 3.14.x até fase aplicável; expansão build.ps1 para P12; P1 e implementações funcionais P1-P12 sem autorização
FINDING_DISPOSITIONS = F-01 ACCEPTED_DEFERRED; F-02 ACCEPTED_INFORMATIONAL; F-03 REMEDIATED; F-04 ACCEPTED_RESOLVED_EVIDENCE; F-05 REMEDIATED; F-06 REMEDIATED; F-07 REMEDIATED; F-08 ACCEPTED_DEFERRED_TO_P12
KNOWN_STALE_STATE = NO
CONTRADICTORY_ACTIVE_STATE = NO
SUPERSEDED_AUTHORITY_USED_AS_CURRENT = NO
NEW_AGENT_CAN_RESUME_FROM_GOVERNED_PROJECT_ARTIFACTS = YES
```

## Invariantes atuais

- Nenhuma coleta ou request real a câmera é executado em P0-A03.
- Nenhuma senha pode aparecer em output, log, `CameraResult`, temporário ou telemetria; o modelo de resultado não possui campo de senha.
- A política de acesso permanece READ_ONLY.
- Nenhuma funcionalidade real de snapshot, RTSP, XLSX MULTI ou concorrência deve ser criada em P0-A03.
- Nenhum path absoluto de máquina foi colocado no código de aplicação.
- As escritas Git autorizadas para P0-A03-G1 foram concluídas; futuras escritas Git exigem nova autorização explícita.
