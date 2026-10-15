# Auditoria arquitetural pré-P12 — CAM Scanner

**Atividade:** `PRE_P12_MULTIAGENT_ARCHITECTURE_AUDIT`<br>
**Baseline:** `b4c67f74bead61a40ab9037934f994dad7dfe701`<br>
**Branch/worktree:** `audit/pre-p12` — `C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_pre_p12_audit`<br>
**Decisão:** `P12_READINESS=BLOCKED`<br>
**Câmera real / build P12:** `NOT_RUN` / `NOT_RUN`

## 1. Resumo executivo

O Architect identificou três bloqueios materiais para iniciar P12: transporte ONVIF sem governança efetiva de TLS/proxy/redirects (PREP12-01); transporte fixo HTTP para snapshots (PREP12-02); e novas consultas autenticadas de snapshot/RTSP possíveis após recusa de autenticação (PREP12-03). A decisão exata recebida é `P12_READINESS=BLOCKED`.

Há 14 findings: 0 Critical, 3 High, 9 Medium e 2 Low. PREP12-01/02/03 são `MUST_FIX_BEFORE_P12`; PREP12-04/05/06/07/08/09/10/12/13/14 são `RECOMMENDED_BEFORE_DELIVERY`; PREP12-11 é `POST_DELIVERY_BACKLOG`. Detalhes por finding em [PRE_P12_FINDINGS_REGISTER.md](PRE_P12_FINDINGS_REGISTER.md). Nenhum finding foi corrigido nesta atividade.

## 2. Identificação da baseline

Baseline `b4c67f74bead61a40ab9037934f994dad7dfe701`, branch `audit/pre-p12`, worktree isolado `projeto_cam_scanner_pre_p12_audit`.

## 3. Escopo auditado

Foram lidos instruções, contratos, continuidade, roadmap/plano, código e testes, cobrindo arquitetura, segurança, identidade, concorrência, cancelamento, snapshots/RTSP, fabricantes, MULTI/XLSX, configuração, logs, dependências e risco de ONEDIR. Não houve alteração de source, testes, dependências; não houve câmera real nem build P12.

## 4. Metodologia e limitações

Inspeção READ_ONLY e verificações offline não destrutivas. Runtime reaproveitado READ_ONLY: Python 3.14.0 Windows AMD64 no `.venv` de `projeto_cam_scanner_p5_concurrency`; sem instalações.

**Execução atual:** `pip check PASS`; `ruff 0.17.0 check --no-cache src tests PASS`; `git diff --check PASS` no início/fim. Pytest completo falhou ao criar/terminar `basetemp` autorizado devido a ACL (WinError 5); sete testes com `tmp_path` inconclusivos. Sem esses casos: 213 passed, 7 deselected, 1,13 s. O handoff não forneceu os nomes dos sete casos, portanto não são inferidos.

**Baseline histórica:** 220 testes passados, Ruff e pip check aprovados em hardening anterior; isso não substitui a execução atual parcial. `REAL_CAMERA_VALIDATION=NOT_RUN`; `PYINSTALLER_BUILD=NOT_RUN`.

As seis referências externas de governança estavam legíveis nesta execução. Isso não certifica pins/hashes nem migração; `GOVERNANCE_BINDING` não é declarado PASS.

## 5. Avaliação arquitetural

A separação modular é adequada ao escopo observado. `CollectionReport` centraliza evidência/estado; os 14 campos de `CameraResult` estão preservados; conflito de evidência essencial bloqueia SUCCESS; firmware parcial não impede identidade completa. Registry contém seis fabricantes, sem ciclo de credenciais. Não foi encontrado uso de operação mutante de câmera.

O limite transversal é a governança incompleta ponta a ponta de transporte, autenticação, orçamento e cancelamento: ONVIF diverge dos adapters HTTP, snapshot tem política própria, e status/contexto agregado não impede sempre novas operações. Detalhes em PREP12-01 a 05.

## 6. Avaliação de segurança

Adapters HTTP vendor inspecionados usam sessão por coleta, `trust_env=False`, redirects desligados e TLS validado em HTTPS. Há credenciais por alvo, `repr` privado, evidências sanitizadas e sem senhas na exportação. Exceções: ONVIF sem governança equivalente (01), snapshot HTTP fixo (02), nova autenticação após recusa (03), risco provável de filtro DTD dependente de encoding (14, sem XXE demonstrado), e U+0001 aceito pelo domínio podendo abortar exportação XLSX (06). O writer protege prefixos de fórmula e usa temporário/hardlink. Níveis de certeza e evidências estão no registro.

## 7. Concorrência e desempenho

MULTI limita workers a 1–32, fila a 2×workers, separa credenciais e preserva ordem. Semáforo global permite uma captura RTSP; recursos fecham em `finally`; solicita-se um frame. O desenho é plausível para ~2.300 câmeras, não medido nessa escala. Resultados/imagens ficam em memória; RTSP serializado intencionalmente.

Budget cumulativo não percorre preauth→vendor→fallback→snapshot (04). CANCELLED pode permitir etapas posteriores; executor aguarda tarefas correntes (05), sem promessa de interrupção forçada. Memória, workbook grande, espera RTSP e hardlink entre volumes/shares não foram demonstrados.

## 8. Coleta e fabricantes

- **Axis:** HTTPS VAPIX `/axis-cgi/basicdeviceinfo.cgi`, `getAllProperties`, Digest limitado; testes sintéticos.
- **Hikvision:** HTTPS GET `/ISAPI/System/deviceInfo`, Digest offline, TLS e ausência de downgrade testados; findings 04/07/14. Snapshot limitado à família indicada no handoff.
- **Samsung/Hanwha:** HTTPS `system.cgi?msubmenu=deviceinfo&action=view`, fabricante explícito, parcial, sintético.
- **Dahua:** `getSystemInfo`/`getVendor`, budget/evidência parcial, firmware ausente, sintético.
- **Panasonic/i-PRO:** `/cgi-bin/getinfo?FILE=1`, NAME/model, SERIAL, version/firmware em família documentada; interface limitada, sintético.
- **Bosch:** sem operação nativa especulativa; `SKIPPED/ENDPOINT_UNSUPPORTED`, fallback ONVIF.

Endpoints foram inspecionados localmente, sem revalidação online com os fabricantes. Adapters não provam exercício no fluxo padrão nem interoperabilidade real; PREP12-13 é `UNVERIFIED_RISK`. Nenhuma câmera real foi homologada.

## 9. Snapshots e RTSP

Imagens HTTP têm limite de bytes; thumbnails têm limites de dimensão/pixels e são reconstruídas sem metadados; falha preserva identidade. RTSP usa um frame, semáforo e fechamento de recursos. A política fixa HTTP não acompanha transporte de inventário (02); decisão pós-rejeição e budgets/cancelamento não se propagam integralmente (03–05). RTSP/autenticação foram testados sinteticamente.

## 10. MULTI/XLSX

MULTI valida entradas, isola credenciais, preserva ordem e escreve temporário/hardlink sem sobrescrever; prefixos de fórmula são protegidos. A projeção perde contexto de tentativas (03). U+0001 pode passar validação e fazer openpyxl abortar relatório (06). Integridade/performance em ~2.300 linhas e hardlink entre volumes não foram demonstrados.

## 11. Prontidão de empacotamento

O scaffold `packaging/cam_scanner.spec` não demonstra recursos/imports ocultos/hooks/DLLs. ONVIF/WSDL, Zeep/lxml, PyAV, TOML, certificados, logs e temporários precisam de validação; caminhos de `__file__` e logger podem falhar em diretório protegido (PREP12-09). Nenhum build foi executado; não se afirma falha certa do executável.

## 12. Avaliação da qualidade dos testes

A configuração consome apenas `concurrency.default_max_workers`; opções de coleta/snapshot/log/retry/RTSP não chegam aos componentes (PREP12-08). Dependências sem pins/lock e import direto de `requests` sem dependência direta tornam a instalação não reprodutível (PREP12-10).

Os testes oferecem regressões sintéticas, mas budget/cancelamento não estão cobertos ponta a ponta, DTD é testado em ASCII, registry recebe fabricante sintético e respostas reais representativas faltam em várias famílias. Pytest atual não foi completo por ACL, portanto não é passe integral.

## 13. Findings priorizados

## 14. Must-fix antes da P12

PREP12-01/02/03.
## 15. Melhorias recomendadas antes da entrega

PREP12-04/05/06/07/08/09/10/12/13/14.
## 16. Backlog pós-entrega

PREP12-11.

## 17. Plano mínimo de remediação

Sequência mínima: revisão do usuário; corrigir os três blockers e testar transporte/TLS/redirects/pós-rejeição; tratar recomendações, com atenção a budget/cancelamento, entradas XLSX, identidade, configuração/dependências, packaging e XML; rodar suíte completa em diretório temporário funcional; homologar READ_ONLY em equipamentos sob autorização própria; executar ONEDIR Windows 11 x64 sem Python instalado cobrindo recursos, DLLs, certificados e permissões; submeter gate de entrega autorizado. Nenhuma etapa pendente é considerada concluída.

```text
P12_READINESS = BLOCKED
BLOCKING_FINDINGS = PREP12-01, PREP12-02, PREP12-03
CURRENT_PYTEST = PARTIAL (213 passed; 7 deselected by temp ACL; full run inconclusive)
HISTORICAL_TEST_BASELINE = 220 passed (earlier report)
RUFF = PASS
PIP_CHECK = PASS
REAL_CAMERA_VALIDATION = NOT_RUN
PYINSTALLER_BUILD = NOT_RUN
SOURCE_CHANGES = NONE
TEST_CHANGES = NONE
DEPENDENCY_CHANGES = NONE
```

## 18. Decisão P12_READINESS

A decisão acima é exatamente a recebida do Architect. Este relatório não autoriza implementação, build, acesso a câmera, fechamento de fase, publicação ou escrita Git.
