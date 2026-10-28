# CAM SCANNER — ASTRA Card B: classificação das 53 falhas iniciais

Data: 2026-10-28
Atividade: `CAM_SCANNER_ASTRA_INTEGRATION_REMEDIATION_01`
Baseline confirmada: branch `feature/pre-p12-unified-remediation`, HEAD `deec969880016fb0fe60d737cceac4909313bc56`.

## Resultado

As 53 falhas observadas no primeiro ciclo foram classificadas individualmente abaixo. O ciclo final completo terminou com **451 passed, 0 failed, 0 skipped e 0 deselected**. A classificação explica as falhas iniciais; não transforma por si só cada AC em aprovado. Os IDs foram reconstruídos a partir do primeiro relatório de falhas preservado na execução e da triagem registrada durante a atividade; para grupos parametrizados, todos os parâmetros são enumerados.

| Categoria | Quantidade | Resolução observada |
|---|---:|---|
| `EXPECTATION_SUPERSEDED` | 9 | Testes alinhados a contratos posteriores explícitos (Axis público, texto P5 e política HTTPS/HTTP). |
| `IMPLEMENTATION_REGRESSION` | 5 | Corrigido filtro que removia regras RTSP explícitas junto com HTTP legado. |
| `TEST_FIXTURE_DEFECT` | 39 | 5 fixtures Panasonic sem perfil exato e 34 falhas de fixtures/ambiente TLS local; corrigidas. |
| `PREEXISTING_VERIFIED` | 0 | Nenhuma falha atribuída a estado preexistente sem evidência suficiente. |
| `UNDETERMINED` | 0 | Nenhuma falha inicial ficou sem categoria. |
| **Total** | **53** | **53 resolvidas no ciclo de regressão final.** |

## `EXPECTATION_SUPERSEDED` — 9

| # | ID inicial | Evidência da causa | Correção e resultado |
|---:|---|---|---|
| 1 | `test_axis_uses_only_documented_bdi_post_and_records_identity_and_firmware` | A expectativa antiga usava a operação/documentação anterior; o contrato P0 atual exige fluxo Axis público anônimo `getSupportedVersions` → `getAllUnrestrictedProperties`. | Atualizado para a interface contratada; passou no conjunto focal. |
| 2 | `test_auth_failure_is_normalized_and_credentials_stay_target_scoped[AxisAdapter-POST-POST /axis-cgi/basicdeviceinfo.cgi getAllProperties]` | Esperava caminho Operator autenticado no fluxo público Axis, supersedido por `ANONYMOUS_ONLY_CONSERVATIVE`; 401 público não autoriza replay. | Substituída pela asserção sem replay/sem credencial; passou. |
| 3 | `test_incomplete_input_iteration_does_not_export_partial_batch` | O comportamento de não exportar foi mantido; mudou somente a frase de UI para refletir a falha durante o pré-voo. | Atualizada a expectativa textual; passou. |
| 4 | `test_single_inventory_path_uses_real_zeep_and_exact_target_port` | Fixture HTTP não corresponde ao default HTTPS nem ao perfil `LEGACY_EXACT` selecionado antes de I/O. | Fixture ajustada ao contrato de transporte; passou. |
| 5 | `test_single_workflow_stops_all_authenticated_io_after_real_onvif_401` | Caminho HTTP legado implícito supersedido pela política explícita de seleção de transporte. | Fixture HTTPS e política de auth mantida; passou. |
| 6 | `test_multi_row_stops_all_authenticated_io_after_real_onvif_401` | Mesmo descompasso de política da fixture anterior no fluxo MULTI. | Fixture HTTPS ajustada; passou. |
| 7 | `test_real_target_transport_ignores_hostile_proxies_netrc_and_ambient_credentials[http]` | A variante presumiu transporte HTTP sem perfil exato explicitamente compilado. | Cenário separado para perfil HTTP explícito; passou. |
| 8 | `tests/test_target_transport.py::test_real_zeep_uses_local_wsdl_and_guarded_requests_before_soap_io` | A expectativa de transporte não selecionava o perfil HTTP permitido antes da rede. | Fixture passou a usar o transporte contratual; passou. |
| 9 | `tests/test_target_transport.py::test_real_zeep_discovers_only_authorized_media_xaddr` | XAddr/fixture de mídia HTTP contrariava a regra de HTTPS ou regra RTSP explicitamente selecionada. | Fixture ajustada para HTTPS e regras autorizadas; passou. |

## `IMPLEMENTATION_REGRESSION` — 5

| # | ID inicial | Causa | Correção e resultado |
|---:|---|---|---|
| 10 | `test_single_deadline_is_shared_through_vendor_onvif_snapshot_and_active_rtsp` | `_rules()` removia qualquer regra cujo protocolo não fosse HTTPS, eliminando também regra RTSP explícita. | Filtra HTTP legado sem descartar RTSP permitido; passou. |
| 11 | `test_cancel_while_rtsp_frame_provider_waits_in_queue_prevents_open` | Mesmo filtro de regra RTSP impedia alcançar o cenário de fila/cancelamento. | Regra RTSP explícita preservada; passou. |
| 12 | `test_rtsp_queue_wait_consumes_camera_deadline_before_handshake` | Mesmo filtro removia a regra RTSP que o teste autorizava. | Regra RTSP explícita preservada; passou. |
| 13 | `test_cancel_during_active_rtsp_closes_container_and_stops_frame_processing[handshake]` | Mesmo filtro impedia a execução do teste de cancelamento durante handshake. | Regra RTSP explícita preservada; passou. |
| 14 | `test_cancel_during_active_rtsp_closes_container_and_stops_frame_processing[frame]` | Mesmo filtro impedia a execução do teste de cancelamento durante frame. | Regra RTSP explícita preservada; passou. |

## `TEST_FIXTURE_DEFECT` — 39

### Panasonic sem perfil documental exato — 5

| # | ID inicial | Defeito da fixture | Correção e resultado |
|---:|---|---|---|
| 15 | `test_panasonic_getinfo_maps_documented_name_serial_and_version_without_inventing_vendor` | Não fornecia o perfil exato do modelo documentado, então o caminho era corretamente ignorado antes do parser. | Passa `i-pro-command-interface-v1.17:WV-S2531L`; teste focal aprovado. |
| 16 | `test_panasonic_rejects_malformed_html_wrapper` | Mesmo perfil ausente, bloqueando a entrada malformada do parser. | Fixture com perfil/modelo exatos; teste focal aprovado. |
| 17 | `test_credentials_are_target_scoped_and_never_copied_to_evidence` | Mesmo perfil ausente, sem alcançar a verificação de escopo da credencial. | Fixture com perfil/modelo exatos; teste focal aprovado. |
| 18 | `test_timeout_is_normalized_without_leaking_exception_text[PanasonicAdapter]` | Mesmo perfil ausente, sem alcançar o timeout. | Fixture com perfil/modelo exatos; teste focal aprovado. |
| 19 | `test_tls_failure_does_not_downgrade_to_http[PanasonicAdapter]` | Mesmo perfil ausente, sem alcançar o teste de TLS. | Fixture com perfil/modelo exatos; teste focal aprovado. |

### TLS/loopback local inválido ou indisponível — 34

Os cenários abaixo foram afetados por certificados de teste sem extensões CA/leaf necessárias (incluindo Authority Key Identifier/SAN/EKU) e/ou restrição de socket loopback na execução não elevada. Foram criados certificados sintéticos novos, assinados por CA de teste local, com SAN `127.0.0.1` e EKU `serverAuth`; os fixtures antigos foram preservados. A suíte final foi executada com a autorização de loopback local desta atividade.

| # | ID inicial |
|---:|---|
| 20 | `test_trusted_https_uses_real_zeep_and_snapshot_transport` |
| 21 | `test_single_workflow_runs_real_https_preauth_inventory_and_snapshot` |
| 22 | `test_multi_workflow_runs_real_https_preauth_inventory_and_snapshot` |
| 23 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_tls-TLS_ERROR-None-single]` |
| 24 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_tls-TLS_ERROR-None-multi]` |
| 25 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-301-single]` |
| 26 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-301-multi]` |
| 27 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-302-single]` |
| 28 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-302-multi]` |
| 29 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-303-single]` |
| 30 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-303-multi]` |
| 31 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-307-single]` |
| 32 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-307-multi]` |
| 33 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-308-single]` |
| 34 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[preauth_redirect-AUTH_REJECTED-308-multi]` |
| 35 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[media_unapproved-TARGET_REJECTED-None-single]` |
| 36 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[media_unapproved-TARGET_REJECTED-None-multi]` |
| 37 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_unapproved-TARGET_REJECTED-None-single]` |
| 38 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_unapproved-TARGET_REJECTED-None-multi]` |
| 39 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-301-single]` |
| 40 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-301-multi]` |
| 41 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-302-single]` |
| 42 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-302-multi]` |
| 43 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-303-single]` |
| 44 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-303-multi]` |
| 45 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-307-single]` |
| 46 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-307-multi]` |
| 47 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-308-single]` |
| 48 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_redirect-TARGET_REJECTED-308-multi]` |
| 49 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_tls-TLS_ERROR-None-single]` |
| 50 | `test_full_workflows_fail_closed_for_tls_redirects_and_unapproved_endpoints[snapshot_tls-TLS_ERROR-None-multi]` |
| 51 | `test_real_target_transport_ignores_hostile_proxies_netrc_and_ambient_credentials[https]` |
| 52 | `test_untrusted_snapshot_tls_does_not_downgrade_to_explicit_vendor_http` |
| 53 | `tests/test_target_transport.py::test_real_digest_replay_does_not_follow_redirect_or_forward_authentication` |

## Limites da conclusão

O resultado final prova que esses 53 casos e a suíte acumulada passaram com os fixtures corrigidos. Não prova compatibilidade física com câmeras, homologação Viewer, ativação operacional de HTTP/RTSP ou os 56 AC individualmente. A matriz de AC fica em [`ASTRA_REMEDIATION_56_AC_MATRIX.md`](ASTRA_REMEDIATION_56_AC_MATRIX.md).
