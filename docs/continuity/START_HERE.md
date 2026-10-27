# CAM SCANNER — continuidade do projeto

Use esta página para retomar o trabalho sem depender do histórico do chat.

## Estado e plano

- [`PROJECT_STATE.md`](PROJECT_STATE.md): estado factual, gates, autorização e ponto seguro de retomada.
- [`ACTIVE_AUTHORITY_MAP.md`](ACTIVE_AUTHORITY_MAP.md): authorities ativas e localizadores.
- [`CONTINUITY_RECORD.md`](CONTINUITY_RECORD.md): decisões, achados e pendências.
- [`PROJECT_GOVERNANCE_BINDING.json`](PROJECT_GOVERNANCE_BINDING.json): baseline adotado e pins por identidade, versão e SHA-256.
- [`planning/ROADMAP.md`](planning/ROADMAP.md): roadmap aprovado.
- [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md): sequência de atividades e critérios de saída.
- [`../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`](../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md): contrato e baseline histórica P1 (`VENDOR_FIRST_WHEN_KNOWN`), válida para a P1 fechada.
- [`../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`](../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md): contrato P2-A01 aprovado em 2026-10-09 (D00–D06); P2 continua aberta e D07 diferida.
- [`../audit/ARCH_AUDIT_01_REPORT.md`](../audit/ARCH_AUDIT_01_REPORT.md): relatório original preservado; fonte da direção híbrida aprovada para planejamento P2.
- A direção corrente após P1 está registrada em [`planning/ROADMAP.md`](planning/ROADMAP.md) e [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md): `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`; P2-I1 offline concluiu F01–F03 e a revisão independente V2 passou. A homologação real está pendente e P2 continua aberta.
- [`handoff/LAST_HANDOFF.md`](handoff/LAST_HANDOFF.md): estado da revisão independente e preflight atual. O checkpoint Git P2-I1 está pronto, mas ainda não publicado; a publicação é a próxima ação após aprovação do usuário.
- [`NEW_AGENT_BOOTSTRAP.md`](NEW_AGENT_BOOTSTRAP.md): instruções para novo agente.

## Regras de retomada

Leia `AGENTS.md`, este pacote e resolva os pins do binding por identidade e hash. O root de governança global fica na pasta irmã `governanca_de_projetos`; redescubra-a pelo binding e artefatos canônicos, sem assumir caminho de usuário ou drive. O checkpoint P1 está publicado em `origin/master`; o checkpoint P2-I1 permanece pendente de publicação. Confirme branch, HEAD, upstream e estado de trabalho em runtime antes de retomar em outro computador.

## Estado histórico após P1-C01-R2 (supersedido por P1-A01)

P0-A04 permanece como revisão concluída com `PASS_WITH_ACCEPTED_FINDINGS`; evidência em [`../audit/FOUNDATION_REVIEW_P0_A04.md`](../audit/FOUNDATION_REVIEW_P0_A04.md). P0-A05-R1 reconciliou a aprovação já concedida: Project Opening Gate `PASS` e P0 `CLOSED`. P1-C01-R1 reconciliou os 14 campos de `CameraResult`; P1-C01-R2 fechou as tipagens. PROJECT_STATE é a fonte do estado corrente; P0-A02 permanece histórico. Os pins foram resolvidos nos ZIPs exatos indicados em ACTIVE_AUTHORITY_MAP.

## Estado histórico após P1-A03 (superado pelo checkpoint P1-CHECKPOINT-01)

P1-A01 implementou e integrou a slice SINGLE sob a estratégia ONVIF-first anterior. P1-A02 e P1-A03 são registros históricos; o estado atual está em `PROJECT_STATE.md` e no handoff mais recente.
## Checkpoint vigente — 2026-10-27

Consulte [`checkpoints/CAM_SCANNER_PRE_IMPLEMENTATION_CHECKPOINT_2026_10_27.md`](checkpoints/CAM_SCANNER_PRE_IMPLEMENTATION_CHECKPOINT_2026_10_27.md). A baseline confirmada é a branch `feature/pre-p12-unified-remediation` no HEAD `37bc8c4`; a implementação P0/P1/TRANSPORT ainda não começou.
