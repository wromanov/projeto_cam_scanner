# Roadmap aprovado — projeto_cam_scanner

| Fase | Escopo e objetivo | Estado |
|---|---|---|
| P0 | Project Opening + Foundation | CLOSED; Foundation Approval `APPROVED_WITH_ACCEPTED_FINDINGS`; Project Opening Gate `PASS` (P0-A05-R1) |
| P1 | SINGLE Minimum Vertical Slice: fluxo real end-to-end para uma câmera, sob a estratégia então vigente `VENDOR_FIRST_WHEN_KNOWN` | CLOSED; P1-A04 implementada e validada sinteticamente; P1-A05 validada operacionalmente com evidência pré-auth preservada como `PARTIAL_SUCCESS`; finding ONVIF Digest aberto |
| P2 | Contrato da política híbrida e evolução da coleta SINGLE/inventário | Contrato P2-A01 `APPROVED` em 2026-10-09 (D00–D06); fase P2 permanece aberta; implementação não autorizada |
| P3 | SINGLE Snapshot Vertical Slice: captura e processamento de snapshot; sem XLSX | Planejada |
| P4 | MULTI + XLSX Vertical Slice: entrada em lote, progresso, INVENTARIO/RESUMO e snapshot embutido | Planejada |
| P5 | MULTI Concurrency / Batch Robustness: limites, cancelamento, exportação parcial e isolamento de falhas | Planejada |
| P6 | Axis Adapter | Planejada |
| P7 | Hikvision Adapter | Planejada |
| P8 | Samsung/Hanwha Adapter | Planejada |
| P9 | Dahua Adapter | Planejada |
| P10 | Panasonic Adapter | Planejada |
| P11 | Bosch Adapter | Planejada |
| P12 | Hardening / Regression / Packaging | Planejada |

## Dependências e integração

- P1 estabeleceu a slice SINGLE integrada; P1-A04 adaptou o baseline para `VENDOR_FIRST_WHEN_KNOWN`; P1-A05 e seu DoD foram fechados com evidência READ_ONLY parcial conforme o contrato vigente.
- P2 segue a direção aprovada `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, preservando o monólito modular e a baseline P1. Seu contrato precede qualquer implementação e define política determinística por fabricante/capacidade, campos necessários, evidências já obtidas, autenticação disponível e budgets. ONVIF permanece genérico, para descoberta quando aplicável, fallback ou complemento justificado; não é obrigatório em toda consulta quando fabricante e caminho nativo válido já forem conhecidos.
- P2 planeja: (A) contrato da política híbrida; (B) preservação de evidências; (C) resolução de fabricante; (D) diagnóstico por etapa/operação; (E) seleção controlada de autenticação ONVIF; (F) proveniência e merge; (G) PoC mínima Hikvision ISAPI; (H) validação operacional futura sob autorização própria; (I) expansão incremental de inventário e rede. A PoC é escopo planejado, não autorização de implementação. O adapter Hikvision completo permanece em P7.
- P2 não permite tentativas autenticadas sequenciais contra fabricantes, reconfiguração automática de câmeras ou provisionamento obrigatório de contas ONVIF em massa. READ_ONLY, credenciais por câmera, ausência de credential spraying e ausência de senhas em saídas são obrigatórios.
- P2-A01 e sua reconciliação documental produziram [`P2_COLLECTION_STRATEGY_EXPANSION.md`](../../contracts/P2_COLLECTION_STRATEGY_EXPANSION.md) como contrato aprovado em 2026-10-09 (D01 `APPROVED_WITH_REVISION`; D02–D06 `APPROVED_WITH_ADJUSTMENTS`; D00 já aprovada). D07 permanece diferida. P0 e P1 permanecem `CLOSED`; a fase P2 não foi encerrada. A aprovação não concede implementação nem validação operacional.
- ARCH-ALIGN-01 registra a evolução documental `PREVIOUS = VENDOR_FIRST_WHEN_KNOWN` → `APPROVED_DIRECTION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, com `DECISION_STATUS = DIRECTION_APPROVED` e fonte [`ARCH_AUDIT_01_REPORT.md`](../../audit/ARCH_AUDIT_01_REPORT.md). A P1 permanece fechada segundo seu contrato e não é reescrita por esta direção para P2. O finding ONVIF Digest segue aberto; `ONVIF_DIGEST_ROOT_CAUSE = UNDETERMINED`.
- P3 integra snapshot ao fluxo SINGLE; não produz XLSX.
- P4 introduz MULTI e XLSX. É o primeiro ponto em que MULTI, XLSX e snapshot embedded coexistem no fluxo canônico.
- P5 robustece o lote de P4, incluindo concorrência controlada.
- P6–P11 expandem adaptadores sobre os fluxos integrados, conforme contratos e aceite de cada fase. A ordem existente Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic e Bosch é preservada; o alvo usado na evidência real não reordena o roadmap.
- P12 executa hardening, regressão e packaging operacional; build operacional exige TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER.

A sequência cumpre `INCREMENTAL_INTEGRATION_RULE`: cada slice deve integrar ao fluxo canônico e validar o fluxo acumulado antes do avanço dependente. `DEFINITION_OF_READY` e `DEFINITION_OF_DONE` são detalhadas no `EXECUTION_PLAN.md` e na autoridade PM-01. Nenhuma fase planejada concede autorização de implementação.
