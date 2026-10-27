# PRE-P12 formal acceptance reassessment — 2026-10-16

**PROJECT_ID:** `projeto_cam_scanner`  
**ACTIVITY:** `PRE_P12_UNIFIED_REMEDIATION`  
**BASELINE:** `feature/pre-p12-unified-remediation` at `37bc8c4cc718559fc1e6f39a9b8a1145563a551e`  
**REVIEW:** independent Architect, read-only; no tests run and no files changed by the reviewer.

## Dispositions

| Finding | Formal disposition | Evidence and remaining criterion |
|---|---|---|
| PREP12-01 | `OPEN` | Targeted HTTPS SINGLE/MULTI, redirect matrix 301/302/303/307/308, hostile proxy/netrc/ambient environment, and Digest→307 evidence exists in `tests/test_pre_p12_transport_integration.py` and `tests/test_target_transport.py`. Contract §14 Gate 2 still requires a full regression with zero skipped/deselected; Gate 3 requires independent security acceptance. The current full run has one skipped test. |
| PREP12-02 | `OPEN` | The same fail-closed TLS/redirect evidence is present. Gate 2 and Gate 3 remain unmet; no clearance is inferred from targeted tests. |
| PREP12-04 | `OPEN` | Offline tests cover shared deadlines through vendor/ONVIF/snapshot, MULTI queueing, RTSP queue timeout before handshake, and zero open after expiration in `tests/test_pre_p12_budget_acceptance.py`. Gate 2 remains unmet. RTSP tests use fake capture; production capture remains disabled. |
| PREP12-05 | `OPEN` | Offline tests cover cancellation during vendor/chunks/RTSP queue and active fake RTSP, resource closure, MULTI completion behavior, and skipped export. Gate 2 remains unmet. RTSP evidence does not establish production capture behavior. |
| PREP12-10 | `BLOCKED_EXTERNAL_DEPENDENCY` | The user confirmed no approved index or wheelhouse is identified and instructed not to bypass `PIP_NO_INDEX=1`. `requirements/locks/windows-py314.in` is the prepared candidate input manifest; it is not a resolved lock. No transitives with hashes or clean reproduction exist. |
| PREP12-11 | `OPEN_CONDITIONAL` | Rollover, locked-file handling, and redaction evidence passed. The real symlink test remains unrun: the prior suite skipped it with WinError 1314, and a disposable capability probe in this session failed with HRESULT `0x80070522` (privilege not held). The probe files were removed. Retest on Windows with authorized symlink capability, then satisfy the zero-skip full regression. |

## Gate state

The latest recorded full regression is **372 passed, 0 failed, 1 skipped, 0 deselected, 0 xfailed**. Under contract §§12 and 14, `GATE_V/GATE_2 = NOT_MET`. Therefore `P12_READINESS = BLOCKED` and `ACTIVITY_COMPLETE = NO`; progress remains 96%.

`PREP12-09` remains `DEFERRED_BY_CONTRACT` to the P12 ONEDIR build/smoke. Existing `CLEARED` dispositions for PREP12-03/06/07/08/12/13/14 are preserved; this reassessment found no contrary evidence. No P12 build, camera access, package installation, or Git publication was performed.

## PREP12-10 source preparation

The existing `requirements/locks/windows-py314.in` remains the candidate manifest, mirroring the runtime/dev pins in `pyproject.toml` and recording proposed resolver/build tooling pins. No versions were changed. The user confirmed that an approved package source has not been identified. Resolution, hash generation, dependency installation, and clean reproduction must wait for an approved source; the existing `PIP_NO_INDEX=1` setting must remain unchanged.
