# Bootstrap para novo agente

```text
IDIOMA = pt-BR
ROLE = ROOT_ORCHESTRATOR
PROJECT = projeto_cam_scanner
FIRST_RESPONSE_MODE = RESUME_P2_DEFINITION_CONTRACT_ONLY
CHAT_HISTORY_REQUIRED_FOR_RESUMPTION = NO
P1_STATUS = CLOSED
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
```

1. Leia `AGENTS.md` e `docs/continuity/START_HERE.md`.
2. Valide `PROJECT_GOVERNANCE_BINDING.json` contra o schema externo do Continuity 3.0.
3. Resolva cada authority por `id + version + sha256`; use `locator` apenas como pista. Não substitua pins por versões globais mais recentes.
4. Confirme fatos mutáveis do projeto e filesystem. O primeiro checkpoint foi publicado em `origin/master`; confirme branch, HEAD, upstream e estado de trabalho novamente em runtime.
5. Leia `PROJECT_STATE.md`, `ACTIVE_AUTHORITY_MAP.md`, `CONTINUITY_RECORD.md`, roadmap, execution plan e `LAST_HANDOFF.md`.
6. Leia o recheck `FOUNDATION_REVIEW_P0_A04.md` e o contrato P1 em `../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`. P1 está fechada após validação operacional READ_ONLY com `PARTIAL_SUCCESS`; o finding de interoperabilidade ONVIF Digest é aberto e não bloqueante. Próxima atividade: definição/contrato de P2 conforme roadmap. Não iniciar implementação P2 sem autoridade separada.

Este bootstrap descreve recuperação e não concede autorização para implementação P2.
