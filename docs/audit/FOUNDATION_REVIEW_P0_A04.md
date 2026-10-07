# P0-A04 — Foundation Review Recheck

Data: 2026-10-07. Escopo autorizado: leitura, validações existentes e atualização de estado/continuidade. Execução DIRECT, MULTIAGENT=NO, SKILLS=NONE; sem implementação, alteração arquitetural, staging, commit ou push. O Card A declara WORK/SOL/HIGH; execução factual neste Codex desktop local, sem transferência de executor ou alteração de configuração do modelo.

## Resultado

`FOUNDATION_REVIEW_RESULT = PASS_WITH_ACCEPTED_FINDINGS`.

Recomendação: Foundation pronta para aprovação explícita do usuário. P0-A02 conserva seu `CHANGES_REQUIRED` histórico. Esta review não concede Foundation Approval, Project Opening Gate, autorização de P1 ou autorização Git. Conclusão limitada à Foundation documental e estrutural; não demonstra capacidade operacional integrada.

## Recheck dos findings

| Finding | Disposição | Evidência e limite |
|---|---|---|
| F-01 | ACCEPTED_DEFERRED | `pyproject.toml` mantém >=3.14,<3.15. Python 3.14.0 existe; testes estruturais diretos passam. Validação operacional continua obrigatória antes de P1 fechar. |
| F-02 | ACCEPTED_INFORMATIONAL | WORK existe e é root atual. HOME ativo/WORK ausente eram fatos do outro computador; continuidade reconciliada sem mudar produto ou arquitetura. |
| F-03 | REMEDIATED | Git: master, HEAD 825b6799aba94fb4f347a3aeafef94b750bcc846, dois commits, upstream origin/master. Worktree limpo na entrada; documentação modificada ao sair. Zero commits/HEAD inválido identificados como históricos da P0-A03. |
| F-04 | ACCEPTED_RESOLVED_EVIDENCE | A atribuição histórica da validação à P0-A02 está preservada. Nova validação P0-A04 por `Test-Json -Schema`: True. Todos os nove pins resolvidos por SHA-256 exato em arquivos ZIP. |
| F-05 | REMEDIATED | ROADMAP P0–P12: P3 snapshot SINGLE sem XLSX; P4 primeiro MULTI+XLSX+snapshot embedded; sequência de integração incremental explícita. |
| F-06 | REMEDIATED | CameraResult: dez campos aprovados explicitamente tipados; sem password ou extension bag. CameraTarget.password repr=False. Teste existente confere conjunto de campos, tipos e repr. |
| F-07 | REMEDIATED | EXECUTION_PLAN define SINGLE Minimum Vertical Slice, integração canônica, getpass, ONVIF read-only, campos mínimos, erros/menu e validação operacional 3.14. P1 planejada sem autorização. |
| F-08 | ACCEPTED_DEFERRED_TO_P12 | build.ps1 permanece scaffold PyInstaller. Plano exige TESTS + RUFF + PACKAGE_SMOKE_TEST + PYINSTALLER em P12. Não se declara build operacional aprovado. |

As disposições aceitas acima derivam das decisões de P0-A03 registradas no pacote. O recheck não cria aceitação nova nem converte lacuna operacional em capacidade implementada.

## Evidências reproduzíveis

- Git somente leitura: `rev-parse --show-toplevel`, `branch --show-current`, `rev-parse HEAD`, `rev-list --count HEAD`, `status --short`, `rev-parse --abbrev-ref @{upstream}`, `rev-parse refs/remotes/origin/master`, `worktree list`. HEAD igual à referência local origin/master; paridade com servidor remoto não revalidada.
- `py -0p`: Python 3.14 e 3.13 instalados. Execução usada: Python 3.14.0, Windows 64 bits.
- `py -3.14 -m pytest -q -p no:cacheprovider` e `py -3.14 -m ruff check .`: indisponíveis, `No module named pytest/ruff`. Python bundled 3.12.14 também sem pytest. Nenhuma instalação realizada.
- Alternativa para validação estrutural: `runpy.run_path('tests/test_scaffold_structure.py')`, com src no sys.path; chamada das duas funções test_* existentes: 2/2 PASS. Não equivale a execução do runner pytest.
- `ast.parse` de src/tests: 44/44 PASS, sem execução dos entrypoints. `tomllib.loads`: pyproject.toml e dois settings TOML PASS.
- Inspeção dos modelos, testes, scaffold, configurações, roadmap, plano e build. Rotinas permanecem placeholders; não houve request de câmera, captura, XLSX operacional ou execução de packaging.

## Integridade e continuidade

Modo: `FIRST_ADOPTION_OR_AGENT_CHANGE`. Contrato adotado 1 suportado por Continuity 3.0. Binding JSON válido no schema externo. Nenhuma migração solicitada ou executada.

Os arquivos extraídos de governança não coincidem em bytes com os pins. Nos seis arquivos PM-00…PM-05, o texto coincide com os membros ZIP após decodificação UTF-8 e normalização de quebra de linha; a causa precisa da diferença binária não foi tratada como alteração normativa. Os blobs HEAD externos desses seis arquivos também divergem. Para VP-01/Opening/Continuity, blobs Git coincidem exatamente com pins e a conversão CRLF→LF explica a diferença de cópia extraída.

Resolução alternativa de bytes exatos, permitida por Continuity §3: membros de `../governanca_de_projetos/Matriz Unificada de Políticas.zip` para PM-00…PM-05/VP-01 e ZIPs `PROJECT_OPENING_3.0-REMEDIATED-MANIFEST-MATCHED.zip` / `CONTINUITY_3.0-REMEDIATED-MANIFEST-MATCHED.zip` em `Protocolos para Projetos - Vigente/Remediacao Integridade Pacotes 3.0 - 2026-10-05/`. Nomes dos membros e paths descobríveis em ACTIVE_AUTHORITY_MAP; hashes esperados permanecem no binding.

| Pin | SHA-256 exato do membro resolvido |
|---|---|
| PM-00 1.0 | db6853c74efccda0d74039bd0d466f7c1b532789f4861e3107a0f3760bae5f0f |
| PM-01 1.0 | b0782078a57fde833577e6b46fe3cd32048dae14569cac5ba9d821aafd1b54fa |
| PM-02 1.7-R2.6 | 0bd42fad5f867e703aaacd4ce89c02a2ac21404657ee20d85646efd3ba8a8a6f |
| PM-03 1.7-R2.3 | cfbb1cd363e6b1c6815918747fe12ce0ad2b35388d0aed0a1d2ca66b742b66aa |
| PM-04 1.2 | e0664fc460008401936c334d80afbd46fe94944391aa0938d56a339853129016 |
| PM-05 v1 | d668de8bdaeea16403f4909678448b59705f094302bc2fe90203c2f3cc62a94e |
| VP-01 v2.0 | aa0b351f939317eb584467e9b7a3d5bd823bafc47ec0a415e6cade38cf2f31d6 |
| PROJECT_OPENING 3.0 | 6fa7c89a6481547123b8d904d65d8e553b259f944507d34ca6ba5c265fbc35ad |
| CONTINUITY 3.0 | 262997f3509a856ed450654c9e5c9b9128beb3f57e1092bc87967ded42d0b5f3 |

Registry global declara baseline V1 e as mesmas versões operacionais; PM-04 traz metadado baseline_role histórico contraditório com CANONICAL/ACTIVE e operational_current_versions. Não houve substituição do pin adotado, alteração do registry ou escolha silenciosa. `GLOBAL_BASELINE_RELATION = UNKNOWN` para integridade do conjunto global; identidade/versionamento declarado coincide com o adotado. A governança externa apresenta alterações de index/worktree anteriores a esta atividade; não foi modificada nem reparada.

`BINDING_STATUS = ACTIVE` é derivado desta execução, não campo persistido no binding. `ADOPTED_CONTRACT_COMPATIBILITY = PASS`; `CONTINUITY_RECOVERY_GATE = PASS`: pins íntegros, limites reportados e retomada segura apenas para decisão da Foundation. Nenhum gate passa por simples comparação de texto normalizado.

## Validação de internalização VP-01

Procedimento aplicado em leitura; os cenários e dry-runs abaixo são simulações. A atualização documental pertence à autorização separada da P0-A04. Descoberta: PM-00/Registry; PM-01…PM-05; VP-01; Opening/Continuity; AGENTS e pacote do projeto. Authorities adotadas verificadas por ZIP; cópias locais divergentes não promovidas. Matrix governa sistema; PM-01 condução/continuidade; PM-02 prompts; PM-03 delegação; PM-04 capabilities; PM-05 julgamento; VP-01 validação; fontes do projeto governam fatos/contratos.

| Regra e fonte | Efeito aplicado / violação evitada |
|---|---|
| Autoridade/escopo — AGENTS, PM-00/01 | Usuário decide aprovação e avanço; review não concede P1 ou Git. |
| Hierarquia — PM-01 §2 | P0 é fase; P0-A04 atividade; roadmap é direção; plano é sequência; checkpoint não é sprint inventada. |
| Integração/DoR/DoD — PM-01 §§3–7 | P1 requer fluxo real integrado e regressão; scaffold/teste isolado não é capability DONE. |
| Frontend — PM-01 §5 | Frontend web NOT_APPLICABLE à CLI; fluxo terminal integra a slice. |
| Avanço — PM-01 §8 | Prontidão, seleção e autorização separadas; approval pendente bloqueia avanço. |
| Continuidade/handoff/safe resume — PM-01 §12 | Estado único em PROJECT_STATE; report/handoff referenciam; histórico não é root atual. |
| DIRECT/modelo/effort/reclassificação — PM-02/03 | Card exige DIRECT; não delegar por disponibilidade; incapacidade exige boundary e reconfiguração pelo usuário, sem substituição silenciosa. |
| Skills/plugins/capability — PM-04 | Execução nativa suficiente; skill não cria autoridade; disponibilidade não autoriza ação externa. |
| Git/escrita — AGENTS, PM-01/VP-01 | Validação read-only; atualização documental separadamente autorizada; nenhum stage/commit/push. |
| Independência/findings/ambiguidade — PM-05 | Buscar evidência contrária, registrar hashes divergentes e limites; preferência não prova readiness. |
| Fato/evidência/inferência — PM-05 | SHA e testes são evidências; prontidão é conclusão limitada; operação futura permanece não demonstrada. |
| Carregamento seletivo/fonte única — PM-00/01 | Policies aplicáveis; pins preservados; PROJECT_STATE único estado atual; fontes locais não promovidas por serem acessíveis. |

Cenários adversariais VP-01 A–R, 18/18 decisões governadas:

- A/B: volume mecânico e criticidade não selecionam modelo mais forte; risco seleciona rigor.
- C/D: disponibilidade ou falha localizada não justificam subagente automático.
- E/F: plugin opcional não é obrigatório; ação externa exige autorização e comunicação pertinentes.
- G/H: candidate mais nova não substitui canonical; solução inferior recebe discordância fundamentada.
- I/J: expansão material exige autoridade; capacidade Git não é permissão.
- K/L: módulo isolado não é DONE; integração big-bang não é default permitido.
- M/N: checkpoint sem continuidade atual falha; chat não substitui estado governado.
- O/P: root insuficiente para em boundary; subagente forte não contorna reclassificação.
- Q/R: backend desconectado não é capability concluída; frontend aplicável não fica para o final.

Dry-run simples: mensagem de erro com contrato fechado → Luna/Medium como recomendação hipotética, DIRECT, sem skill/plugin, um módulo, validação existente, sem commit/push. Nenhuma alteração executada.

Dry-run de capability: definir DoR, contrato e ponto real de integração; somente após autorização, implementar → validar módulo → integrar ao fluxo → validar integração/acumulado/regressão → reconciliar estado → handoff → fechar. Modelo/esforço pela demanda remanescente, não por criticidade. No estado real, próxima ação é aprovação da Foundation; readiness para decisão YES, implementação NOT_GRANTED. Safe resume: relatório e PROJECT_STATE, sem iniciar P1.

Self-check: nenhuma candidate promovida, policy ausente inventada, implementação integrada alegada, delegação realizada ou autoridade de aprovação assumida. Limites materiais documentados. `POLICY_INTERNALIZATION_GATE = PASS_WITH_FINDINGS`; `VP01_VALIDATION = PASS` com findings ambientais/integridade global delimitados, sem substituição dos pins.

## Fechamento

Critérios P0-A04: recheck F-01…F-08, validações disponíveis, resultado fundamentado e continuidade reconciliada. `PROJECT_STATE_UPDATE = PASS`; `ACTIVITY_COMPLETE = YES` para a revisão; `AGENT_HANDOFF_GATE = PASS` condicionado ao acesso explícito aos pacotes externos. Não confundir fechamento desta atividade com encerramento de P0 ou aprovação do usuário.

Próximo passo: decisão explícita do usuário sobre a Foundation. Referência primária de estado e autorização: [PROJECT_STATE.md](PROJECT_STATE.md).
