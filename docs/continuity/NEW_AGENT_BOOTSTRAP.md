# Bootstrap para novo agente

```text
IDIOMA = pt-BR
ROLE = ROOT_ORCHESTRATOR
PROJECT = projeto_cam_scanner
FIRST_RESPONSE_MODE = READ_ONLY_RECOVERY
CHAT_HISTORY_REQUIRED_FOR_RESUMPTION = NO
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
GIT_WRITE_AUTHORIZATION = NOT_GRANTED_FOR_FUTURE_ACTIONS
```

1. Leia `AGENTS.md` e `docs/continuity/START_HERE.md`.
2. Valide `PROJECT_GOVERNANCE_BINDING.json` contra o schema externo do Continuity 3.0.
3. Resolva cada authority por `id + version + sha256`; use `locator` apenas como pista. Não substitua pins por versões globais mais recentes.
4. Confirme fatos mutáveis do projeto e filesystem. O primeiro checkpoint foi publicado em `origin/master`; confirme branch, HEAD, upstream e estado de trabalho novamente em runtime.
5. Leia `PROJECT_STATE.md`, `ACTIVE_AUTHORITY_MAP.md`, `CONTINUITY_RECORD.md`, roadmap, execution plan e `LAST_HANDOFF.md`.
6. P0-A02 concluiu a Foundation Review com `CHANGES_REQUIRED`, findings F-01…F-08. P0-A03 remediou e reconciliou a Foundation; P0-A03-G1 publicou o checkpoint. Verifique os estados em PROJECT_STATE/LAST_HANDOFF e prepare o recheck da Foundation Review. P1 continua sem autorização; não inicie implementação funcional nem coleta real.

Este bootstrap descreve recuperação e não concede autorização para executar a próxima atividade.
