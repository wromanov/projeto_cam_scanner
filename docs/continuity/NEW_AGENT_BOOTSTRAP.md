# Bootstrap para novo agente

```text
IDIOMA = pt-BR
ROLE = SCRIBE
PROJECT = projeto_cam_scanner
FIRST_RESPONSE_MODE = RESUME_P1_A04_AFTER_ACTIVITY_DEFINITION_AND_AUTHORIZATION
CHAT_HISTORY_REQUIRED_FOR_RESUMPTION = NO
IMPLEMENTATION_AUTHORIZATION = NONE_FOR_P1_A04
GIT_WRITE_AUTHORIZATION = NOT_GRANTED_FOR_FUTURE_ACTIONS
```

1. Leia `AGENTS.md` e `docs/continuity/START_HERE.md`.
2. Valide `PROJECT_GOVERNANCE_BINDING.json` contra o schema externo do Continuity 3.0.
3. Resolva cada authority por `id + version + sha256`; use `locator` apenas como pista. Não substitua pins por versões globais mais recentes.
4. Confirme fatos mutáveis do projeto e filesystem. O primeiro checkpoint foi publicado em `origin/master`; confirme branch, HEAD, upstream e estado de trabalho novamente em runtime.
5. Leia `PROJECT_STATE.md`, `ACTIVE_AUTHORITY_MAP.md`, `CONTINUITY_RECORD.md`, roadmap, execution plan e `LAST_HANDOFF.md`.
6. Leia o recheck `FOUNDATION_REVIEW_P0_A04.md` e o contrato P1 em `../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`. Resolva os pins conforme ACTIVE_AUTHORITY_MAP. P1-A01 é o baseline implementado sob a estratégia anterior. P1-A02 é evidência histórica; não retomar apenas para obter autenticação ONVIF válida. P1-A03 aprovou `VENDOR_FIRST_WHEN_KNOWN`, mas a adaptação ainda não foi implementada. Preserve credenciais individuais por câmera e o limite READ_ONLY. Não implementar sem autorização específica para P1-A04.

Este bootstrap descreve recuperação e não concede autorização para executar a próxima atividade.
