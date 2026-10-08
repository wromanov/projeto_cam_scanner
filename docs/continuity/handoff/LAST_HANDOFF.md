# Last Handoff — ARCH-ALIGN-01 (documentary reconciliation)

ARCH-ALIGN-01 registrou a direção aprovada para evolução após P1: `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`. O baseline integrado continua sendo a implementação SINGLE P1 sob `VENDOR_FIRST_WHEN_KNOWN`; esta reconciliação não mudou código, testes ou contrato implementado. A P1 continua `CLOSED`, válida segundo seu contrato e DoD.

Na direção futura, o coletor nativo será preferido quando fabricante/capacidade, campos necessários, autenticação disponível e budget justificarem. ONVIF continua como coleta genérica, descoberta quando aplicável, fallback ou complemento condicionado à necessidade. Descoberta ONVIF não é obrigatória se fabricante conhecido e caminho nativo válido cobrirem a consulta. Não se autoriza tentativa autenticada em sequência contra fabricantes.

O relatório original está em [`../../audit/ARCH_AUDIT_01_REPORT.md`](../../audit/ARCH_AUDIT_01_REPORT.md) e permanece inalterado. F01/F02 são bugs confirmados; F03/F06 são limitações confirmadas; os demais F04–F12 permanecem com suas classes e severidades no execution plan e relatório. `ONVIF_DIGEST_ROOT_CAUSE = UNDETERMINED`; o finding permanece aberto e não resolvido. A PoC Hikvision ISAPI mínima está planejada dentro de P2, mas não implementada nem autorizada; o adapter completo continua em P7.

O próximo trabalho é `P2-A01 — Define P2 Architecture Contract`. Permanecem pendentes campos obrigatórios, cobertura/completude, estruturas tipadas, proveniência/conflitos, mecanismo ONVIF, fallback após erro de autenticação, limites, trust/TLS/destinos, expansão de resultado, registro de adapters, aceite da PoC e validação. `P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`.

Baseline inicial: `master` / `27582e1a3e26d861a94ece15c5d50a7348a8482f`; branch e HEAD foram verificados antes da edição. O relatório estava presente neste commit. Relação do HEAD atual com o remoto não foi revalidada. Arquivos locais `docs/policies/`, `onvif_auth_test.py` e `onvif_preauth_test.py` estavam untracked e foram preservados. Alterações desta atividade ficam unstaged.

```text
PROJECT = projeto_cam_scanner
ACTIVITY = ARCH-ALIGN-01
STARTING_HEAD = 27582e1a3e26d861a94ece15c5d50a7348a8482f
AUDIT_REPORT = docs/audit/ARCH_AUDIT_01_REPORT.md
AUDIT_PRESERVED = YES
ARCHITECTURAL_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE
DIRECTION_DOCUMENTED = PASS
ARCHITECTURE_DOC_UPDATE = PASS (roadmap and execution plan; no separate architecture/ADR authority exists)
ROADMAP_UPDATE = PASS
EXECUTION_PLAN_UPDATE = PASS
CONTINUITY_UPDATE = PASS
AUDIT_FINDINGS_TRACEABILITY = PASS
P1_HISTORICAL_INTEGRITY = PASS
P1_STATUS = CLOSED
P2_STATUS = CONTRACT_PENDING
P2_DETAILED_CONTRACT = PENDING
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
ONVIF_DIGEST_FINDING = OPEN; ROOT_CAUSE = UNDETERMINED
HIKVISION_ISAPI_POC = PLANNED_NOT_IMPLEMENTED
CONTRACT_CHANGE = NONE_IMPLEMENTED
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
DOCUMENTS_MODIFIED = docs/continuity/planning/ROADMAP.md; docs/continuity/planning/EXECUTION_PLAN.md; docs/continuity/ACTIVE_AUTHORITY_MAP.md; docs/continuity/START_HERE.md; docs/continuity/PROJECT_STATE.md; docs/continuity/CONTINUITY_RECORD.md; docs/continuity/handoff/LAST_HANDOFF.md; docs/contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md (scope note only)
DOCUMENTS_CREATED = NONE
DOCUMENTARY_CONTRADICTIONS = NONE in active state; P1 contract remains scoped to closed P1
GIT_DIFF_CHECK = PASS
GIT_WRITES = NONE
NEXT_ACTIVITY = P2-A01 — Define P2 Architecture Contract
STATUS = COMPLETED_WITH_FINDINGS
ACTIVITY_COMPLETION_PERCENT = 100%
COMPLETION_BASIS = Documentary reconciliation only; no P2 implementation included
SAFE_RESUME_POINT = Define the detailed P2 contract; no implementation without separate authority
AGENT_HANDOFF_GATE = PASS; remote parity not revalidated
```
