# Validação offline — Vendor First Runtime Correction R2

```text
ACTIVITY = VENDOR_FIRST_RUNTIME_CORRECTION_R2
VALIDATION_SCOPE = IMPLEMENT_TEST_VALIDATE (offline)
OVERALL_RESULT = PASS_OFFLINE
REAL_CAMERA_VALIDATION = DEFERRED (AC-19)
BUILD_OR_PUBLISH = NOT_RUN
GIT_CONSEQUENTIAL_ACTIONS = NONE
```

Este relatório registra resultados informados pelo executor da atividade e associa cada critério do [contrato R2](../contracts/VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT_R2.md) às evidências de teste existentes. A inspeção dos testes abaixo é de escopo e cobertura; nenhum teste foi executado durante a materialização deste relatório. Testes citados usam fakes, spies, fixtures e/ou workbook local; não demonstram interoperabilidade com câmera física.

## Resultado de validação

| Verificação | Resultado informado |
|---|---|
| Regressão pós-delta final (após fechar a lacuna AC-12 SINGLE) | `389 passed, 0 failed, 0 skipped, 0 deselected` em 55.69s; Python 3.14.0; pytest 9.1.1 |
| Invocação da suíte | pytest com plugins `no:cacheprovider` e `no:tmpdir`; fixture `tmp_path` local configurada por ACL |
| Ruff nos arquivos do delta R2 | PASS |
| `compileall src/cam_scanner` | PASS |
| `git diff --check` | PASS; somente avisos de conversão LF/CRLF |
| Architect Gate 3 | PASS (revisão independente, conforme resultado informado pelo executor) |
| Gate 2 | PASS para regressão integrada do delta, conforme 389/0/0 informado |
| Gate V | PASS para a regressão completa pós-delta, conforme 389/0/0 informado |
| Gate 4 | PASS para reavaliação de prontidão restrita ao R2; pronto para uma nova build Windows quando essa etapa tiver autorização própria |
| AC-19 / câmera real | DEFERRED; nenhum dispositivo real foi acessado |
| Build Windows / publicação | NOT_RUN / NOT_AUTHORIZED nesta atividade |

O `PROJECT_STATE.md` já registrava Gate 2/3/4/V como PASS na etapa antecedente P12. Esses resultados históricos não são usados como prova do delta: Gate 2, Gate 3, Gate 4 e Gate V acima referem-se à evidência pós-delta informada para esta R2. O Gate 4 não significa que a build foi realizada; a prontidão fica limitada à próxima etapa de build Windows.

## Matriz AC-01–AC-18 e AC-20

| Critério | Resultado | Evidência relacionada | Limite da evidência |
|---|---|---|---|
| AC-01 | PASS_OFFLINE | `tests/test_multi_workflow.py::test_multi_row_routes_one_adapter_from_hint_or_onvif_discovery`; `tests/test_vendor_first_runtime_correction_r2.py::test_r2_single_hint_uses_eligible_vendor_before_any_onvif_discovery` | Roteamento com hint demonstrado por adapter fixture e spy que proíbe discovery. Não valida endpoint/vendor real. |
| AC-02 | PASS_OFFLINE | `tests/test_multi_workflow.py::test_multi_row_routes_one_adapter_from_hint_or_onvif_discovery`; `tests/test_p1_vendor_first_strategy.py::test_absent_manufacturer_runs_preauth_before_generic_onvif`; `tests/test_pre_p12_entrypoint_matrix.py::test_single_entrypoint_discovers_routes_falls_back_and_renders_identity` | Identificação automática usa sinais e serviços fake/autorizados; não mede famílias/modelos físicos não cobertos pelas fixtures. |
| AC-03 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_strong_bosch_discovery_never_invokes_unsupported_adapter`; `tests/test_bosch_onvif_fallback.py::test_bosch_vendor_gap_skips_io_and_generic_onvif_collects_identity` | Demonstra que Bosch registrado, sem suporte nativo para manufacturer/model/serial, não é tratado como adapter de identidade elegível e segue ONVIF genérico. Não prova cobertura para todos os fabricantes não listados. |
| AC-04 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_non_tls_vendor_failure_preserves_attempt_and_uses_allowed_onvif_fallback` | Exercita falha vendor não TLS e fallback com doubles; não valida todos os erros/firmwares vendor reais. |
| AC-05 | PASS_OFFLINE | parâmetro `discovery` de `tests/test_vendor_first_runtime_correction_r2.py::test_r2_tls_error_is_terminal_for_all_later_network_attempts`; `tests/test_target_transport.py::test_tls_auth_failure_and_nonretryable_soap_are_not_retried` | Confirma ausência de fallback/downgrade após TLS em fixture; não é homologação de certificados de câmera real. |
| AC-06 | PASS_OFFLINE | parâmetro `vendor` de `tests/test_vendor_first_runtime_correction_r2.py::test_r2_tls_error_is_terminal_for_all_later_network_attempts` | Confirma encerramento após TLS no adapter fixture; não valida matriz de certificados de dispositivos físicos. |
| AC-07 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_vendor_observation_preserves_a_strong_hint_mismatch`; `test_r2_single_diagnostics_display_declared_observed_and_resolved_mismatch`; `test_r2_diagnostics_sheet_is_ordered_sanitized_and_formula_safe`; `tests/test_p2_i1_collection.py::test_hint_never_overrides_conflicting_strong_observed_manufacturers` | Demonstra preservação e exibição de DECLARED/OBSERVED/RESOLVED e aviso sanitizado em fixtures/workbook; não estabelece qualidade de sinal em todos os modelos reais. |
| AC-08 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_conflicting_strong_discovery_is_independent_of_response_order`; `tests/test_p2_i1_collection.py::test_f02_conflicting_signal_order_does_not_change_resolution` | Inverte a ordem de dois sinais fortes em fixture e verifica resolução determinística; sem inferência para sinais não estruturados fora do resolver. |
| AC-09 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_weak_manufacturer_signals_do_not_route_vendor_without_a_hint`; `tests/test_p2_i1_collection.py::test_f02_weak_model_oem_and_substring_false_positive_do_not_resolve_vendor` | Cobre os sinais fracos especificados em fixtures; não constitui inventário universal de banners/OEMs. |
| AC-10 | PASS_OFFLINE | `tests/test_pre_p12_entrypoint_matrix.py::test_single_entrypoint_discovers_routes_falls_back_and_renders_identity` (fabricante vazio e seleção automática) | Caminho SINGLE com transporte fake; não consulta câmera real. |
| AC-11 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_single_hint_uses_eligible_vendor_before_any_onvif_discovery` | Executa SINGLE com hint elegível por UI fixture; descoberta e ONVIF autenticado são spies proibidos. Não valida entrada de modelo fora das famílias suportadas. |
| AC-12 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_single_unknown_hint_keeps_automatic_discovery_and_onvif_fallback`; `test_r2_unknown_declared_hint_is_retained_without_selecting_a_vendor`; `test_r2_multi_reader_preserves_literal_alias_and_unknown_hints` | Verifica no SINGLE que hint desconhecido mantém discovery automática e fallback ONVIF autorizado, além da preservação literal no leitor MULTI; fixtures não representam sessões físicas. |
| AC-13 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_diagnostics_sheet_is_ordered_sanitized_and_formula_safe` | Lê workbook criado localmente e verifica linha/tentativa e ordem; não é exportação de inventário coletado em câmera real. |
| AC-14 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_diagnostics_sheet_is_ordered_sanitized_and_formula_safe`; `tests/test_p2_i1_collection.py::test_attempt_and_report_reprs_exclude_secrets_and_raw_diagnostic_fields` | Valores canário verificam a fronteira XLSX/representação; não substitui revisão de cada destino de logging/UI futuro. |
| AC-15 | PASS_OFFLINE | `tests/test_vendor_first_runtime_correction_r2.py::test_r2_diagnostics_sheet_is_ordered_sanitized_and_formula_safe`; `tests/test_excel_writer_sanitization.py::test_writer_protects_formula_and_keeps_valid_xlsx_rows` | Fórmulas/caráteres de controle são verificados em workbook local; não testa todos os leitores de planilha de terceiros. |
| AC-16 | PASS_OFFLINE | `tests/test_collection_context.py::test_auth_ledger_counts_digest_challenge_physically_but_not_logically`; `test_second_logical_attempt_requires_missing_identity_and_single_vendor_family`; `tests/test_target_transport.py::test_unsupported_401_challenge_closes_auth_scope_without_network_replay` | Confirma ledger e casos sintéticos de challenge/rejeição; não testa política de autenticação em câmeras físicas. |
| AC-17 | PASS_OFFLINE | `tests/test_collection_context.py::test_source_and_camera_deadlines_are_monotonic_and_cumulative`; `tests/test_pre_p12_budget_acceptance.py::test_multi_deadline_starts_before_queue_and_is_shared_with_snapshot`; `test_expired_camera_budget_stops_vendor_and_onvif_acquisition_phases` | Relógio fake e execução controlada; chamadas de biblioteca já bloqueadas não são garantia de interrupção hard-timeout. |
| AC-18 | PASS_OFFLINE | `tests/test_p1_domain.py::test_camera_result_has_exactly_the_approved_14_fields`; `tests/test_pre_p12_entrypoint_matrix.py::test_multi_entrypoint_exports_synthetic_family_results_in_input_order`; teste de diagnóstico R2 | Confirma estrutura/status/exportação sintéticos; não afirma completude de identidade de equipamento real. |
| AC-19 | DEFERRED | Sem teste operacional nesta atividade. | Homologação READ_ONLY depende de autorização, target/credenciais e evidência própria; não faz parte da regressão offline. |
| AC-20 | PASS | Relatório atual; regressão pós-delta final 389/0/0; Ruff direcionado; compileall; diff-check; resultado independente de Architect Gate 3. | Evidência do executor informada para esta atividade; este relatório não reexecutou nem acessou logs brutos. |

## Conclusão e limites

O delta R2 foi validado offline conforme resultados finais informados: regressão completa pós-delta com 389 testes aprovados, sem falhas ou skips, Ruff direcionado, compileall, diff-check e Architect Gate 3 passaram. Os critérios AC-01–AC-18 e AC-20 têm evidência em testes fixture/sintéticos citados; as limitações específicas estão registradas na matriz. AC-19 continua deferido. Não houve câmera real, nova build Windows, publicação ou operação Git consequencial nesta atividade.

```text
GATE_2 = PASS (delta regression, 389 passed / 0 failed / 0 skipped)
GATE_3 = PASS (independent Architect review, result supplied by activity owner)
GATE_4 = PASS (R2 scoped readiness reassessment)
GATE_V = PASS (post-delta full regression, 389 passed / 0 failed / 0 skipped)
P12_READINESS = READY_FOR_NEW_WINDOWS_BUILD (build not performed)
AC_19 = DEFERRED
REAL_CAMERA = NOT_ACCESSED
WINDOWS_BUILD = NOT_RUN
PUBLISH = NOT_RUN
GIT_CONSEQUENTIAL_ACTIONS = NONE
```
