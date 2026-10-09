# Mapa de authorities ativas

| Escopo | Authority | Identidade / versão | Estado | Localizador |
|---|---|---|---|---|
| Governance baseline | Matriz Unificada | PM-00 / 1.0 | CANONICAL / ACTIVE | `../governanca_de_projetos/Matriz Unificada de Políticas/` |
| Condução e continuidade | PM-01 | 1.0 | CANONICAL / ACTIVE | Registry PM-00 / `policies/PM-01-Conducao-de-Projetos-v1.0.md` |
| Prompts e payloads | PM-02 | 1.7-R2.6 | CANONICAL / ACTIVE | Registry PM-00 / `policies/Politica-Prompts-Agente-v1.7-R2.6.md` |
| Multiagente e roteamento | PM-03 | 1.7-R2.3 | CANONICAL / ACTIVE | Registry PM-00 / `policies/AGENTS-Multiagente-Generico-v1.7-R2.3-Roteamento-Economico.md` |
| Skills e plugins | PM-04 | 1.2 | CANONICAL / ACTIVE | Registry PM-00 / `policies/Politica-de-Uso-de-Skills-e-Plugins-Codex-Work-v1.2.md` |
| Independência analítica | PM-05 | v1 | CANONICAL / ACTIVE | Registry PM-00 / `policies/Independencia-Analitica-Agente-v1.md` |
| Validação de internalização | VP-01 | v2.0 | CANONICAL / ACTIVE; VALIDATION_ONLY | Registry PM-00 / `validation/Gate-de-Internalizacao-Operacional-v2.0.md` |
| Abertura do projeto | PROJECT_OPENING | 3.0 | CANONICAL / ACTIVE | Pacote Project Opening 3.0 / `OPENING_PROTOCOL.md` |
| Continuidade | CONTINUITY | 3.0 | CANONICAL / ACTIVE | Pacote Continuity 3.0 / `CONTINUITY_PROTOCOL.md` |
| Contrato P1 SINGLE (baseline histórico) | Contrato P1-C01/P1-A03 + P1-A05 | `VENDOR_FIRST_WHEN_KNOWN`; DoD satisfeito com evidência operacional `PARTIAL_SUCCESS` | CLOSED / P1 válida sob seu contrato | `../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md` |
| Contrato de expansão de coleta P2 | P2-A01; reconciliação de aprovação em 2026-10-09 | `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`; D00–D06 aprovadas; D07 diferida | APPROVED; P2 permanece aberta e implementação não autorizada | [`../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`](../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md) |
| Direção arquitetural após P1 | ARCH-ALIGN-01; decisão de direção baseada na auditoria independente | `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`; contrato P2 aprovado | DIRECTION_APPROVED; P2 contract APPROVED; implementação não autorizada | `planning/ROADMAP.md`, `planning/EXECUTION_PLAN.md`; fonte [`../audit/ARCH_AUDIT_01_REPORT.md`](../audit/ARCH_AUDIT_01_REPORT.md) |

Os pins completos e hashes estão em `PROJECT_GOVERNANCE_BINDING.json`. A resolução usou o `POLICY_REGISTRY.json` do baseline GOV V1. O binding registra adoção inicial; nenhuma migração foi solicitada. Não copiar nem promover authorities normativas neste projeto.

## Resolução dos bytes adotados — P0-A04

Os arquivos extraídos neste computador não devem ser usados como fonte de hash dos pins. Os pins PM-00…PM-05 e VP-01 foram resolvidos exatamente em `../governanca_de_projetos/Matriz Unificada de Políticas.zip`, membros sob `Matriz Unificada de Políticas/` com os nomes indicados no binding. Opening e Continuity foram resolvidos em `../governanca_de_projetos/Protocolos para Projetos - Vigente/Remediacao Integridade Pacotes 3.0 - 2026-10-05/PROJECT_OPENING_3.0-REMEDIATED-MANIFEST-MATCHED.zip` e `CONTINUITY_3.0-REMEDIATED-MANIFEST-MATCHED.zip`, nos respectivos membros `OPENING_PROTOCOL.md` e `CONTINUITY_PROTOCOL.md`. Identidade, versão e SHA-256 continuam sendo os pins do binding; nenhuma migração foi realizada. A resolução em ZIP é localização alternativa dos mesmos bytes, não nova authority. Evidências: [`FOUNDATION_REVIEW_P0_A04.md`](FOUNDATION_REVIEW_P0_A04.md).
