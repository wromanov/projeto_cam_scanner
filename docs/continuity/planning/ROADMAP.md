# Roadmap aprovado — projeto_cam_scanner

## Checkpoint corrente — CAM_SCANNER_P12_WINDOWS_ONEDIR_BUILD_AND_VALIDATION (2026-10-19)

O estado factual está em [`PROJECT_STATE.md`](../PROJECT_STATE.md). Os gates pré-P12 continuam `GATE_2/3/4/V=PASS`, `P12_READINESS=READY_FOR_P12`; não foram repetidos. O build ONEDIR `1.0.0` e os smoke tests P12 passaram, limpando `PREP12-09` para o estágio de empacotamento. P0/P1/P2 e homologações anteriores não mudam. Homologação operacional READ_ONLY e Gate 5/publicação continuam pendentes de autorização separada; nenhuma câmera real foi acessada.

## Aditivo — recuperação de continuidade (2026-10-16; supersedido pelo checkpoint corrente acima)

O gate de authorities passou com os nove pins do binding correspondendo aos bytes das entradas ZIP verificadas; ver evidências e hash do lock em [`PROJECT_STATE.md`](../PROJECT_STATE.md). PyPI público foi autorizado em ambiente local autorizado, sob políticas aplicáveis. `PIP_NO_INDEX=1` permanece configurado. PREP12-10 continua pendente de reprodução limpa e aceite formal. PREP12-01/02/04/05 seguem pendentes de aceite, PREP12-11 permanece condicional, `GATE_V=NOT_MET` e `P12_READINESS=BLOCKED`. Nenhum milestone PRE-P12 ou P12 foi encerrado por esta atualização.

## Snapshot anterior da execução — PRE-P12 targeted acceptance resume (2026-10-16; fonte/lock superseded acima)

### Aditivo de aceite e bloqueios — 2026-10-16 (vigente)

O parecer Architect independente está em [`docs/audit/PRE_P12_ACCEPTANCE_REASSESSMENT_2026-10-16.md`](../../audit/PRE_P12_ACCEPTANCE_REASSESSMENT_2026-10-16.md). PREP12-01/02/04/05 permanecem `OPEN`; o Gate 2 requer regressão integral sem skips/deselected e 01/02 ainda requerem Gate 3. PREP12-10=`BLOCKED_EXTERNAL_DEPENDENCY`: nenhuma fonte aprovada foi identificada, `PIP_NO_INDEX=1` deve permanecer, e `requirements/locks/windows-py314.in` é apenas o manifesto candidato já preparado, sem alteração de versões. PREP12-11=`OPEN_CONDITIONAL`, pois a criação de symlink falhou com HRESULT `0x80070522`/WinError 1314. A suíte completa de referência tem um skip; portanto `GATE_V=NOT_MET`, `P12_READINESS=BLOCKED`, `ACTIVITY_COMPLETE=NO`, progresso 96%.

P0/P1 permanecem CLOSED; P2 permanece IN_PROGRESS. A retomada PRE-P12 está no worktree `projeto_cam_scanner_pre_p12_remediation`, branch `feature/pre-p12-unified-remediation`, checkpoint HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e`; o workspace gate passou e as alterações locais/não rastreados foram preservados.

PREP12-01/02 têm evidência comportamental direta aprovada para HTTPS com preauth integrado SINGLE/MULTI e seis casos negativos em cada workflow. Architect Sol/High concluiu revisão favorável do delta, sem defeito material novo; aceite formal V segue pendente. PREP12-04 demonstra deadline único por câmera persistente entre fila, inventário e snapshot, sem RTSP após expiração. PREP12-05 tem 8 testes focados aprovados, com cancelamento integrado em SINGLE/MULTI e preservação dos resultados; exportação de workbook de lote incompleto é impedida após cancelamento.

PREP12-11 segue OPEN: retention/rollover, bloqueio de arquivo e ausência de sentinelas username/password foram demonstrados em filesystem Windows real; symlink real pulou por WinError 1314. PREP12-10 segue OPEN: estratégia/entrada candidata foram preparadas, mas lock transitivo/hash não foi gerado porque o índice restrito não ofereceu `av==19.0.1`; nenhuma dependência foi instalada. Pytest completo pós-delta não concluiu por WinError 5 em basetemp/fixtures; baseline histórica 325 passed não foi repetida. Ruff, compileall, `pip check` e `git diff --check` passaram. Sem build P12 ou câmeras reais. P12_READINESS=BLOCKED; ACTIVITY_COMPLETE=NO.

## Checkpoint histórico de execução — 2026-10-15 (supersedido)

Este checkpoint de 88% foi supersedido pela atualização PRE-P12 targeted acceptance resume de 2026-10-16 no início deste documento. Os resultados abaixo permanecem como registro histórico.

P0 e P1 permanecem CLOSED; P2 está IN_PROGRESS. Evidências offline anteriores para P3–P11 não declaram fechamento formal nem homologação real. A remediação PRE-P12 permanece no checkpoint 88%, no worktree feature/pre-p12-unified-remediation, HEAD 37bc8c4cc718559fc1e6f39a9b8a1145563a551e, com alterações locais não publicadas. A evidência de regressão abaixo foi fornecida pelo usuário a partir de Windows PowerShell autorizado; Root e Architect não executaram os testes.

~~~text
PYTHON = 3.14.0
PROJECT_IMPORT = CORRECT_WORKTREE
OS_SCANDIR = PASS
TEMP_ENVIRONMENT = PASS
FOCUSED_TESTS = 115 PASSED (9.20s)
FULL_PYTEST = 318 PASSED (8.51s)
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
SKIPPED_DESELECTED_COUNTS = NOT_SEPARATELY_PROVIDED
~~~

| Fase | Estado vigente da execução offline | Homologação real / fechamento formal |
|---|---|---|
| P0 | CLOSED | Fechamento registrado |
| P1 | CLOSED; slice SINGLE e validação operacional READ_ONLY registradas | Fechamento registrado em P1-CHECKPOINT-01 |
| P2 | IN_PROGRESS; política híbrida aprovada; remediação PRE-P12 em andamento | Fase permanece aberta |
| P3 | Fluxo de snapshot implementado/integrado e validado offline em checkpoint anterior | Sem fechamento formal novo; captura RTSP/PyAV está fail-closed |
| P4 | Fluxo MULTI + XLSX + snapshot integrado e smoke offline registrado em checkpoint anterior | Sem fechamento formal novo |
| P5 | Implementação de concorrência offline e validação registradas em atividade própria | Sem fechamento formal de fase registrado |
| P6 | Adapter Axis validado offline | Homologação de família/modelo real não registrada |
| P7 | Adapter Hikvision existente e hardening de transporte em remediação offline | Homologação P7 de modelos não registrada |
| P8 | Adapter Hanwha validado parcialmente offline | Homologação de família/modelo real não registrada |
| P9 | Adapter Dahua validado offline | Homologação de família/modelo real não registrada |
| P10 | Adapter Panasonic/i-PRO validado parcialmente offline | Homologação de família/modelo real não registrada |
| P11 | Fallback ONVIF Bosch validado parcialmente offline | Homologação de família/modelo real não registrada |
| P12 | PRE-P12 em andamento (88%); regressão completa informada como 318 passed; revisão Architect com 7 CLEARED, 6 OPEN e 1 DEFERRED_BY_CONTRACT | P12_READINESS = BLOCKED por PREP12-01/02; build e homologação real não executados |

A revisão do Architect mantém PREP12-01/02 OPEN: a integração real Zeep/Requests e redirects está demonstrada em HTTP loopback, mas falta HTTPS confiável integrado ao produto. PREP12-02 também tem defeito confirmado: erro TLS no snapshot pode ser classificado como erro de rede e permitir fallback HTTP vendor configurado. PREP12-03, 06, 07, 08, 12, 13 e 14 estão CLEARED no estágio offline; PREP12-04, 05, 10 e 11 permanecem OPEN; PREP12-09 é DEFERRED_BY_CONTRACT. RTSP/PyAV continua fail-closed. Não houve build P12, câmera real, mudança de dependências ou publicação Git. O próximo gate é a correção direcionada de PREP12-02, os aceites offline restantes e nova avaliação de readiness; o detalhe e as evidências estão em PROJECT_STATE.md.

## Sequência aprovada na baseline do roadmap (entrada histórica preservada)

| Fase | Escopo e objetivo | Estado na baseline aprovada |
|---|---|---|
| P0 | Project Opening + Foundation | CLOSED; Foundation Approval `APPROVED_WITH_ACCEPTED_FINDINGS`; Project Opening Gate `PASS` (P0-A05-R1) |
| P1 | SINGLE Minimum Vertical Slice: fluxo real end-to-end para uma câmera, sob a estratégia então vigente `VENDOR_FIRST_WHEN_KNOWN` | CLOSED; P1-A04 implementada e validada sinteticamente; P1-A05 validada operacionalmente com evidência pré-auth preservada como `PARTIAL_SUCCESS`; finding ONVIF Digest aberto |
| P2 | Contrato da política híbrida e evolução da coleta SINGLE/inventário | Contrato P2-A01 `APPROVED` em 2026-10-09 (D00–D06); P2-I1 concluída offline com revisão independente V2 PASS; fase P2 permanece `IN_PROGRESS`; homologação operacional pendente; próximos trabalhos exigem authority específica |
| P3 | SINGLE Snapshot Vertical Slice: captura e processamento de snapshot; sem XLSX | Planejada |
| P4 | MULTI + XLSX Vertical Slice: entrada em lote, progresso, INVENTARIO/RESUMO e snapshot embutido | Planejada |
| P5 | MULTI Concurrency / Batch Robustness: limites, cancelamento, exportação parcial e isolamento de falhas | Planejada |
| P6 | Axis Adapter | Planejada |
| P7 | Hikvision Adapter | Planejada |
| P8 | Samsung/Hanwha Adapter | Planejada |
| P9 | Dahua Adapter | Planejada |
| P10 | Panasonic Adapter | Planejada |
| P11 | Bosch Adapter | Planejada |
| P12 | Hardening / Regression / Packaging | Planejada |

## Dependências e integração

- P1 estabeleceu a slice SINGLE integrada; P1-A04 adaptou o baseline para `VENDOR_FIRST_WHEN_KNOWN`; P1-A05 e seu DoD foram fechados com evidência READ_ONLY parcial conforme o contrato vigente.
- P2 segue a direção aprovada `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, preservando o monólito modular e a baseline P1. Seu contrato precede qualquer implementação e define política determinística por fabricante/capacidade, campos necessários, evidências já obtidas, autenticação disponível e budgets. ONVIF permanece genérico, para descoberta quando aplicável, fallback ou complemento justificado; não é obrigatório em toda consulta quando fabricante e caminho nativo válido já forem conhecidos.
- P2 planeja: (A) contrato da política híbrida; (B) preservação de evidências; (C) resolução de fabricante; (D) diagnóstico por etapa/operação; (E) seleção controlada de autenticação ONVIF; (F) proveniência e merge; (G) PoC mínima Hikvision ISAPI; (H) validação operacional futura sob autorização própria; (I) expansão incremental de inventário e rede. A PoC é escopo planejado, não autorização de implementação. O adapter Hikvision completo permanece em P7.
- P2 não permite tentativas autenticadas sequenciais contra fabricantes, reconfiguração automática de câmeras ou provisionamento obrigatório de contas ONVIF em massa. READ_ONLY, credenciais por câmera, ausência de credential spraying e ausência de senhas em saídas são obrigatórios.
- P2-A01 e sua reconciliação documental produziram [`P2_COLLECTION_STRATEGY_EXPANSION.md`](../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md) como contrato aprovado em 2026-10-09 (D01 `APPROVED_WITH_REVISION`; D02–D06 `APPROVED_WITH_ADJUSTMENTS`; D00 já aprovada). D07 permanece diferida. P0 e P1 permanecem `CLOSED`; a fase P2 não foi encerrada. A aprovação não concede implementação nem validação operacional.
- ARCH-ALIGN-01 registra a evolução documental `PREVIOUS = VENDOR_FIRST_WHEN_KNOWN` → `APPROVED_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, com `DECISION_STATUS = DIRECTION_APPROVED` e fonte [`ARCH_AUDIT_01_REPORT.md`](../../audit/ARCH_AUDIT_01_REPORT.md). A P1 permanece fechada segundo seu contrato e não é reescrita por esta direção para P2. O finding ONVIF Digest segue aberto; `ONVIF_DIGEST_ROOT_CAUSE = UNDETERMINED`.
- P3 integra snapshot ao fluxo SINGLE; não produz XLSX.
- P4 introduz MULTI e XLSX. É o primeiro ponto em que MULTI, XLSX e snapshot embedded coexistem no fluxo canônico.
- P5 robustece o lote de P4, incluindo concorrência controlada.
- P6–P11 expandem adaptadores sobre os fluxos integrados, conforme contratos e aceite de cada fase. A ordem existente Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic e Bosch é preservada; o alvo usado na evidência real não reordena o roadmap.
- P12 executa hardening, regressão e packaging operacional; build operacional exige TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER.

A sequência cumpre `INCREMENTAL_INTEGRATION_RULE`: cada slice deve integrar ao fluxo canônico e validar o fluxo acumulado antes do avanço dependente. `DEFINITION_OF_READY` e `DEFINITION_OF_DONE` são detalhadas no `EXECUTION_PLAN.md` e na autoridade PM-01. Nenhuma fase planejada concede autorização de implementação.
## Ponte de continuidade — checkpoint 2026-10-27

O próximo limite autorizado é a implementação offline dos contratos Astra P0/P1/TRANSPORT. P2/RTSP segue diferido e os 56 critérios de aceite permanecem planejados, não implementados.
