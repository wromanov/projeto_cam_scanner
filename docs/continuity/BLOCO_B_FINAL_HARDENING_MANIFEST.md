# Manifesto do checkpoint — BLOCO B FINAL HARDENING

Branch: `feature/bloco-b-vendors`  
Baseline e HEAD: `a5c8445e0262a82cc8d6a3d627f2066223203f09`  
Worktree: `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_bloco_b`

## Arquivos incluídos

### Continuidade

- `docs/continuity/PROJECT_STATE.md`
- `docs/continuity/CONTINUITY_RECORD.md`
- `docs/continuity/BLOCO_B_FINAL_HARDENING_MANIFEST.md`

### Código

- `src/cam_scanner/cameras/manufacturer.py`
- `src/cam_scanner/cameras/manufacturers/_http_utils.py`
- `src/cam_scanner/cameras/manufacturers/axis.py`
- `src/cam_scanner/cameras/manufacturers/bosch.py`
- `src/cam_scanner/cameras/manufacturers/dahua.py`
- `src/cam_scanner/cameras/manufacturers/hikvision.py`
- `src/cam_scanner/cameras/manufacturers/panasonic.py`
- `src/cam_scanner/cameras/manufacturers/samsung_hanwha.py`
- `src/cam_scanner/cameras/registry.py`
- `src/cam_scanner/domain/enums.py`
- `src/cam_scanner/domain/models.py`
- `src/cam_scanner/main.py`

### Testes

- `tests/test_axis_hanwha_adapters.py`
- `tests/test_bosch_onvif_fallback.py`
- `tests/test_dahua_panasonic_adapters.py`
- `tests/test_hikvision_isapi.py`
- `tests/test_p1_cli_flow.py`
- `tests/test_vendor_collection_methods.py`
- `tests/test_vendor_http_budget.py`
- `tests/test_vendor_registry_integration.py`

## Exclusões e estado Git

- Artefatos gerados, caches, ambientes virtuais, planilhas e arquivos privados não fazem parte do manifesto. A consulta de arquivos ignorados no worktree não encontrou itens adicionais.
- O diretório temporário usado pela suíte completa está sob a raiz autorizada de visualizações, fora do worktree.
- Todos os arquivos listados permanecem unstaged. Nenhum `git add`, commit ou push foi executado.
- `HEAD` permanece no baseline; a publicação depende de autorização explícita do usuário.
