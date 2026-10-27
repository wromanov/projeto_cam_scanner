# CAM SCANNER — submissão de evidências do Gate V

## Resultado final e submissão (2026-10-19)

Este resultado supersede o resumo da primeira tentativa logo abaixo, preservado como histórico. A execução real inicial identificou uma incompatibilidade do teste em `os.utime(..., follow_symlinks=False)`; o teste foi corrigido conforme o contrato específico [`CAM_SCANNER_FINAL_STABILIZATION_SYMLINK_TEST_FIX_CONTRACT_2026-10-19.md`](CAM_SCANNER_FINAL_STABILIZATION_SYMLINK_TEST_FIX_CONTRACT_2026-10-19.md), sem alterar código de produção.

```text
SYMLINK_TEST_RESULT = PASS (Windows real, CPython 3.14.0; 1 passed; 0 failed/skipped)
FULL_REGRESSION_RESULT = PASS (373 passed; 0 failed; 0 skipped; 0 deselected; 55.83s; exit 0)
GATE_2_STATUS = PASS
GATE_3_STATUS = PASS (aceite independente offline; PREP12-01/02 CLEARED; PREP12-03 CLEARED preservado)
GATE_V_STATUS = PASS
GATE_V_SUBMISSION = RECORDED_WITH_PASS
GATE_4_STATUS = PASS (prontidão reavaliada sem executar P12)
P12_READINESS = READY_FOR_P12
P12_BUILD = NOT_RUN
REMAINING_BLOCKERS = Nenhum para iniciar P12; PREP12-09 build/smoke ONEDIR e Gate 5/publicação permanecem etapas posteriores; validação com câmera real continua fora deste aceite offline
PROJECT_STATE_UPDATE = PASS
ACTIVITY_COMPLETION_PERCENT = 100%
ACTIVITY_COMPLETE = YES
```

O ambiente foi `_p10r` (CPython 3.14.0, pytest 9.1.1), com `cam_scanner` importado de `src/cam_scanner/__init__.py` neste worktree. O teste focal criou um symlink real, comprovou via `lstat()` que seu próprio mtime estava abaixo do cutoff avançado, removeu um log regular de produto vencido e preservou o link e o conteúdo do alvo. WinError 1314 continua tratado como `SKIP` explícito; não ocorreu nesta execução.

O executor registrou o comando focal abaixo com resultado `1 passed in 0.06s`, exit code 0, sem falha ou skip:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src'); & '.\_p10r\Scripts\python.exe' -m pytest -q -rs -p no:cacheprovider --basetemp '.\_tmp_focus_symlink_test_20261019_escalated' tests/test_logging_setup.py::test_windows_filesystem_retention_never_follows_real_symlink
```

O código do teste está em [`test_logging_setup.py`](../../tests/test_logging_setup.py); nenhuma implementação de produção foi alterada.

Comando da regressão integral: [`full-regression.command.txt`](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_regression/full-regression.command.txt). Log: [`full-regression.log`](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_regression/full-regression.log). Exit code: [`full-regression.exit.txt`](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_regression/full-regression.exit.txt). SHA-256 do log: `FD854E991654612779929B90DB343ACD3BFF850501CD08A27E4C92E93D57F3DC`.

O parecer independente direcionado de Gate 3 concluiu que a revisão técnica já registrada podia ser promovida após Gate 2, pois a única alteração posterior foi no preparo temporal do teste de symlink. PREP12-01/02 foram aceitos para o estágio offline e PREP12-03 foi preservado como `CLEARED`; isso não equivale a validação de câmera real, build P12 ou autorização de publicação. Gate 4 concluiu `READY_FOR_P12` sem executar P12. O Gate 5 continua reservado à aprovação de publicação após existir um pacote concreto.

---

**PROJECT_ID:** `projeto_cam_scanner`  
**ACTIVITY:** `CAM_SCANNER_FINAL_STABILIZATION`  
**Data:** 2026-10-19  
**Modo:** `DIRECT` na tentativa inicial; continuação em `MULTIAGENT` autorizada pelo usuário  
**Worktree:** `feature/pre-p12-unified-remediation`, HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e`

## Resultado

```text
SYMLINK_TEST_RESULT = FAIL (os.symlink criou o link real; NotImplementedError em os.utime(..., follow_symlinks=False), antes da chamada de retenção)
FULL_REGRESSION_RESULT = NOT_RUN (a condição do passo 3 não foi atendida: o teste focal não passou)
GATE_2_STATUS = NOT_MET
GATE_3_STATUS = PENDING_GATE_2 (PREP12-01/02 permanecem DEFERRED pela revisão independente anterior)
GATE_V_STATUS = NOT_MET (evidência submetida; regressão integral zero-skip não executada)
GATE_V_SUBMISSION = RECORDED_WITH_FAILURE
P12_READINESS = BLOCKED
REMAINING_BLOCKERS = corrigir ou substituir, com autorização, a preparação temporal incompatível do teste; passar o teste real; então executar regressão integral sem falhas/skips/deselected e promover Gate 3; reavaliar readiness
PROJECT_STATE_UPDATE = PASS
ACTIVITY_COMPLETION_PERCENT = 92%
ACTIVITY_COMPLETE = NO
```

## Evidência e interpretação

O ambiente de reprodução limpo `_p10r` executa CPython 3.14.0 e pytest 9.1.1. Com `PYTHONPATH` apontando para `src` deste worktree, `cam_scanner` foi importado de `src/cam_scanner/__init__.py` no worktree, não do checkout principal. O usuário informou que Windows Developer Mode está habilitado e que um teste standalone de symlink em Python 3.14 passou; essas duas informações são entradas fornecidas pelo usuário.

Na execução final do teste do projeto, a chamada `os.symlink(target, link)` retornou sem erro: o fluxo avançou para `os.utime`. Essa chamada levantou `NotImplementedError: utime: follow_symlinks unavailable on this platform` em `tests/test_logging_setup.py:229`. Portanto, a execução não chegou a chamar `configure_logging()` nem a verificar a retenção. O resultado é FAIL do teste como escrito e não demonstra falha nem sucesso do comportamento de retenção.

Houve duas tentativas anteriores no sandbox, preservadas sem reinterpretá-las como resultados de produto: a execução com o `tmp_path` nativo terminou com `WinError 5` no cleanup de sessão; o harness temporário isolado falhou ao criar o arquivo-alvo (`FileNotFoundError`) antes de tentar o symlink. A execução local autorizada removeu esse bloqueio de escrita e revelou a falha acima.

O contrato PRE-P12 §12 exige suíte Python 3.14 completa sem falhas, skips ou deselected para V; §14 vincula Gate 2 a essa regressão e ordena Gate 3 depois de Gate 2. Como o teste focal falhou, a regressão completa não foi executada nesta retomada. O resultado histórico de 372 passed, 0 failed e 1 skipped permanece referência não qualificante. A revisão independente de 2026-10-19 deixou PREP12-01/02/04/05 como `DEFERRED`; esta execução não promove esses findings nem repete a auditoria.

Nenhum arquivo de código ou teste foi alterado. Não houve instalação de dependências, alteração persistente de pip, build P12, acesso a câmeras ou operação Git consequencial. O diretório de evidências e o link temporário eventualmente criado foram preservados.

## Índice de evidências

- [Comando, log e exit code da execução local](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.local.command.txt), [log](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.local.log), [exit code](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.local.exit.txt), [origem do pacote](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.local.python-origin.txt).
- Tentativas no sandbox: [execução inicial](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.log) e [execução com fixture temporária](../../_tmp_CAM_SCANNER_FINAL_STABILIZATION_20261019_b77a735cedf44c66af08991a511f283a/symlink.retry.log).
- Contrato aplicável: [PRE-P12 Unified Remediation Contract](../contracts/PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md), §§12 e 14.
- Estado anterior da revisão independente: [reavaliação de aceite PRE-P12 de 2026-10-16](PRE_P12_ACCEPTANCE_REASSESSMENT_2026-10-16.md) e snapshot anterior em `docs/continuity/PROJECT_STATE.md`.

SHA-256 dos artefatos decisivos:

```text
symlink.local.command.txt = BD529FB9CE7866F7C62EB6A0942F83ACC2FC6F2325F72662BDA5E77B13BE6D78
symlink.local.log = 7A919E66D69770FE7CB077F38BF73ECBC07D9F54D91F88B8D8630E5570BBBE3B
symlink.local.exit.txt = F1B2F662800122BED0FF255693DF89C4487FBDCF453D3524A42D4EC20C3D9C04
symlink.local.python-origin.txt = D99263C40BA16E9F5730BB667EB93B0FAB4BEE31AF198D92635FDA3B3580CE31
```

## Próxima ação autorizável

Ajustar a preparação temporal do teste para que ele exercite symlink real em Windows sem depender de `os.utime(..., follow_symlinks=False)`, preservando o propósito do teste. Esta atividade autorizou atualização documental somente, então nenhum teste/código foi alterado. Depois do ajuste autorizado, executar novamente o teste focal; somente se passar, executar a regressão completa zero-skip e então concluir a promoção independente de Gate 3 e a reavaliação pré-P12.
