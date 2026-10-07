# CAM SCANNER — continuidade do projeto

Use esta página para retomar o trabalho sem depender do histórico do chat.

## Estado e plano

- [`PROJECT_STATE.md`](PROJECT_STATE.md): estado factual, gates, autorização e ponto seguro de retomada.
- [`ACTIVE_AUTHORITY_MAP.md`](ACTIVE_AUTHORITY_MAP.md): authorities ativas e localizadores.
- [`CONTINUITY_RECORD.md`](CONTINUITY_RECORD.md): decisões, achados e pendências.
- [`PROJECT_GOVERNANCE_BINDING.json`](PROJECT_GOVERNANCE_BINDING.json): baseline adotado e pins por identidade, versão e SHA-256.
- [`planning/ROADMAP.md`](planning/ROADMAP.md): roadmap aprovado.
- [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md): sequência de atividades e critérios de saída.
- [`handoff/LAST_HANDOFF.md`](handoff/LAST_HANDOFF.md): handoff deste checkpoint.
- [`NEW_AGENT_BOOTSTRAP.md`](NEW_AGENT_BOOTSTRAP.md): instruções para novo agente.

## Regras de retomada

Leia `AGENTS.md`, este pacote e resolva os pins do binding por identidade e hash. O root de governança global está fora deste projeto e deve ser redescoberto por seus arquivos canônicos; neste ambiente ele fica em `../governança_de_projetos/`. O repositório Git existe: confirme branch, HEAD e estado de trabalho em runtime; no checkpoint P0-A03, `master` tem zero commits e ainda não tem HEAD válido.

P0-A02 executou Foundation Review com resultado `CHANGES_REQUIRED`; decisões F-01…F-08 e remediação estão registradas em `PROJECT_STATE.md` e `CONTINUITY_RECORD.md`. `PROJECT_OPENING_GATE` e `AGENT_HANDOFF_GATE` refletem somente evidências registradas no pacote. Nenhum gate concede autorização de implementação ou publicação Git. P1 permanece planejada e não autorizada.
