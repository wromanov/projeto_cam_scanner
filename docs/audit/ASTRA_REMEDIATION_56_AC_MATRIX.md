# CAM SCANNER — ASTRA Card B: matriz dos 56 critérios

Data: 2026-10-29
Atividades: CAM_SCANNER_ASTRA_INTEGRATION_REMEDIATION_01, CAM_SCANNER_ASTRA_FINAL_AC_CLOSURE_01, CAM_SCANNER_ASTRA_AC_CLOSURE_02, CAM_SCANNER_ASTRA_EVIDENCE_COMPLETION_03, CAM_SCANNER_ASTRA_FINAL_OFFLINE_EVIDENCE_04, CAM_SCANNER_ASTRA_FINAL_EVIDENCE_05 e CAM_SCANNER_ASTRA_TECHNICAL_CLOSURE_06
Referências contratuais: P0 Required Corrections, P1 Coverage Improvements e Centralized Transport Implementation Contract.

## CAM_SCANNER_ASTRA_TECHNICAL_CLOSURE_06 — adjudicação offline (2026-10-29)

Retomada no checkpoint `809da2046841b2f84f372602979162084656b9f8`, sem alterar HEAD. O ambiente `.venv/Scripts/python.exe` usou Python 3.14.7, pytest 9.1.1, requests 2.34.2, zeep 4.3.3 e Ruff 0.17.0; não houve instalação. Todos os endpoints de teste foram fixtures loopback sintéticas.

Evidência executada após a última alteração de teste: conjunto focal técnico/G-PN/transporte **79 passed**; `tests/test_astra_technical_closure_06.py` **10 passed**; `tests/test_astra_gpn_joint_integration.py` **31 passed**; regressão completa **587 passed, 0 failed, 0 skipped, 0 deselected** em 133.17 s. Ruff direcionado a `src tests`, Ruff global, `compileall src tests` e `git diff --check` passaram. O Ruff global imprimiu avisos de acesso negado em diretórios `.pytest-run-*` históricos; não reportou infrações. O inventário exato de não rastreados não pôde ser recontado, e os 1416 caminhos do checkpoint foram preservados sem limpeza.

| AC promovido | Evidência nominal e critério observado | Limite da conclusão | Estado |
|---|---|---|---|
| ASTRA-P0-02-AC02 | `tests/test_astra_final_evidence_05.py::test_strong_conflict_in_single_never_selects_a_vendor_or_sends_cgi` prova as duas ordens Panasonic/Axis, conflito preservado, `selected=None`, nenhum lookup de adapter nem request; registra um `VALIDATE/SKIPPED/ENDPOINT_UNSUPPORTED` sem protocolo/status. `tests/test_astra_gpn_joint_integration.py::test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities` cobre ausente, desconhecido e dois modelos legados; `tests/test_astra_technical_closure_06.py` confirma texto terminal e projeção MULTI com zero envio. | Não declara compatibilidade de modelos nem homologa câmera física. | PASS_OFFLINE |
| ASTRA-P0-02-AC06 | `tests/test_astra_final_evidence_05.py::test_panasonic_digest_fixture_validates_account_and_separates_api_outcomes` valida Digest e identidade da conta na fixture em SINGLE/MULTI: 200 com firmware 9.99 apenas observado, 200 sem firmware, 401 por credencial inválida, 403 de conta autenticada sem permissão e 404 de API ausente. Confere `[401, status]`, duas trocas físicas, tentativas lógicas, conta autenticada, identidade parcial e bloqueio posterior após recusa. | 9 variantes de fixture sintética; 9.99 permanece valor observado, sem classificação de incompatibilidade ou ACL física. | PASS_OFFLINE |
| ASTRA-P1-01-AC08 | O mesmo teste percorre SINGLE e MULTI com `ModelHint` exato, perfil Panasonic P0, CGI real via adapter, identidade da conta e resultado/diagnósticos; as variantes MULTI conferem XLSX real com 9 colunas e estados API/conta distintos. `test_multi_ineligible_models_project_skip_and_never_send` completa o ramo sem aplicabilidade. | Não afirma suporte a todos os modelos ou versões; fabricante não é inventado a partir do hint. | PASS_OFFLINE |
| ASTRA-P1-G-AC01 | `tests/test_astra_technical_closure_06.py::test_multi_complete_identity_does_not_authenticate_for_optional_fields` integra duas linhas/contas independentes no mesmo IP, `ModelHint`, perfil nomeado, Digest validado, uma tentativa lógica e duas trocas físicas por linha, 14 campos de `CameraResult`, 9 colunas de `DIAGNOSTICOS`, saída sem sentinelas e bloqueio de nova família/RTSP por D03. `tests/test_astra_p1_cross_invariant.py::test_single_real_collection_reaches_disabled_rtsp_guard_without_media_io` percorre Panasonic → coleta/ONVIF → `SnapshotService` real → guard RTSP desativado, sem lock, cliente de mídia ou PyAV. | Fixtures locais e providers HTTP de snapshot inertes; sem RTSP operacional ou alegação física. | PASS_OFFLINE |
| ASTRA-TR-AC13 | `test_multi_complete_identity_does_not_authenticate_for_optional_fields` prova uma tentativa lógica e duas trocas Digest por linha isolada mesmo sem firmware/MAC/HardwareId e sem autenticação adicional por opcionais. `test_digest_challenge_interruption_blocks_replay[cancel]` e `[deadline]` interrompem após o challenge, comprovam uma troca física e nenhuma repetição. `test_multi_cancel_after_digest_challenge_does_not_export` confirma cancelamento MULTI sem XLSX; as variantes 401 final/403 do teste Panasonic impedem auth posterior. `tests/test_collection_context.py::test_second_logical_attempt_requires_missing_identity_and_single_vendor_family` valida limite de família e necessidade de identidade essencial. | Deadline/cancelamento e recusa são variantes explícitas em fixture; nenhum dispositivo real foi consultado. | PASS_OFFLINE |

`CameraResult` permaneceu em 14 campos; `DIAGNOSTICOS` permaneceu em 9 colunas. `NO_EXPORT_INCOMPLETE_MULTI_BATCH` permanece conforme PRE-P12 §8.1. TLS segue validado em HTTPS com certificados locais e comportamento fail-closed; não houve fallback operacional. Não foram feitos acessos a câmeras, rede corporativa, auth elevada, build/deploy ou mídia P2.

AC anterior: **47 PASS_OFFLINE / 9 PARTIAL / 0 UNVERIFIED**. AC atual: **52 PASS_OFFLINE / 4 PARTIAL / 0 UNVERIFIED**. Os quatro PARTIAL restantes são gates condicionados: `ASTRA-P0-01-AC04` (autorização elevada não concedida), `ASTRA-P0-05-AC01/02` (baseline histórica não comprovável) e `ASTRA-P0-G-AC01` (revisão de segurança requer proteção técnica read-only). `SECURITY_REVIEW_STATUS=BLOCKED_RUNTIME_PROTECTION`; `SECURITY_FINDINGS=NOT_ASSESSED`; `P2_MEDIA=DEFERRED`; `FORMAL_CLOSURE_STATUS=NOT_CLOSED`.

O chat “Projeto Scanner 2.0” não foi atualizado: as ferramentas `list_threads` e `send_message_to_thread` não estavam expostas no runtime desta retomada. Esta adjudicação não depende do total agregado: cada linha acima cita teste nominal e resultado específico.

## CAM_SCANNER_ASTRA_EVIDENCE_05B_VALIDATION_CLOSURE - validacao offline (2026-10-29)

Diretamente no ROMA_CASA, HEAD f314035c4f7a8b4fdcb2122523649672b0bf12d2 e branch feature/pre-p12-unified-remediation. Ambiente correto: .venv/Scripts/python.exe, Python 3.14.7, pytest 9.1.1, requests 2.34.2, zeep 4.3.3, Ruff 0.17.0; sem instalar pacotes. O bloqueio de ambiente anterior foi superado.

Mudanca exclusiva em tests/test_astra_final_evidence_05.py: corrigidas duas capturas tardias B023 (families, sends) por argumentos default; nenhuma mudanca produtiva ou contratual.

Evidencia executada: pytest completo 575 passed, zero falhas/skips/deselected, 129.17 s, exit 0, antes da correcao B023; G-PN-JOINT 31 passed em 30.27 s, antes da correcao; focal APOS correcao 9 passed em 6.21 s e tres testes nominais de SINGLE/status/CANCELLED APOS correcao 3 passed em 1.23 s. Ruff global e focal PASS, compileall PASS, git diff --check PASS. A regressao integral NAO foi repetida depois da correcao somente em testes.

| AC promovido | Evidencia especifica | Resultado |
|---|---|---|
| ASTRA-P0-03-AC04 | Testes nominais: quatro estados no SINGLE, identidade incompleta/conflito sem SUCCESS; XLSX apenas dos tres estados completos MULTI; cancelamento encerra sem XLSX parcial (PRE-P12 8.1). | PASS_OFFLINE |
| ASTRA-P1-01-AC01 | Teste novo: SINGLE legado, hint ausente/vazio/valido/invalido, CameraTarget preservado, contextos isolados e 14 campos, sem identidade inventada. | PASS_OFFLINE |
| ASTRA-P1-02-AC04 | Quatro estados e cancelamento visiveis no dominio/UI, N/A no XLSX do lote completo e nenhum XLSX do lote cancelado (PRE-P12 8.1). | PASS_OFFLINE |

Permanecem cinco lacunas tecnicas: ASTRA-P0-02-AC02 (SKIPPED/matriz conflito e zero CGI), ASTRA-P0-02-AC06 (modelo/firmware/API/Digest por variante), ASTRA-P1-01-AC08 (matriz conjunta ModelHint/CGI/conta/saida), ASTRA-P1-G-AC01 (invariantes cruzadas em cadeia suficiente) e ASTRA-TR-AC13 (orcamentos D03 opcionais, familia, deadline/cancel/pos-recusa). Nenhuma delas e promovida por pytest agregado.

AC_INITIAL = 44 PASS_OFFLINE / 12 PARTIAL / 0 UNVERIFIED.
AC_FINAL = 47 PASS_OFFLINE / 9 PARTIAL / 0 UNVERIFIED.
Permanecem os quatro condicionados ASTRA-P0-01-AC04 (auth elevada sem autoridade), P0-05-AC01/02 (manifesto historico irrecuperavel), P0-G-AC01 (security review bloqueada por sandbox read-only). SECURITY_FINDINGS=NOT_ASSESSED. P2_MEDIA=DEFERRED; FORMAL_CLOSURE=NOT_CLOSED. Sem camera real, HTTP/RTSP operacional, auth elevada, build/deploy, commit ou push.

## CAM_SCANNER_ASTRA_FINAL_EVIDENCE_05 — diagnóstico e evidência offline (2026-10-29)

Baseline confirmada em ROMA_CASA: repositório C:\Users\walac\desenvolvimento\projeto_cam_scanner, branch feature/pre-p12-unified-remediation, HEAD f314035c4f7a8b4fdcb2122523649672b0bf12d2, upstream origin/feature/pre-p12-unified-remediation. HEAD/branch/upstream coincidem com o Card. Foram preservados os 15 arquivos rastreados já modificados e todos os não rastreados; nenhum stage, commit, push ou operação Git destrutiva ocorreu.

O estado anterior anotava 968 arquivos não rastreados; a contagem de entrada foi 1418, divergência analisada antes de escrita. Após a criação autorizada de um teste novo, a contagem por git ls-files --others --exclude-standard foi 1419: 1401 caminhos sob .pytest-run-*, cinco fontes de teste e 13 demais caminhos. A variação de listagens/histórico não foi conciliada por remoção; nenhum artefato foi descartado.

O diagnóstico dos oito ACs não confirmou defeito produtivo. Foi criado tests/test_astra_final_evidence_05.py com três testes novos, todos limitados a fixtures locais/sintéticas. O arquivo passou por ast.parse informado pelo test_engineer e compileall do ROOT. Nenhum novo teste foi executado: Python 3.15 não tem pytest, requests, openpyxl, zeep ou Ruff; o Python 3.14 disponível e o runtime bundled também não têm pytest, requests, zeep ou Ruff. A tentativa de pytest encerrou antes da coleta. Ruff não está instalado. Não houve instalação de dependências nem acesso de rede.

| AC | Categoria principal | Diagnóstico, evidência e limite | Trabalho mínimo e critério verificável | Estado |
|---|---|---|---|---|
| ASTRA-P0-02-AC02 | INTEGRATION_EVIDENCE_MISSING | Testes anteriores cobrem modelos ausentes/desconhecidos/legados; o novo teste percorre SINGLE nas duas ordens de conflito forte, observa selected=None e bloqueia envios. Não verifica marcador explícito SKIPPED nem foi executado. | Executar a matriz integrada, confirmar zero CGI e nenhuma família vendor alternativa, além da resolução conflitante preservada; adjudicar a semântica de SKIPPED contra o contrato sem inferir defeito antes do resultado. | PARTIAL |
| ASTRA-P0-02-AC06 | INTEGRATION_EVIDENCE_MISSING | Testes existentes cobrem modelo exato/inelegível, firmware ausente, 404, 401/403 e Digest; novo fixture valida hash Digest e separa respostas 200, 401, 403 e 404 em SINGLE/MULTI, com contagens. Não executado. Não há faixa de firmware incompatível documentada; firmware observado não foi classificado como incompatível. | Executar o novo teste no runtime do projeto e revisar contagens/API/conta por variante; não alegar ACL de câmera nem homologação física. | PARTIAL |
| ASTRA-P0-03-AC04 | ENVIRONMENT_BLOCKER | Testes existentes projetam os quatro estados em SINGLE e três resultados concluídos em XLSX MULTI; teste de cancelamento preserva a linha retornada, mostra aviso e não cria arquivo. Código e testes não foram executados nesta atividade. | Disponibilizar runtime local com dependências aprovadas e executar os dois nodes; confirmar identidade incompleta não vira SUCCESS e CANCELLED permanece visível sem exportar lote incompleto. | PARTIAL |
| ASTRA-P1-01-AC01 | INTEGRATION_EVIDENCE_MISSING | Novo teste compara fluxo SINGLE legado, ausência de hint, vazio, modelo documentado e inválido, target/contexto e ausência de identidade fabricada; existe teste separado do adapter Panasonic real. Teste novo não executado. | Executar os dois nodes e confirmar encaminhamento do hint válido, isolamento de contexto, CameraTarget preservado, 14 campos e nenhum hint como observação. | PARTIAL |
| ASTRA-P1-01-AC08 | INTEGRATION_EVIDENCE_MISSING | Novo fixture Panasonic verifica criptograficamente duas contas sintéticas, 200/401/403/404 e encadeia partial→403→XLSX/provedores bloqueados em MULTI; firmware é somente valor observado. Teste novo não executado e não demonstra ACL real. | Executar as variantes e consolidar por modelo/API/conta, com contagens físicas/lógicas e saídas sanitizadas. | PARTIAL |
| ASTRA-P1-02-AC04 | ENVIRONMENT_BLOCKER | O AC pede cancelamento visível; PRE-P12 §8.1 manda preservar parciais e não exportar lote incompleto. A tabela P1 menciona domínio/UI/XLSX, mas não exige literalmente uma linha CANCELLED em um XLSX de lote cancelado. ROOT adjudica que domain/UI mostram CANCELLED e o XLSX só existe para lote completo; nenhum writer será alterado para produzir arquivo parcial. Testes existentes não foram executados nesta atividade. | Executar os nodes de estado e cancelamento, comprovando status/conflicto visíveis, estados concluídos no XLSX e ausência de XLSX no cancelamento. Mudança futura para persistir CANCELLED exige decisão normativa explícita. | PARTIAL |
| ASTRA-P1-G-AC01 | INTEGRATION_EVIDENCE_MISSING | Novo cenário Panasonic encadeia plano HTTPS, adapter real, ledger, evidência/protocolo, CameraResult, workflow e XLSX; a recusa bloqueia providers de imagem com tripwire. Teste novo não executado. | Executar e conferir a cadeia completa incluindo schema 14/9 e todos os providers bloqueados; o bloqueio operacional de RTSP permanece. | PARTIAL |
| ASTRA-TR-AC13 | INTEGRATION_EVIDENCE_MISSING | Ledger e budget têm testes focais separados; o novo cenário observa trocas Digest e estados 401/403, limite de família e recusa futura. Ainda não integra identidade completa com opcionais ausentes, deadline/cancelamento e zero autenticação motivada por opcionais no mesmo percurso; teste novo não executado. | Completar/rodar matriz D03 integrada: até duas tentativas lógicas, uma família vendor, contagem física de challenge, sem auth por firmware/MAC/imagem e zero envio após recusa/deadline/cancelamento. | PARTIAL |

Decisão ROOT — cancelamento MULTI: manter NO_EXPORT_INCOMPLETE_BATCH conforme PRE-P12 §8.1. O comportamento atual é compatível; não criar planilha parcial ou linha fictícia. P1-02-AC04 não é promovido porque a execução atual está bloqueada, não porque seja obrigatório persistir CANCELLED em lote interrompido.

Resultado AC da atividade: 44 PASS_OFFLINE / 12 PARTIAL / 0 UNVERIFIED, sem promoção. Os oito ACs técnicos permanecem PARTIAL até execução e revisão focal; os quatro gates fora do escopo permanecem inalterados. Testes de referência da atividade anterior (566 total; G-PN-JOINT 31) são históricos, não resultados desta atividade.

Validação nesta atividade: TESTS_AFTER=NOT_RUN_ENVIRONMENT_BLOCKER; G_PN_JOINT=NOT_RUN; RUFF=UNAVAILABLE; COMPILEALL(src/tests)=PASS; GIT_DIFF_CHECK=PASS. SECURITY_REVIEW_STATUS=BLOCKED_RUNTIME_PROTECTION; SECURITY_FINDINGS=NOT_ASSESSED. Nenhuma câmera real, rede corporativa, HTTP/RTSP operacional, autenticação elevada, deploy, build de distribuição, commit ou push.

ACTIVITY_STATUS=PARTIAL; ACTIVITY_COMPLETE=NO; ACTIVITY_COMPLETION_PERCENT=85% (marcos de execução, separado do aceite técnico). PROJECT_STATE_UPDATE=PASS após registro deste adendo. FORMAL_CLOSURE_STATUS=NOT_CLOSED.
DELIVERY_STATUS=SENT (chat existente Projeto Scanner 2.0; confirmação da ferramenta recebida).

## CAM_SCANNER_ASTRA_FINAL_OFFLINE_EVIDENCE_04 — adjudicação (2026-10-28)

Baseline confirmada: `HEAD=f314035c4f7a8b4fdcb2122523649672b0bf12d2`, branch `feature/pre-p12-unified-remediation`, sincronizada ao remoto antes da atividade. A suíte anterior passou em 536 testes; a validação final passou em 566 testes, sem falha, skip ou deselection. G-PN-JOINT passou em 31/31. Ruff global e direcionado, `compileall` e `git diff --check` passaram. A igualdade do total de testes com a baseline não é presumida: 30 testes novos foram coletados.

Seis critérios passaram de `PARTIAL` para `PASS_OFFLINE`, somente no escopo das fixtures locais:

| AC promovido | Evidência principal | Limite |
|---|---|---|
| ASTRA-P0-01-AC05 | `tests/test_astra_final_offline_axis_boundaries.py`: body acima de 64 KiB, deadline, cancelamento e TLS inválido; fechamento de response/session, sem segundo POST nem autenticação. SINGLE integrado não cai para ONVIF em body inseguro ou deadline. | Fixture loopback sintética; sem alegação sobre câmeras físicas. |
| ASTRA-P0-02-AC03 | `test_panasonic_partial_then_onvif_refusal_or_tls_blocks_snapshot_in_same_context` — 6 variantes SINGLE/MULTI × 401/403/TLS. Identidade parcial e proveniência sobrevivem; ledger fecha ou marca TLS; snapshot e autenticação posterior bloqueados no mesmo contexto. | TLS ONVIF é injetado no transporte; não é um servidor TLS complementar inválido real. |
| ASTRA-P1-02-AC03 | O mesmo teste integrado comprova recusa final/403 bloqueando auth futura, sem recriar contexto, e falha TLS impedindo a etapa de imagem. | Escopo de adapters/fluxos e respostas sintéticas exercitados. |
| ASTRA-P1-02-AC05 | `tests/test_astra_final_offline_secrets.py`: canários em respostas hostis, logs, terminal, repr e cada byte/aba do XLSX SINGLE/MULTI; fórmulas não propagadas; exceções arbitrárias sem payload. | Apenas canários e fixtures sintéticos. |
| ASTRA-TR-AC04 | `test_single_transport_selection_and_frozen_plan_precede_first_request`: seleção, referência e aceite precedem requests; plano compilado permanece idêntico após troca de configuração. Teste de cancelamento pré-coleta complementa o fluxo positivo. | Perfil e endpoint restritos a loopback. |
| ASTRA-TR-AC11 | Canários abrangem username/password, Authorization, URL, body, nonce, fórmula e secret; oito campos sensíveis de perfil são rejeitados sem erro ecoado nem objeto de rede. | Não equivale a uma auditoria de segurança independente. |

Oito ACs técnicos permanecem `PARTIAL`: `ASTRA-P0-02-AC02` (conflito forte ainda sem matriz integrada de zero CGI/família alternativa); `ASTRA-P0-02-AC06` (falta matriz Panasonic completa de aplicabilidade/firmware e identidade Digest por variante); `ASTRA-P0-03-AC04` e `ASTRA-P1-02-AC04` (CANCELLED é mostrado no terminal e aborta MULTI sem XLSX, portanto não há projeção CANCELLED na planilha); `ASTRA-P1-01-AC01` (falta comparação completa de input legado/blank/modelo válido com mesmo target/contexto); `ASTRA-P1-01-AC08` (falta validação Digest da conta na matriz Panasonic por variante); `ASTRA-P1-G-AC01` (invariantes ainda se distribuem por vários percursos); `ASTRA-TR-AC13` (falta matriz integrada D03, limites de família e ausência de login por campo opcional).

Estado final dos 56 critérios: **44 PASS_OFFLINE / 12 PARTIAL / 0 UNVERIFIED**. Quatro PARTIAL são gates/limites que não podiam ser removidos nesta atividade: `ASTRA-P0-01-AC04` (elevação não autorizada), `ASTRA-P0-05-AC01/02` (manifesto inicial histórico não recuperável) e `ASTRA-P0-G-AC01` (revisão independente bloqueada pela falta de runtime tecnicamente read-only). Segurança permanece `BLOCKED_RUNTIME_PROTECTION`, achados `NOT_ASSESSED`; projeto sem fechamento formal. P2 mídia continua `DEFERRED`.

## Critério de classificação

`PASS` significa que a evidência local citada satisfaz o critério específico coberto. `PARTIAL` indica implementação/testes relevantes, mas falta ao menos uma variante ou integração exigida pelo contrato. `UNVERIFIED` indica que não há evidência suficiente para afirmar o critério. A suíte acumulada aprovada não substitui uma prova AC a AC.

| ID | Verificação contratual resumida | Evidência observada | Estado / lacuna restante |
|---|---|---|---|
| ASTRA-P0-01-AC01 | Viewer usa só versões + método irrestrito 1.2, nenhuma credencial/Operator | `tests/test_astra_vendor_adapters.py::test_axis_uses_only_anonymous_supported_version_12_flow`; `tests/test_astra_acl_axis_policy.py::test_axis_role_labels_do_not_select_operator_or_enable_credentials[viewer|operator|administrator]` | PASS OFFLINE — requests loopback comprovam exatamente as duas operações públicas, API 1.2, zero Authorization/cookies/credenciais e zero chamada Operator; execução focal ROOT: 4 nodes PASS. Escopo não comprova a identidade/ACL de câmera física. |
| ASTRA-P0-01-AC02 | Reutilizar versão observada; sem enumeração/auth se ausente ou inválida | `tests/test_astra_p0_axis_gap_closure.py::test_axis_unsupported_or_malformed_versions_stop_before_enumeration_or_auth` (5 variantes); `::test_axis_reuses_observed_12_without_an_extra_versions_or_operator_request` | PASS OFFLINE — versão 1.2 reutilizada; ausente, unsupported e malformada param antes de enumeração; zero auth. 6 nodes focais passaram. Fixture sintética, sem afirmação sobre câmera física. |
| ASTRA-P0-01-AC03 | Erro 2001/401/403 não vira sucesso nem replay | `tests/test_astra_p0_axis_gap_closure.py::test_axis_public_errors_never_succeed_replay_or_fallback_to_authenticated_request` (200+error 2001, 401 sem/com challenge, 403); `tests/test_astra_vendor_adapters.py::test_axis_public_401_does_not_replay_or_try_credentials` | PASS OFFLINE — cada variante retorna falha/categoria esperada, uma operação pública e zero credenciais/replay/fallback. 4 nodes focais passaram; sem extrapolação operacional. |
| ASTRA-P0-01-AC04 | Operator apenas com escopo elevado explícito; matriz Viewer/Operator/Admin | `tests/test_astra_acl_axis_policy.py::test_axis_role_labels_do_not_select_operator_or_enable_credentials[viewer|operator|administrator]`; `test_axis_credentials_never_replay_after_public_401_challenge[viewer|operator|administrator]` — PASS | PARTIAL — plano Axis continua anônimo, não envia credenciais/cookies, não inicia auth e não chama `getAllProperties`, inclusive após 401. Os rótulos usam a mesma conta sintética e não exercitam contas por papel nem um caminho `ELEVATED_AUTHORIZED`; esse caminho não está implementado. |
| ASTRA-P0-01-AC05 | TLS, deadline, cancelamento ou body inseguro interrompe plano público | `tests/test_astra_final_offline_axis_boundaries.py::test_axis_oversized_first_body_closes_resources_without_second_post`; `::test_axis_interruption_after_versions_closes_before_second_post`; `::test_axis_invalid_tls_closes_before_http_request_and_never_replays`; `::test_single_axis_failure_does_not_fall_back_to_onvif` | PASS_OFFLINE — variantes Axis fecham response/session e não enviam segundo POST nem login; body inseguro/deadline no workflow SINGLE não aciona ONVIF. Fixture loopback. |
| ASTRA-P0-01-AC06 | Plano público fixado antes de I/O; opções não habilitam credenciais/Operator | `tests/test_astra_p0_axis_gap_closure.py::test_axis_public_errors_never_succeed_replay_or_fallback_to_authenticated_request[401-with-challenge]`; `tests/test_astra_p1_transport.py::test_axis_public_profile_rejects_authenticated_http_before_session_creation` | PASS OFFLINE — alvo `admin`, profile HTTP `PUBLIC_NONE` compilado antes do adapter e challenge 401 não alteram o plano nem iniciam auth/Operator. Cenário local sintético; não cria fluxo elevado. |
| ASTRA-P0-02-AC01 | Panasonic produz evidência parcial válida sem inventar fabricante | `tests/test_astra_gpn_joint_integration.py::test_exact_model_single_workflow_uses_real_default_panasonic_adapter` — PASS no pytest integral | PASS — workflows, contexto, plano HTTPS e adaptador Panasonic reais preservam modelo/serial/firmware observados sem inventar fabricante; fixture offline, sem homologação. |
| ASTRA-P0-02-AC02 | Modelo desconhecido/legado ou conflito não chama CGI | `tests/test_astra_gpn_joint_integration.py::test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities` — 4 variantes PASS; estratégia corrigida para pular discovery antes de I/O | PARTIAL — ausência/desconhecido/legados parametrizados passam sem I/O; conflito forte e demais variantes legadas ainda sem matriz integrada. |
| ASTRA-P0-02-AC03 | Parcial sobrevive a 403/401 final/TLS no complemento; sem auth posterior | `tests/test_astra_final_offline_integration.py::test_panasonic_partial_then_onvif_refusal_or_tls_blocks_snapshot_in_same_context` (SINGLE/MULTI × 401/403/TLS, 6 variantes) | PASS_OFFLINE — mantém identidade/proveniência parcial no mesmo contexto, fecha ledger ou TLS e bloqueia snapshot/auth posteriores; requests finais e contagens físicas verificadas. TLS sintético. |
| ASTRA-P0-02-AC04 | 404/resposta inválida não fabrica identidade | test_cgi_http_statuses_are_reported_without_fallback; test_invalid_panasonic_payload_never_fabricates_identity (4 variantes) — PASS | PASS_OFFLINE — 404/401/403 e payloads vazio, XML/texto inválidos e nomes semelhantes não produzem identidade nem evidência inventada; sentinelas ausentes. Fixture HTTPS local. |
| ASTRA-P0-02-AC05 | P0 isolado pode ignorar fonte sem perfil e não declara suporte operacional | `test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities[None]` — PASS, zero requests | PASS — sem perfil exato a fonte e discovery são pulados antes de I/O; evidência apenas offline, sem alegação operacional. |
| ASTRA-P0-02-AC06 | P0+P1 separa suporte/API/permissão nas variantes Panasonic contratadas | `test_exact_model_single_workflow_uses_real_default_panasonic_adapter`; `test_unknown_firmware_remains_unknown_in_exact_model_response`; `test_cgi_http_statuses_are_reported_without_fallback` — PASS | PARTIAL — cobre modelo exato, firmware ausente e 404/401/403 integrados; faltam matriz completa de versões/aplicabilidade e contagens por variante. |
| ASTRA-P0-03-AC01 | ACL Viewer/Operator/Admin diferencia operações e verifica conta | `tests/test_astra_acl_operation_matrix.py::test_digest_acl_fixture_authenticates_accounts_for_real_hikvision_operation` — PASS | PASS OFFLINE — no `GET /ISAPI/System/deviceInfo`, o servidor local verifica Digest e identidade efetiva: Viewer=403, Operator=200, Administrator=200; senha incorreta da conta conhecida=401 final. AuthLedger registra 1 tentativa lógica/2 trocas físicas. Escopo comprovado é esta operação em fixture sintética; não comprova ACL de câmera física nem outras operações. |
| ASTRA-P0-03-AC02 | Digest físico contabilizado; 401 final/403 fecha escopo | tests/test_astra_evidence_completion_03.py::test_auth_challenge_matrix_counts_exchanges_and_blocks_later_families (Basic-only, SHA-256, Digest final 401, Digest 403); Digest challenge 200 and WSSE tests - PASS | PASS_OFFLINE - em um CollectionContext do HikvisionAdapter, quatro challenges/status terminam no AuthLedger esperado; 401/403 bloqueiam novas familias ONVIF e Panasonic, sem troca/replay nao suportado. Fixture loopback. |
| ASTRA-P0-03-AC03 | SINGLE/MULTI compartilham regra e isolam credenciais/sessões inclusive IP duplicado | test_multi_real_excel_path_isolates_credentials_for_same_ip_and_sanitizes_output; test_model_hint_mismatch_preserves_observed_identity_without_new_requests_or_auth - PASS | PASS_OFFLINE - duas contas Digest concorrentes no mesmo IP retornam os seriais corretos em dois CollectionContexts/AuthLedgers distintos; a comparacao SINGLE/MULTI de hint correspondente e divergente conserva requests e contadores. Offline. |
| ASTRA-P0-03-AC04 | 200 incompleto e hint/porta nao fecham identidade; quatro estados contratuais | tests/test_astra_final_offline_integration.py::test_single_four_and_multi_three_statuses_conflicts_and_missing_identity; ::test_multi_cancelled_row_returns_without_spin_or_export, ambos reexecutados na 05B | PASS_OFFLINE - quatro estados SINGLE; XLSX MULTI com tres estados concluidos; CANCELLED em dominio/UI e sem XLSX do lote incompleto (PRE-P12 8.1). |
| ASTRA-P0-04-AC01 | HTTP autorizado permanece HTTP em tentativas, evidência, UI e XLSX | test_multi_profile_applies_only_to_loopback_member_and_other_target_stays_https | PASS_OFFLINE — fluxo MULTI real usa HTTP apenas no membro exato do profile loopback e mantém o outro alvo em HTTPS; tentativas, evidências, TerminalUI e aba DIAGNOSTICOS registram scheme/policy/ref efetivos; schema de 14 campos e nove colunas preservado. |
| ASTRA-P0-04-AC02 | HTTPS confiável preservado; TLS inválido encerra sem downgrade | `tests/test_pre_p12_transport_integration.py`, `tests/test_target_transport.py` e suíte local com certificados sintéticos | PASS — cenários de TLS e ausência de downgrade exercitados no transporte real de fixture. |
| ASTRA-P0-04-AC03 | HTTP implícito, redirects, destinos externos, proxy/netrc negados | `tests/test_astra_p1_transport.py` perfil exato; `tests/test_pre_p12_transport_integration.py` redirects/destinos/proxies | PASS — testes locais de allowlist, destino e isolamento de ambiente passaram. |
| ASTRA-P0-05-AC01 | Confirmar baseline local+delta e parar ante divergência | Raiz, branch e HEAD confirmados; baseline usada para este trabalho | PARTIAL — não foi arquivado manifesto completo de hashes do delta preexistente e teste deliberado de divergência antes de editar. |
| ASTRA-P0-05-AC02 | Preservar dirty state e integrar no fluxo real sem publicar | HEAD/branch permaneceram; sem staging/commit/push; regressão integral no worktree | PARTIAL — preservação Git verificada; não há inventário/hash completo pré/pós de cada arquivo preexistente. |
| ASTRA-P0-G-AC01 | AC locais + regressão, segurança e 14 campos | Regressão atual: pytest 510 passed; Ruff direcionado, compileall e git diff --check PASS | PARTIAL — revisão independente bloqueada por ausência de sandbox read-only técnico; ruff check src tests mantém I001 preexistente em tests/test_logging_setup.py, não editado. |
| ASTRA-P1-01-AC01 | SINGLE legado/blank compativel e modelo valido encaminhado sem alterar target | tests/test_astra_final_evidence_05.py::test_single_legacy_blank_valid_and_invalid_model_inputs_preserve_target, reexecutado nominalmente na 05B | PASS_OFFLINE - legado/ausente/vazio/valido/invalido, contexto por execucao e CameraTarget preservado, 14 campos e sem identidade inventada. |
| ASTRA-P1-01-AC02 | Coluna MODELO opcional/case-insensitive; duplicata falha antes de rede | `test_excel_model_column_is_optional_case_insensitive_and_position_independent`; `test_excel_duplicate_model_header_fails_before_rows_are_iterated` | PASS — asserções diretas do leitor cobrem ausência/posição/duplicata e execução não avalia fórmula. |
| ASTRA-P1-01-AC03 | NFC/espaços/256; controles, URL e segredo recusados sem eco | Testes parametrizados `test_model_hint_*` em `tests/test_astra_p1_transport.py` | PASS — normalização, limites e entradas hostis cobertos. |
| ASTRA-P1-01-AC04 | Hint não preenche modelo/coverage nem roteia vendor por prefixo | `test_model_hint_is_not_a_vendor_routing_signal`; teste de metadata allowlisted | PASS — declaração não é fonte observada nem sinal suficiente de vendor. |
| ASTRA-P1-01-AC05 | Mismatch preserva observado e não aumenta requests/auth em duas ordens/SINGLE/MULTI | test_model_hint_mismatch_preserves_observed_identity_without_new_requests_or_auth; test_model_hint_mismatch_preserves_observed_evidence_in_both_merge_orders - PASS | PASS_OFFLINE - observado WV-S2531M prevalece sobre hint WV-S2531L em SINGLE e MULTI; a sequencia de requests e os contadores AuthLedger igualam os casos correspondentes; merge nas duas ordens preserva hint e evidencia observada. |
| ASTRA-P1-01-AC06 | Modelo Panasonic exato chega ao adapter; ausente/desconhecido/legado não força CGI | `test_exact_model_single_workflow_uses_real_default_panasonic_adapter`; `test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities` (4 variantes) — PASS | PASS — workflow chega ao adaptador produtivo para perfil exato e bloqueia modelos inelegíveis antes de qualquer I/O; evidência offline. |
| ASTRA-P1-01-AC07 | Planilhas antigas/extras e hint invalido mantem linhas validas | test_multi_legacy_workbook_exports_mixed_rows_and_rejects_formula_model_hint; test_excel_formula_cell_is_never_evaluated_as_model_hint; test_excel_formula_with_cached_text_is_invalid_model_hint | PASS_OFFLINE - fluxo MULTI le workbook legado com coluna extra, rejeita formula MODELO mesmo com texto em cache, preserva linha valida ao lado de linha invalida e exporta 3 linhas na ordem; sem request Panasonic para a formula. Loopback. |
| ASTRA-P1-01-AC08 | Entrada SINGLE/MULTI→ModelHint→Panasonic P0→merge/saída nas variantes conjuntas | G-PN-JOINT 31/31 e `tests/test_astra_final_offline_integration.py::test_panasonic_partial_then_onvif_refusal_or_tls_blocks_snapshot_in_same_context` | PARTIAL — fluxo integrado e recusa posterior comprovados; falta validar Digest/identidade da conta em cada variante da matriz Panasonic de suporte, firmware e disponibilidade. |
| ASTRA-P1-02-AC01 | Diagnóstico distingue ausência, 401, 403, 404, rede, TLS e SOAP | test_single_workflow_diagnostic_scenario_matrix_is_stage_specific_and_sanitized (7 cenarios: campo ausente, 401, 403, 404, timeout, TLS e SOAP) - PASS | PASS_OFFLINE - a tabela confirma etapas e categorias distintas (PARSE, AUTH, HTTP, CONNECT e SOAP) e varre report/UI contra sentinelas de credencial; o 403 SOAP e classificado SOAP_FAULT pelo adapter. |
| ASTRA-P1-02-AC02 | Evidências úteis anteriores sobrevivem a negação e timeout posteriores | test_panasonic_partial_evidence_survives_later_onvif_denial_or_timeout (403 SOAP e timeout) - PASS | PASS_OFFLINE - workflow real preserva modelo, serial, firmware, fonte VENDOR, HTTPS e operacao Panasonic apos falha SOAP 403 ou timeout subsequente; o resultado permanece PARTIAL_SUCCESS. |
| ASTRA-P1-02-AC03 | Recusa final fecha auth futura inclusive imagem | `tests/test_astra_final_offline_integration.py::test_panasonic_partial_then_onvif_refusal_or_tls_blocks_snapshot_in_same_context` (6 variantes) | PASS_OFFLINE — recusa final/403 fecha o AuthLedger no contexto original e impede auth posterior; snapshot falha fechado; TLS impede sua chamada. |
| ASTRA-P1-02-AC04 | Hint/discovery nao completam identidade; conflito/cancelamento visivel | tests/test_astra_final_offline_integration.py::test_single_four_and_multi_three_statuses_conflicts_and_missing_identity; ::test_multi_cancelled_row_returns_without_spin_or_export, ambos reexecutados na 05B | PASS_OFFLINE - quatro estados dominio/UI, N/A na planilha de lote completo e nenhuma exportacao de lote cancelado conforme PRE-P12 8.1. |
| ASTRA-P1-02-AC05 | SINGLE/MULTI sanitizam saída, sem URLs/segredos/fórmulas em XLSX/diagnósticos | `tests/test_astra_final_offline_secrets.py::test_single_multi_hostile_response_never_reaches_outputs`; `::test_unexpected_collector_error_keeps_raw_payload_out_of_log_and_outputs`; `::test_profile_rejects_secret_fields_without_leaking_error_or_starting_network` | PASS_OFFLINE — canários verificados em logs, UI, repr, bytes/células de todas as abas XLSX; fórmulas e payloads arbitrários não chegam às saídas. |
| ASTRA-P1-03-AC01 | HardwareId ONVIF validado preservado; inválido/ausente não inventado | test_onvif_hardware_id_is_preserved_only_when_valid (válido, ausente, tipo inválido) | PASS_OFFLINE — o coletor produtivo chama GetDeviceInformation uma vez por variante; preserva HardwareId string válida e deixa ausência/tipo inválido como None, sem perder modelo/serial observados. |
| ASTRA-P1-03-AC02 | HardwareId Axis só da operação já selecionada, sem request opcional | test_axis_hardware_id_comes_only_from_the_selected_public_response (válido/None) | PASS_OFFLINE — somente a resposta pública selecionada fornece HardwareID; cada variante faz exatamente duas operações públicas previstas, sem auth ou request opcional. |
| ASTRA-P1-03-AC03 | MAC Panasonic válido normaliza; ausente/inválido fica None/N/A | `tests/test_astra_p1_mapping_gap_closure.py::test_panasonic_mac_variants_preserve_partial_identity` (6 variantes) | PASS OFFLINE — compacto, `:` e `-` normalizam; ausente/misto/inválido ficam None e preservam modelo, serial e firmware. 6 nodes focais passaram. |
| ASTRA-P1-03-AC04 | deviceName/hardwareVersion/chaves desconhecidas não viram hostname/HardwareId | Nodes negativos de ONVIF, Axis, Panasonic e Dahua em test_astra_p1_mapping_gap_closure.py | PASS_OFFLINE — as quatro famílias exercitadas não promovem campos desconhecidos à identidade; schema não foi ampliado. Limite: fontes/parser cobertos por esses nodes. |
| ASTRA-P1-03-AC05 | Vazio/conflito/segredo não apaga evidência anterior em ambas as ordens | `tests/test_astra_acl_merge_acceptance.py::test_partial_conflicting_and_empty_evidence_merge_is_monotonic_in_both_orders` — PASS | PASS — preserva HardwareId/MAC conflitantes, remove canários de credencial e retorna proveniência determinística nas duas ordens. |
| ASTRA-P1-G-AC01 | Regressão P1 preserva transporte/ledger/RTSP e 14 campos | Regressão atual 566/0/0/0; G-PN-JOINT 31/31; teste de cancelamento integrado e teste de transporte congelado | PARTIAL — profile/proveniência, mappings, ledger, TLS, RTSP e saída ainda não estão vinculados em um único percurso; revisão de segurança também bloqueada. |
| ASTRA-TR-AC01 | HTTPS verificado por default; HTTP só com regra explícita | Testes de schema/profile, verify TLS e transporte local | PASS — default e seleção segura exercitados; HTTP implícito negado. |
| ASTRA-TR-AC02 | Regra limita-se a grupo/interseção; demais targets seguem HTTPS | test_multi_profile_applies_only_to_loopback_member_and_other_target_stays_https | PASS_OFFLINE — InventoryService, collector, adapter Axis e workflow MULTI produtivos usam o profile somente em 127.0.0.2; 127.0.0.1 segue HTTPS; duas operações públicas HTTP observadas, sem enumeração. |
| ASTRA-TR-AC03 | Rejeitar CIDR/wildcard/DNS/range/campos extras/duplicatas/conflitos antes da rede | tests/test_astra_acl_axis_policy.py::test_invalid_transport_profile_schema_fails_before_transport_construction (8 classes); test_secret_bearing_transport_profile_is_rejected_with_sanitized_error - PASS | PASS_OFFLINE - CIDR, wildcard, DNS, range, host alternativo, chave extra, ID duplicado e conflito sao rejeitados antes de criar Session/TargetTransportPolicy; campo password e erro sanitizado. Sem request. |
| ASTRA-TR-AC04 | Seleção/aceite precedem rede; plano congelado apesar de config mutada | `tests/test_astra_final_offline_integration.py::test_single_transport_selection_and_frozen_plan_precede_first_request`; `tests/test_astra_transport_selection_workflows.py::test_single_transport_cancellation_precedes_collection_after_model_preflight` | PASS_OFFLINE — seleção e aceite/ref precedem o primeiro POST; o plano compilado sobrevive à mutação posterior de settings. Cancelamento no pré-voo continua sem coleta. Loopback. |
| ASTRA-TR-AC05 | TLS_ERROR encerra todas as operações, mesmo com regra HTTP anterior | Matriz de TLS/redirect e teste de não downgrade em workflows | PASS — cenários SINGLE/MULTI e snapshot/preauth exercitados em HTTPS local. |
| ASTRA-TR-AC06 | Digest challenge→200 é uma tentativa lógica; trocas físicas contabilizadas | `test_digest_challenge_then_200_records_both_exchanges_and_effective_https`; `test_wsse_auth_evidence_requires_valid_username_token_bound_to_row_credentials` — PASS | PASS — dois envios físicos, uma operação lógica e token WSSE validado contra credenciais da linha; não equivale a ACL real. |
| ASTRA-TR-AC07 | 401 final/403/erro fecha auth; Basic/SHA-256 não causa troca/replay | tests/test_astra_evidence_completion_03.py::test_auth_challenge_matrix_counts_exchanges_and_blocks_later_families (4 variantes) - PASS | PASS_OFFLINE - Basic-only e Digest SHA-256 nao repetem; Digest final 401 e 403 contam as duas trocas fisicas, mantem estado terminal e bloqueiam AuthLedger futuro. |
| ASTRA-TR-AC08 | Perfil não implica privilégio: Viewer nega Operator; Axis público permanece sem credenciais mesmo com HTTP selecionado | `tests/test_astra_acl_operation_matrix.py::test_digest_acl_fixture_authenticates_accounts_for_real_hikvision_operation`; `tests/test_astra_acl_axis_policy.py::test_axis_role_labels_do_not_select_operator_or_enable_credentials[viewer|operator|administrator]` | PASS OFFLINE — Digest sintético valida Viewer=403 e Operator/Admin=200 para `GET /ISAPI/System/deviceInfo`; Axis seleciona HTTP exato e permanece anônimo sem chamar operação Operator. Execução focal ROOT: 5 nodes PASS incluindo esses casos. Não extrapolar para outra operação ou câmera física. |
| ASTRA-TR-AC09 | Sessões/credenciais/estado isolados entre linhas/targets, inclusive IP repetido | test_multi_real_excel_path_isolates_credentials_for_same_ip_and_sanitizes_output | PASS_OFFLINE — duas sessões Digest concorrentes para o mesmo IP usam usuários distintos; serial de cada resposta confirma associação à linha de entrada e não há canários de credencial nas saídas. Fixture local. |
| ASTRA-TR-AC10 | Diagnóstico scheme/policy seguro; schema de 14 campos/nove colunas mantido | Testes MULTI de profile HTTP e isolamento Digest no mesmo IP | PASS_OFFLINE — TerminalUI e XLSX distinguem HTTP autorizado de HTTPS default; policy/ref/auth são reportados de forma sanitizada, CameraResult mantém 14 campos e DIAGNOSTICOS nove colunas; canários ausentes. |
| ASTRA-TR-AC11 | Sem segredo/URL/header/body/nonce/fórmula nas saídas; perfil com segredo recusado | `tests/test_astra_final_offline_secrets.py::test_single_multi_hostile_response_never_reaches_outputs`; `::test_unexpected_collector_error_keeps_raw_payload_out_of_log_and_outputs`; `::test_profile_rejects_secret_fields_without_leaking_error_or_starting_network` | PASS_OFFLINE — todos os canários sintéticos ficam fora de logs, exceções, repr, terminal e XLSX; oito campos sensíveis de perfil são recusados antes de iniciar rede. |
| ASTRA-TR-AC12 | Native-first/Panasonic não faz preauth indevida; inelegível não faz I/O | `tests/test_astra_gpn_joint_integration.py::test_exact_model_single_workflow_uses_real_default_panasonic_adapter`; `::test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities` (4 variantes) — PASS | PASS OFFLINE — caminho produtivo integrado usa Panasonic elegível sem preauth; variantes inelegíveis não emitem requests. Fixture loopback; sem homologação física. |
| ASTRA-TR-AC13 | Secundária apenas se essencial faltar/sem recusa; limite e deadline; sem descoberta opcional | Testes de deadline/cancelamento e políticas existentes | PARTIAL — falta matriz integrada de D03, limite de famílias e ausência de login por campo opcional. |
| ASTRA-TR-AC14 | Regra legada preservada, HTTP por `LEGACY_EXACT`, precedência sem ordem implícita | `test_transport_accepts_only_exact_legacy_http_rule`; compilação e seleção | PASS — regras exatas e negação de HTTP não autorizado exercitadas. |
| ASTRA-TR-AC15 | Regressão acumulada offline; mídia continua bloqueada | Regressão atual 510/0/0/0; testes RTSP fail-closed existentes; P2 permanece DEFERRED | PASS OFFLINE — suíte completa atual passou sem câmera; nenhuma ativação operacional de RTSP. I001 global está registrado separadamente, fora dos arquivos alterados. |

## Contagem e gates

| Grupo | PASS | PARTIAL | UNVERIFIED | Total |
|---|---:|---:|---:|---:|
| P0 | 15 | 7 | 0 | 22 |
| P1 | 15 | 4 | 0 | 19 |
| TRANSPORT | 14 | 1 | 0 | 15 |
| **Total** | **44** | **12** | **0** | **56** |

`G-PN-JOINT=PASS (OFFLINE)`: 31/31 casos passaram em fixtures locais. O percurso usa workflows, InventoryService, VendorFirstCollector, registry/adaptador Panasonic e transport produtivos; MULTI usa leitor/escritor XLSX reais. Não representa homologação física. `56/56 PASS=NO`.

`SECURITY_REVIEW=BLOCKED_RUNTIME_PROTECTION`: metadata efetivo do agente reviewer informa `sandbox_mode=workspace-write` com escrita no repositório. A revisão independente não foi iniciada; ausência de findings não significa aprovação.

`REGRESSION` anterior a esta atividade: 536 passed, 0 failed, 0 skipped, 0 deselected. Regressão final atual: 566 passed, 0 failed, 0 skipped, 0 deselected. O histórico e as evidências AC a AC de CAM_SCANNER_ASTRA_FINAL_OFFLINE_EVIDENCE_04 estão registrados no adendo acima e em PROJECT_STATE.md.

## CAM_SCANNER_ASTRA_ACL_SECURITY_CLOSURE_01 — reconciliação focal (2026-10-28)

| ID | Alteração de estado | Evidência e limite |
|---|---|---|
| ASTRA-P0-01-AC04 | UNVERIFIED → PARTIAL | Axis real permanece PUBLIC_NONE: chamadas produtivas de versões/propriedades são anônimas; 401 não gera replay e não chama `getAllProperties`. Os rótulos Viewer/Operator/Admin do teste não são contas distintas; o caminho elevado explícito continua ausente. |
| ASTRA-P0-03-AC01 | UNVERIFIED → PASS OFFLINE | Fixture Digest local usa adapter Hikvision/transport produtivos e três contas sintéticas; servidor valida resposta Digest, usuário e resultado por papel para `GET /ISAPI/System/deviceInfo`. 1 logical auth/2 exchanges; senha incorreta termina 401. Sem extrapolação a hardware ou operações não exercitadas. |
| ASTRA-TR-AC12 | PARTIAL → PASS OFFLINE | Teste integrado Panasonic comprova sequência sem preauth no modelo elegível e zero I/O nas quatro variantes inelegíveis. |
| ASTRA-TR-AC15 | PARTIAL → PASS OFFLINE | Pytest integral novo 479/0/0/0; bloqueio RTSP demonstrado por testes fail-closed e decisão P2 DEFERRED. |
| ASTRA-P1-G-AC01 | PARTIAL mantido | G-PN e schema 14 campos passaram; falta vinculação isolada de mappings/hints a todas as invariantes de transporte, ledger e RTSP. |

Os sete casos focais ACL passaram após repetição com loopback local habilitado; junto com os 15 testes G-PN-JOINT totalizam 22 casos focais aprovados. A regressão integral final foi executada depois do ajuste de anotação de tipo do fixture. Nenhuma fixture acessou endpoint externo ou câmera.

`SECURITY_SANDBOX_VERIFIED=NO`; `SECURITY_REVIEW=BLOCKED_RUNTIME_PROTECTION`. O runtime disponível não fornece sandbox read-only efetivo ao `security_reviewer` (`workspace-write`); o scan padrão iniciado permaneceu somente em preflight e não emitiu findings. Portanto `SECURITY_FINDINGS_REMAINING=NOT_ASSESSED`, não zero. `ruff check .` continua com 1 I001 em `tests/test_logging_setup.py`, preexistente e fora do ownership desta atividade.

Estado de entrada desta atividade: P0 5 PASS / 17 PARTIAL / 0 UNVERIFIED; P1 5 / 14 / 0; TRANSPORT 6 / 9 / 0; total 16 PASS / 40 PARTIAL / 0 UNVERIFIED. Após vincular e reexecutar os nodes específicos, P0-01-AC01 e ASTRA-TR-AC08 foram promovidos a PASS OFFLINE; estado ROOT atual: P0 6/16/0; P1 5/14/0; TRANSPORT 7/8/0; total 18 PASS / 38 PARTIAL / 0 UNVERIFIED. Veja a classificação individual e o cruzamento P1-G abaixo.

## CAM_SCANNER_ASTRA_EVIDENCE_SECURITY_GATE_01 — classificação individual e fechamento (2026-10-28)

O requisito literal de cada ID está reproduzido abaixo a partir da tabela de aceitação do contrato canônico. Para implementação, node IDs, resultado registrado e evidência sanitizada, consulte a linha do mesmo ID na matriz principal acima; esta tabela complementa essa linha com a categoria de lacuna, ação mínima e estado reconciliado. A suíte `479/0/0/0` era histórica; o novo resultado será registrado após a regressão consolidada desta atividade. Nenhuma lacuna foi classificada como necessidade de homologação operacional porque o escopo e os ACs aqui avaliados são offline.

| ID | Requisito canônico | Categoria | Lacuna concreta e próxima ação mínima | Estado |
|---|---|---|---|---|
| ASTRA-P0-01-AC01 | Viewer usa só versões + método irrestrito 1.2, nenhuma credencial/Operator | EVIDENCE_ALREADY_EXISTS | Nodes de API 1.2 e fluxo Axis público cobrem as duas operações, sem credenciais nem chamada Operator; referência reexecutada e vinculada à linha principal. Não extrapolar a ACL física. | PASS_OFFLINE |
| ASTRA-P0-01-AC02 | Versão já obtida reutilizada; ausente/unsupported/malformed não enumera nem autentica | TEST_COVERAGE_MISSING | O conjunto negativo/positivo novo tem contagens por variante, API 1.2 reutilizada e zero auth. 6 nodes focais passaram; a lacuna de teste foi fechada em escopo offline. | PASS_OFFLINE |
| ASTRA-P0-01-AC03 | 200+error 2001, 401 público com/sem challenge e 403 não viram sucesso nem replay com senha | TEST_COVERAGE_MISSING | Matriz nova cobre 200/2001, 401 sem/com challenge e 403 com uma única operação e zero auth/replay. 4 nodes focais passaram. | PASS_OFFLINE |
| ASTRA-P0-01-AC04 | Operator retido só para escopo elevado explícito antes de I/O; username não o ativa | IMPLEMENTATION_DEFECT | Plano `ELEVATED_AUTHORIZED` não está implementado/exercitável. Qualquer implementação depende de autorização normativa/técnica específica e teste bounded; não habilitar elevação nesta atividade. | PARTIAL |
| ASTRA-P0-01-AC05 | TLS inválido, deadline/cancel ou body inseguro encerra plano público | INTEGRATION_EVIDENCE_MISSING | Falhas genéricas existem, mas falta provar no adapter Axis que cada variante impede o segundo POST/auth e fecha recursos. Integrar essas variantes ao plano Axis. | PARTIAL |
| ASTRA-P0-01-AC06 | Perfil público é fixado antes de I/O; configuração HTTP/Digest, username admin e challenge não ativam auth Axis ou Operator | TEST_COVERAGE_MISSING | Node novo fixa o profile `PUBLIC_NONE` antes do adapter, usa username `admin` e challenge 401; plano permanece imutável, sem auth/Operator. Focal passou. | PASS_OFFLINE |
| ASTRA-P0-02-AC02 | Aplicabilidade desconhecida/legado não chama CGI; conflito forte não seleciona vendor | INTEGRATION_EVIDENCE_MISSING | Modelos inelegíveis e conflito de sinais passam em testes distintos; integrar o conflito ao workflow e provar zero CGI e zero família alternativa. | PARTIAL |
| ASTRA-P0-02-AC03 | Parcial sobrevive a 403/401 final/TLS no complemento; nenhum login posterior | INTEGRATION_EVIDENCE_MISSING | Merge monotônico e status/TLS estão cobertos separadamente; integrar evidência válida anterior → recusa/TLS, preservação de proveniência e zero auth posterior no mesmo contexto. | PARTIAL |
| ASTRA-P0-02-AC04 | 404, vazio, XML/texto inválido e nomes semelhantes não fabricam identidade | TEST_COVERAGE_MISSING | 404, hint e HTML malformado têm nodes; completar vazio/XML/texto inválido/nomes semelhantes e comprovar não-overwrite/categoria. | PARTIAL |
| ASTRA-P0-02-AC06 | P0+P1 separa suporte, API e permissão para modelo exato, desconhecido, firmware incerto, 404, 401 final e 403 | INTEGRATION_EVIDENCE_MISSING | Nodes integrados cobrem modelo, firmware ausente e status HTTP, mas não a matriz completa de versão/aplicabilidade e identidade de conta por variante; consolidar contagens sem alegar homologação física. | PARTIAL |
| ASTRA-P0-03-AC02 | Challenge Digest conta fisicamente; 401 final/403 fecha scope | INTEGRATION_EVIDENCE_MISSING | tests/test_astra_evidence_completion_03.py::test_auth_challenge_matrix_counts_exchanges_and_blocks_later_families (Basic-only, SHA-256, Digest final 401, Digest 403); Digest challenge 200 and WSSE tests - PASS | PASS_OFFLINE |
| ASTRA-P0-03-AC03 | SINGLE e MULTI usam as mesmas regras; IPs/linhas não compartilham sessão/credencial | INTEGRATION_EVIDENCE_MISSING | test_multi_real_excel_path_isolates_credentials_for_same_ip_and_sanitizes_output; test_model_hint_mismatch_preserves_observed_identity_without_new_requests_or_auth - PASS | PASS_OFFLINE |
| ASTRA-P0-03-AC04 | 200 incompleto ≠ completo; hint/porta acessível não fecha identidade | INTEGRATION_EVIDENCE_MISSING | Hint, schema e projeções estão cobertos em partes; integrar SUCCESS/PARTIAL_SUCCESS/FAILED/CANCELLED com valores ausentes e saída final. | PARTIAL |
| ASTRA-P0-04-AC01 | HTTP autorizado é HTTP em tentativas/evidência/UI/XLSX | INTEGRATION_EVIDENCE_MISSING | Proveniência e XLSX têm testes separados; falta percurso local HTTP escolhido até tentativas, UI e bytes XLSX/diagnóstico. | PARTIAL |
| ASTRA-P0-05-AC01 | Executor comprova R2 local+delta e baseline divergente para antes de editar | PREEXISTING_BASELINE_UNPROVABLE | Não havia manifesto/hash prévio do dirty state; não é possível reconstruí-lo retroativamente. Manter PARTIAL e exigir inventário prévio em atividade futura equivalente. | PARTIAL |
| ASTRA-P0-05-AC02 | Sem perda de alterações preexistentes ou publicação; integração no fluxo real offline | PREEXISTING_BASELINE_UNPROVABLE | HEAD/branch e ausência de Git consequencial estão registrados, mas não há hashes/manifesto inicial por arquivo. Preservar o dirty state e a limitação histórica. | PARTIAL |
| ASTRA-P0-G-AC01 | ACs locais e regressão acumulada passam; 14 campos e segurança preservados | OTHER_WITH_JUSTIFICATION | A nova regressão local pode comprovar testes, mas o parecer independente de segurança exige sandbox read-only efetivo, indisponível no runtime atual. Obter revisão em sessão tecnicamente read-only e então reavaliar. | PARTIAL |
| ASTRA-P1-01-AC01 | SINGLE antigo, blank e fabricante opcional mantêm fluxo; modelo válido é encaminhado sem alterar CameraTarget | INTEGRATION_EVIDENCE_MISSING | Há nodes de fluxo/hint, mas falta comparar target e contexto idênticos para input antigo, blank e modelo válido dentro do workflow SINGLE. | PARTIAL |
| ASTRA-P1-01-AC05 | Mismatch declarado/observado conserva observado e não aumenta requests/auth | TEST_COVERAGE_MISSING | test_model_hint_mismatch_preserves_observed_identity_without_new_requests_or_auth; test_model_hint_mismatch_preserves_observed_evidence_in_both_merge_orders - PASS | PASS_OFFLINE |
| ASTRA-P1-01-AC07 | Planilhas anteriores com extras e MODELO invalido mantem linhas validas | INTEGRATION_EVIDENCE_MISSING | test_multi_legacy_workbook_exports_mixed_rows_and_rejects_formula_model_hint e testes focais de formula; reader/writer e saida XLSX real validados | PASS_OFFLINE |
| ASTRA-P1-01-AC08 | Entrada SINGLE/MULTI → ModelHint → perfil P0 → CGI → merge/saída distingue suporte, disponibilidade e conta nas variantes conjuntas | INTEGRATION_EVIDENCE_MISSING | G-PN exercita fluxos reais e XLSX, mas o fixture Panasonic não autentica/valida a identidade da conta para cada variante; fechar a matriz integrada de suporte/API/conta. | PARTIAL |
| ASTRA-P1-02-AC01 | Campo ausente, 401 challenge/final, 403, 404, rede, TLS e SOAP têm diagnóstico distinto | TEST_COVERAGE_MISSING | test_single_workflow_diagnostic_scenario_matrix_is_stage_specific_and_sanitized (7 cenarios: campo ausente, 401, 403, 404, timeout, TLS e SOAP) - PASS | PASS_OFFLINE |
| ASTRA-P1-02-AC02 | Evidências úteis sobrevivem a negação e timeout posteriores | INTEGRATION_EVIDENCE_MISSING | test_panasonic_partial_evidence_survives_later_onvif_denial_or_timeout (403 SOAP e timeout) - PASS | PASS_OFFLINE |
| ASTRA-P1-02-AC03 | Recusa final fecha todas as autenticações futuras, inclusive imagem | INTEGRATION_EVIDENCE_MISSING | Panasonic/ONVIF e bloqueio de snapshot são provados em casos diferentes; integrar recusa, ledger/contexto e tentativa de imagem sem recriação nem auth posterior. | PARTIAL |
| ASTRA-P1-02-AC04 | Status não trata hint/discovery como completude; conflito/cancelamento não é ocultado | INTEGRATION_EVIDENCE_MISSING | Projeções e cancelamento estão em nodes separados; completar quatro estados e valores None/N/A na saída UI/XLSX. | PARTIAL |
| ASTRA-P1-02-AC05 | SINGLE e MULTI mostram limitações sem URL, header, body, credencial ou fórmula | TEST_COVERAGE_MISSING | XLSX G-PN, proteção de fórmula e diagnósticos têm nodes distintos; ampliar varredura por canários em todas as saídas finais. | PARTIAL |
| ASTRA-P1-03-AC01 | HardwareId ONVIF válido é preservado; ausente/inválido não inventado | TEST_COVERAGE_MISSING | Há prova positiva com Zeep local; adicionar ausente/inválido e comparar contagem de requests por variante. | PARTIAL |
| ASTRA-P1-03-AC02 | HardwareID Axis depende só da resposta pública/elevada já selecionada | TEST_COVERAGE_MISSING | Fluxo público/erro está coberto; completar versões/None e provar zero request opcional adicional por variante. | PARTIAL |
| ASTRA-P1-03-AC03 | MAC Panasonic válido normaliza; ausente/inválido fica None/N/A | TEST_COVERAGE_MISSING | 6 nodes cobrem três formatos válidos, ausência e duas formas inválidas, preservando identidade parcial. Lacuna específica fechada offline. | PASS_OFFLINE |
| ASTRA-P1-03-AC04 | deviceName/hardwareVersion/chaves desconhecidas não viram hostname/HardwareId | TEST_COVERAGE_MISSING | Nodes novos cobrem ONVIF, Axis, Panasonic e Dahua; falta vincular os demais mapeadores/fontes aplicáveis. | PARTIAL |
| ASTRA-P1-G-AC01 | Novos mappings/hints não alteram transporte/ledger/RTSP, 14 campos e fluxo integrado | INTEGRATION_EVIDENCE_MISSING | Novo node percorre ModelHint → coleta Panasonic/ONVIF real → `SnapshotService` real → RTSP provider desativado e saída sanitizada. Profile/proveniência, contadores AuthLedger, TLS e XLSX ainda dependem de nodes distintos; completar o cruzamento semântica por semântica antes de promover. | PARTIAL |
| ASTRA-TR-AC02 | Perfil aplica a grupo explícito/interseção do lote, sem enumeração; demais alvos HTTPS | INTEGRATION_EVIDENCE_MISSING | Plano por linha usa collector fake; provar com adapters produtivos em loopback o membro do grupo e outro alvo que permanece HTTPS. | PARTIAL |
| ASTRA-TR-AC03 | CIDR/wildcard/DNS/range/host alternativo de perfil/chaves desconhecidas/id duplicado/conflitos são rejeitados antes da rede | TEST_COVERAGE_MISSING | tests/test_astra_acl_axis_policy.py::test_invalid_transport_profile_schema_fails_before_transport_construction (8 classes); test_secret_bearing_transport_profile_is_rejected_with_sanitized_error - PASS | PASS_OFFLINE |
| ASTRA-TR-AC04 | Seleção, autorização vinculada e aceite de risco antecedem a primeira operação; config mutada depois não altera plano | INTEGRATION_EVIDENCE_MISSING | Pré-voo/cancelamento e plano compilado estão cobertos; integrar CLI/workflow com ordem observada e mutação pós-seleção sem alterar o plano. | PARTIAL |
| ASTRA-TR-AC07 | 401 final/403/erro vendor fecha auth; Basic-only/SHA-256 não suportado não provoca troca/replay | TEST_COVERAGE_MISSING | tests/test_astra_evidence_completion_03.py::test_auth_challenge_matrix_counts_exchanges_and_blocks_later_families (4 variantes) - PASS | PASS_OFFLINE |
| ASTRA-TR-AC08 | Perfil não implica privilégio: Viewer nega Operator; Axis público permanece sem credenciais mesmo com HTTP selecionado | EVIDENCE_ALREADY_EXISTS | Nodes Digest Hikvision e Axis PUBLIC_NONE cobrem as duas cláusulas específicas; executados novamente e vinculados à linha principal. Limite: fixture sintética, endpoint Hikvision único e Axis anônimo. | PASS_OFFLINE |
| ASTRA-TR-AC09 | Sessões/credenciais/estado não atravessam linhas iguais ou targets; default/profile sem interferência | INTEGRATION_EVIDENCE_MISSING | Credenciais por linha no mesmo IP são verificadas sequencialmente; falta concorrência loopback e contexto isolado por sessão/perfil. | PARTIAL |
| ASTRA-TR-AC10 | Policy/ref/auth sanitizados aparecem no diagnóstico local; scheme corresponde só à rede real; 14 campos/nove colunas preservados | INTEGRATION_EVIDENCE_MISSING | 14 campos, diagnóstico e XLSX HTTPS têm nodes; falta verificar policy/ref e bytes/layout por scheme selecionado no mesmo percurso. | PARTIAL |
| ASTRA-TR-AC11 | Logs/XLSX/repr/erros não contêm username/password, URL, header, body, nonce, fórmula ou secret; perfil com segredo é rejeitado | TEST_COVERAGE_MISSING | Saídas e canários estão parcialmente cobertos; varrer conjunto contratual completo em todas as saídas e entradas de perfil. | PARTIAL |
| ASTRA-TR-AC13 | Secundária só por identidade essencial, sem recusa, até duas lógicas/uma família; sem descoberta de auth/porta ou request por opcional | INTEGRATION_EVIDENCE_MISSING | D03, budgets e cancelamento estão em nodes separados; integrar contagens de tentativas/famílias, recusa e zero login por opcional. | PARTIAL |

### P1-G-AC01 — cruzamento das invariantes

| Elo | Evidência vinculada | O que o teste observa | Limite residual |
|---|---|---|---|
| ModelHint | `tests/test_astra_gpn_joint_integration.py::test_exact_model_single_workflow_uses_real_default_panasonic_adapter`, `::test_ineligible_model_does_not_call_panasonic_cgi_or_capabilities`; `tests/test_astra_p1_transport.py::test_model_hint_nfc_ascii_spaces_and_casefold`, `::test_model_hint_is_not_a_vendor_routing_signal`; novo `tests/test_astra_p1_cross_invariant.py::test_single_real_collection_reaches_disabled_rtsp_guard_without_media_io` | Hint exato normalizado chega pelo workflow SINGLE; variantes inelegíveis/ausentes bloqueiam CGI; não inventa fabricante/modelo observado. | Os nodes de normalização/negativas e o percurso RTSP são casos distintos. |
| Seleção/perfil | `tests/test_astra_p1_transport.py::test_transport_selection_summary_and_row_plans_require_exact_panasonic_model`, `::test_profile_ineligible_row_skips_collection_and_records_safe_local_policy`; `tests/test_astra_transport_selection_workflows.py::test_multi_freezes_profile_per_row_and_skips_ineligible_rows_before_io` | Eligibility e plano congelado são exercitados; G-PN usa `HTTPS_DEFAULT` e regras HTTPS exatas. | A seleção de profile/linha ainda é testada em fluxo de teste separado; workflow RTSP integrado não usa profile nomeado. |
| Adapter e proveniência | G-PN `::test_exact_model_single_workflow_uses_real_default_panasonic_adapter`, `::test_digest_challenge_then_200_records_both_exchanges_and_effective_https`; `tests/test_astra_p1_transport.py::test_collection_metadata_is_allowlisted_and_secret_free` | Adapter Panasonic produtivo, requests HTTPS efetivos, resposta parcial e metadados allowlisted. | Proveniência não é correlacionada no mesmo node com o profile e ledger. |
| AuthLedger | `tests/test_astra_acl_operation_matrix.py::test_digest_acl_fixture_authenticates_accounts_for_real_hikvision_operation`; G-PN `::test_digest_challenge_then_200_records_both_exchanges_and_effective_https` | Digest realmente envia Authorization; fixture ACL verifica 1 tentativa lógica/2 trocas físicas, Viewer/Operator/Admin e 401 inválido. | Contadores/estados do ledger pertencem a outra operação/fixture, não ao mesmo G-PN Panasonic→RTSP. |
| Transporte autorizado e TLS | G-PN `::test_exact_model_single_workflow_uses_real_default_panasonic_adapter`, `::test_invalid_tls_is_fail_closed_without_http_fallback`; `tests/test_astra_p1_transport.py::test_tls_failure_closes_transport_before_creating_session` | HTTPS selecionado por regra exata e fixture trusted; certificado inválido retorna TLS_ERROR sem fallback HTTP/ONVIF posterior. | O teste RTSP cruzado não inclui cenário TLS inválido; a correlação é por nodes separados. |
| RTSP fail-closed | `tests/test_astra_p1_cross_invariant.py::test_single_real_collection_reaches_disabled_rtsp_guard_without_media_io`; `tests/test_snapshot_pipeline.py::test_rtsp_context_path_fails_closed_before_lock_or_decoder` | Workflow SINGLE e coleta real chegam ao `SnapshotService` real; `RtspFrameProvider` produtivo retorna `TARGET_REJECTED`; lock, media ONVIF e PyAV têm tripwires sem chamada. Node integrado: 1 passed. | Os providers de snapshot HTTP são stubs inertes; nenhum fluxo RTSP operacional é autorizado ou executado. |
| Resultado/14 campos/XLSX | G-PN `::test_exact_model_single_workflow_uses_real_default_panasonic_adapter`, `::test_multi_real_excel_path_isolates_credentials_for_same_ip_and_sanitizes_output`; `tests/test_astra_p1_transport.py::test_camera_result_stays_at_exactly_fourteen_fields` | Resultado parcial preserva evidência válida, modelo ausente não é inventado, MULTI lê/escreve XLSX real e sanitiza credenciais; schema tem 14 campos. | Invariante de schema e saída não é observada na mesma execução que verifica o provider RTSP. |

**Decisão ROOT:** `ASTRA-P1-G-AC01=PARTIAL`. O teste integrado novo fecha a evidência de bloqueio RTSP no percurso de hint/coleta real; a vinculação entre profile nomeado, proveniência, estado do AuthLedger, TLS e saída final ainda está distribuída por fixtures distintas. `G-PN-JOINT=PASS_OFFLINE (15/15)` permanece separado dessa matriz e não equivale a revisão de segurança.

### Reconciliação do gate desta atividade

```text
ACTIVITY_ID = CAM_SCANNER_ASTRA_EVIDENCE_SECURITY_GATE_01
INITIAL_AC = 16 PASS / 40 PARTIAL / 0 UNVERIFIED
CURRENT_AC = 22 PASS_OFFLINE / 34 PARTIAL / 0 UNVERIFIED
P0 = 9 PASS / 13 PARTIAL / 0 UNVERIFIED
P1 = 6 PASS / 13 PARTIAL / 0 UNVERIFIED
TRANSPORT = 7 PASS / 8 PARTIAL / 0 UNVERIFIED
INITIAL_GAP_CATEGORIES_FOR_40 = EVIDENCE_ALREADY_EXISTS:2; TEST_COVERAGE_MISSING:14; INTEGRATION_EVIDENCE_MISSING:20; IMPLEMENTATION_DEFECT:1; PREEXISTING_BASELINE_UNPROVABLE:2; OTHER_WITH_JUSTIFICATION:1
RESOLVED_PARTIAL_ACS = 6 (ASTRA-P0-01-AC01/02/03/06; ASTRA-P1-03-AC03; ASTRA-TR-AC08)
CURRENT_PARTIAL_CATEGORIES = TEST_COVERAGE_MISSING:10; INTEGRATION_EVIDENCE_MISSING:20; IMPLEMENTATION_DEFECT:1; PREEXISTING_BASELINE_UNPROVABLE:2; OTHER_WITH_JUSTIFICATION:1
OPERATIONAL_HOMOLOGATION_REQUIRED = 0
P1_G_AC01 = PARTIAL
P0_01_AC04 = PARTIAL
P0_03_AC01 = PASS_OFFLINE_SCOPED (GET /ISAPI/System/deviceInfo only)
G_PN_JOINT = PASS_OFFLINE (15/15 reexecuted)
PYTEST_LAST_FULL_RUN = 505 passed / 0 failed / 0 skipped / 0 deselected
NEW_FOCAL_NODES = AXIS 10/10; MAPPING 15/15; P1_CROSS_RTSP 1/1; G_PN 15/15
ACL_FOCAL_NODES = 5 passed
RUFF_NEW_TEST_FILES = PASS
RUFF_GLOBAL = PARTIAL (1 preexisting I001 in tests/test_logging_setup.py; unchanged)
COMPILEALL = PASS (src/tests)
GIT_DIFF_CHECK = PASS
ACTIVITY_STATUS = PARTIAL
ACTIVITY_COMPLETION_PERCENT = 76% (marcos de execução; não proporção de ACs PASS)
ACTIVITY_COMPLETE = NO
DELIVERY_STATUS = SENT (chat existente “Projeto Scanner 2.0”; confirmação da ferramenta recebida)
SECURITY_SANDBOX_VERIFIED = NO
SECURITY_REVIEW_STATUS = BLOCKED_RUNTIME_PROTECTION
SECURITY_FINDINGS = NOT_ASSESSED
```

O reviewer não foi iniciado porque o runtime fornece `workspace-write`, sem proteção técnica read-only efetiva. O preflight anterior de scanner continua apenas preflight. Para concluir a revisão, abrir sessão separada com sandbox read-only e validar o modo/permissões antes de ler fontes; se a proteção não estiver ativa, interromper sem revisar. Não declarar ausência de findings.

Resultados finais das verificações: pytest completo **505 passed, 0 failed, 0 skipped, 0 deselected**; G-PN-JOINT **15/15**; nodes focais novos Axis **10/10**, mapeamentos P1 **15/15**, RTSP integrado **1/1** e ACL focal **5 passed**. Ruff nos três arquivos de teste novos, compileall de `src`/`tests`, `git diff --check` e a varredura de trailing whitespace dos artefatos novos passaram. `ruff check .` continua com somente o I001 preexistente em `tests/test_logging_setup.py`; o arquivo não foi alterado. Nenhum device, HTTP externo ou RTSP operacional foi acessado.

## CAM_SCANNER_ASTRA_AC_CLOSURE_02 — remediação focal offline (2026-10-28)

Baseline do Card confirmada em feature/pre-p12-unified-remediation, HEAD 0c936d443e4865e0f9c9d2dba5fb8927bb6f5431, igual ao upstream rastreado. Nenhum checkout, pull, reset, clean, stash, rebase, stage, commit ou push ocorreu. As alterações da atividade estão restritas a dois arquivos de teste e a esta matriz/PROJECT_STATE. Nenhum código de produção ou contrato foi alterado.

O gate multiagente cumulativo foi executado. Resultado: FAIL_FOR_DELEGATION. Embora as frentes fossem divisíveis, este runtime não comprovou checkout isolado com escrita para agentes nem sandbox tecnicamente read-only para revisão independente. A execução seguiu diretamente pelo ROOT conforme fallback do Card. Nenhum subagente foi iniciado; modelo de agente não solicitado/verificado. Roteador local R4.1 e referências foram lidos/aplicados manualmente; loader/modelos/permissões nativos permanecem não verificados.

| AC | Estado anterior → atual | Evidência atual e limite |
|---|---|---|
| ASTRA-P0-02-AC04 | PARTIAL → PASS_OFFLINE | Nodes Panasonic 404/401/403 e quatro payloads inválidos não criam identidade/evidência. |
| ASTRA-P0-04-AC01 | PARTIAL → PASS_OFFLINE | Workflow MULTI/adapters/TerminalUI/XLSX reais em loopback mostram scheme efetivo por linha, profile/ref/auth sanitizados, schema 14/9 e ausência de canários. |
| ASTRA-P1-03-AC01 | PARTIAL → PASS_OFFLINE | Node ONVIF testa HardwareId válido/ausente/tipo inválido e uma chamada GetDeviceInformation por variante. |
| ASTRA-P1-03-AC02 | PARTIAL → PASS_OFFLINE | Node Axis testa HardwareID válido/None, duas operações públicas por variante e ausência de auth/request opcional. |
| ASTRA-P1-03-AC04 | PARTIAL → PASS_OFFLINE | Quatro nodes negativos de mapeamento ONVIF, Axis, Panasonic e Dahua; campos desconhecidos não fabricam identidade. |
| ASTRA-TR-AC02 | PARTIAL → PASS_OFFLINE | Membro do profile usa HTTP autorizado e alvo fora do profile permanece HTTPS, sem enumeração. |
| ASTRA-TR-AC09 | PARTIAL → PASS_OFFLINE | Duas contas Digest concorrentes no mesmo IP são correlacionadas às linhas por serial; sem vazamento nas saídas. |
| ASTRA-TR-AC10 | PARTIAL → PASS_OFFLINE | Diagnósticos/UI/XLSX refletem schemes HTTP/HTTPS, policy/ref/auth, 14 campos e nove colunas, com canários ausentes. |

Estado ao fim de CAM_SCANNER_ASTRA_AC_CLOSURE_02: P0 = 9 PASS_OFFLINE / 13 PARTIAL / 0 UNVERIFIED; P1 = 6 / 13 / 0; Transport = 7 / 8 / 0; total = 30 PASS_OFFLINE / 26 PARTIAL / 0 UNVERIFIED. O estado anterior era 22/34/0. G-PN-JOINT foi 15/15 PASS_OFFLINE.

Os 26 ACs ainda PARTIAL e suas categorias/dependências são:
- TEST_COVERAGE_MISSING (6): ASTRA-P1-01-AC05; ASTRA-P1-02-AC01/AC05; ASTRA-TR-AC03/AC07/AC11.
- INTEGRATION_EVIDENCE_MISSING (16): ASTRA-P0-01-AC05; ASTRA-P0-02-AC02/AC03/AC06; ASTRA-P0-03-AC02/AC03/AC04; ASTRA-P1-01-AC01/AC05/AC07/AC08; ASTRA-P1-02-AC02/AC03/AC04; ASTRA-P1-G-AC01; ASTRA-TR-AC04/AC13.
- IMPLEMENTATION_DEFECT (1): ASTRA-P0-01-AC04. ELEVATED_AUTHORIZED não está autorizado/implementado; não foi criado.
- PREEXISTING_BASELINE_UNPROVABLE (2): ASTRA-P0-05-AC01/AC02. O manifesto de hashes histórico não existe e não pode ser fabricado retroativamente.
- OTHER_WITH_JUSTIFICATION (1): ASTRA-P0-G-AC01. A revisão independente exige proteção read-only técnica, indisponível neste runtime; findings permanecem NOT_ASSESSED.

Validação atual: regressão integral 510 passed, 0 failed, 0 skipped, 0 deselected; G-PN-JOINT 15/15; nodes focais P1 mapping 15/15. Ruff nos dois arquivos alterados PASS; compileall src/tests PASS com cache temporário isolado; git diff --check PASS. ruff check src tests permanece PARTIAL por um único I001 preexistente em tests/test_logging_setup.py, não editado. A primeira execução local do pytest falhou por PermissionError no TEMP compartilhado; repetida em diretório temporário exclusivo com acesso ampliado, passou.

SECURITY_REVIEW_STATUS=BLOCKED_RUNTIME_PROTECTION; SECURITY_FINDINGS=NOT_ASSESSED, não zero. Nenhuma câmera real, HTTP operacional ou RTSP operacional foi acessado. Nenhum privilégio elevado foi implementado. P0-01-AC04, P0-05-AC01/02 e os critérios listados como PARTIAL permanecem assim.

### Registro estruturado

ACTIVITY_ID = CAM_SCANNER_ASTRA_AC_CLOSURE_02
BASELINE_HEAD = 0c936d443e4865e0f9c9d2dba5fb8927bb6f5431
FINAL_HEAD = 0c936d443e4865e0f9c9d2dba5fb8927bb6f5431
BRANCH = feature/pre-p12-unified-remediation
BASELINE_SYNC = HEAD == origin/feature/pre-p12-unified-remediation
WORKTREE_STATUS = 4 modified tracked paths after documentation; 0 staged; untracked listing incomplete due access-denied directories; preserve baseline artifacts
ROUTER_SKILL_STATUS = LOCAL_R4.1_MANUALLY_READ_AND_APPLIED; NATIVE_LOADER_UNVERIFIED
ROUTER_REFERENCE_VERSION = R4.1
MULTIAGENT_GATE_RESULT = FAIL_FOR_DELEGATION
MULTIAGENT_GAIN_JUSTIFICATION = Independent adapter, integration, CLI/XLSX and test slices offer material gain, but sibling checkout/write isolation and technical read-only security review were not verified in this runtime.
EXECUTION_MODE_EFFECTIVE = DIRECT_ROOT_ONLY
AGENTS_SELECTED = NONE
AGENTS_ACTUALLY_SPAWNED = NONE
AGENTS_NOT_USED_AND_REASON = Gate failed runtime isolation/protection requirements; direct fallback executed.
AGENT_DECLARED_MODELS = NOT_APPLICABLE
AGENT_RUNTIME_VERIFICATION = NOT_APPLICABLE; native runtime capability unverified
FILE_OWNERSHIP = ROOT owned two test files, matrix and PROJECT_STATE
FILES_CHANGED = tests/test_astra_acl_axis_policy.py; tests/test_astra_gpn_joint_integration.py; docs/audit/ASTRA_REMEDIATION_56_AC_MATRIX.md; docs/continuity/PROJECT_STATE.md
TESTS_BEFORE = 505 historical checkpoint; not treated as current execution
TESTS_AFTER = 510 passed / 0 failed / 0 skipped / 0 deselected
AC_INITIAL = 22 PASS / 34 PARTIAL / 0 UNVERIFIED
AC_FINAL = 30 PASS_OFFLINE / 26 PARTIAL / 0 UNVERIFIED
AC_PROMOTED = ASTRA-P0-02-AC04; ASTRA-P0-04-AC01; ASTRA-P1-03-AC01; ASTRA-P1-03-AC02; ASTRA-P1-03-AC04; ASTRA-TR-AC02; ASTRA-TR-AC09; ASTRA-TR-AC10
AC_REMAINING = 26 IDs enumerated by category above; reasons in the per-AC matrix and this activity record
G_PN_JOINT_RESULT = PASS_OFFLINE (15/15); distinct from ASTRA-P1-G-AC01
SECURITY_REVIEW_STATUS = BLOCKED_RUNTIME_PROTECTION
SECURITY_FINDINGS = NOT_ASSESSED
CONTINUITY_STATUS = PROJECT_STATE_UPDATE_PASS
FORMAL_CLOSURE_STATUS = NOT_CLOSED; 26 ACs PARTIAL and independent security review blocked
GIT_COMMIT_PUSH = NONE
REAL_CAMERA_ACCESS = NONE
OPERATIONAL_HTTP = NONE
NEXT_RECOMMENDED_ACTIVITY = Reavaliar os 26 PARTIAL conforme a matriz; conduzir revisão independente somente após confirmar sessão tecnicamente read-only; obter autoridade específica antes de plano de autenticação elevada.
ACTIVITY_COMPLETION_PERCENT = 92% (marcos de execução; fechamento formal permanece aberto)
ACTIVITY_STATUS = PARTIAL
ACTIVITY_COMPLETE = NO
DELIVERY_STATUS = SENT (chat existente Projeto Scanner 2.0; threadId 6ad2b0c4-24a4-83e9-b87b-043194e0ff57; kind=chatgpt; hostId=N/A; confirmação da ferramenta recebida)
GIT_WRITES = NONE


## CAM_SCANNER_ASTRA_EVIDENCE_COMPLETION_03 - fechamento de evidencias offline (2026-10-28)

Baseline do Card confirmada: repositorio `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_pre_p12_remediation`, branch `feature/pre-p12-unified-remediation`, HEAD `0c936d443e4865e0f9c9d2dba5fb8927bb6f5431`. Os quatro paths modificados na entrada foram preservados. A listagem dos untracked preexistentes permaneceu incompleta por restricoes de acesso; nenhum artefato foi apagado. Sem staging, commit, push, reset, restore, clean, stash, rebase ou merge.

### Roteamento e ownership

Router local `codex-task-router` lido manualmente; catalogo local encontrado em R4.2 e referencias aplicadas. Loader nativo permanece UNVERIFIED. MULTIAGENT_GATE_RESULT=PASS para as quatro frentes autorizadas, com duas vagas de agente por lote e ownership por path; gate de seguranca read-only e separado e continua bloqueado. Agentes efetivamente iniciados e concluidos: `test_engineer` (`tests/test_astra_acl_axis_policy.py`, escreveu testes); `backend_engineer` (frente vendor, revisao read-only, sem alteracoes); `integration_engineer` (application/transport/config, revisao read-only, sem alteracoes); `python_cli_engineer` (Excel/terminal, revisao read-only porque a permissao efetiva nao autorizou escrita no checkout). Modelo/esforco em perfis sao declarados; nao foram verificados em metadata de turno dos filhos. ROOT integrou e validou as mudancas.

### Resultado AC a AC

Estado inicial: 30 PASS_OFFLINE / 26 PARTIAL / 0 UNVERIFIED. Estado final: **38 PASS_OFFLINE / 18 PARTIAL / 0 UNVERIFIED**. Oito promocoes defensaveis:

| AC | Evidencia desta atividade |
|---|---|
| ASTRA-P0-03-AC02 | Matriz local de Basic-only, Digest SHA-256 nao suportado, 401 final e 403 com contagens fisicas/logicas e bloqueio AuthLedger. |
| ASTRA-P0-03-AC03 | Isolamento de duas contas Digest concorrentes no mesmo IP; mismatch de ModelHint compara SINGLE/MULTI e contagens. |
| ASTRA-P1-01-AC05 | Evidencia observada prevalece sobre hint em duas ordens de merge e nos fluxos SINGLE/MULTI sem requests/auth extras. |
| ASTRA-P1-01-AC07 | Workbook legado com coluna extra, formula MODELO com texto em cache, linha invalida e valida; fluxo exporta as tres linhas, registra invalid hint e nao roteia pela formula. |
| ASTRA-P1-02-AC01 | Sete cenarios de falha recebem etapa/categoria distintas e verificacao de sentinelas. |
| ASTRA-P1-02-AC02 | Evidencia parcial Panasonic/proveniencia sobrevive a falha SOAP 403 ou timeout posterior. |
| ASTRA-TR-AC03 | Oito classes de schema de profile e profile com segredo falham antes de construir transportes/sessoes. |
| ASTRA-TR-AC07 | Challenges Basic/SHA-256/Digest final 401/403 encerram conforme contrato e bloqueiam autenticacao posterior. |

ACs ainda PARTIAL (18):
- TEST_COVERAGE_MISSING (2): ASTRA-P1-02-AC05; ASTRA-TR-AC11. Falta varredura completa de canarios em todas as saidas finais.
- INTEGRATION_EVIDENCE_MISSING (12): ASTRA-P0-01-AC05; ASTRA-P0-02-AC02/AC03/AC06; ASTRA-P0-03-AC04; ASTRA-P1-01-AC01/AC08; ASTRA-P1-02-AC03/AC04; ASTRA-P1-G-AC01; ASTRA-TR-AC04/AC13. Permanecem lacunas de cadeia integrada descritas por AC.
- IMPLEMENTATION_DEFECT / AUTHORITY_GATE (1): ASTRA-P0-01-AC04; ELEVATED_AUTHORIZED nao esta autorizado nem implementado.
- PREEXISTING_BASELINE_UNPROVABLE (2): ASTRA-P0-05-AC01/AC02; manifesto historico ausente, sem fabricacao retroativa.
- OTHER_WITH_JUSTIFICATION (1): ASTRA-P0-G-AC01; revisao de seguranca independente exige protecao tecnica read-only.

### Mudancas e validacao

ROOT corrigiu `ExcelReader` para identificar celulas formula na coluna MODELO em um workbook `data_only=False` paralelo somente quando a coluna existe; formulas sao hint invalido mesmo quando possuem texto em cache. `ExcelWriter` passou a manter `validate_model_hint` na allowlist sanitizada de `DIAGNOSTICOS`. Foram acrescentados testes de formula sem cache/com cache textual e fluxo MULTI com workbook legado, extra, linha valida/invalida e exportacao.

- TESTS_BEFORE = 510 passados (resultado historico informado no Card).
- TESTS_AFTER = 536 passed / 0 failed / 0 skipped / 0 deselected, 94.52 s, warnings nao reportados.
- G_PN_JOINT = 31 passed, 25.27 s.
- Suite focal das seis frentes = 124 passed, 32.81 s.
- RUFF_CHANGED_PATHS = PASS. RUFF global segue PARTIAL por um unico I001 preexistente em `tests/test_logging_setup.py`, nao editado.
- COMPILEALL = PASS. GIT_DIFF_CHECK = PASS apos integracao documental.

SECURITY_REVIEW_STATUS=BLOCKED_RUNTIME_PROTECTION; SECURITY_FINDINGS=NOT_ASSESSED, nao zero. P2 MEDIA continua DEFERRED. Sem camera real, HTTP operacional, RTSP operacional, auth elevada, firmware/config/ACL operacional ou publicacao. ACTIVITY_STATUS=PARTIAL; FORMAL_CLOSURE_STATUS=NOT_CLOSED.

```text
ACTIVITY_ID = CAM_SCANNER_ASTRA_EVIDENCE_COMPLETION_03
BASELINE_HEAD = 0c936d443e4865e0f9c9d2dba5fb8927bb6f5431
FINAL_HEAD = 0c936d443e4865e0f9c9d2dba5fb8927bb6f5431
BRANCH = feature/pre-p12-unified-remediation
WORKTREE_STATUS = 7 tracked paths modified; 1 new untracked test; preexisting untracked inventory incomplete; 0 staged
ROUTER_SKILL_STATUS = LOCAL_SKILL_READ_AND_APPLIED; NATIVE_LOADER=UNVERIFIED
ROUTER_VERSION = R4.2 (local catalog)
MULTIAGENT_GATE_RESULT = PASS_FOR_AUTHORIZED_OFFLINE_WORK; SECURITY_REVIEW_GATE=BLOCKED_RUNTIME_PROTECTION
EXECUTION_MODE_EFFECTIVE = MULTIAGENT (two batches, ROOT integration)
AGENTS_PLANNED = test_engineer; backend_engineer; integration_engineer; python_cli_engineer
AGENTS_SELECTED = test_engineer; backend_engineer; integration_engineer; python_cli_engineer
AGENTS_ACTUALLY_SPAWNED = test_evidence; vendor_evidence; workflow_transport; input_output
AGENTS_COMPLETED = all four
AGENTS_NOT_USED_AND_REASON = security_reviewer not spawned: required technical read-only protection unavailable; no additional agents beyond the four assigned roles
AGENT_DECLARED_MODELS = Card says gpt-6-luna/high for all four; local R4.2 catalog says backend/integration/test are gpt-6.1-terra/high and python_cli is gpt-6-luna/high; declarations diverge
AGENT_REQUESTED_MODELS = no explicit model override; agent_type requested
AGENT_RUNTIME_VERIFIED_MODELS = UNVERIFIED (no correlated child-turn metadata)
AGENT_PERMISSIONS = path-scoped prompts; test agent wrote assigned test; vendor/workflow read-only; Excel agent stopped without write when effective path permission was unavailable; no filesystem isolation claimed
AGENT_OWNERSHIP = test_evidence: tests/test_astra_acl_axis_policy.py; vendor_evidence: vendor paths; workflow_transport: application/transport/config; input_output: excel/terminal; ROOT: integration tests, reader/writer corrections, matrix, PROJECT_STATE
FILES_CHANGED = tests/test_astra_acl_axis_policy.py; tests/test_astra_gpn_joint_integration.py; tests/test_astra_p1_transport.py; tests/test_astra_evidence_completion_03.py (new); src/cam_scanner/excel/reader.py; src/cam_scanner/excel/writer.py; docs/audit/ASTRA_REMEDIATION_56_AC_MATRIX.md; docs/continuity/PROJECT_STATE.md
FILES_PRESERVED = quatro tracked paths modificados na entrada, sem perda dos deltas anteriores
TESTS_BEFORE = 510 passed (historical)
TESTS_AFTER = 536 passed / 0 failed / 0 skipped / 0 deselected; 94.52 s
G_PN_JOINT_RESULT = 31 passed / 0 failed; 25.27 s
RUFF_RESULT = changed paths PASS; global PARTIAL due preexisting I001 in tests/test_logging_setup.py
COMPILEALL_RESULT = PASS
DIFF_CHECK_RESULT = PASS
AC_INITIAL = 30 PASS_OFFLINE / 26 PARTIAL / 0 UNVERIFIED
AC_FINAL = 38 PASS_OFFLINE / 18 PARTIAL / 0 UNVERIFIED
AC_PROMOTED = ASTRA-P0-03-AC02; ASTRA-P0-03-AC03; ASTRA-P1-01-AC05; ASTRA-P1-01-AC07; ASTRA-P1-02-AC01; ASTRA-P1-02-AC02; ASTRA-TR-AC03; ASTRA-TR-AC07
AC_REMAINING = 18 IDs listed above; evidence gaps and gates retained
SECURITY_REVIEW_STATUS = BLOCKED_RUNTIME_PROTECTION
SECURITY_FINDINGS = NOT_ASSESSED
CONTINUITY_STATUS = PROJECT_STATE_UPDATE_PENDING_FINAL_DIFF_CHECK
FORMAL_CLOSURE_STATUS = NOT_CLOSED
GIT_COMMIT_PUSH = NONE
REAL_CAMERA_ACCESS = NONE
OPERATIONAL_HTTP = NONE
OPERATIONAL_RTSP = NONE
ELEVATED_AUTH = NONE
NEXT_RECOMMENDED_ACTIVITY = Fechar evidencias dos 18 ACs PARTIAL; realizar revisao independente somente em runtime tecnicamente read-only
SAFE_RESUME_POINT = branch/HEAD inalterados; regressao completa 536 passed; sem Git writes
ACTIVITY_COMPLETION_PERCENT = 92% (marcos executados; nao equivale a ACs aceitos)
ACTIVITY_COMPLETE = NO
DELIVERY_STATUS = SENT (chat existente Projeto Scanner 2.0; threadId 6ad2b0c4-24a4-83e9-b87b-043194e0ff57; kind=chatgpt; confirmacao recebida)
GIT_WRITES = NONE
```
