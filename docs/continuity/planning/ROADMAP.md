# Roadmap aprovado — projeto_cam_scanner

| Fase | Escopo e objetivo | Estado |
|---|---|---|
| P0 | Project Opening + Foundation | CLOSED; Foundation Approval `APPROVED_WITH_ACCEPTED_FINDINGS`; Project Opening Gate `PASS` (P0-A05-R1) |
| P1 | SINGLE Minimum Vertical Slice: fluxo real end-to-end para uma câmera; adaptar a coleta para `VENDOR_FIRST_WHEN_KNOWN` | CLOSED; P1-A04 implementada e validada sinteticamente; P1-A05 validada operacionalmente com evidência pré-auth preservada como `PARTIAL_SUCCESS`; finding ONVIF Digest aberto não bloqueante |
| P2 | SINGLE Collection Strategy + Inventory Expansion: fingerprint, manufacturer resolution, evidence merge e coleta nativa/ONVIF | Planejada; próxima atividade é definição/contrato; implementação não autorizada |
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
- P2 estrutura a expansão da coleta SINGLE: identificação/fingerprint READ_ONLY, resolução do fabricante, merge de evidências e seleção de adapter nativo com ONVIF como complemento/fallback. Não antecipar endpoints proprietários ainda não contratados.
- P3 integra snapshot ao fluxo SINGLE; não produz XLSX.
- P4 introduz MULTI e XLSX. É o primeiro ponto em que MULTI, XLSX e snapshot embedded coexistem no fluxo canônico.
- P5 robustece o lote de P4, incluindo concorrência controlada.
- P6–P11 expandem adaptadores sobre os fluxos integrados, conforme contratos e aceite de cada fase. A ordem existente Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic e Bosch é preservada; o alvo usado na evidência real não reordena o roadmap.
- P12 executa hardening, regressão e packaging operacional; build operacional exige TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER.

A sequência cumpre `INCREMENTAL_INTEGRATION_RULE`: cada slice deve integrar ao fluxo canônico e validar o fluxo acumulado antes do avanço dependente. `DEFINITION_OF_READY` e `DEFINITION_OF_DONE` são detalhadas no `EXECUTION_PLAN.md` e na autoridade PM-01. Nenhuma fase planejada concede autorização de implementação.
