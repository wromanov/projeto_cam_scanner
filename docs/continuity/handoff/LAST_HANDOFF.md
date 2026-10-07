# Last Handoff — P1-CHECKPOINT-01 (published)

P1-A04 implementou e integrou `VENDOR_FIRST_WHEN_KNOWN` no fluxo SINGLE canônico. A sequência começa com descoberta ONVIF anônima/read-only; resolve fabricante por evidência estrutural; consulta apenas o adapter registrado daquele fabricante; e usa ONVIF genérico quando o fabricante é desconhecido, não há adapter, ou o caminho vendor não produz resultado. Quando adapter registrado omite dados P1, ONVIF complementa os campos ausentes sem substituir os valores vendor. Não há adapters vendor funcionais registrados nesta fase.

A descoberta pré-autenticação não recebe credenciais. O caminho vendor e a autenticação ONVIF recebem o `CameraTarget` corrente. `TRY_ALL_VENDOR_LOGINS` está estruturalmente ausente. Evidência pré-auth válida com falha posterior de autenticação ONVIF produz `PARTIAL_SUCCESS`; sem evidência pré-auth válida a coleta falha normalmente. A entrada SINGLE permanece IP, username e password, sem prompt novo de fabricante. O resultado mantém os 14 campos e não contém senha.

P1-A05 foi reconciliada a partir da evidência operacional autorizada: target `10.143.36.33`; descoberta pré-auth PASS; fabricante Hikvision; coleta autenticada ONVIF retornou `AUTH_ERROR`; tratamento da falha e semântica `PARTIAL_SUCCESS` PASS; proteção de senha PASS; chamadas mutantes zero. A falha ONVIF Digest permanece `OPEN_NON_BLOCKING`. Nenhuma senha, username ou header de autorização foi registrado.

O contrato P1 foi atualizado para explicitar que evidência READ_ONLY pré-auth válida, preservada como `PARTIAL_SUCCESS`, satisfaz o DoD operacional sem exigir autenticação ONVIF bem-sucedida. P1 está fechada; próxima atividade é definição/contrato de P2. Implementação P2 não autorizada.

Validação do checkpoint: Python 3.14.0, pytest 51 PASS, Ruff PASS, CLI smoke PASS, `git diff --check` PASS, security PASS e source scope P1 PASS. Scripts diagnósticos e cópias locais de políticas foram excluídos. Os seis commits pendentes foram publicados em `origin/master`; fetch posterior confirmou `LOCAL_HEAD == ORIGIN_MASTER_HEAD == ec53d2bd08b8bf0ee0d82b1411122f246502e820`. Os scripts diagnósticos e cópias locais de políticas continuam untracked e excluídos.

```text
PROJECT = projeto_cam_scanner
ACTIVITY = P1-CHECKPOINT-01
STARTING_HEAD = b6c3c09fc2588af1d800c5450845a510fc7333ca
IMPLEMENTATION_STATUS = COMPLETE
COLLECTION_STRATEGY = VENDOR_FIRST_WHEN_KNOWN
CANONICAL_FLOW_IMPLEMENTED = YES
VENDOR_FIRST_ROUTING = PASS
MANUFACTURER_HINT_SUPPORT = NOT_REQUIRED_BY_CONTRACT
PREAUTH_FINGERPRINT = PASS
UNKNOWN_MANUFACTURER_FLOW = PASS
KNOWN_MANUFACTURER_WITHOUT_ADAPTER = PASS
ONVIF_ROLE = PASS
ONVIF_AUTH_FAILURE_SEMANTICS = PASS
PARTIAL_SUCCESS = PASS
MANUFACTURER_MISMATCH = PASS
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
PYTHON_3_14 = PASS
PYTEST = PASS (51 tests)
RUFF = PASS
CLI_SMOKE = PASS
REAL_CAMERA_VALIDATION = PASS_WITH_PARTIAL_SUCCESS
TARGET_AUTHORIZED = YES
OPERATIONAL_CAMERA_RESULT = PARTIAL_SUCCESS
PREAUTH_DISCOVERY = PASS
MANUFACTURER_RESOLUTION = HIKVISION
ONVIF_AUTHENTICATED_COLLECTION = AUTH_ERROR
AUTH_FAILURE_SEMANTICS = PASS
PARTIAL_SUCCESS_SEMANTICS = PASS
PASSWORD_SECURITY = PASS
MUTATING_CALLS = 0
ONVIF_DIGEST_INTEROPERABILITY_FINDING = OPEN_NON_BLOCKING
REGRESSION = PASS
CONTRACT_GAP = NONE
ARCHITECTURE_CHANGE = NONE
DOMAIN_CONTRACT_CHANGE = NONE
PROJECT_STATE_UPDATE = PASS
CONTINUITY_UPDATE = PASS
P1_CLOSURE = PASS
P1_STATUS = CLOSED
UNRESOLVED_BLOCKERS = NONE
NEXT_PHASE = P2
NEXT_ACTIVITY = P2 definition/contract according to canonical roadmap
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
GIT_PUSH = PASS
PUSHED_COMMIT_COUNT = 6
LOCAL_HEAD = ec53d2bd08b8bf0ee0d82b1411122f246502e820
ORIGIN_MASTER_HEAD = ec53d2bd08b8bf0ee0d82b1411122f246502e820
LOCAL_REMOTE_MATCH = YES
CROSS_COMPUTER_CONTINUITY = PASS
STATUS = COMPLETED_WITH_FINDINGS
ACTIVITY_COMPLETION_PERCENT = 100%
COMPLETION_BASIS = P1-A04, P1-A05 evidence reconciliation, P1 closure, published checkpoint, and local/remote parity
SAFE_RESUME_POINT = Define/approve P2 contract; do not begin P2 implementation without separate authority
AGENT_HANDOFF_GATE = PASS
```
