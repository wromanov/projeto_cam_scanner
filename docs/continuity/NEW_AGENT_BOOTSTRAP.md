# Bootstrap para novo agente

```text
IDIOMA = pt-BR
ROLE = VALIDATOR
PROJECT = projeto_cam_scanner
FIRST_RESPONSE_MODE = RESUME_BLOCKED_P1_A02_AFTER_ONVIF_AUTHENTICATION_REMEDIATION
CHAT_HISTORY_REQUIRED_FOR_RESUMPTION = NO
IMPLEMENTATION_AUTHORIZATION = NONE_FOR_P1_A02; do not implement code
GIT_WRITE_AUTHORIZATION = NOT_GRANTED_FOR_FUTURE_ACTIONS
```

1. Leia `AGENTS.md` e `docs/continuity/START_HERE.md`.
2. Valide `PROJECT_GOVERNANCE_BINDING.json` contra o schema externo do Continuity 3.0.
3. Resolva cada authority por `id + version + sha256`; use `locator` apenas como pista. Não substitua pins por versões globais mais recentes.
4. Confirme fatos mutáveis do projeto e filesystem. O primeiro checkpoint foi publicado em `origin/master`; confirme branch, HEAD, upstream e estado de trabalho novamente em runtime.
5. Leia `PROJECT_STATE.md`, `ACTIVE_AUTHORITY_MAP.md`, `CONTINUITY_RECORD.md`, roadmap, execution plan e `LAST_HANDOFF.md`.
6. Leia o recheck `FOUNDATION_REVIEW_P0_A04.md` e o contrato aprovado em `../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`. Resolva os pins em ZIP conforme ACTIVE_AUTHORITY_MAP. P0-A02 é histórica e a Foundation Approval foi concedida. P1-A01 implementou o fluxo SINGLE e as validações sintéticas foram aprovadas. P1-A02 executou contra o alvo autorizado `10.143.36.33`, mas três tentativas retornaram `AUTH_ERROR`; nenhum dado de dispositivo foi obtido. Retome após confirmar uma conta com autenticação e permissão ONVIF; não buscar nem reutilizar secrets locais. A senha deve ser fornecida pelo prompt local `getpass()`. Não implementar código nem executar operações fora do fluxo P1.

Este bootstrap descreve recuperação e não concede autorização para executar a próxima atividade.
