# AGENTS.md — Projeto CAM SCANNER

## 1. Finalidade

Este arquivo é o entrypoint e guardrail operacional para agentes do Projeto

CAM SCANNER. Ele resume regras estáveis e aponta para as fontes canônicas; políticas

e contratos detalhados prevalecem em caso de conflito. Não deve evoluir para

uma segunda política extensa.

## 2. Ordem mínima de leitura

1. `docs/continuity/PROJECT_STATE.md` (snapshot factual deste projeto)
2. `../governanca_de_projetos/Protocolos para Projetos - Vigente/Protocolo Continuidade Projeto Em Andamento Com Novo Agente 3.0/CONTINUITY_PROTOCOL.md`
3. `../governanca_de_projetos/Matriz Unificada de Políticas/policies/PM-01-Conducao-de-Projetos-v1.0.md`
4. `../governanca_de_projetos/Matriz Unificada de Políticas/policies/Independencia-Analitica-Agente-v1.md`
5. `../governanca_de_projetos/Matriz Unificada de Políticas/policies/Politica-Prompts-Agente-v1.7-R2.6.md`
6. `../governanca_de_projetos/Matriz Unificada de Políticas/policies/Politica-de-Uso-de-Skills-e-Plugins-Codex-Work-v1.2.md`
7. `../governanca_de_projetos/Matriz Unificada de Políticas/policies/AGENTS-Multiagente-Generico-v1.7-R2.3-Roteamento-Economico.md`
8. `Documentos específicos da atividade atual.`
Se existir uma política canônica de delegação multiagente, referenciá-la pelo path exato em vez de reproduzi-la.

## 3. Autoridade

- O usuário é a autoridade final sobre produto, escopo, arquitetura, roadmap,
commits, push, LIVE, encerramento de sprint e governança.

- Agentes, modelos e skills não criam authority. Ausência de authority deve ser
explicitada; usar `DEFERRED_NO_AUTHORITY` quando aplicável.

- Falsa authority e falsa capability são proibidas.
## 4. Independência analítica

Não concordar automaticamente. Buscar a melhor solução independente e, quando

material, distinguir `FATO`, `EVIDÊNCIA`, `INFERÊNCIA`, `HIPÓTESE`,

`PREFERÊNCIA`, `RECOMENDAÇÃO` e `DECISÃO`. Seguir a política canônica de

independência analítica.

## 5. Model / Effort / Multiagent / Skills

`MODEL / EFFORT` define capacidade cognitiva; `MULTIAGENT` define estratégia de

execução; `SKILLS / CAPABILITIES` define capacidade especializada. Os eixos

são independentes.

- Usar a menor capacidade suficiente.
- Usar subagentes somente quando houver benefício material; execução direta é
o padrão quando não agregarem valor.

- Skills podem ser `NONE`; nunca inventar skill indisponível.
- Skills não substituem reasoning, gates, revisão ou authority.
- Prompts Codex/Work devem declarar esses eixos conforme as políticas vigentes,
em pt-BR.

## 6. Work / Codex

Escolher o ambiente pela natureza da tarefa. Usar Codex para engenharia,

repositório, testes e Git quando apropriado; usar Work para browser,

persistência, artifacts ou workflows próprios quando houver benefício

material. Regras específicas do ambiente prevalecem.

## 7. Git e segurança

- Confirmar repo root, branch, `HEAD` e worktree antes de operações críticas.
- Fazer staging explícito; nunca usar `git add .`.
- Não executar automaticamente `reset`, `restore`, `clean`, `stash`, `amend` ou
force push.

- Commit e push exigem autorização explícita.
- Nunca expor passwords, master keys, TOTP, recovery codes, tokens ou secrets.
Segredos locais permanecem fora do Git.

## 8. Continuidade

Git é a fonte de verdade para repo root, branch, `HEAD` e worktree.

`PROJECT_STATE.md` é o snapshot lógico/técnico. A documentação canônica

mais recente prevalece sobre memória conversacional; divergências devem ser

investigadas, não reconciliadas silenciosamente.

## 9. Comunicação

Responder em português do Brasil, com comunicação humana e intuitiva primeiro e

estado técnico depois quando útil. Preservar rigor, rastreabilidade e

transparência sobre incerteza.

## 10. Prevalência

`AGENTS.md` é entrypoint/guardrail. Políticas, contratos e demais documentos

canônicos detalhados são a autoridade normativa; este arquivo apenas os resume

e referencia.

Toda atividade formal requer `PROJECT_STATE_UPDATE = PASS` antes de declarar

`ACTIVITY_COMPLETE = YES`.
