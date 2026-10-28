# Registro de continuidade

## Registro vigente - CAM_SCANNER_ASTRA_CROSS_MACHINE_CHECKPOINT_GIT_02 (2026-10-28)

As atividades CAM_SCANNER_ASTRA_AC_CLOSURE_02 e CAM_SCANNER_ASTRA_EVIDENCE_COMPLETION_03 elevaram a matriz de 22/56 para 30/56 e depois 38/56 PASS_OFFLINE. Última regressão reportada: 536 testes sem falhas; G-PN 31/31. Quatro subagentes concluíram as frentes no ciclo R4.2; ROOT integrou; modelos efetivos dos turnos filhos não verificados.

Este checkpoint é um registro de transporte seguro do estado por Git; a publicação efetiva deve ser confirmada no remoto. Conteúdo, 18 AC restantes e limites em checkpoints/CAM_SCANNER_ASTRA_CROSS_MACHINE_CHECKPOINT_2026_10_28.md.

Segurança permanece BLOCKED_RUNTIME_PROTECTION / NOT_ASSESSED; 14 AC técnicos podem ser trabalhados offline em atividade separada e quatro estão condicionados. Sem câmera real, auth elevada, HTTP/RTSP operacional ou deploy. Os registros seguintes são históricos.


## CAM_SCANNER_P12_WINDOWS_ONEDIR_BUILD_AND_VALIDATION — estado final (2026-10-19)

O build P12 autorizado gerou e validou o pacote portátil CAM Scanner `1.0.0` para Windows 11 24H2 x64. `PREP12-09` foi satisfeito nesta etapa: ONEDIR, WSDL/XSD e recursos, DLLs, certificado, configuração externa, logs/temp, CLI sem Python no PATH, pasta protegida, falha controlada sem diretório gravável, destino local não sobrescrito e exportação XLSX/snapshot sintético passaram. O destino UNC/SMB não foi exercitado porque nenhum caminho autorizado foi fornecido. Veja [`PROJECT_STATE.md`](PROJECT_STATE.md) para status, hashes e limites; evidências do executável e do manifesto estão em `_tmp_P12_WINDOWS_ONEDIR_20261019`.

O fixture de runtime usou somente `127.0.0.1`; GetCapabilities, GetDeviceInformation, GetProfiles, GetSnapshotUri e snapshot terminaram com uma linha `SUCCESS` e uma imagem embutida. Nenhuma câmera real, publicação, Git write ou homologação operacional foi executada. Os gates pré-P12 e a regressão completa de 373 testes foram preservados sem reexecução. Próximo passo: autorização separada de homologação READ_ONLY com câmera/modelo real.

## Snapshot anterior — CAM_SCANNER_FINAL_STABILIZATION — estado final (2026-10-19; supersedido pelo build P12 abaixo)

Gate V e os resultados finais estão registrados em [`PROJECT_STATE.md`](PROJECT_STATE.md) e no [relatório de submissão](../audit/CAM_SCANNER_FINAL_STABILIZATION_GATE_V_2026-10-19.md). O teste real de symlink passou em Windows/Python 3.14.0; a regressão terminou com 373 passed e zero failures, skips ou deselected. Gate 2, Gate 3 independente e Gate V passaram; Gate 4 concluiu `P12_READINESS=READY_FOR_P12`. PREP12-09/build-smoke ONEDIR, câmera real e Gate 5/publicação continuam posteriores. Nenhum pacote P12 foi gerado.

## Snapshot anterior — CAM_SCANNER_FINAL_STABILIZATION (2026-10-19; supersedido acima)

O estado factual e a submissão de evidências estão em [`PROJECT_STATE.md`](PROJECT_STATE.md) e [`docs/audit/CAM_SCANNER_FINAL_STABILIZATION_GATE_V_2026-10-19.md`](../audit/CAM_SCANNER_FINAL_STABILIZATION_GATE_V_2026-10-19.md). O teste real criou o symlink, mas falhou com `NotImplementedError` em `os.utime(..., follow_symlinks=False)` antes das verificações de retenção. A regressão completa não foi executada; Gate 2 e Gate V não foram atendidos, Gate 3 permanece pendente e `P12_READINESS=BLOCKED`.

Próximo passo: com autorização para ajustar o teste, remover a dependência da operação temporal não suportada sem enfraquecer o caso; repetir o teste focal e, somente após PASS, rodar regressão integral zero-skip, promover Gate 3 independentemente e reavaliar readiness. Nenhum build P12, acesso a câmera ou Git write ocorreu.

## Recuperação de continuidade — CAM_CONTINUITY_RECOVERY_UNBLOCK_01 (2026-10-16)

O estado atual de pins, origem de pacotes e PREP12-10 está em [`PROJECT_STATE.md`](PROJECT_STATE.md). Gate de authorities passou: 9 pins do binding correspondem aos bytes das entradas verificadas nos pacotes governados. Arquivos extraídos divergentes foram preservados e não usados como fonte. PyPI público foi autorizado pelo usuário; `PIP_NO_INDEX=1` foi preservado. O lock candidato fora do repo foi confirmado pelo SHA-256 registrado no estado; não houve instalação nem reprodução. Findings PREP12 permanecem abertos, Gate V não atendido e P12 bloqueada.

## PRE-P12 — checkpoint de aceite e dependências (2026-10-16; fonte/lock superseded pela recuperação acima)

O Architect independente formalizou as disposições em [`docs/audit/PRE_P12_ACCEPTANCE_REASSESSMENT_2026-10-16.md`](../audit/PRE_P12_ACCEPTANCE_REASSESSMENT_2026-10-16.md): PREP12-01/02/04/05 permanecem `OPEN` até Gate 2 sem skips; 01/02 também precisam do Gate 3. PREP12-10 = `BLOCKED_EXTERNAL_DEPENDENCY`; o usuário confirmou fonte aprovada não identificada e instruiu manter `PIP_NO_INDEX=1` sem contorno. `requirements/locks/windows-py314.in` já é o manifesto candidato; não alteramos versões, instalamos dependências, geramos hashes ou lock, nem reproduzimos ambiente. PREP12-11 = `OPEN_CONDITIONAL`; a sondagem temporária de capacidade symlink falhou com HRESULT `0x80070522` / WinError 1314 e os arquivos da sondagem foram removidos.

Mantém-se a execução integral de referência 372 passed/1 skipped, logo `GATE_V = NOT_MET`, `P12_READINESS = BLOCKED`, `ACTIVITY_COMPLETE = NO` e progresso 96%. PREP12-09 continua diferido por contrato; CLEARED anteriores preservados. Nenhuma câmera, build P12 ou Git write.

## PRE-P12 — evidência final e reavaliação de aceite (2026-10-16; vigente)

Checkpoint final da atividade PRE_P12_UNIFIED_REMEDIATION, executado pelo agente em PowerShell Windows autorizado. Python 3.14.0 foi validado em `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner\.venv\Scripts\python.exe`; o import `cam_scanner` aponta para o target worktree. A suíte integral pós-delta, por harness autorizado que desabilita apenas tmpdir/cacheprovider e fornece `tmp_path` único por teste sob diretório preservado, terminou com 372 passed, 0 failed, 1 skipped, 0 deselected, 0 xfailed em 111.06s. O skip é do teste de symlink real em Windows (WinError 1314, privilégio ausente); nenhuma elevação ocorreu. Ruff `src tests`, `pip check` e `git diff --check` passaram; avisos LF/CRLF não são falhas. O caso focado das filas RTSP teve 2 passed e 12 deselected pelo filtro focado; a full run teve zero deselected.

Parecer independente do Architect sobre o delta: PREP12-01/02 têm novas provas E/F para redirects 301/302/303/307/308 nos workflows, ambiente proxy/netrc hostil e Digest→307, sem defeito novo; permanecem para reavaliação formal, sem `CLEARED` nesta atualização. PREP12-04 demonstra deadline da cadeia, fila MULTI e fila RTSP que esgota budget antes do handshake (TIMEOUT, zero open). PREP12-05 tem evidência offline completa pela ficha de cancelamento dentro da fila RTSP e vendor/chunks/handshake/frame/close anteriores, sem defeito novo. PREP12-04/05 têm evidência offline completa pendente de aceite formal e não são marcados `CLEARED`. Gate V formal continua pendente por um skip.

**Atualização da tentativa PREP12-10:** worktree `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_pre_p12_remediation`, branch `feature/pre-p12-unified-remediation`, HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e` confirmados. Python 3.14.0 AMD64. O venv isolado novo `_tmp_PREP12_10_venv_f7619b781f1b49719a7d236faa951a7d/resolver-venv` foi validado e pip 25.2 bootstrapped. `PIP_NO_INDEX=1`, herdado, impediu consultas a índices: `pip index` mostrou zero versões locais e `pip install pip-tools` não encontrou pacote. Nenhuma configuração foi removida/sobrescrita; nenhuma ferramenta ou dependência do produto foi instalada; não houve geração de lock/hash nem reprodução de ambiente/testes. O bloqueio atual é índice inacessível pela política/configuração efetiva, não evidência de ausência/incompatibilidade de `av==19.0.1`; PyPI oferece wheel `cp312-abi3 win_amd64` e SHA já registrado. A estratégia documental corrigida limita execução futura à área temporária da atividade, resolvedor separado e segundo venv limpo com requirements hasheado; não foi executada. PREP12-10 = `PENDING_VALIDATION/OPEN`.

PREP12-11 segue OPEN_CONDITIONAL: retenção, arquivo bloqueado e redação passaram em filesystem Windows real; symlink real foi SKIPPED (WinError 1314). PREP12-09 segue DEFERRED_BY_CONTRACT ao build P12. PREP12-03/06/07/08/12/13/14 permanecem CLEARED conforme checkpoint anterior, sem reabertura. Nenhuma câmera, build P12 ou Git write; temporários, untracked e `docs/continuity.zip` foram preservados.

Próximo gate: ambiente autorizado com índice permitido ou wheelhouse aprovado; gerar locks com hashes, reproduzir em ambiente limpo, executar checks e obter revisão Architect. Também executar teste real de symlink em Windows autorizado com capacidade de criação; depois regressão integral sem skip e nova avaliação formal. P12_READINESS=BLOCKED; ACTIVITY_COMPLETE=NO; progresso 96%.

~~~text
EVIDENCE_SOURCE = AGENT_EXECUTED_AUTHORIZED_WINDOWS_POWERSHELL
PYTHON = 3.14.0 (validated executable: C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner\.venv\Scripts\python.exe)
IMPORT_CAM_SCANNER = TARGET_WORKTREE
FULL_PYTEST = 372 PASSED, 0 FAILED, 1 SKIPPED, 0 DESELECTED, 0 XFAILED (111.06s)
PYTEST_HARNESS = TMPDIR_AND_CACHEPROVIDER_DISABLED_ONLY; UNIQUE_TMP_PATH_PER_TEST_UNDER_PRESERVED_DIRECTORY
SYMLINK_TEST = SKIPPED (WinError 1314; no elevation)
FOCUSED_RTSP_QUEUE = 2 PASSED, 12 DESELECTED (focused filter only)
RUFF_SRC_TESTS = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS (LF/CRLF warnings only)
ARCHITECT_DELTA_REVIEW = NO_NEW_DEFECT; PREP12_01_02_04_05_EVIDENCE_COMPLETE_PENDING_GLOBAL_GATE_FORMALITY
PREP12_01_02 = OPEN_PENDING_FORMAL_REASSESSMENT (new E/F evidence complete; no auto-clear)
PREP12_04_05 = EVIDENCE_COMPLETE_PENDING_FORMAL_ACCEPTANCE (not CLEARED)
PREP12_03_06_07_08_12_13_14 = CLEARED (preserved; no reopening)
PREP12_09 = DEFERRED_BY_CONTRACT
PREP12_10 = PENDING_VALIDATION/OPEN (inherited PIP_NO_INDEX=1 blocked index; no lock/hash/reproduction/install)
PREP12_11 = OPEN_CONDITIONAL (symlink skipped: WinError 1314)
GATE_V = NOT_MET (one skipped)
P12_READINESS = BLOCKED
ACTIVITY_COMPLETION_PERCENT = 96%
ACTIVITY_COMPLETE = NO
PREP12_10_ATTEMPT = NEW_ISOLATED_VENV_VALIDATED; PIP_25.2_BOOTSTRAPPED; INDEX_ACCESS_BLOCKED; NO_PRODUCT_INSTALL; NO_LOCK_HASH_OR_REPRODUCTION
NEXT_GATE = AUTHORIZED_INDEX_OR_APPROVED_WHEELHOUSE; LOCK_HASH_GENERATION; CLEAN_REPRODUCTION_AND_CHECKS; ARCHITECT_REVIEW; REAL_WINDOWS_SYMLINK_TEST; ZERO_SKIP_FULL_REGRESSION; FORMAL_READINESS_REASSESSMENT
~~~

## PRE-P12 — regressão e revisão final de aceite (2026-10-16; vigente)

Esta atualização supersede o checkpoint 96% abaixo; checkpoints anteriores permanecem preservados como histórico. Evidência fornecida pelo usuário, origem Windows PowerShell local autorizado: Python 3.14.0; pytest 346 passed, 0 failed, 1 skipped em 30.11s; Ruff, `pip check` e `git diff --check` PASS. O Scribe não executou esses checks. ONVIF Zeep apresentou anteriormente falha intermitente `ConnectionAbortedError/WinError 10053`, mas passou isoladamente e na full run mais recente. O último resultado não mostra falha persistente; a causa da intermitência é desconhecida.

Architect independente: `FINDINGS_STATUS=OPEN_ACCEPTANCE_GAPS`, `P12_READINESS=BLOCKED`; nenhuma nova falha material de runtime nem novo `CLEARED` baseado só na contagem. Pelo contrato §12/§14, GATE_V requer suíte completa Python 3.14 sem falha, skipped ou deselected. Logo 346/0/1 é execução concluída com um skipped, mas V/GATE_2 permanece `NOT_MET`.

PREP12-01 = `OPEN_ACCEPTANCE` (HIGH inalterada): HTTPS real Zeep/Requests, preauth/inventory/snapshot em SINGLE/MULTI, TLS inválido sem downgrade, recursos e 14 campos têm evidência favorável. Lacunas E/F: somente redirect 302 exercitado; não encontrados 301/303/307/308 ou redirect em replay Digest; proxy/netrc/credenciais ambientais hostis não foram efetivamente configurados em teste, embora `trust_env=False` e proxies limpos sejam inspecionados/assertados. PREP12-02 = `OPEN_ACCEPTANCE`: snapshot HTTPS/no-downgrade e endpoints allowlist cobertos, mas matriz 30x incompleta deixa critério E pendente.

PREP12-04 = `OPEN_PARTIAL_ACCEPTANCE`: deadline compartilhado por câmera, expiração no preauth, fila de executor + inventory/snapshot e bloqueio de envio RTSP após expiração cobertos; falta cadeia completa preauth→vendor→fallback→snapshot/RTSP e fila/handshake RTSP. `rtsp.py` mantém `_RTSP_CAPTURE_ENABLED=False`; fail-closed não comprova fila/handshake/frame ativo. PREP12-05 = `OPEN_PARTIAL_ACCEPTANCE`: cobertos cancelamento de preauth/inventory, provider/processamento de snapshot, MULTI futures ativos/pendentes, fechamento, preservação de resultados completos/parciais e ausência de export de lote cancelado; faltam vendor, chunks e fila RTSP ativa. Estas lacunas não são bugs de runtime comprovados.

PREP12-10 = `OPEN`, sem lock transitivo/hashes/reprodução limpa; há estratégia e `requirements/locks/windows-py314.in`, mas resolução anterior falhou porque o índice não ofereceu `av==19.0.1`; nenhuma instalação ocorreu. PREP12-11 = `OPEN_CONDITIONAL`: rollover/retenção, arquivo bloqueado e sentinelas username/password passaram em filesystem Windows real; symlink real foi `SKIPPED` por WinError 1314. PREP12-09 = `DEFERRED_BY_CONTRACT` ao build P12. PREP12-03/06/07/08/12/13/14 permanecem `CLEARED`, sem reabertura; PREP12-13 segue offline e homologação real é separada.

Rastreabilidade: `tests/test_pre_p12_transport_integration.py` (HTTPS SINGLE/MULTI, matriz 302, TLS/endpoints), `tests/test_pre_p12_budget_acceptance.py` (budget/cancel), `tests/test_target_transport.py`, `tests/test_logging_setup.py`. Próximo gate: `COMPLETE_TARGETED_ACCEPTANCE_EVIDENCE → ZERO_SKIP_FULL_REGRESSION_V → INDEPENDENT_SECURITY_ACCEPTANCE → READINESS_REASSESSMENT`. PREP12-01/02 impedem início de P12; 10/11 fazem parte do pacote e impedem conclusão da remediação; 09 continua diferido.

~~~text
EVIDENCE_SOURCE = USER_PROVIDED_AUTHORIZED_LOCAL_WINDOWS_POWERSHELL
PYTHON = 3.14.0
FULL_PYTEST = 346 PASSED, 0 FAILED, 1 SKIPPED (30.11s)
ONVIF_ZEEP = PRIOR_INTERMITTENT_CONNECTIONABORTEDERROR_WINERROR_10053; PASSED_ISOLATED_AND_LATEST_FULL_RUN; CAUSE_UNKNOWN; NO_PERSISTENT_CURRENT_FAILURE_SHOWN
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS (user-provided run)
ARCHITECT_REVIEW = OPEN_ACCEPTANCE_GAPS; NO_NEW_MATERIAL_RUNTIME_FAILURE
GATE_V = NOT_MET (zero failures/skips/deselected required)
ACTIVITY_COMPLETION_PERCENT = 96%
ACTIVITY_COMPLETE = NO
P12_READINESS = BLOCKED
PROJECT_STATE_UPDATE = PASS
~~~

## PRE-P12 — retomada de aceites direcionados (2026-10-16)

Este registro supersede o checkpoint 92% abaixo. O gate do workspace passou no worktree alvo (`feature/pre-p12-unified-remediation`, HEAD publicado `37bc8c4cc718559fc1e6f39a9b8a1145563a551e`). Alterações locais e arquivos não rastreados foram preservados; não houve operação Git destrutiva, stage, commit ou push.

PREP12-01/02 têm evidência comportamental direta: HTTPS do produto com preauth nos workflows SINGLE e MULTI e seis cenários negativos em ambos, cobrindo TLS e redirect de preauth, endpoint Media não aprovado, snapshot URI não aprovado, redirect de snapshot e TLS de snapshot. As invocações diretas passaram. A revisão final Architect Sol/High foi favorável ao delta sem defeito material novo. O aceite formal V continua pendente.

PREP12-04 demonstra por invocação direta um deadline único por câmera persistente na fila, inventário e snapshot, sem iniciar RTSP depois da expiração. PREP12-05 corrigiu cancelamento no limite de `InventoryService`, prioridade de cancelamento em `SnapshotService` e encerramento/drain de futures em `MultiWorkflow`; preserva resultados concluídos/parciais e não exporta workbook de lote incompleto após cancelamento. `tests/test_pre_p12_budget_acceptance.py` teve 8 passed. Architect Sol/High revisou o novo delta sem encontrar defeito material.

PREP12-11: retenção/rollover, arquivo bloqueado e ausência de username/password-sentinela foram exercitados em filesystem Windows real e passaram. A tentativa de symlink real pulou com WinError 1314; o finding fica OPEN. PREP12-10 permanece OPEN: há estratégia e entrada candidata `requirements/locks/windows-py314.in`, mas `pip lock` não gerou lock com hashes porque o índice disponível/restrito não ofereceu `av==19.0.1`; nenhuma dependência foi instalada.

Python 3.14.0 foi confirmado no executável validado. A suíte inteira pós-delta não concluiu devido a WinError 5 em basetemp/fixtures. A baseline histórica de 325 passed não foi repetida e não valida este delta. Ruff, compileall, `pip check` e `git diff --check` passaram. PREP12-03/06/07/08/12/13/14 permanecem CLEARED; PREP12-09 permanece `DEFERRED_BY_CONTRACT`. PREP12-10/11 permanecem OPEN, e o gate V/formal não foi aprovado. P12_READINESS=BLOCKED; ACTIVITY_COMPLETE=NO.

~~~text
PREP12_01_02 = DIRECT_BEHAVIORAL_EVIDENCE_PASS; FORMAL_V_ACCEPTANCE_PENDING
PREP12_04 = DIRECT_INTEGRATED_DEADLINE_EVIDENCE_PASS
PREP12_05 = FOCUSED_PYTEST_PASS (8 passed); ARCHITECT_REVIEW = FAVORABLE
PREP12_10 = OPEN (lock/hash unavailable; restricted index lacks av==19.0.1)
PREP12_11 = OPEN (real symlink skipped: WinError 1314)
FULL_PYTEST = NOT_COMPLETED (post-delta WinError 5)
HISTORICAL_BASELINE = 325 PASSED (not repeated)
RUFF = PASS
COMPILEALL = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
P12_READINESS = BLOCKED
ACTIVITY_COMPLETE = NO
~~~

## PRE-P12 — revisão final direcionada após regressão local (2026-10-16; checkpoint 92%)

Esta atualização supersede o checkpoint 88% logo abaixo. O usuário informou regressão completa em Windows PowerShell local autorizado, Python 3.14.0: 325 passed em 8.88s; Ruff full PASS com I001 corrigido; `pip check` e `git diff --check` PASS. A origem é evidência fornecida pelo usuário. Contagens de failed/errors/skipped/deselected/xfail não foram informadas. O Scribe não executou esses checks.

O Architect concluiu revisão direcionada com `REVIEW=FINDINGS`, devido a lacunas de aceite, sem confirmar novo defeito material. PREP12-01 permanece OPEN: HTTPS Zeep/Requests + SnapshotService usa CA local restrita e `verify=True`, mas context/auth são preparados manualmente; falta preauth real por HTTPS em SINGLE/MULTI, cujos fluxos reais atuais usam HTTP e `EmptyDiscovery`. PREP12-02 está OPEN/PARTIAL: teste negativo verifica TLS_ERROR, tentativa única, `context.tls_failed` e zero HTTP vendor/RTSP; integração e matriz completa faltam. PREP12-04 segue OPEN: fake clock demonstra expiração no preauth e bloqueio de vendor/ONVIF, mas falta cadeia integrada até snapshot/RTSP/fila e deadline persistente entre clientes. PREP12-05 segue OPEN: cancelamento SINGLE após preauth impede aquisição/snapshot e fecha resource; faltam cancelamento durante vendor/ONVIF/chunks, fila e MULTI futures/export; decoder RTSP está fail-closed/desativado. PREP12-11 segue OPEN/CONDITIONAL: rollover, backupCount, RUN_ID, byte cap e retention em tmp_path; PermissionError e symlink são simulados com mocks, sem validação do filesystem Windows real. PREP12-10 continua OPEN por ausência de lock integral, hashes e reprodução limpa; `setuptools>=75` e `wheel` não estão fixados, e pip check no venv reutilizado não substitui essas provas.

PREP12-03 permanece CLEARED, sem regressão observada; PREP12-09 permanece DEFERRED_BY_CONTRACT. PREP12-06/07/08/12/13/14 continuam CLEARED segundo a revisão. Atividade incompleta, 92%; P12_READINESS=BLOCKED pelos findings e aceites pendentes. Próximo gate: HTTPS preauth real em SINGLE/MULTI e matriz negativa; ampliar aceites 04/05; validar filesystem Windows para 11; decidir e autorizar artefatos de lock/hashes/reprodução.

~~~text
EVIDENCE_SOURCE = USER_PROVIDED_AUTHORIZED_LOCAL_WINDOWS_POWERSHELL
PYTHON = 3.14.0
FULL_PYTEST = 325 PASSED (8.88s)
FAILED_ERRORS_SKIPPED_DESELECTED_XFAIL = NOT_REPORTED
RUFF_FULL = PASS (I001 corrected)
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
ARCHITECT_REVIEW = FINDINGS (acceptance gaps; no new material defect confirmed)
ACTIVITY_COMPLETION_PERCENT = 92%
P12_READINESS = BLOCKED
ACTIVITY_COMPLETE = NO
~~~

## PRE-P12 — targeted security fix and acceptance (2026-10-16; checkpoint 88%)

Este checkpoint supersede o registro de 2026-10-15 abaixo, sem apagar o histórico. As correções direcionadas TLS, teste negativo, teste de transporte HTTPS local offline e testes de logging para arquivo bloqueado/symlink foram escritos. Sua execução pytest não foi concluída com resumo: a tentativa focada apresentou F/E parciais e falhou ao limpar `--basetemp` com `PermissionError: [WinError 5]` em `cleanup_dead_symlinks/root.iterdir/os.scandir`. Contagens exatas de passed, failed, errors, skipped, deselected e xfailed indisponíveis. Não repetir nem contornar pytest no sandbox atual. O baseline reportado anteriormente de 318 passed não valida o delta atual.

Ruff 0.16.10 = PASS; `pip check` = PASS no venv Python 3.14 existente, sem instalar; `git diff --check` = PASS, com avisos LF/CRLF apenas. A revisão estática do Architect não confirmou novo defeito no delta, mas PREP12-01/02 continuam abertos enquanto faltam execução confiável, fluxo integrado SINGLE/MULTI com preauth e matriz negativa completa. PREP12-04/05 ainda carecem de evidência integrada de budget e cancelamento por fase/lote/espera cooperativa RTSP. PREP12-10 permanece aberto sem lock transitivo, hashes, tooling totalmente fixado e reprodução limpa. PREP12-11 tem testes com mocks para `PermissionError` e symlink ainda não executados; comportamento real em filesystem Windows não foi demonstrado, embora `backupCount >= 1` já tenha cobertura.

**Atualização Ruff após o adendo de testes:** o resultado PASS acima precede a inclusão de `tests/test_pre_p12_budget_acceptance.py`. Ruff no conjunto focado reportou `I001` nesse arquivo; o estado atual é `FAIL/PENDING_FIX`. `ruff --fix` retornou `E902/WinError 5` ao escrever no worktree alvo. Nenhum outro método de escrita foi tentado para contornar o erro, ACL não foi alterada e pytest não foi repetido. `git diff --check` permanece PASS, com avisos LF/CRLF apenas.

PREP12-03/06/07/08/12/13/14 permanecem CLEARED por ausência de regressão demonstrada; PREP12-09 permanece DEFERRED_BY_CONTRACT. HEAD continua `37bc8c4cc718559fc1e6f39a9b8a1145563a551e` na branch `feature/pre-p12-unified-remediation`. P12 segue BLOCKED, atividade não completa e progresso mantido em 88%. Nenhuma câmera real, build P12, instalação de dependências ou operação Git de publicação foi executada. Arquivos não rastreados e diretórios `.validator-tmp-*` foram preservados.

Adendo: foi acrescentado `tests/test_pre_p12_budget_acceptance.py` com dois testes offline em nível de aplicação para interrupção da aquisição por budget por câmera expirado, cancelamento cooperativo interrompendo aquisição/snapshot e fechamento de recursos por `SingleWorkflow`. A suíte continua sem execução conclusiva; esses testes não foram executados e não alteram o estado de aceite PREP12-04/05.

~~~text
ACTIVITY = PRE_P12_UNIFIED_REMEDIATION / TARGETED_SECURITY_FIX_AND_ACCEPTANCE
ACTIVITY_COMPLETION_PERCENT = 88% (mantido)
ACTIVITY_STATUS = BLOCKED_ON_VALIDATION_AND_OPEN_ACCEPTANCE
TEST_EXECUTION = INCOMPLETE (partial F/E; WinError 5 during pytest basetemp cleanup; no summary/counts)
FULL_PYTEST = NOT_COMPLETED
RUFF = PASS (0.16.10)
PIP_CHECK = PASS (existing Python 3.14 venv; no installation)
GIT_DIFF_CHECK = PASS (LF/CRLF warnings only)
ARCHITECT_DELTA_REVIEW = NO_NEW_CONFIRMED_DEFECT; acceptance gaps remain
PREP12_01_02_04_05_10_11 = OPEN
PREP12_03_06_07_08_12_13_14 = CLEARED (no regression demonstrated)
PREP12_09 = DEFERRED_BY_CONTRACT
P12_READINESS = BLOCKED
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
ACTIVITY_COMPLETE = NO
NEXT_GATE = AUTHORIZED_WINDOWS_TEST_EXECUTION_AND_REASSESSMENT
~~~

## PRE-P12 Unified Remediation — revisão após regressão Windows (2026-10-15; checkpoint 88%)

O contrato foi aprovado com ajustes e a autorização segue limitada à remediação offline. A atividade continua aberta. A revisão atualiza o checkpoint anterior de 84% após os resultados de regressão fornecidos pelo usuário e a revisão independente do Architect. O snapshot factual e a matriz dos 14 findings estão em [PROJECT_STATE.md](PROJECT_STATE.md).

O usuário informou que uma execução autorizada em Windows PowerShell, Python 3.14.0, passou a importar o worktree correto, enumerar os.scandir e usar o ambiente temporário; 115 testes focados passaram em 9.20s e 318 testes completos passaram em 8.51s. Ruff, pip check e git diff check também foram reportados como PASS. Esses resultados são evidência fornecida pelo usuário; Root e Architect não executaram os testes nesta revisão. A comunicação recebida não detalha separadamente skipped/deselected nem inclui logs/manifesto de execução.

A revisão direcionada do Architect encontrou PREP12-01/02 ainda sem integração real de HTTPS confiável. Confirmou também defeito em PREP12-02: SSLError nos providers de snapshot é classificado como erro de rede, permitindo continuação do fallback; com regra HTTP vendor explícita, pode ocorrer tentativa HTTP após falha TLS. Correção proposta, ainda não implementada: distinguir TLS de erro de rede, parar o fallback nessa condição e testar que uma falha de certificado não gera requisição HTTP.

Estado final da matriz: sete CLEARED (03, 06, 07, 08, 12, 13, 14), seis OPEN (01, 02, 04, 05, 10, 11), e um DEFERRED_BY_CONTRACT (09). PREP12-03 passou no aceite offline por ledger, Digest/401/403 e integração SINGLE/MULTI 401. PREP12-04/05 ainda carecem do teste integrado completo de budget/cancelamento, particularmente envolvendo espera RTSP. PREP12-10 carece lock transitivo/hashes e reprodução em ambiente limpo. PREP12-11 carece dos cenários de log anterior bloqueado e symlink expressamente previstos no contrato. PREP12-13 está aceito somente no estágio offline; homologação com câmeras/modelos reais continua separada.

PyAV RTSP segue fail-closed antes do decoder, pois o controle atual não autoriza cada conexão de redirect/SDP. PREP12-09 não foi validado por build: preparar paths/recursos offline é distinto do build e smoke ONEDIR, que pertencem à P12 e permanecem não executados. P12_READINESS = BLOCKED; nenhum teste com câmera real, build P12 ou instalação/atualização de dependências foi feito. Não houve stage, commit ou push; a publicação Git continua não autorizada. Artefatos não rastreados e diretórios temporários foram preservados.

~~~text
ACTIVITY = PRE_P12_UNIFIED_REMEDIATION
ACTIVITY_COMPLETION_PERCENT = 88%
ACTIVITY_STATUS = BLOCKED_ON_OPEN_ACCEPTANCE
EVIDENCE_SOURCE = USER_PROVIDED_LOCAL_WINDOWS_POWERSHELL
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
ROOT_OR_ARCHITECT_TEST_EXECUTION = NONE
ARCHITECT_FINAL_REVIEW = COMPLETED_WITH_FINDINGS
ALL_14_FINDINGS = 7_CLEARED; 6_OPEN; 1_DEFERRED_BY_CONTRACT
PREP12_01 = OPEN
PREP12_02 = OPEN; CONFIRMED_TLS_FALLBACK_DEFECT
PREP12_03 = CLEARED
PREP12_04 = OPEN
PREP12_05 = OPEN
PREP12_06 = CLEARED
PREP12_07 = CLEARED
PREP12_08 = CLEARED
PREP12_09 = DEFERRED_BY_CONTRACT (P12_BUILD_NOT_RUN)
PREP12_10 = OPEN
PREP12_11 = OPEN
PREP12_12 = CLEARED
PREP12_13 = CLEARED_OFFLINE; REAL_CAMERA_HOMOLOGATION_SEPARATE
PREP12_14 = CLEARED
RTSP_PYAV_CAPTURE = CLOSED_FOR_SECURITY
P12_READINESS = BLOCKED
REAL_CAMERA_VALIDATION = NOT_RUN
P12_BUILD = NOT_RUN
DEPENDENCY_CHANGES = NONE
GIT_PUBLICATION = NOT_AUTHORIZED; NOT_PERFORMED
STAGE_COMMIT_PUSH = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
ACTIVITY_COMPLETE = NO
NEXT_GATE = TARGETED_PREP12_02_TLS_FIX_AND_NEGATIVE_TEST; COMPLETE_REMAINING_OPEN_ACCEPTANCE; REASSESS_P12
STATUS = BLOCKED
~~~

## BLOCO B — Final Hardening (2026-10-14)

O adapter Hikvision agora chama somente `https://<IP>/ISAPI/System/deviceInfo`, valida o certificado (`verify=True`), mantém Digest limitado, `trust_env=False` e redirects desativados. Não há fallback para HTTP. Testes offline confirmam challenge Digest, endpoint, scheme, IPv6, TLS error sanitizado e ausência de downgrade. Dispositivos com certificados autoassinados/não confiáveis falharão fechado; CA/pinning não foi configurado por esta atividade.

Os adapters vendor mantêm budget cumulativo monotônico de 10 s; cada requisição começa com o menor timeout entre connect/read e o restante do budget. A leitura limitada verifica o prazo entre chunks e antes do parse; Dahua não inicia o segundo GET se o prazo esgotar. O deadline é soft: uma chamada já bloqueada pode aguardar até o timeout de rede retornar, conforme o contrato, sem thread adicional ou promessa de cancelamento imediato.

Validação final em Python 3.14.0: 220 testes aprovados, zero falhas e zero ignorados; Ruff, `pip check` e `git diff --check` aprovados. O fixture `tmp_path` foi redirecionado para a raiz autorizada de visualizações porque o sandbox bloqueia o diretório temporário padrão. Não houve câmera real, mudança de dependência, stage, commit ou push. O manifesto explícito do checkpoint está em [`BLOCO_B_FINAL_HARDENING_MANIFEST.md`](BLOCO_B_FINAL_HARDENING_MANIFEST.md); artefatos gerados/privados ficam fora dele.

```text
ACTIVITY = BLOCO_B_FINAL_HARDENING
HIKVISION_TRANSPORT_D04 = PASS
VENDOR_BUDGET = PASS_WITH_SOFT_DEADLINE
SECURITY_REGRESSION = PASS
PYTEST = PASS (220 passed; 0 failed; 0 skipped; Python 3.14.0)
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
CHECKPOINT_READY = YES
GIT_ADD_COMMIT_PUSH = NONE
REAL_CAMERA_VALIDATION = NOT_RUN
P2_STATUS = IN_PROGRESS
NEXT_GATE = USER_APPROVAL_FOR_BLOCO_B_PUBLICATION
STATUS = COMPLETED_WITH_LIMITATION
```

## BLOCO B — Multiagent Vendor Expansion (2026-10-14)

O Card A autorizou implementação, integração e validação offline no worktree `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_bloco_b`, branch `feature/bloco-b-vendors`, sobre a baseline `a5c8445e0262a82cc8d6a3d627f2066223203f09`. O checkout original e worktrees anteriores foram preservados. A composição de produção agora registra Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic/i-PRO e Bosch; o registry vazio padrão continua disponível para consumidores e testes. Bosch registra tentativa não suportada sem I/O e segue para o fallback ONVIF.

Os adapters novos executam apenas operações de leitura fundamentadas, usam as credenciais do alvo, não seguem redirects, desativam `trust_env`, validam TLS e não fazem downgrade. Axis implementa VAPIX Basic Device Information. Hanwha implementa SUNAPI `deviceinfo`, sem inferir fabricante quando ausente no payload. Dahua obtém modelo/serial via `getSystemInfo` e fabricante via `getVendor`, sem leitura separada de firmware. Panasonic/i-PRO obtém modelo/serial/firmware via `getinfo` na família H.265 documentada; não inventa fabricante. Bosch permanece sem coleta nativa porque a fonte Bosch consultada não documenta operação mínima para fabricante/modelo/serial. Hikvision ISAPI não foi reconstruído; permanece o adapter existente, cuja limitação de HTTP fixo é anterior a este bloco.

A revisão independente READ_ONLY encontrou e o integrador corrigiu: proveniência HTTPS registrada como HTTP; falta de budget cumulativo durante leitura; aliases exatos de fabricante que não chegavam ao registry; e rejeição de wrappers `<HTML>` documentados pelo i-PRO. O único risco residual revisado é LOW: o deadline de 10 segundos é soft, pois `iter_content` pode bloquear até o timeout de rede retornar; não se promete interrupção rígida de thread.

Validação acumulada em Python 3.14.0: `pytest -q -rs` com fixture `tmp_path` direcionado à raiz de visualizações autorizada (o sandbox bloqueia criação/leitura do diretório temporário padrão): 217 aprovados, nenhum falho ou ignorado. A regressão inclui P1, segurança P2-I1, Hikvision P2-I2, snapshots P3, MULTI/XLSX P4 e concorrência P5. Ruff, `pip check` e `git diff --check` passaram. Nenhuma câmera real foi consultada; não houve alteração de dependências nem escrita Git de publicação.

```text
ACTIVITY = BLOCO_B_MULTIAGENT_VENDOR_EXPANSION
BASELINE = a5c8445e0262a82cc8d6a3d627f2066223203f09
WORKTREE = C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_bloco_b
BRANCH = feature/bloco-b-vendors
AGENTS_A_B_C = IMPLEMENTATION_HANDOFFS_RECEIVED
AGENT_D = INDEPENDENT_READ_ONLY_REVIEW_PASS_WITH_LOW_LIMITATION
PYTEST = PASS (217 passed; 0 failed; 0 skipped; Python 3.14.0)
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
REAL_CAMERA_VALIDATION = NOT_RUN
PHASE_CLOSURE = NONE (P2/P3/P4 continuam abertas; P6–P11 não homologadas)
GIT_ADD_COMMIT_PUSH = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
ACTIVITY_COMPLETE = YES (escopo offline autorizado)
NEXT_GATE = USER_APPROVAL_FOR_BLOCO_B_CHECKPOINT
STATUS = COMPLETED_WITH_LIMITATIONS
```

## Histórico de atividades

- **P5_CONCURRENCY_IMPLEMENTATION — COMPLETED (offline):** `feature/p5-concurrency` sobre baseline `53034e0`; ThreadPoolExecutor limitado a 1–32 workers (padrão 8), resultados ordenados, falhas isoladas e semáforo RTSP global limitado a uma captura. Python 3.14.0: 184 testes, Ruff, pip check e diff check passaram. Benchmark sintético: 64 câmeras; 1,0016 s com 1 worker e 0,1274 s com 8 (7,86× observado). Câmeras reais não testadas; stage/commit/push não executados. Próximo gate: aprovação do usuário para checkpoint Git P5.
- **P0-A01 — COMPLETED_WITH_FINDINGS:** persistência inicial da Engineering Foundation e scaffold governado. Não atribuir a esta atividade a validação do binding Continuity 3.0 feita posteriormente.
- **P0-A02 — BLOCKED_FOR_FORMAL_CLOSURE / CHANGES_REQUIRED:** Foundation Review executada; findings F-01…F-08. Recomendação de aprovação: `DO_NOT_APPROVE_YET`; Foundation Approval não concedida; Project Opening Gate não pronto.
- **P0-A03 — COMPLETED_WITH_FINDINGS:** aplicou as decisões posteriores do usuário, reconciliou os fatos e preparou a Foundation para recheck. Não converte retroativamente P0-A02 em PASS.
- **P0-A03-G1 — COMPLETED_WITH_FINDINGS:** publicou o primeiro checkpoint governado em `origin/master`; commit inicial `chore(project): establish governed foundation baseline`, seguido por commit documental de continuidade. Sem implementação funcional, force push, tag ou release.
- **P1-A04 — COMPLETED_WITH_FINDINGS:** adaptou e validou sinteticamente o fluxo SINGLE para `VENDOR_FIRST_WHEN_KNOWN`.
- **P1-CHECKPOINT-01 — COMPLETED_WITH_FINDINGS:** reconciliou P1-A05, fechou P1 e publicou o checkpoint em `origin/master`; HEAD local e remoto coincidem. P2 segue sem autorização de implementação.
- **ARCH-ALIGN-01 — COMPLETED_WITH_FINDINGS:** registrou `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE` como direção aprovada para P2; P1 e sua estratégia implementada permanecem baseline histórica válida; P2-A01 é a próxima atividade e sua implementação não está autorizada.
- **P2-A01 — COMPLETED_WITH_FINDINGS:** contrato proposto foi criado e revisado; decisões materiais D01–D06 aguardam aprovação humana; P2 implementation permanece não autorizada.
- **P2-A01-R1 — COMPLETED:** aprovação humana D01–D06 formalizada no contrato em 2026-10-09 e continuidade reconciliada; implementação P2 permanece não autorizada.

## Decisões e evidências aplicáveis

- F-01: Python 3.14.x permanece baseline; validação operacional 3.14.x é exigida antes de P1 fechar.
- F-02: root WORK ausente e HOME ativo descreviam o ambiente da P0-A03; P0-A04 confirma WORK existente e ativo neste computador.
- F-03: na P0-A03, repositório existia sem commits/HEAD; P0-A03-G1 publicou dois commits. P0-A04 confirmou `master` e HEAD válido; não há escrita Git nesta review.
- F-04: binding Continuity 3.0 validado na P0-A02 com PowerShell `Test-Json -Schema` contra o schema canônico. Não atribuir essa evidência à P0-A01.
- F-05: roadmap é P0–P12 conforme [`planning/ROADMAP.md`](planning/ROADMAP.md); P3 snapshot não gera XLSX; P4 primeiro fluxo com MULTI + XLSX + snapshot embedded.
- F-06: `CameraResult` contém somente campos explicitamente tipados/aprovados, sem senha e sem extension bag arbitrário.
- F-07: P1 é SINGLE Minimum Vertical Slice, com critérios completos em [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md); planejada não significa autorizada.
- F-08: expansão de `build.ps1` está aceita e deferida a P12: TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER.

Decisões e evidências da P0-A03 não alteram silenciosamente authorities externas. O checkpoint P0-A03-G1 consumiu a autorização explícita de stage/commit/push desta atividade; novas escritas Git e implementação funcional permanecem sem autorização.

## Baseline, riscos e retomada

O baseline integrado contém a slice SINGLE implementada sob `VENDOR_FIRST_WHEN_KNOWN`. P1-A05 confirmou descoberta pré-auth READ_ONLY e fabricante Hikvision; coleta autenticada falhou com `AUTH_ERROR`, mas a evidência foi preservada como `PARTIAL_SUCCESS`, conforme o contrato reconciliado. P1 e P0 estão fechadas. ARCH-ALIGN-01 aprovou documentalmente a direção híbrida para evolução após P1. O contrato P2 foi aprovado em 2026-10-09; a fase P2 permanece aberta e a implementação não está autorizada. O HEAD local de entrada de P2-A01 foi `d8d2d02c9a659391fd80a7b4590f6767ab625cba`, igual a `origin/master` na entrada. Nenhuma credencial foi persistida.

## P2-A01 — Hybrid Collection Architecture Contract (2026-10-09; estado inicial antes da aprovação, supersedido por P2-A01-R1)

O contrato [`../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`](../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md) materializa a direção híbrida aprovada sem reabrir P1. A auditoria original continua inalterada e é a fonte de evidências F01–F12. F01 (preservação), F02 (fingerprint determinístico) e F03 (diagnóstico por operação) estão contratados. F01–F03 são critérios para implementação futura, não mudanças realizadas.

Decisões materiais D01–D06 — perfil mínimo de identidade, domínio tipado, limite/fallback de auth, TLS/destinos, PoC ISAPI e resolução/conflito de fabricante — estão como propostas pendentes de aprovação. D07 (retomada abrupta de lote) foi diferida por não ser material para P2-A01/SINGLE. `ONVIF_DIGEST_ROOT_CAUSE` continua `UNDETERMINED`; a política não declara Digest corrigido. P2 permanece `NOT_GRANTED` para implementação. P3–P12 permanecem intactas.

```text
PROJECT = projeto_cam_scanner
ACTIVITY = P2-A01
STARTING_HEAD = d8d2d02c9a659391fd80a7b4590f6767ab625cba
CONTRACT_PATH = docs/contracts/P2_COLLECTION_STRATEGY_EXPANSION.md
CONTRACT_STATUS = PENDING_APPROVAL
P1_STATUS = CLOSED
P1_REOPEN = NO
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
DEPENDENCY_CHANGES = NONE
REAL_CAMERA_CALLS = NONE
GIT_WRITES = NONE
NEXT_ACTIVITY = USER REVIEW / APPROVAL OF P2-A01 CONTRACT
SAFE_RESUME_POINT = Review D01-D06; no implementation until separate approval
```

## P2-A01-R1 — Reconciliation of Human Contract Approval (2026-10-09)

O usuário aprovou D01 como `APPROVED_WITH_REVISION` e D02–D06 como `APPROVED_WITH_ADJUSTMENTS`; D00 já estava aprovada. O contrato foi atualizado em todas as seções afetadas: perfil e sucesso `IDENTITY_V1`, fallback, coleta complementar, domínio e proveniência, casos A–G, PoC ISAPI, critérios T01–T15 e encerramento. Firmware permanece complementar; `SUCCESS` requer fabricante confirmado, modelo e serial number válidos e ausência de conflito material. F01–F03 e o histórico P1 foram preservados. D07 continua diferida. P0/P1 permanecem fechadas, P2 continua aberta e implementação não autorizada.

```text
ACTIVITY = P2 CONTRACT APPROVAL RECONCILIATION
CONTRACT_STATUS = APPROVED
DECISIONS_D01_D06 = APPROVED
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
P1_STATUS = CLOSED
P0_STATUS = CLOSED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
REAL_CAMERA_CALLS = NONE
GIT_WRITES = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_STATUS = PASS_WITH_FINDINGS (external governance sibling paths unavailable in this checkout)
SAFE_RESUME_POINT = P2 planning; any implementation needs separate explicit authority
```

**Safe resume point histórico (antes de P0-A04):** conferir [`PROJECT_STATE.md`](PROJECT_STATE.md) e [`handoff/LAST_HANDOFF.md`](handoff/LAST_HANDOFF.md), revalidar estado Git atual e executar o recheck Foundation conforme authority aplicável. O estado corrente está registrado abaixo.

## ARCH-ALIGN-01 — Documentary Architecture Reconciliation (2026-10-08)

A direção aprovada para evolução após P1 é `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`. A auditoria independente permanece preservada em [`../audit/ARCH_AUDIT_01_REPORT.md`](../audit/ARCH_AUDIT_01_REPORT.md) e é a fonte dos achados F01–F12. O roadmap registra o destino e o execution plan registra o conteúdo pendente de P2-A01. Não existe ADR/arquivo de arquitetura separado no pacote ativo; nenhum documento redundante foi criado.

```text
PREVIOUS = VENDOR_FIRST_WHEN_KNOWN (P1 implemented baseline)
APPROVED_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE
ARCH_AUDIT_01 = COMPLETED_WITH_FINDINGS
ARCH_AUDIT_PUBLICATION = PUBLISHED at starting HEAD 27582e1a3e26d861a94ece15c5d50a7348a8482f
P1_STATUS = CLOSED
P2_STATUS = CONTRACT_PENDING
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
ONVIF_DIGEST_FINDING = OPEN; ROOT_CAUSE = UNDETERMINED
HIKVISION_ISAPI_POC = PLANNED_NOT_IMPLEMENTED
CONTRACT_CHANGE = NONE_IMPLEMENTED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
GIT_WRITES = NONE
NEXT_ACTIVITY = P2-A01 — Define P2 Architecture Contract
```

P2 planeja correções de preservação de evidências, fingerprint/resolução, diagnóstico por operação, seleção controlada de autenticação ONVIF, proveniência/merge, PoC ISAPI mínima, validação operacional futura autorizada e expansão incremental do inventário/rede. F01/F02 são bugs confirmados; F03/F06 limitações confirmadas; F04 mantém causa Digest real indeterminada; F05 é capability planejada; F07–F11 mantêm os tipos individuais registrados no execution plan e relatório; F12 é divergência documental. READ_ONLY, escopo de credenciais por câmera, proibição de credential spraying, saída sem senhas e ausência de operações mutantes continuam obrigatórios. A descoberta ONVIF não é exigida em todas as consultas quando fabricante e caminho nativo válido já cobrem o necessário; nenhuma câmera será reconfigurada automaticamente ou exigirá provisionamento de contas em massa.

## P0-A04 — Foundation Review Recheck (2026-10-07)

Resultado: `PASS_WITH_ACCEPTED_FINDINGS`. Os blockers remediados foram rechecados; os deferred items foram preservados. Divergências de root, Git e runtime foram explicitadas e reconciliadas. Todos os nove pins foram resolvidos por bytes exatos em ZIPs externos, sem alterar binding ou governança. Testes estruturais existentes passaram por chamada direta; pytest/Ruff indisponíveis. Relatório primário: [`../audit/FOUNDATION_REVIEW_P0_A04.md`](../audit/FOUNDATION_REVIEW_P0_A04.md). Estado, próxima decisão e autorizações: [`PROJECT_STATE.md`](PROJECT_STATE.md). P0-A02 conserva seu resultado histórico. Sem implementação, stage, commit ou push.

## P0-A05 — Project Opening Gate Finalization (2026-10-07; estado histórico, reconciliado por P0-A05-R1)

Entrada: `P0-A04 = COMPLETED`, `FOUNDATION_REVIEW_RESULT = PASS_WITH_ACCEPTED_FINDINGS`, recomendação `APPROVE_WITH_ACCEPTED_FINDINGS` e aprovação explícita do usuário `APPROVED_WITH_ACCEPTED_FINDINGS`. Disposições mantidas: F-01 `ACCEPTED_DEFERRED`, F-02 `ACCEPTED_INFORMATIONAL`, F-03/F-05/F-06/F-07 `REMEDIATED`, F-04 `ACCEPTED_RESOLVED_EVIDENCE`, F-08 `ACCEPTED_DEFERRED_TO_P12`. Nenhuma evidência nova contra a Foundation foi encontrada; nenhuma finding foi reavaliada. Verificação de continuidade identificou que a linha P0 no roadmap ainda diz que a aprovação do usuário e Opening Gate estão pendentes. Como alterar roadmap foi expressamente excluído do escopo, esta contradição impede declarar continuidade reconciliada e handoff válido. O projeto permanece scaffold sem implementação funcional.

`FOUNDATION_APPROVAL = APPROVED_WITH_ACCEPTED_FINDINGS`; `PROJECT_OPENING_GATE = BLOCKED`; `P0_STATUS = OPEN`; `PROJECT_READY_FOR_IMPLEMENTATION_PLANNING = NO`; `P1_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`. Próxima atividade pretendida: `P1-C01 — P1 SINGLE Minimum Vertical Slice Implementation Contract`, mas `BLOCKED` até reconciliar a roadmap sob escopo autorizado. `AGENT_HANDOFF_GATE = BLOCKED`. Nenhuma implementação funcional ou escrita Git consequencial ocorreu.

## P0-A05-R1 — Project Opening Gate Reconciliation (2026-10-07)

P0-A05-R1 alterou somente o estado factual da linha P0 em `planning/ROADMAP.md`: Foundation Approval `APPROVED_WITH_ACCEPTED_FINDINGS`, Project Opening Gate `PASS`, P0 `CLOSED`. Estrutura P0–P12, conteúdo técnico, escopo P1 e sequência ficaram inalterados. Não houve evidência nova contra a Foundation nem reavaliação de findings.

`PROJECT_OPENING_GATE = PASS`; `P0_STATUS = CLOSED`; `PROJECT_READY_FOR_IMPLEMENTATION_PLANNING = YES`; `P1_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`. Próxima atividade: `P1-C01 — P1 SINGLE Minimum Vertical Slice Implementation Contract`, `READY`, `CONTRACT_ONLY`. Continuidade reconciliada, blockers `NONE`, `AGENT_HANDOFF_GATE = PASS`. Nenhuma implementação funcional ou escrita Git consequencial ocorreu.

## P1-C01 — P1 SINGLE Minimum Vertical Slice Implementation Contract (2026-10-07)

Contrato reconciliado: [`../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`](../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md). Em P1-C01-R1 o usuário aprovou preservar os dez campos de `CameraResult` e adicionar apenas `error_code`, `error_message`, `collection_method` e `duration`, totalizando 14, sem password nem extension bag. A tipagem/unidade dos novos campos permanece pendente por falta de definição canônica aprovada. Contrato `READY_FOR_USER_APPROVAL`; implementação não autorizada. Sem código, stage, commit ou push.

## P1-C01-R2 — Typing Contract Closure (2026-10-07)

O usuário forneceu as decisões canônicas para `error_code`, `error_message`, `collection_method` e `duration`; todas foram persistidas no contrato P1, com `CollectionStatus` reutilizado. `TYPING_DECISIONS_PENDING = NONE`; contrato pronto para aprovação final; implementação não autorizada.

## P1-A01 — SINGLE Minimum Vertical Slice Implementation (2026-10-07)

O payload executor do usuário aprovou o contrato e autorizou P1-A01. O fluxo SINGLE foi integrado do entrypoint ao menu, workflow, serviço de inventário, collector ONVIF genérico, solicitação explícita de `GetDeviceInformation`, `CameraResult`, terminal e navegação controlada pelo `ApplicationController`. A biblioteca também faz descoberta interna somente leitura com `GetServices` e pode usar `GetCapabilities` como fallback. O cliente usa cache desativado e timeout de request de 7 segundos. Nenhuma operação mutante, funcionalidade fora do escopo ou escrita Git foi introduzida.

Validações focais e acumuladas, teste de fluxo CLI com ONVIF falso, regressão aplicável, pytest e Ruff passaram em Python 3.14.0. O entrypoint `cam-scanner` iniciou e saiu pelo menu. Os testes cobrem os 14 campos, invariantes de duração, erros mapeados, `getpass()`, ausência de senha em terminal/logs e navegação pós-consulta.

Não foi fornecido target com credenciais explicitamente autorizados para validação operacional. Nenhuma câmera foi consultada. P1 não pode ser declarada fechada até a consulta READ_ONLY real ser evidenciada. O repositório permanece sem stage/commit/push.

```text
P1_CONTRACT_STATUS = APPROVED
P1_IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_P1_A01
P1_A01_IMPLEMENTATION = COMPLETE
CANONICAL_FLOW_INTEGRATED = YES
REAL_CAMERA_VALIDATION = BLOCKED_NO_AUTHORIZED_TARGET
P1_STATUS = NOT_READY
NEXT_ACTIVITY = P1-A01-R1 — Validação READ_ONLY contra câmera real autorizada
NEXT_ACTIVITY_READINESS = BLOCKED_NO_AUTHORIZED_TARGET
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
AGENT_HANDOFF_GATE = PASS
GIT_WRITES = NONE
```

## P1-A02 — Real Camera READ_ONLY Validation (2026-10-07; histórico)

O usuário autorizou o escopo READ_ONLY para `10.143.36.33`. O fluxo SINGLE foi executado três vezes com credenciais informadas localmente e retornou `AUTH_ERROR` em todas. O log sanitizado confirma as três falhas sem registrar username ou senha; a saída sanitizada retornou ao menu pós-consulta. A evidência não identifica se a recusa ocorreu durante descoberta ONVIF ou `GetDeviceInformation`. Nenhum dado do dispositivo foi obtido, nenhuma operação mutante ocorreu e nenhum defeito de código foi identificado. O blocker é autenticação ONVIF. O próximo passo seguro é confirmar autenticação e permissão ONVIF da conta, sem registrar ou compartilhar a senha.

```text
P1-A02 = BLOCKED
TARGET_AUTHORIZED = YES
TARGET_IP = 10.143.36.33
REAL_CAMERA_VALIDATION = BLOCKED_AUTHENTICATION
CANONICAL_CLI_FLOW = PASS
ONVIF_READ_ONLY = PASS
GET_DEVICE_INFORMATION = FAIL (autenticação rejeitada; etapa ONVIF específica não identificada)
DEVICE_INFORMATION_OBTAINED = NO
CAMERA_RESULT = PASS (resultado FAILED produzido e apresentado)
COLLECTION_METHOD = PASS (InventoryService atribui ONVIF ao iniciar coleta)
DURATION = PASS (InventoryService mede duração monotônica)
PASSWORD_SECURITY = PASS
EXPECTED_ERROR_HANDLING = PASS
POST_QUERY_NAVIGATION = PASS
MUTATING_CAMERA_CALLS = 0
DEFECT_DETECTED = NO
DEFECT_SUMMARY = NONE
FUNCTIONAL_SCOPE_LEAKAGE = NONE
SOURCE_CODE_CHANGES = NONE
UNRESOLVED_BLOCKERS = BLOCKED_AUTHENTICATION
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
AGENT_HANDOFF_GATE = PASS
P1_STATUS = NOT_READY
NEXT_ACTIVITY_AT_THAT_TIME = Retomar P1-A02 após confirmar autenticação e permissão ONVIF da conta autorizada
STATUS = BLOCKED
ACTIVITY_COMPLETION_PERCENT = 40%
COMPLETION_BASIS = fluxo SINGLE e tratamento de erro real confirmados; estado e handoff reconciliados; diff --check sem erros; aceite de obtenção de informações do dispositivo não cumprido
GIT_WRITES = NONE
```

O bloqueio e a evidência acima são históricos, sob a premissa de coleta então vigente. A retomada focada em autenticação ONVIF foi supersedida pela direção P1-A03; os fatos originais permanecem preservados.

## P1-A03 — Collection Strategy Documentation Reconciliation (2026-10-07)

O baseline P1-A01/P1-A02 foi checkpointado localmente antes da edição documental no commit `d64ff9799d5d84c22a33ab7c24f589cbe619e3a6` (`feat(p1): implement single camera vertical slice`). Python 3.14.0 e os 29 testes passaram; Ruff passou em `src/` e `tests/`. Os únicos achados de Ruff ocorreram nos dois scripts temporários de diagnóstico, excluídos do commit. `git diff --check` passou. Nenhum push foi feito.

O usuário aprovou `COLLECTION_STRATEGY = VENDOR_FIRST_WHEN_KNOWN`. `FABRICANTE` é opcional; é `STRONG_HINT`, não verdade absoluta. Sem fabricante, deve ocorrer identificação READ_ONLY pré-autenticação antes de qualquer login; `TRY_ALL_VENDOR_LOGINS = PROHIBITED`. Credenciais são individuais por linha/câmera. ONVIF é fallback genérico, complemento e mecanismo de descoberta pré-autenticação. Falha ONVIF autenticada não invalida automaticamente evidência válida; `SUCCESS`, `PARTIAL_SUCCESS` e `FAILED` permanecem distintos. Divergência do fabricante é detectada e reportada. Sem novos endpoints, estruturas definitivas ou alterações de código nesta atividade.

Complemento factual à evidência histórica P1-A02, fornecido na decisão desta atividade: para `10.143.36.33` autorizado, conectividade e descoberta do endpoint ONVIF passaram; `GetSystemDateAndTime` e `GetCapabilities` pré-autenticação passaram; fingerprint Hikvision por capability extension passou; `GetDeviceInformation` autenticado retornou `AUTH_ERROR`; WS-UsernameToken e HTTP Digest receberam HTTP 401. Operações mutantes: zero. Não registrar username ou senha. Esse resultado demonstra descoberta e fingerprint READ_ONLY, não coleta vendor-first já implementada.

```text
P1-A03 = COMPLETED_WITH_FINDINGS
COLLECTION_STRATEGY = VENDOR_FIRST_WHEN_KNOWN
ONVIF_FIRST_REMOVED = YES
ONVIF_ROLE_RECONCILED = PASS
IMPLEMENTATION_ADAPTATION_REQUIRED = YES
P1_STATUS = NOT_READY
P1_A02_HISTORICAL_RECONCILIATION = PASS
ROADMAP_RECONCILIATION = PASS
EXECUTION_PLAN_RECONCILIATION = PASS
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
AGENT_HANDOFF_GATE = NOT_REEVALUATED; canonical Continuity 3.0 protocol path unavailable
DOCUMENTATION_GIT_WRITES = NONE
GIT_PUSH = NONE
TEMP_DIAGNOSTIC_FILES_COMMITTED = NO
GOVERNANCE_SOURCE_READABILITY = PARTIAL; paths externos de CONTINUITY_PROTOCOL.md e PM-01 indicados por AGENTS.md não encontrados neste checkout
NEXT_ACTIVITY = P1-A04 — Implementar adaptação da estratégia de coleta revisada
NEXT_ACTIVITY_AUTHORIZATION = NOT_GRANTED; requer autorização específica
ACTIVITY_COMPLETE = YES (P1-A03; reconciliação documental concluída com findings registrados)
ACTIVITY_COMPLETION_PERCENT = 100% (somente P1-A03)
STATUS = COMPLETED_WITH_FINDINGS
```

## P1-A03-CLOSE — Documentation Authority Reconciliation + Git Closure (2026-10-07)

As referências externas de `AGENTS.md` apontavam para `../governança_de_projetos/`, enquanto a raiz existente neste workspace é `../governanca_de_projetos/`. O PM-01 v1.0 foi identificado pelo registry e confirmado pelo SHA-256 `b0782078a57fde833577e6b46fe3cd32048dae14569cac5ba9d821aafd1b54fa`; Continuity 3.0 foi confirmado pelo SHA-256 `262997f3509a856ed450654c9e5c9b9128beb3f57e1092bc87967ded42d0b5f3` no membro do ZIP canônico. `AGENTS.md` recebeu apenas a correção do path da raiz; os pins e o conteúdo normativo não foram alterados.

O diff documental P1-A03 foi revisado, os invariantes do contrato e do estado foram conferidos, `git diff --check` passou e não foram encontrados secrets. Foram staged e commitados explicitamente apenas `AGENTS.md` e os nove documentos P1-A03 aprovados; políticas locais não promovidas e scripts diagnósticos permaneceram fora do commit. Nenhum código ou teste foi alterado; testes não foram rerodados por se tratar de fechamento documental. O commit é local e não houve push.

```text
P1-A03-CLOSE = COMPLETED
AUTHORITY_REFERENCE_RECONCILIATION = PASS
CONTINUITY_PROTOCOL_RESOLUTION = PASS
PM01_RESOLUTION = PASS
DOCUMENTATION_CONSISTENCY = PASS
SOURCE_CODE_CHANGES = NONE
TEST_CODE_CHANGES = NONE
CODE_REGRESSION_RERUN = NOT_REQUIRED_DOCUMENTATION_ONLY
DIFF_CHECK = PASS
SECRETS_EXPOSED = NO
STAGED_SCOPE_VALIDATION = PASS
TEMP_DIAGNOSTIC_FILES_COMMITTED = NO
DOCUMENTATION_COMMIT = CURRENT_REPOSITORY_HEAD
GIT_PUSH = NONE
P1_STATUS = NOT_READY
IMPLEMENTATION_ADAPTATION_REQUIRED = YES
NEXT_ACTIVITY = P1-A04 — Implementar adaptação da estratégia de coleta revisada
NEXT_ACTIVITY_AUTHORIZATION = NOT_GRANTED; requer autorização específica
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
STATUS = COMPLETED
```

## P1-A04 — SINGLE vendor-first strategy adaptation (2026-10-07)

O payload executor concedeu authority de implementação específica P1-A04. A adaptação foi integrada no entrypoint canônico SINGLE: descoberta ONVIF anônima/read-only, fingerprint estrutural limitado, resolução/normalização de fabricante, seleção de um único adapter registrado e fallback genérico ONVIF. Nenhum placeholder de fabricante está registrado como implementação funcional. A estratégia nunca itera credenciais nem tenta autenticar outros fabricantes. Quando há evidência pré-auth e a autenticação ONVIF falha, o resultado permanece `PARTIAL_SUCCESS`; sem evidência válida, o serviço retorna falha sanitizada. A entrada SINGLE segue IP, username e password; nenhum novo prompt foi autorizado pelo contrato.

O fluxo e regressão sintética passaram em Python 3.14.0: 48 testes, Ruff em `src` e `tests`, smoke do menu de entrada/saída e `git diff --check`. O pytest reportou aviso de cache sem permissão de escrita; todos os testes passaram. Nenhuma câmera real foi consultada porque a autorização da P1-A02 para `10.143.36.33` não foi estendida pela authority P1-A04. O `CameraResult` continua com 14 campos, nenhum contrato de domínio/arquitetura foi alterado e nenhuma funcionalidade P2+ foi incluída.

```text
P1-A04 = COMPLETED
COLLECTION_STRATEGY = VENDOR_FIRST_WHEN_KNOWN
CANONICAL_FLOW_IMPLEMENTED = YES
VENDOR_FIRST_ROUTING = PASS
MANUFACTURER_HINT_SUPPORT = NOT_REQUIRED_BY_CONTRACT_FOR_SINGLE
PREAUTH_FINGERPRINT = PASS (sintético)
UNKNOWN_MANUFACTURER_FLOW = PASS
KNOWN_MANUFACTURER_WITHOUT_ADAPTER = PASS
ONVIF_ROLE = PASS
ONVIF_AUTH_FAILURE_SEMANTICS = PASS
PARTIAL_SUCCESS = PASS
MANUFACTURER_MISMATCH = PASS (detecção sem substituição silenciosa; SINGLE não recebe hint)
PER_CAMERA_CREDENTIAL_SCOPE = PASS
TRY_ALL_VENDOR_LOGINS = ABSENT
CAMERA_RESULT_14_FIELDS = PASS
PASSWORD_SECURITY = PASS
READ_ONLY_INVARIANT = PASS
SOURCE_CODE_SCOPE = PASS
P2_PLUS_SCOPE_LEAKAGE = NONE
UNIT_VALIDATION = PASS
INTEGRATION_VALIDATION = PASS
ACCUMULATED_FLOW_VALIDATION = PASS
PYTHON_3_14 = PASS (3.14.0)
PYTEST = PASS (51 tests)
RUFF = PASS
CLI_SMOKE = PASS
REAL_CAMERA_VALIDATION = NOT_RUN_NO_ACTIVITY_AUTHORITY
REGRESSION = PASS
CONTRACT_GAP = NONE
ARCHITECTURE_CHANGE = NONE
DOMAIN_CONTRACT_CHANGE = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
P1_STATUS = NOT_READY (real-camera operational DoD remains pending)
NEXT_ACTIVITY = P1-A05 — READ_ONLY operational validation with explicit target authority
GIT_WRITES = NONE
ACTIVITY_COMPLETE = YES (somente P1-A04; validação operacional da P1 não foi incluída na authority)
ACTIVITY_COMPLETION_PERCENT = 100% (somente P1-A04)
STATUS = COMPLETED_WITH_FINDINGS
```

## P1-CHECKPOINT-01 — P1 Closure + Published Checkpoint

O payload executor autorizou reconciliar P1-A05, executar validação do baseline, stage explícito, commit e push para `origin/master`. Evidência operacional autorizada para `10.143.36.33`: descoberta pré-auth PASS; fabricante Hikvision; coleta autenticada ONVIF `AUTH_ERROR`; tratamento da falha e semântica `PARTIAL_SUCCESS` PASS; segurança de senha PASS; chamadas mutantes zero. Nenhum username, password ou header de autorização foi preservado. O finding ONVIF Digest permanece `OPEN_NON_BLOCKING`. A primeira tentativa de push foi rejeitada pela revisão automática; após autorização explícita direta e verificação do remoto, os seis commits pendentes foram publicados sem force push. Fetch posterior confirmou `HEAD = origin/master = ec53d2bd08b8bf0ee0d82b1411122f246502e820`.

O contrato P1 foi esclarecido para aceitar evidência real READ_ONLY pré-autenticação como `PARTIAL_SUCCESS` quando a autenticação posterior falha, sem exigir `AUTHENTICATED_SUCCESS`. Assim, todos os requisitos P1 foram satisfeitos e P1 foi fechada. P0 permanece CLOSED. Próxima atividade: definição/contrato de P2; implementação P2 não autorizada. Continuidade e bootstrap foram ajustados para checkout cross-computer e não requerem path absoluto específico.

```text
P1_A04_IMPLEMENTATION = PASS
P1_A05_REAL_VALIDATION = PASS
REAL_CAMERA_RESULT = PARTIAL_SUCCESS
P1_CLOSURE = PASS
P1_STATUS = CLOSED
ONVIF_DIGEST_INTEROPERABILITY_FINDING = OPEN_NON_BLOCKING
GIT_PUSH = PASS
PUSHED_COMMITS = 6
LOCAL_HEAD = ec53d2bd08b8bf0ee0d82b1411122f246502e820
ORIGIN_MASTER_HEAD = ec53d2bd08b8bf0ee0d82b1411122f246502e820
LOCAL_REMOTE_MATCH = YES
CROSS_COMPUTER_CONTINUITY = PASS
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
```

## P2-I1 — Hybrid Collection Foundation: F01 + F02 + F03 (2026-10-12)

O payload executor fornecido pelo usuário concedeu `GRANTED_FOR_P2_I1_ONLY`. A autorização cobre implementação offline das fundações F01–F03 no fluxo SINGLE; não amplia a authority geral de P2 nem autoriza consulta de câmera, PoC ISAPI, MULTI, concorrência, mudança de dependências ou escrita Git. P0 e P1 continuam fechadas; P2 permanece aberta.

A implementação integrada adiciona `EvidenceRecord`, `CollectionAttempt` e `CollectionReport` sem alterar os 14 campos de `CameraResult`; preserva evidência por merge monotônico, deriva sucesso/partial/failure conforme `IDENTITY_V1`, resolve fabricantes por sinais estruturados sem seleção por substring/ordem e registra diagnósticos sanitizados por tentativa/operação. O caminho SINGLE passa o relatório até a UI e mantém a projeção compatível `CameraResult`. Erros/exceções não são retidos em bruto; tentativas não guardam URLs, headers, credenciais ou bodies. Não houve alterações de dependências.

Validação offline: 41 casos das funções da nova suíte P2 executados por runner direto mínimo com stub de decorators do pytest; `AST_PARSE = PASS` em 53 arquivos Python; smoke do fluxo SINGLE e `git diff --check = PASS`. Isso não equivale à execução de pytest. O launcher Python 3.15 configurado no host aponta para caminho inválido, e não há `pytest` ou `ruff`; portanto execução do pytest, Ruff e regressão acumulada da P1 permanecem bloqueadas. Nenhuma câmera real foi consultada, ISAPI não foi implementado e nenhum segredo foi exposto.

Estado Git observado: branch `master`; `HEAD = origin/master = 3737a5c64043950d053ec702929f528fc53a72cf` na entrada e após alterações de código/testes; arquivos continuam unstaged. A continuidade atualizada está em [`PROJECT_STATE.md`](PROJECT_STATE.md) e [`handoff/LAST_HANDOFF.md`](handoff/LAST_HANDOFF.md). Ponto seguro de retomada: recuperar o runtime de projeto Python 3.14 com dependências de desenvolvimento já aprovadas, sem alterar manifests, então rodar pytest, Ruff e regressão acumulada antes de fechar P2-I1.

```text
ACTIVITY = P2-I1
AUTHORITY = GRANTED_FOR_P2_I1_ONLY
ROOT_MODEL_TARGET = LUNA
ROOT_EFFORT_TARGET = XHIGH
ROOT_RUNTIME = UNVERIFIABLE
EXECUTION_MODE = DIRECT
F01 = IMPLEMENTED; DIRECT_OFFLINE_ASSERTIONS_PASS
F02 = IMPLEMENTED; DIRECT_OFFLINE_ASSERTIONS_PASS
F03 = IMPLEMENTED; DIRECT_OFFLINE_ASSERTIONS_PASS
P2_OFFLINE_ASSERTIONS = PASS (41 cases; direct runner, not pytest)
AST_PARSE = PASS (53 Python files)
SINGLE_FLOW_OFFLINE_SMOKE = PASS
PYTEST = BLOCKED
RUFF = BLOCKED
P1_ACCUMULATED_REGRESSION = BLOCKED
REAL_CAMERA_VALIDATION = NOT_RUN_HOME
ISAPI = NOT_IMPLEMENTED
MULTI_AND_CONCURRENCY = NOT_IMPLEMENTED
DEPENDENCY_CHANGES = NONE
GIT_WRITES = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_STATUS = PASS_WITH_FINDINGS
ACTIVITY_COMPLETE = NO
STATUS = BLOCKED
```

### P2-I1 — Retomada para remediação de regressões (2026-10-12)

A atividade P2-I1 existente foi retomada dentro da authority concedida, sem abrir nova atividade formal, alterar decisões D01–D06 ou modificar o contrato P1. As fixtures positivas de identidade pré-auth agora usam fabricante estruturado; o teste que oferece apenas horário/alcançabilidade passou a afirmar `FAILED` após recusa de autenticação. Foi adicionada regressão para garantir essa distinção. A coleta genérica preserva `manufacturer_original` exatamente como recebido quando o conteúdo é seguro e continua produzindo o fabricante normalizado no campo separado; texto com credenciais/URL ou controles não é exposto. `CameraResult` continua com 14 campos.

A investigação da CLI encontrou conflito falso em `onvif_reachable`: cada operação registrava o próprio nome como valor. As operações agora compartilham `REACHABLE`, separando serviço alcançável de autenticação, identidade e conflito material.

Gates no Python 3.14.7 do `.venv`: `pip check` aprovado; suíte P2 com 41 testes; acumulado com 93 testes; Ruff aprovado; `git diff --check` aprovado. O launcher emite aviso de localização antiga do Python base, mas executa os comandos e os códigos de saída foram bem-sucedidos. Não foram consultadas câmeras reais nem alteradas dependências. Os seis arquivos de `src/cam_scanner.egg-info/` foram inspecionados e permaneceram intactos, sem stage.

```text
ACTIVITY = P2-I1 (continuação; sem atividade formal nova)
F01 = PASS
F02 = PASS
F03 = PASS
IDENTITY_V1 = PASS
P1_COMPATIBILITY = PASS
PYTEST = PASS (93 passed; P2 suite 41 passed)
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
FALSE_CONFLICT_INVESTIGATION = RESOLVED
LEGACY_TEST_CHANGES = tests/test_p1_cli_flow.py; tests/test_p1_vendor_first_strategy.py; tests/test_p1_onvif_collector.py — justificativas registradas no execution plan
REAL_CAMERA_VALIDATION = NOT_RUN_HOME
DEPENDENCY_CHANGES = NONE
GIT_STAGE_COMMIT_PUSH = NONE
UNTRACKED_EGG_INFO = PRESERVED_UNSTAGED_AND_EXCLUDED_FROM_CHECKPOINT
PROJECT_STATE_UPDATE = PASS
CONTINUITY_STATUS = PASS_WITH_FINDINGS (external governance sibling paths unavailable in this checkout)
ACTIVITY_COMPLETE = YES
STATUS = COMPLETED
ACTIVITY_COMPLETION_PERCENT = 100%
NEXT_ACTIVITY = P2 follow-on work requires separate explicit user authority
```

### P2-I1 — Revisão independente V2 e reconciliação final de continuidade (2026-10-12)

A revisão independente V2 reportou `PASS`, sem findings materiais, e confirmou F01–F03, `IDENTITY_V1`, compatibilidade P1 e controles de segurança. A baseline acumulada mais recente reportada é 127 testes (34 de segurança), com Ruff, `pip check` e `git diff --check` aprovados. A documentação foi reconciliada sem reexecutar a suíte e sem alterar o contrato P2 aprovado. P0/P1 continuam `CLOSED`, P2 `IN_PROGRESS`; D01–D06 `APPROVED`, D07 `DEFERRED`. A homologação real permanece `NOT_RUN_HOME`.

As seis fontes externas de governança referenciadas pelo `AGENTS.md` não estavam disponíveis nos caminhos HOME esperados. Esse finding é preservado; `GOVERNANCE_BINDING` não é promovido a PASS e nenhum hash foi inventado. O preflight do checkpoint está pronto, mas a publicação Git continua pendente. O manifesto com caminhos exatos está em `PROJECT_STATE.md`; os artefatos locais `src/cam_scanner.egg-info/` permanecem preservados e excluídos.

```text
ACTIVITY = P2-I1-GIT-CHECKPOINT-PREFLIGHT (continuação; sem nova atividade formal)
SECURITY_RECHECK = PASS
CONTINUITY_RECONCILIATION = PASS
SCOPE_REVIEW = PASS
MANIFEST_VERIFICATION = PASS
GOVERNANCE_BINDING = FINDING
CHECKPOINT_READY = YES
GIT_ADD_COMMIT_PUSH = NONE
P2_STATUS = IN_PROGRESS
REAL_CAMERA_VALIDATION = NOT_RUN_HOME
```

## BLOCO A — Executable Integration (2026-10-14)

O Card B foi executado em worktree separado a partir de `origin/master` na baseline `d4ddcc5f81e78583fa5bfe3b597ce5dd6197a210`, branch `integration/bloco-a`, em `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_bloco_a_integration`. O checkout de origem em `master`/`3737a5c64043950d053ec702929f528fc53a72cf` e suas alterações locais foram preservados. A integração usa os contratos publicados de `domain/models.py`; não mantém um segundo contrato para relatórios de coleta.

Foram integrados Hikvision ISAPI somente leitura com Digest limitado, parsing XML seguro, snapshots ONVIF/vendor/um frame RTSP com miniatura JPEG 320×180 sem metadata, MULTI sequencial com leitura/exportação XLSX, progresso Rich com fallback de terminal e navegação SINGLE/MULTI compartilhando `InventoryService`. Evidências P2-I1 e os diagnósticos ONVIF canônicos foram mantidos. O leitor XLSX também mascara IPs inválidos com URL/userinfo.

Validação em Python 3.14.0: 170 testes aprovados; `pip check`, Ruff 0.17.0 e `git diff --check` passaram. O smoke MULTI usou duas câmeras sintéticas válidas e uma inválida, credenciais distintas, snapshots, exportação XLSX temporária com abas `INVENTARIO`/`RESUMO` e conferência de ausência de senhas. O smoke SINGLE percorreu CLI, coleta sintética, resultado e menu pós-consulta. Nenhum equipamento real foi contatado.

Limites: validação com câmera real continua pendente; snapshot vendor Hikvision está limitado aos modelos DS-KD8003; MULTI segue sequencial; P5 não foi iniciado; P2/P3/P4 não foram formalmente encerradas. A branch permanece sem stage/commit/push. Próximo gate: aprovação do usuário para o checkpoint integrado.

```text
ACTIVITY = BLOCO_A_EXECUTABLE_INTEGRATION
INTEGRATION_BASELINE = d4ddcc5f81e78583fa5bfe3b597ce5dd6197a210
INTEGRATION_BRANCH = integration/bloco-a
SOURCE_WORKTREE_PRESERVED = YES
PYTEST = PASS (170 passed)
RUFF = PASS
PIP_CHECK = PASS
GIT_DIFF_CHECK = PASS
REAL_CAMERA_VALIDATION = NOT_RUN
P5 = NOT_STARTED
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
ACTIVITY_COMPLETE = YES (somente BLOCO A)
ACTIVITY_COMPLETION_PERCENT = 100%
GIT_ADD_COMMIT_PUSH = NONE
NEXT_GATE = USER_APPROVAL_FOR_INTEGRATED_CHECKPOINT
STATUS = COMPLETED
```
## CAM_SCANNER_PRE_IMPLEMENTATION_CHECKPOINT_GIT_01 — 2026-10-27

Baseline R2 confirmada em `feature/pre-p12-unified-remediation` / `37bc8c4`. Auditoria Astra: `CONDITIONAL_GO`; contratos P0 V2, P1 V2 e TRANSPORT V1 aprovados pelo usuário; P2/RTSP diferido; homologação Viewer não comprovada; implementação não iniciada. Próxima atividade: `CAM_SCANNER_ASTRA_P0_P1_TRANSPORT_IMPLEMENTATION`, exclusivamente offline.
