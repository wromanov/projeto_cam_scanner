# Roadmap aprovado — projeto_cam_scanner

| Fase | Escopo e objetivo | Estado |
|---|---|---|
| P0 | Project Opening + Foundation | Em andamento; P0-A02 review `CHANGES_REQUIRED`; P0-A03 concluída; recheck e gates pendentes |
| P1 | SINGLE Minimum Vertical Slice: fluxo real end-to-end para uma câmera por ONVIF read-only | Planejada; implementação não autorizada |
| P2 | SINGLE ONVIF Inventory Expansion: hostname, rede, MAC, portas e demais campos aplicáveis | Planejada |
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

- P1 estabelece a primeira slice integrada ao fluxo canônico: menu → SINGLE → consulta ONVIF read-only → resultado normalizado → terminal e menu pós-consulta.
- P2 expande o inventário SINGLE sobre a base integrada de P1.
- P3 integra snapshot ao fluxo SINGLE; não produz XLSX.
- P4 introduz MULTI e XLSX. É o primeiro ponto em que MULTI, XLSX e snapshot embedded coexistem no fluxo canônico.
- P5 robustece o lote de P4, incluindo concorrência controlada.
- P6–P11 expandem adaptadores sobre os fluxos integrados, conforme contratos e aceite de cada fase.
- P12 executa hardening, regressão e packaging operacional; build operacional exige TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER.

A sequência cumpre `INCREMENTAL_INTEGRATION_RULE`: cada slice deve integrar ao fluxo canônico e validar o fluxo acumulado antes do avanço dependente. `DEFINITION_OF_READY` e `DEFINITION_OF_DONE` são detalhadas no `EXECUTION_PLAN.md` e na autoridade PM-01. Nenhuma fase planejada concede autorização de implementação.
