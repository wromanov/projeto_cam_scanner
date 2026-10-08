# ARCH_AUDIT_01_REPORT

Projeto CAM SCANNER — auditoria independente de arquitetura e coleta de câmeras IP

Data: 08/10/2026, America/Sao_Paulo. Baseline auditado: `019dc70bdd9bedcca4f72f16c13b6d419a59309c`, branch `master`.

## Escopo, execução e autoridade

Esta entrega contém diagnóstico e recomendações. Não implementa nem aprova mudanças. `READ_ONLY_REPOSITORY = YES`, `READ_ONLY_RESEARCH = YES`, `NO_REAL_CAMERA_CALLS = YES`, `NO_CREDENTIAL_USAGE = YES`. O relatório foi salvo fora do repositório. P1 permanece CLOSED e implementação P2 permanece NOT_GRANTED.

```text
EXECUTION_MODE = DIRECT
MODEL_TARGET_REQUESTED = SOL
EFFORT_TARGET_REQUESTED = HIGH
MODEL_RECONFIGURATION = NOT_PERFORMED
ORCHESTRATOR_ROLE = ROOT / auditor de arquitetura
SUBAGENTS_ALLOWED = NO
SUBAGENTS_PLANNED = 0
SKILLS = activity-progress-reporting (solicitada pelo perfil do usuário)
SPECIALIZED_AUDIT_SKILL = NONE
PLUGIN_SPECIALIZATION = NONE
EXPECTED_MATERIAL_GAIN_FROM_DELEGATION = NO; modo DIRECT explicitamente solicitado
```

Não há alegação de mudança do modelo/esforço da sessão. A skill local de progresso foi usada por instrução explícita do usuário, que prevalece sobre a restrição geral de skills locais em PM-04.

As referências canônicas do AGENTS.md foram localizadas. Os nove pins do binding foram conferidos por SHA-256 nos ZIPs indicados no mapa de authorities; todos coincidiram. O binding passou em `Test-Json` contra seu schema Continuity 3.0. Não foi executada uma campanha completa VP-01 e não se declara novo gate de internalização ou handoff PASS. A auditoria não concede authority de implementação, Git ou câmera.

Rótulos de evidência usados: **CÓDIGO** = inspeção direta; **REPRODUÇÃO** = execução sintética desta auditoria; **OPERACIONAL INFORMADA** = fatos do payload e continuidade, sem nova consulta ao equipamento; **DOCUMENTADO** = fonte primária citada; **INFERÊNCIA/HIPÓTESE** = conclusão que ainda requer comprovação; **RECOMENDAÇÃO** = proposta, não decisão aprovada.

## A. EXECUTIVE ASSESSMENT

**Avaliação: ACCEPT_WITH_CHANGES.** O monólito modular, o controller de navegação, os workflows e as fronteiras de coleta são adequados à escala informada. Não existe evidência de necessidade de reconstrução, microserviços, filas distribuídas, banco de credenciais ou plataforma de observabilidade.

A estratégia vendor-first é uma boa preferência quando fabricante e capacidade nativa estão estabelecidos. Sua implementação atual ainda depende de descoberta ONVIF em todas as consultas e de ONVIF autenticado para obter inventário: nenhum adapter nativo está registrado no entrypoint. Isso é compatível com o escopo limitado da P1, mas não comprova a estratégia operacional para seis fabricantes.

Recomendo **HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE**: seleção determinística orientada a evidências, disponibilidade do adapter, escopo da credencial e campos solicitados. O protocolo secundário só é consultado quando pode recuperar ou completar informações necessárias e quando o orçamento de tempo/autenticação permite. Essa evolução mantém a intenção vendor-first e elimina sua aplicação indiscriminada.

As prioridades são: preservar evidências diante de qualquer falha; identificar etapa e causa técnica de cada tentativa; corrigir fingerprint ambíguo; validar uma slice Hikvision ISAPI mínima integrada ao SINGLE; diagnosticar ONVIF Digest com transporte controlado. A causa do 401 Digest da câmera real permanece **UNDETERMINED**. Há explicação provável para a rejeição WS-UsernameToken, mas ela não resolve a rejeição Digest também relatada.

O fechamento contratual de P1 permanece válido. Ele aceitou descoberta parcial sem exigir inventário autenticado. Assim, P1 CLOSED e coleta autenticada ainda não comprovada são fatos compatíveis.

## B. VERIFIED BASELINE

### B.1 Git e continuidade

| Item | Verificação desta auditoria |
|---|---|
| Root | `C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner` |
| Branch / HEAD | `master` / `019dc70bdd9bedcca4f72f16c13b6d419a59309c` |
| Worktree | Um checkout listado pelo Git, no root acima |
| Mudanças tracked/staged | Nenhuma observada; `git diff` de source/tests/dependências e diff staged vazios |
| Arquivos locais excluídos do checkpoint | `docs/policies/`, `onvif_auth_test.py`, `onvif_preauth_test.py`, untracked. Os scripts não foram executados nem lidos, evitando acesso a credenciais eventualmente embutidas |
| Limite da enumeração | Git reportou acesso negado a diretórios temporários/cache preexistentes; não se afirma limpeza total dos arquivos ignorados |
| SHA documental | PROJECT_STATE e LAST_HANDOFF citam `ec53d2…`, predecessor imediato de `019dc70…` |
| Explicação da divergência | O último commit altera quatro documentos de continuidade; o diff entre os SHAs não altera implementação. Não houve reconciliação documental nesta auditoria |
| Remoto publicado | Informação histórica. Não houve fetch nem revalidação do servidor remoto nesta atividade |

Foram inspecionados AGENTS, PROJECT_STATE, ACTIVE_AUTHORITY_MAP, binding, ROADMAP, EXECUTION_PLAN, contrato P1, CONTINUITY_RECORD e LAST_HANDOFF. Entradas antigas de P1 NOT_READY estão marcadas como históricas nos documentos; o estado ativo é P1 CLOSED. A divergência do SHA foi registrada, sem usar documento como substituto de Git.

### B.2 Implementação e pontos de integração

| Componente | Evidência direta e avaliação |
|---|---|
| Entry point | [main.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/main.py:22) integra InventoryService(VendorFirstCollector), SingleWorkflow e ApplicationController |
| Controller/workflow | Navegação permanece no controller; SINGLE retorna ao menu; MULTI apresenta indisponibilidade |
| Coleta | [strategy.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/cameras/strategy.py:38) executa preauth sempre, resolve com hint `None`, seleciona um adapter e usa ONVIF como fallback/complemento |
| Preauth | [preauth.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/cameras/preauth.py:55) não passa username/password do target; usa porta 80, timeout 7s, GetCapabilities e GetSystemDateAndTime |
| Fingerprint | [preauth.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/cameras/preauth.py:114) procura substrings em strings/keys/valores e retorna o primeiro fabricante encontrado |
| Hint de fabricante | Resolver suporta hint e mismatch, mas CameraTarget tem somente IP/username/password e a estratégia chama resolver com `None`. Não é requisito pendente da P1 SINGLE; integração MULTI futura precisa transportar o hint |
| Registry | [registry.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/cameras/registry.py:16) aceita registro explícito, normaliza a chave e substitui registro duplicado sem validação de capacidade; protocolo usa object→object |
| Adapters | Os seis arquivos em `cameras/manufacturers` levantam NotImplementedError. Nenhum é registrado pela aplicação |
| ONVIF autenticado | [adapter.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/cameras/onvif/adapter.py:24) passa target corrente, porta 80, timeout 7s e CacheMode.NONE; chama GetDeviceInformation |
| Resultado | [models.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/domain/models.py:16) tem exatamente 14 campos explícitos; password está somente no target e usa repr=False |
| Campos ONVIF usados | Manufacturer, Model, SerialNumber e FirmwareVersion. HardwareId da resposta não é mapeado atualmente; isso não viola o mínimo P1 |
| Falhas | [inventory_service.py](C:/Users/walacedelgado/PycharmProjects/projeto_cam_scanner/src/cam_scanner/application/inventory_service.py:74) classifica chains por status HTTP, markers e nomes de exceptions; não registra etapa/operação |
| Configuração | Defaults 3/7/15/10/45s existem, mas loader é placeholder e não está conectado ao fluxo. O timeout efetivo da coleta é escalar 7s; budgets/deadline não são aplicados |
| Lote e snapshot | Workflows/adapters correspondentes são scaffolds; não existe ThreadPoolExecutor operacional |

### B.3 Ambiente e validação executada

Python 3.14.0; onvif-python 0.4.4; Zeep 4.3.3; Requests 2.34.2; pytest 9.1.1; Ruff 0.16.10. `httpx` está declarado em pyproject.toml, mas **não está instalado neste venv**. Nenhuma dependência foi instalada.

Nesta auditoria: **51 testes PASS** e **Ruff PASS**. Testes executados com bytecode/cache pytest desativados e temporários no diretório temporário do sistema. Conexão de socket e envio UDP foram bloqueados no processo de testes; **NETWORK_ATTEMPTS = 0**. A suíte inclui testes do fluxo CLI com dependências falsas. Não houve novo smoke interativo com câmera ou inicialização do logger operacional.

As reproduções adicionais foram executadas em memória, com dados sintéticos e sem arquivos de teste novos:

| Caso | Resultado observado | Implicação |
|---|---|---|
| Preauth Hikvision + TimeoutError na coleta | FAILED, manufacturer=None, TIMEOUT | Evidência de fabricante desaparece |
| Preauth Hikvision + collector retorna FAILED/AUTH_ERROR | FAILED, manufacturer=Hikvision | O tratamento parcial depende de exception; resultado de falha não segue a mesma semântica |
| Vendor parcial/TIMEOUT + ONVIF preenche quatro campos P1 | PARTIAL_SUCCESS/TIMEOUT, com modelo/serial/firmware preenchidos | Status/erro original são herdados sem avaliar cobertura final; a política de sucesso futura precisa decidir se o erro foi recuperado |
| XAddr contendo `/galaxis/device` | Fabricante Axis | Substring sem identidade de fabricante produz falso positivo |
| Capabilities com Axis e Hikvision, ordem invertida | Axis em uma ordem; Hikvision na outra | Resultado depende da ordem do payload em conflito |
| Seleção auth da biblioteca, em memória | False→somente WSSE; True→somente HTTPDigestAuth | Não há mistura automática dos dois mecanismos na versão instalada |
| Requests Digest com qop somente auth-int | Header não produzido | Limitação confirmada do transporte instalado; challenge real não foi fornecido, portanto não é causa comprovada do 401 |

### B.4 Registro de findings e contagem

Severidades abaixo indicam prioridade de evolução e impacto no objetivo, não uma classificação de vulnerabilidades exploradas. Gap planejado não é automaticamente bug da P1.

| ID | Severidade | Classificação | Finding |
|---|---|---|---|
| F01 | HIGH | Bug confirmado | Evidência prévia perdida em timeout/falha não-auth e semântica diferente entre exception e FAILED retornado |
| F02 | HIGH | Bug confirmado | Fingerprint com falso positivo e escolha dependente da ordem de sinais conflitantes |
| F03 | HIGH | Limitação confirmada | Ausência de etapa/tentativas; erros nativos/preauth/complemento descartados ou reduzidos ao último erro |
| F04 | MEDIUM | Gap confirmado; causa real aberta | Scanner usa WSSE default, sem seleção explícita de Digest |
| F05 | MEDIUM | Capability planejada | Nenhum adapter nativo operacional comprova a estratégia |
| F06 | MEDIUM | Limitação confirmada | Merge sem proveniência, conflito ou recomposição de status/método |
| F07 | MEDIUM | Capability planejada | Budgets/deadline/retries não conectados; porta 80 fixa |
| F08 | MEDIUM | Gap de contrato futuro | Resultado de 14 campos não representa rede, disponibilidade por protocolo e várias tentativas |
| F09 | MEDIUM | Gap confirmado | Dependências sem versões reproduzíveis e httpx ausente no venv auditado |
| F10 | MEDIUM | Limitação confirmada | Registry não impede placeholder e contrato object→object não declara suporte |
| F11 | MEDIUM | Risco de transporte; exploração não demonstrada | Requests session mantém trust_env=True; ONVIF default verify_ssl=False e fronteira de destinos não é contratada |
| F12 | LOW | Divergência documental | SHA de continuidade aponta para predecessor documental do HEAD |

Total: 0 CRITICAL, 3 HIGH, 8 MEDIUM, 1 LOW. Não há alegação de vazamento, lockout ocorrido, mutação de câmera ou exploração efetiva.

## C. REAL PROBLEMS DIAGNOSIS

### C.1 PROBLEM_01 — ONVIF Digest Hikvision

**CONFIRMED:** o scanner não pede `http_digest=True`; o transporte instalado escolhe UsernameToken PasswordDigest. **OPERACIONAL INFORMADA:** ONVIF da câmera estava em Digest, preauth respondeu, WSSE e uma tentativa Digest falharam. **PROBABLE:** a escolha WSSE explica a recusa do caminho atual se o firmware do alvo se comporta conforme o modo informado. **UNDETERMINED:** por que o caminho Digest separado também falhou.

GetCapabilities responde sem autenticação porque consulta capacidades tem classe de acesso diferente de informação de dispositivo. Isso não demonstra credencial válida nem autorização para a segunda operação. A análise detalhada, correção condicional e testes discriminantes estão na seção E.

### C.2 PROBLEM_02 — ausência de adapter nativo

A infraestrutura genérica leve era justificável como slice mínima. Manter toda a expansão dependente dela até P7, sem uma prova nativa, já não reduz os riscos do projeto. Não é necessário construir todo ISAPI: **um GET de deviceInfo, parser e erros tipados integrados ao SINGLE** são suficientes para provar autenticação e caminho nativo. Isso não prova cobertura dos seis fabricantes nem inventário completo de rede.

Modelos/firmwares devem fornecer suporte por operação/campo, com resultado SUPPORTED/UNSUPPORTED/UNKNOWN. 404, 405 e erro de recurso não suportado não devem ser classificados como credencial inválida; 401 após negociação e 403 devem conservar semânticas distintas, com incerteza quando o dispositivo usa códigos de maneira não padronizada. Registry recebe apenas implementações habilitadas para um conjunto de operações testado. Uma allowlist local de adapters habilitados é suficiente; não é preciso autodescobrir plugins.

Sem adapter, informar NATIVE_ADAPTER_UNAVAILABLE e usar ONVIF disponível dentro da política. Medir a vantagem nativa em campos reais por modelo/firmware: cobertura, divergências, latência e número de requests. Mais campos no XML não significam melhor resultado se os valores não forem válidos ou autorizados.

### C.3 PROBLEM_03 — diagnóstico das falhas

O modelo atual é adequado para mensagens gerais P1 e insuficiente para decisões de retry/fallback em lote. TCP aberto não prova resposta HTTP, SOAP válido ou autenticação. Um timeout HTTP anônimo e um AUTH_ERROR posterior podem ocorrer em etapas/execuções diferentes; não demonstram uma causa única.

Adicionar CollectionAttempt tipado, com protocolo, operação, etapa, duração, status HTTP, código SOAP/vendor, categoria normalizada e mensagem sanitizada. Cada operação registra sucesso ou falha; o agregador mantém toda evidência útil. A UI mostra a causa principal e o que ainda foi obtido, por exemplo: “Hikvision identificada. ISAPI indisponível; ONVIF recusou autenticação em GetDeviceInformation. Modelo e serial não obtidos.”

Não armazenar headers completos, usuário, senha, Authorization, SOAP UsernameToken ou corpos integrais. A sessão de diagnóstico registra apenas metadados permitidos. A observabilidade necessária é stdlib logging local com RUN_ID e referência da linha/câmera; não requer framework.

### C.4 PROBLEM_04 — identificação automática

Não existe um fingerprint universal confiável para os seis fabricantes. ONVIF não é obrigatório: respostas públicas HTTP, estrutura de namespace, modelo explícito, certificados e dados de inventário já existentes podem contribuir. Headers Server e realm são pistas fracas; podem identificar webserver/OEM, não o fabricante comercial. MAC OUI indica fornecedor do prefixo, pode refletir OEM e geralmente depende de proximidade de rede para coleta anônima. mDNS/WS-Discovery multicast não atravessam todas as VLANs; não criar varredura broadcast geral para cada linha XLSX. SNMP exigiria configuração/credenciais próprias e não deve ser incluído no mínimo.

Priorizar hint validado/normalizado, evidência estruturada de marca/modelo, namespace exato e confirmação autenticada quando o protocolo já tiver sido selecionado. Usar níveis categóricos, sem inventar probabilidade numérica: STRONG, WEAK, CONFLICTING, UNKNOWN. Um marker deve corresponder a namespace/chave documentada ou token de identidade permitido; substring arbitrária não basta. Conflitos fortes bloqueiam escolha automática de adapter nativo. Hint contraditório por sinal fraco gera aviso e continua como hint; contraditório por sinal forte exige resolução ou ONVIF genérico disponível, sem alternar logins entre vendors.

Sem sinal suficiente: retornar fabricante desconhecido e usar um único caminho genérico ONVIF, se houver endpoint utilizável e orçamento de auth. Se também indisponível, resultado de descoberta incompleta com orientação para informar fabricante/porta ou revisar permissões. Não tentar autenticar todas as APIs.

### C.5 PROBLEM_05 — estratégia

Vendor-first puro não é demonstradamente melhor em todo modelo. ONVIF-first universal também não atende a operação que não deseja provisionar usuários ONVIF. Recomendo seleção híbrida com preferência nativa e complementação por necessidade; comparação e algoritmo estão em F/G.

API nativa autentica e ONVIF falha: preservar dados nativos; parar ONVIF após a recusa; resultado final depende da cobertura solicitada. ONVIF autentica e nativa falha: preservar ONVIF e não insistir na nativa. Se ambos falham, manter identificação/protocolo observado como parcial, sem chamar isso de inventário autenticado. Se nenhuma evidência útil existir, FAILED.

### C.6 PROBLEM_06 — fusão

O merge atual preenche None e protege valores vendor, mas não registra origem, conflitos ou erros secundários. O caso de status herdado é comportamento confirmado; qualificá-lo como erro semântico definitivo depende do contrato futuro de cobertura. Recomendo status calculado no agregador a partir de campos exigidos e conflitos materiais, mantendo falhas recuperadas no histórico. Regras por campo e exemplos estão em H.

Resultado parcial aceitável depende do uso: identificação de família pode bastar para triagem; inventário de ativos precisa, pelo menos, identidade suficiente e campos requeridos explicitamente aprovados. Não promover fabricante isolado a “inventário completo”.

### C.7 PROBLEM_07 — 2.300 câmeras

ThreadPoolExecutor continua adequado ao I/O síncrono atual. Não existe evidência para infraestrutura distribuída ou migração assíncrona integral. Preservar 8 workers iniciais, teto configurável 32 e um fluxo sequencial por câmera; ajustar só com medição. Clientes/sessões/auth/cookies pertencem a uma linha e devem ser fechados ao terminar; cliente autenticado compartilhado entre câmeras é proibido.

Detalhes de deadlines, retries, duplicatas, cancelamento, preservação de ordem e carga estão em K. O lote ainda não foi implementado nem submetido a carga nesta auditoria.

## D. OFFICIAL TECHNICAL RESEARCH

Pesquisa consultada em 08/10/2026. Suporte documentado de uma interface não comprova suporte no parque real. Endpoints abaixo são apenas referências; nenhum foi chamado. GET e POST não determinam, isoladamente, se a operação é mutante.

### D.1 ONVIF

Core 24.12 distingue GetCapabilities/GetServices/GetSystemDateAndTime pré-auth e GetDeviceInformation READ_SYSTEM; não recomenda enviar credenciais simultaneamente em HTTP e WS. A norma consultada é referência de protocolo, não prova de conformidade do alvo. [ONVIF Core 24.12, §§5.9, 8.1 e 8.3](https://www.onvif.org/specs/2412/ONVIF-Core-Spec-v2412.pdf).

Para inventário, operações de leitura relevantes são GetDeviceInformation, GetHostname, GetNetworkInterfaces, GetNetworkDefaultGateway, GetDNS e GetNetworkProtocols. Elas oferecem identidade e configuração de rede/portas, sujeitos a capability e permissões. Manter listas de interfaces/endereços, sem reduzir silenciosamente a primeira entrada. A URI de serviço deve vir de descoberta confiável ou configuração; não assumir porta 80 universal. [WSDL Device Management oficial](https://github.com/onvif/specs/blob/master/wsdl/ver10/device/wsdl/devicemgmt.wsdl).

Autenticação HTTP Digest negocia challenge; UsernameToken transporta nonce/Created/PasswordDigest no SOAP. São mecanismos diferentes. Discovery por WS-Discovery é mecanismo adicional; não comprova disponibilidade autenticada nem atravessa necessariamente sub-redes. As políticas de seleção/rede deste relatório são recomendações de engenharia, não requisitos atribuídos à norma.

### D.2 Matriz dos seis fabricantes

| Fabricante | Interface e leitura oficialmente localizadas | Campos verificados | Auth e variações | Fallback / limites / riscos |
|---|---|---|---|---|
| Axis | VAPIX: POST `/axis-cgi/basicdeviceinfo.cgi`, métodos getProperties/getAllProperties/getSupportedVersions | Brand, ProdNbr, SerialNumber, Version, HardwareID | BDI documentada desde AXIS OS 8.40; getAllProperties exige Operator. Auth depende de OS/modelo | ONVIF quando permitido; confirmar versões e API discovery. POST desses métodos é leitura; não liberar POST arbitrário |
| Hikvision | ISAPI: GET `/ISAPI/System/deviceInfo` | deviceName, model, serialNumber, firmwareVersion, macAddress, hardwareVersion no exemplo oficial | HTTP Digest no material oficial; contas ONVIF podem ser independentes. Modo ONVIF e CGI variam | ONVIF quando disponível e com credencial apropriada. Endpoints de rede adicionais não contratados aqui |
| Samsung/Hanwha | SUNAPI: `/stw-cgi/system.cgi?msubmenu=deviceinfo&action=view`; `/stw-cgi/attributes.cgi` | Model, SerialNumber, FirmwareVersion no exemplo de deviceinfo | Digest documentado para famílias atuais; documento SUNAPI completo requer contato com fabricante | ONVIF; Samsung legado exige manual por modelo. Autorização granular e todos os campos de rede: NOT_VERIFIED |
| Dahua | Interface CGI encontrada em documento oficial, mas sem manual primário suficiente de inventário nesta pesquisa | Campos/URLs de inventário: NOT_VERIFIED | Auth CGI de inventário e diferenças de firmware: NOT_VERIFIED | ONVIF conforme modelo; obter documento de integração do modelo antes de implementar CGI. Não tratar PDFs hospedados por terceiros como suporte oficial |
| Panasonic/i-PRO | H.265 CGI: GET `/cgi-bin/getinfo?FILE=1` | MAC, VERSION, NAME, SERIAL | Nível de acesso 3; manual descreve Digest/Basic conforme configuração | ONVIF; confirmar família/modelo, principalmente Panasonic legado H.264. Não assumir que manual H.265 cobre todos os Panasonic |
| Bosch | RCP+ over CGI: `/rcp.xml`, parâmetros command/type/direction=READ; exemplo `command=0x0019&type=P_UNICODE&direction=READ&num=1` | Nome de câmera; documento menciona leituras de hardware/firmware, mas seus command IDs não foram verificados aqui | Documento legado descreve Basic/Digest/cookie; disponibilidade varia com CPP/firmware | ONVIF quando habilitado; comandos de inventário completos exigem manual correspondente. HTTP GET também pode executar escrita; direction=READ e command allowlist são essenciais |

**Axis — documentação:** BDI oferece propriedades de identificação e versão, com negociação de versão e erros no JSON mesmo em HTTP 200. Autenticação oficial recomenda Digest em HTTP e Basic em HTTPS, com privilégios por usuário; Basic só deve ser usado em transporte TLS verificado. Outras APIs VAPIX serão selecionadas por modelo para rede, não por suposição de endpoint. [Basic device information](https://www.developer.axis.com/vapix/network-video/basic-device-information/), [Authentication](https://www.developer.axis.com/vapix/authentication/).

**Hikvision — documentação:** o exemplo oficial de integração mostra deviceInfo e Digest Auth. O portal permite localizar guias por série/modelo; a apresentação não estabelece compatibilidade de todos os firmwares. O endpoint mínimo da PoC é esse, sem inventar URLs adicionais. [Material oficial de integração](https://www.hikvision.com/content/dam/hikvision/vn/webinar/Thang3_Hikvision_Tich_Hop_He_Thong_Overview-of-3rd-Party-Integration.pdf), [ISAPI & OTAP Developer Guide](https://tpp.hikvision.com/download/). O PDF da apresentação foi localizado/indexado pela pesquisa, mas sua abertura direta não forneceu páginas renderizáveis; confirmar o guia específico antes da implementação ampliada.

**Hanwha — documentação:** o suporte oficial publica as duas URLs SUNAPI acima, exemplos de campos e respostas não suportadas; informa que o manual completo deve ser solicitado ao representante. A existência de Digest em ficha de uma câmera não verifica todos os níveis de autorização SUNAPI. [SUNAPI no suporte oficial](https://support.hanwhavision.com/hc/en-001/articles/47256995793555-HealthPro-Settings-How-to-Send-SUNAPI-CGI-Commands-from-HealthPro), [XNB-6002: interfaces e segurança](https://supportportal.hanwhavision.com/global/products/XNB-6002-en).

**Dahua — limite explícito:** os resultados de getSystemInfo localizados em cópias externas não foram usados como evidência técnica oficial. O documento primário encontrado comprova CGI para uma ação de desligamento em NVR, não inventário de câmera. Essa ação é mutante e está excluída de qualquer PoC. A página chamada “API” do site não foi promovida a manual de integração. `NATIVE_INVENTORY_DOCUMENTATION = NOT_VERIFIED`. [Documento oficial que evidencia CGI e o risco de ação mutante](https://www.dahuasecurity.com/asset/upload/uploads/soft/20210608/UPS-Integrates-NVR-for-Safe-Shutdown.pdf).

**Panasonic/i-PRO — documentação:** foi lida a especificação H.265 v1.17, disponibilizada em 26/06/2026; §§9.1 e 10.2 descrevem produto e autenticação. O catálogo mantém documento separado para famílias antigas. [Command Interface H.265 v1.17](https://i-pro.com/products_and_solutions/en/media/documentation_file/command-interface-i-pro_h265models), [Catálogo CGI e documento legado](https://i-pro.com/products_and_solutions/en/surveillance/learning-and-support/device-integration/i-pro-cgi). O link do PDF antigo não pôde ser aberto pela ferramenta; cobertura Panasonic legado é NOT_VERIFIED.

**Bosch — documentação:** RCP+ CGI suporta leitura desde firmware 3.0, tipos e autenticação HTTP, além de mecanismos de escrita. Não usar senha em query string, embora documentada como opção legada. Mudanças de portas/defaults em CPP13/CPP14 e versões de firmware impedem assumir HTTP/RCP+ aberto em todas as câmeras. [RCP+ over CGI, §§1–3](https://media.boschsecurity.com/fs/media/pb/media/partners_1/integration_tools_1/developer/rcpplus-over-cgi.pdf), [Secure by default](https://media.boschsecurity.com/fs/media/pb/images/products/video_systems/data_security_1/Bosch_Secure_by_default_TechNote.pdf).

### D.3 Dependências e alternativas

| Opção | Evidência | Recomendação |
|---|---|---|
| onvif-python 0.4.4 + Zeep/Requests | API instalada aceita http_digest, HTTPS, verify_ssl e cache; coleta faz discovery no construtor. Distribuição declara Python >=3.10; há releases recentes | KEEP inicialmente; encapsular transporte e controlar descoberta, auth e destino. Não confundir com onvif-zeep, outra distribuição que também fornece módulo onvif |
| httpx síncrono | Documenta DigestAuth, timeouts connect/read/write/pool e limites de conexão | Usar para adapter nativo mínimo, com uma sessão por target/contexto. Não está instalado neste venv; introdução futura exige ambiente reproduzível |
| Zeep direto + Requests Session | Documenta WSSE e Transport configurável | Alternativa preferida se wrapper impedir sessão explícita, deadline, auth ou diagnóstico; reutilizar WSDL oficial/bundled e portar somente Device Management necessário |
| python-onvif-zeep | Projeto primário existe, mas tracker contém problemas de distribuição/venv e ressalva de diferenças entre câmeras | Não migrar por reputação; comparar na mesma fixture de SOAP/Digest e Python 3.14. Manutenção e compatibilidade operacional pretendidas: NOT_VERIFIED |
| SOAP manual/HTTP | Dá controle exato de uma operação para comparação | Instrumento diagnóstico isolado; não reconstruir toda a biblioteca nem criptografia Digest própria |
| SDK proprietário | Pode cobrir funções exclusivas, mas traz binários/licença/packaging e complexidade | Fora do mínimo, salvo falta comprovada de HTTP/ONVIF em família necessária |

Fontes primárias: [onvif-python no mantenedor](https://github.com/nirsimetri/onvif-python), [distribuição/release history](https://pypi.org/project/onvif-python/), [HTTPX auth](https://www.python-httpx.org/advanced/authentication/), [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [HTTPX limites](https://www.python-httpx.org/advanced/resource-limits/), [Zeep WSSE](https://docs.python-zeep.org/en/latest/wsse.html), [Zeep transports](https://docs.python-zeep.org/en/latest/transport.html), [python-onvif-zeep](https://github.com/FalkTannhaeuser/python-onvif-zeep), [tracker do mantenedor](https://github.com/FalkTannhaeuser/python-onvif-zeep/issues).

A distribuição onvif-python 0.4.3 foi retirada por falta de WSDL em subdiretórios; 0.4.4 publicada em 05/10/2026 corrige esse empacotamento. Isso não explica um 401. Fixar conjunto de versões efetivamente validado e testar wheel/ONEDIR contendo WSDL; não adotar automaticamente toda atualização. Declaração Python >=3.10 não é comprovação de toda integração em 3.14.

## E. ONVIF DIGEST INVESTIGATION

### E.1 Respostas às dez perguntas obrigatórias

1. **Capabilities sem login versus deviceInfo com falha:** classes de acesso diferentes permitem descoberta pública e proteção do inventário. O sucesso anônimo não valida a conta.
2. **Cliente está usando corretamente os mecanismos?** A implementação instalada configura HTTPDigestAuth quando solicitado e UsernameToken(use_digest=True) por padrão. O scanner não solicita HTTP Digest. Há configuração válida para cada mecanismo, mas não existe evidência de interoperabilidade do Digest com o alvo.
3. **Diferenças:** HTTP Digest está no Authorization HTTP e usa challenge, realm, nonce, URI/método, algoritmo e qop. UsernameToken PasswordDigest está no SOAP e usa nonce/Created/senha. “Digest” nesses contextos não designa o mesmo formato. [RFC 7616](https://www.rfc-editor.org/rfc/rfc7616), [OASIS UsernameToken 1.1](https://docs.oasis-open.org/wss/v1.1/wss-v1.1-spec-os-UsernameTokenProfile.pdf).
4. **Mistura incompatível:** não foi encontrada mistura automática na versão instalada. Com http_digest=True, _create_wsse retorna None. Mistura no script diagnóstico histórico é UNDETERMINED, pois não foi lido/executado. Não recomendar enviar ambos para “tentar resolver”.
5. **Distinguir causas:** registrar challenge sem valores sensíveis, etapa e resultado da resposta autenticada. 401 inicial pode ser negociação normal; 401 final indica rejeição, não prova senha errada. 403 indica acesso recusado, mas aceitação da credencial exige evidência adicional. SOAP ter:NotAuthorized preserva ambiguidade entre conta/permissão/mecanismo. ErrorCode sozinho não resolve essa distinção.
6. **Diagnosticar sem modificar:** ler configuração/modelo já disponível, reproduzir SOAP exato em servidor simulado e, somente numa atividade operacional futura explicitamente autorizada, comparar clientes na mesma operação/endpoint/conta. Sem reboot, mudança de hora, habilitação de serviço ou alteração de usuários.
7. **Limitações:** Requests 2.34.2 não implementa qop somente auth-int e não cobre todos os algoritmos session Digest. O scanner não controla connect/read separados, timestamp por target nem sessão explícita. Não há challenge real para relacionar qualquer limitação ao 401. HTTPX também não implementa auth-int no source consultado; trocar para ele não resolve esse caso automaticamente. [Source oficial HTTPX Digest](https://github.com/encode/httpx/blob/master/httpx/_auth.py).
8. **Correção recomendada:** adicionar política explícita de auth ONVIF, escolhida por configuração/capability/challenge, e testar http_digest=True para caso Digest-only em ambiente autorizado. Usar um mecanismo por tentativa. Caso o wrapper impeça controles necessários, Device Management via Zeep/Session explícita é evolução localizada. Correção definitiva do 401 depende do diagnóstico abaixo.
9. **Comprovar:** fixture HTTP Digest valida challenge→Authorization→SOAP de sucesso; fixture WSSE valida ausência de HTTP auth, nonce/Created novos e resposta; comparação operacional futura deve obter GetDeviceInformation e campos esperados sem writes e dentro do limite de requests. Sem isso, declarar apenas correção sintética/configuração.
10. **Papel ONVIF:** manter como protocolo comum, descoberta e complemento. ONVIF bem suportado pode ser primário no fabricante desconhecido; não obrigar conta específica em toda câmera nem abandonar o protocolo por um alvo com falha indeterminada.

Um manual Hikvision atual diferencia Digest de Digest&ws-username token; manual de outra família esclarece que contas ONVIF são independentes. Esses documentos sustentam a hipótese de mecanismo/escopo, sem provar firmware ou permissões do alvo. [Manual G5 Web5.0, §8.22](https://assets.hikvision.com/prd/normal/all/doc/m000000026/UD39407B-C_Network-Camera_User-Manual_G5-Web5.0_20260310.pdf), [Manual V5.5.90, Integration Protocol](https://assets.hikvision.com/prd/public/all/doc/m000007837/UD12963B-C_Baseline_User-Manual-of-Network-Camera_V5.5.90_20221222.pdf).

### E.2 Hipóteses e testes discriminantes propostos — NÃO executados contra câmera

| Hipótese / status | Teste futuro | Resultado que a sustenta | Critério para escolher correção |
|---|---|---|---|
| WSSE incompatível com Digest-only / PROBABLE | Confirmar manual do modelo e modo informado; testar apenas HTTP Digest | Mesmo endpoint/conta funciona em Digest, falha WSSE | Seleção explícita Digest para esse perfil; não mudar câmera |
| Conta/senha ONVIF incorreta ou domínio diferente / UNDETERMINED | Cliente conhecido para GetDeviceInformation, mesma conta fornecida localmente | Ambos rejeitam com mecanismo suportado | Revisão pelo operador da conta existente; não provisionar milhares de contas |
| Permissão insuficiente / UNDETERMINED | Comparar operação permitida e GetDeviceInformation com mesma autenticação | Auth aceita numa operação, acesso recusado noutra | Reportar AUTHORIZATION_DENIED com operação; respeitar acesso |
| Challenge incompatível / UNDETERMINED | Observar somente scheme, algorithm, qop, stale presente e sequência de status | auth-int-only/algoritmo ausente no cliente, antes de validação válida | Transporte compatível, testado; sem downgrade silencioso de câmera |
| URI/redirect/proxy interfere / UNDETERMINED | Comparar destination/método/path SOAP, sem proxies e sem seguir redirect | Cliente controlado funciona no endpoint canônico | Corrigir seleção de endpoint/session, não senha |
| Clock skew WSSE / UNDETERMINED | Ler UTC via operação pública; comparar Created sintético e offset local do cliente | WSSE passa somente com Created apropriado | Offset por target em memória, sem SetSystemDateAndTime. Essa hipótese não explica automaticamente HTTP Digest |
| Defeito do wrapper / UNDETERMINED | SOAP e auth equivalentes via Zeep/Session explícita versus wrapper | Transporte controlado passa e wrapper falha, com mesmas entradas | Corrigir/configurar wrapper ou substituir somente essa fronteira |
| Firmware implementa auth de forma distinta / UNDETERMINED | Guia exato + reprodução de challenge/response sanitizada e suporte do fabricante | Falha persiste em clientes conformes e conta confirmada | Registrar incompatibilidade por perfil; caminho nativo onde disponível |

O sucesso H264 no ARGOS demonstra apenas o caminho de mídia testado. Não verifica GetDeviceInformation, nem conta ONVIF, nem que Digest HTTP/SOAP foram negociados.

O 401 inicial não deve consumir “falha de login” lógica no scanner, mas a câmera pode contabilizar tráfego segundo política própria. O scanner não pode prometer lockout zero. Após uma resposta autenticada final rejeitada, parar tentativas automáticas de auth naquele dispositivo por padrão.

## F. ARCHITECTURAL ALTERNATIVES

Comparação qualitativa fundamentada em requisitos e interfaces; não há benchmark operacional multivendor.

| Critério | ONVIF-FIRST | VENDOR-FIRST fixo | Híbrida recomendada |
|---|---|---|---|
| Cobertura | Contrato comum; depende de ONVIF disponível | Depende de adapters completos e família correta | ONVIF comum + nativo comprovado |
| Modelos/firmwares | Quirks de SOAP/auth/profiles | Quirks proprietários e endpoint por família | Suporte por operação, com UNKNOWN explícito |
| ONVIF habilitado | Dependência forte | Evitável em teoria; preauth atual ainda chama ONVIF sempre | Não obrigatório para fabricante conhecido/capacidade nativa |
| Credenciais | Pode exigir conta ONVIF independente | Favorece conta HTTP existente | Usa somente a credencial da linha; escopo respeitado |
| APIs disponíveis | Menos dependência nativa | Pode parar em API ausente | Escolha pelo suporte observado/documentado |
| Latência/requests | Bom se primeiro caminho resolve; discovery duplicada possível | Bom se adapter resolve; ruim se sempre complementa | Evita requests sem campo ou recuperação útil |
| Lockout | Risco se tentar vários auth modes | Risco ao alternar native/ONVIF após 401 | Budget de auth por dispositivo; sem spraying/retry de rejeição |
| Qualidade de dados | Bom conjunto padrão; extensões variam | Pode oferecer identidade/rede mais fiel | Precedência por campo + conflito/proveniência |
| Fallback | Proprietário exige identificação | ONVIF pode exigir outra conta | Elegibilidade antes de credencial; parar quando acesso recusado |
| Segurança | WSSE/Digest/TLS requerem controles | CGI pode incluir ações mutantes até em GET | Allowlist de operações/destinos e TLS verificado |
| Escala/manutenção | Menos adapters; quirks genéricos | Seis famílias elevam manutenção | Mesma modularidade; plano curto, sem motor de regras |

Não recomendo uma quarta arquitetura estrutural: “adaptativo com aprendizagem”, plugin runtime dinâmico ou serviço distribuído não apresenta benefício comprovado. A política híbrida cabe em uma função determinística e tabelas de operações; não necessita framework.

## G. RECOMMENDED TARGET ARCHITECTURE

### G.1 Diagrama textual

```text
ApplicationController
  ├─ SingleWorkflow ─┐
  └─ MultiWorkflow ──┴─ InventoryService
                         ├─ Target validation / per-row credential scope
                         └─ CollectionCoordinator (evolução de VendorFirstCollector)
                              ├─ BoundedDiscovery → ManufacturerResolution
                              ├─ CollectionPolicy → plano curto de operações
                              ├─ NativeAdapterRegistry → adapter habilitado
                              ├─ OnvifAdapter
                              ├─ TransportContext / deadline / auth budget
                              └─ EvidenceMerger → CollectionReport
                                                   ├─ CameraResult tipado
                                                   ├─ attempts / provenance / conflicts
                                                   └─ TerminalUI / ExcelWriter / log local
```

SnapshotService continua separado e posterior; executor de lote envolve collect_one, não implementa política de fabricante. As responsabilidades podem ser funções/dataclasses nos módulos atuais, sem uma classe obrigatória para cada caixa.

### G.2 Algoritmo determinístico

1. Validar target, row_id, campos solicitados e configurar contexto exclusivo da linha. IP/porta/scheme aceitos são dados de destino; nunca username/password em URL. Iniciar relógio monotônico, deadline e contadores.
2. Normalizar hint opcional. Hint confiável e adapter habilitado permitem caminho nativo sem descoberta ONVIF obrigatória. Fazer confirmação de identidade na resposta autenticada do próprio caminho selecionado.
3. Sem hint suficiente, descoberta anônima curta em destino explicitamente permitido. Preferir observações já disponíveis; limitar a um fluxo ONVIF de capabilities/serviços e, se justificado por resposta pública, uma leitura HTTP genérica. Não pesquisar seis APIs com credenciais. Reusar capabilities obtidas; GetSystemDateAndTime só quando acrescenta evidência ou será usado em diagnóstico WSSE.
4. Resolver fabricante em STRONG/WEAK/CONFLICTING/UNKNOWN. Sinais em conflito não são resolvidos pela ordem do XML. Hint preservado como declarado, identidade detectada separada. Não encaminhar para outro vendor após uma falha de login.
5. Selecionar um adapter nativo habilitado se fabricante suficientemente estabelecido e operações necessárias suportadas/possíveis. Caso contrário, selecionar ONVIF genérico se endpoint utilizável existir; informar motivo de ausência nativa.
6. Ler operação mínima de identidade com um mecanismo de auth escolhido. Challenge anônimo e resposta autenticada pertencem à mesma negociação; preservar seus eventos. Não ativar ambos os mecanismos nem testar uma lista de senhas/modos.
7. Validar payload, identidade e campos. Registrar cada evidência imediatamente, inclusive se outra operação falhar. Resposta vazia não constitui coleta de inventário bem-sucedida por si só.
8. Calcular campos exigidos faltantes. Sem faltas/conflictos relevantes, encerrar. Se faltantes, consultar apenas operações capazes de fornecê-los. Não consultar uma segunda fonte apenas para “ter duas fontes”. Auditoria de divergência pode ser um modo explícito posterior.
9. Fallback por ausência de suporte/endpoint ou falha transitória pode usar o outro protocolo, dentro do orçamento. **Após rejeição autenticada final, o default é não realizar novo login automático na mesma câmera**, inclusive em outro protocolo. Exceção exige política por família e escopo de credencial comprovado, com limite aprovado; o histórico não muda a senha nem importa outra credencial. Isto reduz risco, embora não prove ausência de lockout.
10. Agregar valores, origem, conflitos e tentativas; calcular status por cobertura. Apresentar causa principal sanitizada e resultado por linha; fechar sessões e liberar referências da credencial.

Credenciais independentes por protocolo não podem ser inventadas a partir das três colunas atuais. Quando a mesma conta não serve ONVIF e HTTP, registrar SCOPE_UNVERIFIED/ACCESS_DENIED e manter dados permitidos. Uma eventual entrada com duas credenciais por câmera seria decisão de produto futura, fora do mínimo recomendado.

### G.3 Fluxos solicitados

| Cenário | Fluxo e saída |
|---|---|
| Fabricante conhecido | hint→adapter habilitado→identidade nativa→campos faltantes→ONVIF somente se elegível. Se não houver adapter, ONVIF direto disponível |
| Fabricante desconhecido | descoberta anônima limitada→resolução. Se continuar desconhecido, um coletor ONVIF genérico; sem sinais/endpoint, diagnóstico de identificação insuficiente |
| Auth bem-sucedida | operação autorizada→evidências validadas→operações adicionais necessárias→SUCCESS quando atende perfil solicitado |
| Auth parcialmente bem-sucedida | fonte A fornece dados, B recusa→preservar A e falha B→SUCCESS com warning se cobertura total; PARTIAL_SUCCESS se incompleta/conflitante |
| Todos coletores falham | sem evidência útil→FAILED; com identificação/public response útil→PARTIAL_SUCCESS de descoberta, explicitamente sem inventário autenticado |
| Nativa autentica, ONVIF não | nenhuma invalidação dos dados nativos; sem retry auth; mostrar aviso/campos faltantes |
| ONVIF autentica, nativa não | preservar ONVIF; só tentar outra fonte se auth budget ainda permitir; não insistir em nativa rejeitada |

### G.4 KEEP / CHANGE / REMOVE / ADD

| Ação | Componente e motivo |
|---|---|
| KEEP | Monólito modular, entrypoint/controller, workflows, InventoryService, CameraTarget, normalizer/registry como fronteiras, stdlib logging, snapshot/Excel isolados |
| KEEP | onvif-python inicialmente; proteção repr=False, cache em disco desativado, monotonic duration e clientes falsos |
| CHANGE | VendorFirstCollector para coordenação por evidência/necessidade; preauth condicional e reutilizável; exceptions/FAILED uniformes |
| CHANGE | Fingerprint, normalizer aliases por família comprovada, contratos tipados de adapter, status/merge e seleção explícita auth |
| CHANGE | Transporte: scheme/port, trust_env=False, verificação TLS explícita, deadlines, destino permitido, fechamento de sessões |
| REMOVE | Dependência de substrings arbitrárias, preauth obrigatório mesmo com fabricante confiável, descarte silencioso de falhas e erro agregado fixo ONVIF |
| REMOVE | Somente da política futura: complementação duplicada sem campo útil; nenhum módulo inteiro precisa ser apagado agora |
| ADD | Native Hikvision deviceInfo mínimo; CollectionAttempt, EvidenceRecord/FieldProvenance e CollectionReport tipados; policy/budgets pequenos |
| ADD | Em P4/P5: executor limitado, cancelamento cooperativo, resultados indexados por linha e saída parcial sem credenciais |

### G.5 Contratos entre componentes e transporte

Recomendação de contratos internos, sujeitos à aprovação P2:

- `ScanRequest`: CameraTarget, row_id, manufacturer_hint opcional, required_fields e perfil de operação. O hint fica fora das credenciais; nenhum vault/profiling compartilhado.
- `CollectionContext`: deadline monotônico, cancel_event, destinos aprovados e budget de auth/retry. Scope exclusivo por linha, com controle de concorrência por IP no lote.
- `AdapterSupport`: fabricante/famílias, operações implementadas, campos possíveis e versão do adapter. Registro duplicado explícito ou rejeitado; placeholders ficam fora da composição.
- `AdapterResult`: evidências tipadas e tentativas, independentemente de falha parcial; não usa CameraResult final para representar cada fonte isolada.
- `CollectionAttempt`: source/protocol, operation, stage, outcome, normalized_error, http_status, soap/vendor_code, auth_mechanism, duration e retry_count. Sem request/response integrais.
- `EvidenceRecord`: campo tipado, valor validado, origem/operação, confiança categórica e instante observado; conflito guarda candidatos sanitizados.
- `CollectionReport`: resultado público + tuple de attempts + tuple de proveniência + tuple de conflitos e campos faltantes. Um DTO complementar evita bag arbitrária dentro de CameraResult.

Implementar contratos só na medida necessária à primeira slice; não criar catálogo de regras de todos os fabricantes antes das provas.

TransportContext impede credenciais/segredos via environment/netrc: desabilitar trust_env e autenticação implícita. Requests instalado preserva trust_env=True; isso é risco de rota/proxy/credencial ambiente, não prova de que preauth enviou uma conta real nesta execução. Anonymous transport não recebe auth nem cookies herdados.

Validar XAddr/redirect/snapshot URI contra target e portas permitidas, impedir userinfo e troca para host externo; redirects cross-origin bloqueados. Não substituir hostname anunciado por IP indiscriminadamente, pois TLS/virtual hosts podem depender dele: exigir correspondência ou mapeamento explicitamente aprovado. Não reduzir HTTPS a HTTP após erro TLS. CA confiável ou fingerprint previamente autorizado dispensa mudanças no equipamento; certificados ainda não confiáveis produzem erro específico. Operações XML usam parser sem entidades externas e limite de tamanho; não transportar configuração/usuarios/logs sensíveis fora da allowlist de inventário.

## H. DOMAIN MODEL ASSESSMENT

### H.1 CameraResult

Os 14 campos são suficientes para o contrato mínimo P1, **insuficientes para o inventário desejado**. Preservar a validade histórica da P1 e propor revisão em P2: campos explícitos de network interfaces, DHCP, prefix/netmask, gateways, DNS e network protocols/ports; capacidade ONVIF separada de auth/consulta bem-sucedida; snapshots permanecem no contrato de sua fase.

Não acrescentar vinte strings soltas nem bag genérica. Preferir `NetworkInventory` tipado, com interfaces/IPv4/IPv6 e DNS manual/DHCP distintos, e `ProtocolAvailability` tipado. Disponibilidade pode ser REACHABLE/UNREACHABLE/UNTESTED e auth SUCCESS/DENIED/UNTESTED separadamente. Uma porta configurada pelo protocolo não equivale a conexão testada. `collection_method` pode representar NATIVE/ONVIF/HYBRID/PREAUTH conforme contribuição efetiva; fonte detalhada permanece no report. Valores novos exigem contrato futuro aprovado.

Result status não deve codificar todas as causas técnicas. Manter SUCCESS/PARTIAL_SUCCESS/FAILED/CANCELLED; diferenças ficam em attempts e cobertura. O enum CANCELLED já existe, embora o lote ainda não esteja implementado.

### H.2 Precedência concreta por campo

| Campo | Regra recomendada |
|---|---|
| IP alvo | Sempre o IP solicitado. Endereços reportados pela câmera ficam no inventário de interfaces; não substituem alvo |
| Fabricante | identidade autenticada explícita e validada > identidade pública estruturada > hint > pista fraca. Declarado/detectado ficam distintos; OEM/rebrand pode exigir revisão |
| Modelo/serial | nativo autenticado documentado > ONVIF autenticado > público explícito. Não preencher serial com MAC ou deviceID |
| Firmware | versão de firmware nativa documentada > ONVIF FirmwareVersion. Preservar release/build e valor alternativo quando divergir; não tratar encoderVersion como firmware do sistema |
| Hardware ID | ONVIF HardwareId e hardwareVersion nativa têm semânticas potencialmente diferentes. Conservar campos distintos quando necessário; não colapsar por semelhança do nome |
| Hostname | campo de hostname dedicado > deviceName apenas se manual confirmar equivalência. Caso contrário conservar nome do dispositivo separado |
| MAC/rede | dados da interface nativa documentada ou ONVIF GetNetworkInterfaces, vinculados ao token/interface/endereço do alvo. Empate resolvido por prioridade declarada por adapter/família |
| Portas | valores reportados em operação de configuração de protocolos; porta efetivamente testada é evidência separada |
| Disponibilidade ONVIF | sucesso público demonstra serviço alcançável na operação observada; não demonstra auth nem todas as capabilities operacionais |

Estas são políticas propostas, não superioridade universal comprovada da API nativa. Um adapter só recebe precedência específica após fixture e validação de seu campo. Semânticas desconhecidas ficam ausentes/NOT_VERIFIED.

### H.3 Conflitos, status e exemplos

Valores None, vazios/whitespace, placeholders documentados e formatos inválidos não substituem valores úteis. Normalizar só o que for semanticamente seguro; não remover caracteres de serial nem inventar equivalência de firmware. Ordem de retorno das fontes não altera a seleção. Falha posterior nunca apaga um valor validado.

1. ISAPI modelo X/serial Y/firmware Z, ONVIF X/Y/W: manter Z por regra documentada e registrar conflito de firmware com origem. Se firmware é requerido e a diferença não é explicada por build/formato, PARTIAL_SUCCESS; conflito não é apagado silenciosamente.
2. ISAPI identidade completa, ONVIF auth negada quando apenas campo opcional foi solicitado: SUCCESS no perfil satisfeito, aviso no report; error_code agregado None. O histórico mantém AUTH_REJECTED.
3. ISAPI modelo X e serial Y, ONVIF completa firmware Z após timeout inicial: SUCCESS se todos os requisitos são atendidos e sem conflito; timeout recuperado fica na tentativa, não como erro final pendente.
4. Apenas fingerprint Hikvision e auth negada: PARTIAL_SUCCESS de descoberta, identidade/inventário ausentes. Pode ser aceitável para triagem, não para inventário de serial.
5. TCP aberto, sem resposta de leitura útil: FAILED. TCP sozinho não é dado suficiente para inventário; conectividade observada permanece em diagnostics.
6. Cancelamento: CANCELLED com evidências já obtidas e coverage; não converter em FAILED por fim do executor.

Critério proposto de SUCCESS: todos os campos exigidos pelo perfil estão válidos ou explicitamente classificados como não aplicáveis por regra aprovada, sem conflito material. Campo requerido UNSUPPORTED não vira sucesso automaticamente: o perfil deve definir se aceita essa ausência. PARTIAL_SUCCESS: alguma evidência útil, com falta/conflito relevante. FAILED: nenhuma evidência útil após o plano permitido. O perfil mínimo de identidade sugerido é fabricante/modelo/serial/firmware; sua aprovação é decisão humana, não mudança realizada.

Para escolher erro principal: INVALID_INPUT antes de rede; CANCELLED como status; conflito de identidade antes de enriquecimento; rejeição final de acesso na operação necessária; depois deadline/transport/protocol/parse, conforme bloqueio efetivo do campo requerido. Demais erros preservados em ordem de tentativa. Não reduzir todo 403 a senha inválida nem todo OSError a câmera offline.

## I. CONCRETE REMEDIATION PLAN

As tabelas seguintes são contratos de recomendação para implementação futura. As referências a arquivos identificam responsabilidade prevista; não houve alteração desses arquivos. Os testes Txx são definidos em K.

### I.1 ONVIF Digest

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_01_ONVIF_DIGEST |
| DESCRIPTION | Descoberta Hikvision responde; GetDeviceInformation autenticado falha por WSSE e por Digest em diagnóstico informado |
| CURRENT_EVIDENCE | Código omite http_digest; versão 0.4.4 alterna mecanismos sem misturá-los; operacional informa 401 em ambos; não há challenge/firmware/trace sanitizado suficiente |
| ROOT_CAUSE_STATUS | UNDETERMINED para o 401 Digest; PROBABLE para incompatibilidade do default WSSE com Digest-only informado |
| RECOMMENDED_SOLUTION | Política de auth explícita, uma modalidade por tentativa e transporte controlado; aplicar correção condicional segundo E.2 |
| WHY_THIS_SOLUTION | Corrige uma omissão objetiva e permite distinguir conta/permissão/negociação sem modificar câmera |
| ALTERNATIVES_CONSIDERED | Troca imediata de biblioteca rejeitada por ausência de prova; WSSE+Digest simultâneos rejeitados; Zeep direto se wrapper limitar controles |
| REQUIRED_CODE_CHANGES | adapter.py/preauth.py: contexto de transporte, opções auth/HTTPS/porta e captura permitida de etapas; teste de fixture do cliente real; evitar discovery autenticada duplicada |
| REQUIRED_CONTRACT_CHANGES | AuthMechanism e tentativa tipados; política de rejeição/retry; endpoint/scope; nenhum campo de senha no resultado |
| EXPECTED_IMPACT | Possível recuperação do caminho atual e diagnóstico causal; não prometer resolver 401 Digest antes do teste discriminante |
| RISKS | Tentativas autenticadas adicionais podem consumir lockout; timestamps/redirects/certificados exigem controle; credentials HTTP podem não ser ONVIF |
| VALIDATION_TESTS | T03–T06, T10, T12; futura comparação operacional sob autorização separada, conforme E.2 |
| ROADMAP_PLACEMENT | Primeira slice P2 de transporte/diagnóstico, em paralelo lógico com PoC ISAPI, sem implementação simultânea necessária |
| PRIORITY | Alta no plano técnico; finding F04 classificado MEDIUM porque a causa operacional permanece aberta |

### I.2 Adapter nativo mínimo

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_02_NATIVE_ADAPTER |
| DESCRIPTION | Registry vazio e seis placeholders; preferência nativa ainda não comprovada |
| CURRENT_EVIDENCE | main.py compõe registry vazio; HikvisionAdapter.collect levanta NotImplementedError; teste operacional usou ONVIF |
| ROOT_CAUSE_STATUS | CONFIRMED — capability não implementada por escopo P1, não regressão |
| RECOMMENDED_SOLUTION | Hikvision ISAPI mínimo: GET deviceInfo, HTTP Digest, parser XML por namespace/local-name permitido, identidade/campos e tentativas, integrado ao SINGLE |
| WHY_THIS_SOLUTION | Ataca risco real com uma operação oficial e valida política/adapter/merge antes de seis implementações completas |
| ALTERNATIVES_CONSIDERED | Axis mínimo seria alternativa válida se único target nativo disponível fosse Axis; aguardar P7 mantém risco; adapter Hikvision completo agora amplia escopo sem necessidade |
| REQUIRED_CODE_CHANGES | manufacturers/hikvision.py, registry.py e composição em main.py; cliente HTTP síncrono isolado; suporte por operação; tests de transport/parser/fluxo |
| REQUIRED_CONTRACT_CHANGES | CameraCollector/adapter deixa object→object; operações read-only allowlist; capability/status por operação; CollectionMethod nativo e identidade sanitizada |
| EXPECTED_IMPACT | Primeiro inventário nativo autenticado demonstrável, sem depender de conta ONVIF se conta HTTP já for apropriada |
| RISKS | Usuário ONVIF do teste pode não ter acesso ISAPI; firmware desconhecido pode não oferecer endpoint; GET não é proteção suficiente sem allowlist |
| VALIDATION_TESTS | T07–T10, T13; futura prova autorizada da resposta de identidade e vantagem objetiva sobre ONVIF |
| ROADMAP_PLACEMENT | PoC extraída de P7 dentro de P2, sujeita a aprovação; P7 continua expansão/completude Hikvision |
| PRIORITY | Alta para reduzir incerteza, finding F05 MEDIUM por ser trabalho planejado |

**Escopo mínimo implementável proposto:** somente GET `/ISAPI/System/deviceInfo`. Mapping: model→model; serialNumber→serial; firmwareVersion→firmware; macAddress→MAC validado. deviceName é nome do dispositivo, sem renomeá-lo automaticamente hostname. hardwareVersion fica com semântica própria, não HardwareId por inferência. A identidade Hikvision é confirmada por resposta/namespace e perfil de adapter, sem tratar string arbitrária como fabricante autenticado.

HTTP Digest deve ser negociado no endpoint selecionado, com lib existente, sem registrar headers e sem login browser. Resposta HTTP 200 com XML inválido ou ResponseStatus de erro não é sucesso. Campos ausentes ficam ausentes; namespace/version é tolerado quando a família documentada permite. 404/405/unsupported interrompem a operação como indisponível, não acionam logins em outros vendors. Só ampliar para rede após documentação do modelo e objetivo de campo.

O critério de registro é implementação de operação declarada + testes determinísticos dessa operação + composição explícita. `ENABLED_FOR_DEVICE_INFO` não significa “adapter completo”. Uma futura validação operacional comprova família/modelo específico, não todas as Hikvision.

### I.3 Diagnóstico das falhas

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_03_ERROR_DIAGNOSTICS |
| DESCRIPTION | Mensagens genéricas não mostram fase/operação nem cadeia de tentativas |
| CURRENT_EVIDENCE | Preauth engole erros; vendor/complemento descartam exceptions; InventoryService só vê erro final; TIMEOUT agrega connect/read |
| ROOT_CAUSE_STATUS | CONFIRMED para limitação do software; causa do timeout real UNDETERMINED |
| RECOMMENDED_SOLUTION | CollectionAttempt por operação e CollectionReport agregado, classification no transporte/protocolo, summary sanitizado na UI |
| WHY_THIS_SOLUTION | Torna retries/fallback verificáveis e explica parcial sem framework de observabilidade |
| ALTERNATIVES_CONSIDERED | Mais strings no ErrorCode não preservam contexto; raw debug expõe credenciais; stack completo de observabilidade é desproporcional |
| REQUIRED_CODE_CHANGES | domain/errors/enums, preauth, ONVIF/native boundaries, strategy e InventoryService; log estruturado por allowlist; TerminalUI mostra causa principal |
| REQUIRED_CONTRACT_CHANGES | Stages DISCOVERY/CONNECT/HTTP/AUTH/SOAP/PARSE/MERGE; categorias específicas e tentativa com timeout kind; um erro agregado compatível + histórico completo |
| EXPECTED_IMPACT | Diferencia falha de rede, leitura, acesso, endpoint e payload; fallback deixa de apagar causas anteriores |
| RISKS | Diagnóstico bruto pode incluir segredo; testes devem incluir canários em exceptions/URLs/XML; código legado pode confluir 403 e 401 |
| VALIDATION_TESTS | T01/T02, T06, T09/T10, T12/T14; zero segredo em todos os outputs |
| ROADMAP_PLACEMENT | Primeiro incremento P2, usado pela PoC e por ONVIF |
| PRIORITY | HIGH, finding F03 |

Vocabulário interno mínimo proposto: CONNECT_TIMEOUT, READ_TIMEOUT, CONNECTION_REFUSED, TLS_ERROR, HTTP_ERROR, AUTH_REJECTED, AUTHORIZATION_DENIED, AUTH_MECHANISM_UNSUPPORTED, SOAP_FAULT, ENDPOINT_UNSUPPORTED, INVALID_RESPONSE, DEADLINE_EXCEEDED, CANCELLED e UNEXPECTED. Public ErrorCode pode mapear famílias para compatibilidade; não precisa conter toda a combinação de protocolo×etapa. Marcadores textuais ficam como fallback de exceções legadas, com causa indeterminada explicitada.

### I.4 Identificação de fabricante

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_04_MANUFACTURER_DISCOVERY |
| DESCRIPTION | Identificação sem FABRICANTE não pode depender de acesso público ONVIF universal nem usar spraying |
| CURRENT_EVIDENCE | Resolver aceita qualquer substring de marker; falso Axis e escolha por ordem reproduzidos; suporte hint não chega ao collect atual |
| ROOT_CAUSE_STATUS | CONFIRMED para bugs de fingerprint; cobertura real multivendor UNDETERMINED |
| RECOMMENDED_SOLUTION | Sinais tipados/contextuais, confiança STRONG/WEAK/CONFLICTING/UNKNOWN, hint separado e caminho UNKNOWN explícito |
| WHY_THIS_SOLUTION | Evita adapter errado, conserva incerteza e permite escolha segura sem autenticar seis APIs |
| ALTERNATIVES_CONSIDERED | MAC OUI/Server/realm isolados rejeitados como prova; discovery multicast opcional por site; SNMP/SADP/protocolos adicionais fora do mínimo |
| REQUIRED_CODE_CHANGES | ManufacturerResolver/Normalizer, transporte de hint em ScanRequest, parser de sinais estruturados e policy de conflito; registro de suporte por família |
| REQUIRED_CONTRACT_CHANGES | ManufacturerResolution declara selected/detected/declared/confidence/reasons; sinais fortes conflitantes não selecionam vendor automaticamente |
| EXPECTED_IMPACT | Resultado determinístico e menos falso positivo; fabricante desconhecido deixa de ser mascarado |
| RISKS | OEM/rebranding; certificado/challenge é pista não necessariamente marca; sinais públicos podem ser indisponíveis ou manipulados |
| VALIDATION_TESTS | T11: substrings, ordem invertida, OEM, namespace, alias e hint conflitante; T12 para destinos não permitidos; T13 fluxo UNKNOWN |
| ROADMAP_PLACEMENT | P2 junto à seleção; descoberta adicional só após ganho medido |
| PRIORITY | HIGH, finding F02 |

Aliases como Hanwha Vision/Hanwha Techwin devem ser adicionados quando a família correspondente estiver documentada e testada. Não transformar todo nome desconhecido em fabricante suportado. Confiança forte não equivale a autenticação criptográfica do produto.

### I.5 Estratégia de coleta

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_05_COLLECTION_STRATEGY |
| DESCRIPTION | Ordem rígida pode gerar descoberta obrigatória, chamadas duplicadas e fallback com conta incompatível |
| CURRENT_EVIDENCE | preauth sempre; _needs_onvif_complement fixo em quatro campos; porta 80; auth default; nenhum registry nativo real |
| ROOT_CAUSE_STATUS | CONFIRMED para comportamento atual; superioridade operacional da alternativa ainda não medida |
| RECOMMENDED_SOLUTION | HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE, algoritmo G.2 e auth budget por dispositivo |
| WHY_THIS_SOLUTION | Maximiza cobertura permitida com plano curto e evita segundo protocolo sem benefício ou após rejeição final |
| ALTERNATIVES_CONSIDERED | ONVIF-first e vendor-first universais comparados em F; descoberta exaustiva e engine de regras excluídas |
| REQUIRED_CODE_CHANGES | strategy evolui para coordinator/policy; reutiliza discovery; operações dependem de required_fields/support/deadline; erros tipados alimentam decisões |
| REQUIRED_CONTRACT_CHANGES | Perfil de coleta, eligibility/reasons e stop conditions; credencial vinculada à linha; regra de fallback após auth failure sujeita a aprovação |
| EXPECTED_IMPACT | Menos requests e latência quando fonte primária basta; caminho previsível quando API ou ONVIF indisponíveis |
| RISKS | Política conservadora após 401 pode deixar campos ausentes; precisa representar restrição de acesso, não esconder falha |
| VALIDATION_TESTS | T13–T15: sem duplicação, nativa/ONVIF alternadas por indisponibilidade, nenhum outro fabricante, limite de auth e de operações |
| ROADMAP_PLACEMENT | P2, antes de snapshot; política usada inalterada por MULTI |
| PRIORITY | MEDIUM, findings F04/F07 e dependência de F01–F03 |

Capacidades devem ser descobertas **na medida em que decidem a próxima operação**. Evitar catálogo completo antes de uma leitura de identidade barata. API nativa conhecida pode demonstrar disponibilidade ao próprio GET documentado. Ausência de suporte por campo não exige scan de todos os endpoints.

### I.6 Fusão de evidências

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_06_EVIDENCE_MERGE |
| DESCRIPTION | Falha posterior apaga fabricante público; merge herda status/erro/método da fonte principal e não conserva origem |
| CURRENT_EVIDENCE | Reprodução preauth+timeout perde fabricante; merge completo mantém TIMEOUT/PARTIAL; conflicts apenas warning de manufacturer |
| ROOT_CAUSE_STATUS | CONFIRMED para perda/limitação; decisão final de status exige contrato de cobertura |
| RECOMMENDED_SOLUTION | EvidenceMerger determinístico por campo, preservação imediata, conflito explícito e status calculado sobre perfil final |
| WHY_THIS_SOLUTION | Recupera dados já obtidos e evita chamar consulta parcial de falha total ou resultado completo de parcial indefinido |
| ALTERNATIVES_CONSIDERED | Last-write-wins rejeitado; vendor-prevalece-em-tudo rejeitado por semânticas distintas; bags arbitrárias rejeitadas |
| REQUIRED_CODE_CHANGES | strategy/InventoryService e DTOs tipados; sources entregam evidências; agregador define CameraResult e report; normalização de vazio/placeholder |
| REQUIRED_CONTRACT_CHANGES | H.2/H.3, required_fields, métodos contributing, proveniência e conflitos; CameraResult rede tipada em P2 após aprovação |
| EXPECTED_IMPACT | Nenhuma evidência válida perdida; status consistente e auditável; divergência de firmware visível |
| RISKS | Conflitos de OEM e campos sem equivalência; precedência nativa só após validar semântica por perfil |
| VALIDATION_TESTS | T01/T02/T14: erros de qualquer fonte, FAILED como retorno, vazio, conflitos, ordem das fontes e status recalculado |
| ROADMAP_PLACEMENT | Primeiro incremento P2 de preservação/diagnóstico; expansão de rede incremental depois da PoC |
| PRIORITY | HIGH para F01; MEDIUM para F06/F08 |

### I.7 Escalabilidade

| Campo obrigatório | Resolução |
|---|---|
| PROBLEM_ID | PROBLEM_07_SCALABILITY |
| DESCRIPTION | 2.300 linhas individuais, tempos heterogêneos, duplicatas, cancelamento e resultados parciais |
| CURRENT_EVIDENCE | Contratos preveem threads/deadlines; implementação de lote/config está ausente; validação atual sequencial/sintética não comprova carga |
| ROOT_CAUSE_STATUS | CONFIRMED como capability ainda não implementada; falha concreta em carga UNDETERMINED |
| RECOMMENDED_SOLUTION | ThreadPoolExecutor limitado, submissão em janela, contexto por linha, gates por IP, deadlines cooperativos, exportação parcial/reinício explícito |
| WHY_THIS_SOLUTION | Adequado ao I/O bloqueante e stack existente; custo/complexidade suficientes sem distribuição |
| ALTERNATIVES_CONSIDERED | asyncio exige outra integração ONVIF; processo por câmera só para isolamento rígido comprovadamente necessário; sistema distribuído não justificado |
| REQUIRED_CODE_CHANGES | MultiWorkflow/ExcelReader/Writer e batch runner em P4/P5; loader efetivo e budgets antes; lifecycle de clientes e cancellation Event |
| REQUIRED_CONTRACT_CHANGES | Identidade row_id, duplicatas, budget de auth por IP, resultado individual, deadline/retry/retomada, status CANCELLED e saída parcial |
| EXPECTED_IMPACT | Limites de recursos, falha individual isolada, ordem preservada e não compartilhamento de credenciais |
| RISKS | Python não cancela thread bloqueada; firmware pode responder lentamente; soft deadline não é kill rígido; saída atômica XLSX requer fechamento controlado |
| VALIDATION_TESTS | T15–T19: 2.300 alvos falsos, auth canary por linha, duplicatas, limite real de concorrência, Ctrl+C e parcial |
| ROADMAP_PLACEMENT | Contratos de budgets em P2; lote serial P4, concorrência/carga P5; hardening/packaging P12 |
| PRIORITY | MEDIUM, F07; elevar somente se lote for requerido antes do restante do roadmap |

## J. ROADMAP IMPACT

**Recomendação: alterar somente o conteúdo/ordem interna de P2 e antecipar uma PoC mínima de P7.** Manter P0/P1 CLOSED. Não executar nem editar a roadmap nesta auditoria.

| Sequência recomendada | Conteúdo e evidência de saída |
|---|---|
| P2 definição | Aprovar contrato pequeno de attempts/merge/auth/resultado; definir campos mínimos e política de conflito/stop; não inventar framework |
| P2-A: preservação e diagnóstico | Corrigir F01/F02, attempts tipados, erros por etapa, explicit auth, destino/time budgets e fixtures do transporte real. Integrar no SINGLE e manter regressão P1 |
| P2-B: ISAPI mínimo | GET deviceInfo integrado ao SINGLE, registry explícito, resultado nativo e fallback controlado. Não construir todo Hikvision |
| P2-C: comparação operacional autorizada | Mesma câmera/credencial de escopo apropriado e mesmos campos, caminhos nativo/ONVIF separados; quantificar cobertura, requests e latência. A atividade futura exige target/credencial/escopo próprios |
| P2-D: expansão incremental | Rede/portas por operações ONVIF e nativas documentadas; resultado tipado, precedência por campo e unsupported explícito |
| P3 | Snapshot após identificação/auth/diagnóstico permitirem fluxo confiável; testar URI/destino e captura sem credenciais em saída |
| P4 | MULTI/XLSX serial funcional, por linha, parciais e recuperação de resultados; credenciais só no input/memória |
| P5 | Concorrência controlada, carga 2.300, cancelamento/retomada e medição; preservar ordem |
| P6–P11 | Completar cobertura dos fabricantes; P7 reaproveita a PoC. Ordem global não precisa ser invertida por causa de um único alvo |
| P12 | Regressão, robustez, ambiente reproduzível, WSDL/ONEDIR e packaging. Segurança/read-only são verificadas desde P2, não adiadas até P12 |

Respostas diretas às questões de roadmap:

1. **Corrigir ONVIF antes de P2?** Não transformar solução do 401 em pré-requisito externo que bloqueie toda P2. Diagnóstico/seleção de auth e correções objetivas são o primeiro trabalho dentro da P2 contratada; causa real segue E.2.
2. **Validar ISAPI antes de fechar toda arquitetura P2?** Sim, como prova dos contratos provisórios mínimos; fechar decisões amplas somente após esse aprendizado. A PoC também precisa de contrato/autorização próprios, não de arquitetura completa.
3. **Adapter mínimo agora?** Próxima implementação técnica recomendada na slice P2, após autorização; não autorizado nesta auditoria.
4. **Dois protocolos antes de snapshots?** Sim, demonstrar o nativo mínimo e o comportamento ONVIF de sucesso ou falha diagnosticada. Não exigir que ambos autentiquem a mesma conta se os domínios são distintos. Para afirmar interoperabilidade ONVIF resolvida, é indispensável sucesso de sua operação autenticada.
5. **Decisões antes de programar:** campos exigidos/status parcial; transporte/TLS/destino; auth budget e fallback após rejeição; hint conflitante; estrutura tipada/proveniência; extensão mínima do adapter na P2.
6. **Incrementais:** suporte de endpoints por família/modelo, aliases comprovados, mapeamento de campos adicionais, parâmetros de desempenho medidos e expansão das fixtures.
7. **Riscos que justificam ajuste:** nenhuma fonte nativa provada, perda de evidência, diagnóstico insuficiente e dúvida de auth. Não justificam reconstrução; justificam uma PoC curta antes de multiplicar snapshots/lote.

Nenhum gate administrativo novo é proposto: testes/integração e futura comprovação operacional são critérios de aceite do incremento que reduz esses riscos. Não exigir seis fabricantes completos para permitir P3, nem manter P1 aberta artificialmente.

## K. ACCEPTANCE TESTS

### K.1 Plano de testes objetivos

Esta tabela propõe testes futuros. Somente os 51 testes existentes, Ruff e as reproduções descritas em B foram executados nesta auditoria.

| ID | Teste | Aceite objetivo |
|---|---|---|
| T01 | Preauth válida + connect/read timeout, TLS, HTTP, SOAP ou unexpected posterior | Todas as evidências válidas permanecem; parcial tem etapa/causa; zero segredo |
| T02 | Falha como exception versus AdapterResult de falha | Mesmos dados/status agregado para eventos equivalentes; nenhum fabricante desaparece |
| T03 | Servidor/transport fake Digest-only com cliente instalado real | Primeiro challenge, segundo request autenticado sem WSSE, GetDeviceInformation parseado; sequência contada |
| T04 | Fixture WSSE-only | Token com nonce e Created por request; HTTP Authorization ausente; schema/resposta corretos |
| T05 | Digest algorithm/qop suportado e não suportado, challenge ausente/malformado | Categoria negotiation unsupported específica; sem fallback auth cego; auth-int limitado explicitamente |
| T06 | 401 inicial→200 versus 401 final, 403, SOAP NotAuthorized | Negotiation não vira falha final; acesso/auth/protocolo distintos e incerteza preservada |
| T07 | ISAPI deviceInfo fixtures XML namespaces/versões/campos ausentes | Mapping correto; nada inventado; hardwareVersion/deviceName não confundidos com HardwareId/hostname |
| T08 | ISAPI 200 erro vendor, 404, 405, XML malformado, payload vazio | Erro semântico/unsupported/parse específico; nenhum SUCCESS vazio por HTTP 200 |
| T09 | Registro placeholder e adapter incompleto | Placeholders não habilitados; suporte limitado explícito; duplicate registration rejeitado ou substituição deliberada |
| T10 | Allowlist read-only | Nenhum Set/reboot/change user/time/write/action=set; SOAP POST permitido só para operações de leitura aprovadas |
| T11 | Fingerprint positivo/negativo/conflitante | `/galaxis` não vira Axis; ordem dos sinais não altera resolução; hint/alias/OEM seguem contrato |
| T12 | Auth/segredos/destinos | Canários não aparecem em repr/log/terminal/XLSX/attempts; trust_env/netrc não fornece auth; redirect/XAddr cross-origin bloqueado; TLS failure sem downgrade |
| T13 | Matriz de seleção/fallback | Uma única família nativa por target; ausência→ONVIF; cobertura total→zero segunda consulta; rejeição final→sem novo login default |
| T14 | Merge/completude/conflito | Ordem de fontes invariável; None/vazio não sobrescreve; firmware conflitante preservado; campos recuperados recalculam status e erro agregado |
| T15 | Requests/deadline/retry/auth budget | Eventos fake provam limites, no máximo um retry elegível; após deadline/cancel não começa operação; descoberta não duplica capabilities |
| T16 | 2.300 targets sintéticos heterogêneos | Exatamente 2.300 resultados, uma linha por entrada válida/inválida contratada, ordem original, nenhuma falha aborta lote |
| T17 | Credenciais distintas e IP duplicado | Cada chamada recebe credencial de sua linha; sessões/cookies isolados; mesmo IP sem autenticações simultâneas; budget do IP aplicado |
| T18 | Cancelamento em discovery/auth/coleta/export | Nenhuma nova submissão após Event; trabalho em curso finaliza por timeout; resultados prontos preservados; restantes CANCELLED |
| T19 | Reinício/exportação parcial e recursos | XLSX/arquivo parcial válido sem senha; processo reinicia com input local; sem reutilizar segredo de output; sessões e handles não crescem com 2.300 linhas |
| T20 | Regressão/packaging | P1 CLI e 51 testes preservados conforme contrato futuro; Ruff; Python 3.14; WSDL incluídos; ONEDIR smoke na fase apropriada |

T03/T04 devem usar wrapper/Zeep/Requests reais contra fixtures de transporte, não substituir ONVIFClient inteiro: os mocks atuais comprovam passagem de opções e fluxo, não bytes SOAP ou negociação. A biblioteca realiza GetServices e, em falha, GetCapabilities no construtor; contabilizar essas operações e testar se timeout ali impede leituras posteriores úteis. Um HTTP 401 do construtor não deve iniciar uma sequência invisível de novas tentativas autenticadas.

Testar relógio com tempo falso para deadline/retry; para carga, transportes em memória ou servidor local controlado em atividade de implementação, sem varrer redes. Carga com duração artificial precisa verificar active_workers e per_ip_active diretamente, não apenas tempo total. Sanitização deve cobrir canários no erro, XML, query, Authorization e URL; não usar credenciais reais nas fixtures.

### K.2 Política de timeout e retry recomendada

Preservar valores da Foundation como início: connect 3s; request/read 7s; budget ONVIF 15s; nativo 10s; deadline soft por câmera 45s. Os budgets são cumulativos por mecanismo, incluindo discovery/handshake/retry, e todos competem pelo deadline da câmera. Não somar limites como se fossem autorizações para ultrapassar 45s. Um perfil só de inventário poderá ter deadline menor após medição; nenhuma mudança foi aprovada aqui.

Antes de cada request, calcular restante do deadline e do budget da fonte, aplicar o menor timeout admissível e conferir cancel_event. HTTPX read timeout é limite de espera entre recebimentos, não deadline total; fluxo que envia bytes lentamente pode exceder o deadline. Fazer verificações entre chunks e limitar tamanho de corpo. Para SOAP bloqueante, o timeout de operação deve ser reduzido ao restante; request em andamento pode ultrapassar soft deadline por detalhes do transporte. Não alegar timeout total rígido com Future.result(timeout).

Uma repetição com backoff inicial 1s é permitida somente para falha transitória de operação de leitura idempotente, se restar budget e não houver rejeição autenticada. Candidatos: reset de conexão, timeout transitório, HTTP 502/503/504 e 429 com Retry-After válido dentro do budget. SOAP Fault transitório só se documentado; não repetir indiscriminadamente. Auth reject, autorização, TLS/certificado, connection refused, invalid input, 404/405 unsupported e parse determinístico não têm retry automático. HTTP Digest handshake é negociação; não duplicar retry da aplicação sobre retries ocultos da dependência.

Começar com no máximo um intento autenticado lógico por dispositivo após descoberta/seleção. Dentro de sessão aceita, leituras adicionais com a mesma autenticação continuam permitidas até primeira recusa, limites de requests e deadline. Controlar número de operações previstas e requests reais da lib; o plano mínimo de identity não precisa autenticar todas as leituras de rede. Se o transporte/firmware pedir reauth inesperada, registrar e parar conforme política, em vez de reiniciar login sem limite.

### K.3 Concorrência, isolamento e cancelamento

- **Workers:** 8 inicial, configurável 1..32; sem concorrência intra-câmera. RTSP futuro com semaphore separado de 2, conforme Foundation.
- **Submissão:** janela pequena, por exemplo 2×workers, evitando 2.300 futures contendo todos os targets/senhas vivos simultaneamente. Ler linhas sob controle; a biblioteca XLSX pode manter conteúdo da entrada em memória, portanto isso limita retenção extra, não promete eliminação absoluta dos segredos.
- **Isolamento:** uma sessão/auth/cookies por row_id; nenhum singleton HTTP autenticado no registry. Registry contém fábricas/implementações sem estado de conta. Reuso de conexão só dentro do contexto da mesma linha.
- **Duplicatas:** preservar todas as linhas e warning contratado. Serializar por IP; não transferir credenciais ou resultado autenticado entre linhas. Depois de auth reject, circuito conservador por IP impede novas rejeições automáticas na execução, mantendo cada linha com diagnóstico de tentativa suprimida; não persistir senha/hash para esse controle.
- **Recursos de rede:** teto global de conexões/requests e, quando o parque for segmentado, limite por site/grupo configurado. Não inventar `/24` como equivalente de site. Ajustar por observação de p95/erros, não pelo teto 32 apenas.
- **Ordem:** row_id/index estável; futures podem completar fora de ordem, mas exportação final usa índice de entrada. Cada câmera produz exatamente um report final.
- **Ctrl+C:** thread principal seta Event, para submissão, cancela queued futures e solicita encerramento cooperativo. Workers em request não podem ser mortos pelo executor. Não perder resultados prontos; marcar não iniciados CANCELLED e gravar parcial após fechamento consistente.
- **Interrupção/processo morto:** Ctrl+C tem caminho graceful; falha abrupta exige checkpoint incremental sanitizado se esse requisito for aprovado. JSONL temporário de resultados, sem credenciais e com permissões adequadas, permite reconstruir XLSX; apagá-lo conforme política. Não incluir input de senha no checkpoint nem prometer XLSX íntegro antes de finalizar workbook.
- **Retomada:** selecionar linhas pendentes por referência estável ao input local e execução anterior; buscar credenciais novamente na entrada sensível, sem obtê-las do output. Não reexecutar auth failures automaticamente na retomada.

Python permite I/O paralela em threads, mas não cancellation rígido de threads bloqueadas. Isolamento por processos só deve entrar se transporte impossível de limitar demonstrar travamentos e requisito exigir prazo rígido. É decisão localizada de execução, não motivo atual para distribuí-lo.

Estimativa matemática, **não benchmark**: com 8 workers e média de 2s por câmera, 2.300×2/8 ≈ 575s, ou 9min35s, fora overhead. Se todas consumirem 45s, são aproximadamente 3h36min em ondas de 8. Câmeras lentas no fim e exportação aumentam tempo; a concorrência sozinha não elimina o custo de timeouts. Registrar média/p95, throughput, requests por câmera, peak connections/memória e taxas de parcial/falha por categoria no teste sintético e no piloto futuro autorizado.

### K.4 Prova operacional futura mínima

Sob uma autorização específica futura, selecionar uma câmera com API nativa disponível e credencial HTTP adequada, mais caminho ONVIF cuja conta existente possa ser fornecida localmente. Não exigir alterar a câmera para compor a prova. Registrar apenas modelo/firmware/resultado/latência/contagens e metadados sanitizados.

Aceites: identity nativa autenticada obtida; campos esperados conferidos contra leitura permitida do equipamento; comportamento ONVIF explicado por sucesso ou falha por etapa; parcial preservado; chamadas mutantes zero; nenhuma outra família/autenticação indiscriminada; resultados reproduzíveis dentro do budget. Para afirmar **correção de ONVIF Digest**, exigir sucesso GetDeviceInformation por Digest no alvo que falhava, ou prova causal de incompatibilidade/conta/permissão e correção apropriada. Uma PoC ISAPI bem-sucedida, isoladamente, não resolve nem comprova ONVIF.

## L. OPEN DECISIONS

Somente decisões que precisam de autoridade humana, sem pedir aprovação nesta entrega:

1. Aprovar evolução para política híbrida e inclusão da PoC Hikvision mínima dentro de P2; manter P7 para completar cobertura.
2. Aprovar perfil de campos exigidos e quando parcial/unsupported/conflito é aceitável; recomendação inicial de identidade em H.
3. Aprovar contrato tipado de report/network/protocol availability e expansão de CollectionMethod/ErrorCode estritamente necessária, preservando ausência de senha/bag arbitrária.
4. Aprovar tratamento de hint forte conflitante e política default de parar autenticações após rejeição final, incluindo IP duplicado. Exceções precisam de escopo comprovado, não de “tentar outra API”.
5. Se necessária operação em HTTPS sem CA pública, aprovar mecanismo de confiança local/pinning e destinos/portas permitidos. Não habilitar `verify=False` global nem modificar câmeras automaticamente.
6. Autorizar separadamente implementação P2 e futuros testes operacionais com targets, operações e credenciais fornecidas localmente. Esta auditoria não é autorização.
7. Aprovar requisito e retenção de checkpoint sanitizado para interrupção abrupta do lote, caso além de Ctrl+C graceful e exportação parcial.

Escolha de nomes de classes, parser, fixtures e organização interna de funções é decisão técnica incremental, não pendência humana. Completar documentação Dahua/Panasonic legado/Bosch de inventário é pendência de evidência por fabricante, não uma escolha arbitrária de produto. Pode ser pesquisada nas respectivas fases sem bloquear a PoC Hikvision.

## M. FINAL TECHNICAL RECOMMENDATION

**Qual arquitetura adotar?** Monólito modular existente, com coordinator/policy pequenos, evidências/attempts tipados e seleção híbrida por capacidade e campos, preservando preferência nativa quando justificada. ONVIF continua comum, fallback e complemento. ThreadPoolExecutor continua apropriado ao lote futuro.

**O que está correto?** Separação de navegação/coleta/UI, SINGLE integrado, credencial por target, repr protegido, resultado sem senha, cache de disco ONVIF desativado, monotonic duration, registry vazio em vez de placeholders registrados, ausência de spraying no fluxo atual, testes fake e contrato explícito do parcial P1.

**O que corrigir?** Perda de evidência, fingerprint permissivo, falta de diagnóstico por etapa, auth sem seleção explícita, merge/status/proveniência, suporte declarativo de adapter, configuração/tempo/destino controlados e ambiente reproduzível. Rede/ONVIF availability/portas exigem resultado tipado futuro; não encaixar em bag genérica.

**Bugs confirmados?** Perda de evidência prévia em timeout e inconsistência exception/FAILED; falso positivo de fabricante e resolução dependente da ordem. As demais limitações são gaps de capacidade, contrato ou diagnóstico, com causa indicada no registro. Status do merge herdado é confirmado, mas a regra correta precisa do contrato de cobertura; não atribuir essa falha à câmera.

**O que depende de diagnóstico?** Causa específica do 401 HTTP Digest, permissões/conta do alvo, firmware e challenge negociado, cobertura real de cada família e desempenho do parque de 2.300 câmeras. Nenhuma dessas incertezas foi transformada em fato.

**Primeira implementação?** Uma slice P2 integrada de preservação/diagnóstico e transporte/auth explícitos, seguida imediatamente da PoC Hikvision ISAPI deviceInfo. A primeira capability nativa é essa PoC; não um adapter completo ou seis módulos paralelos. P2 requer autorização posterior.

**Como saber que resolveu?** Testes T01–T15 para comportamento, fixture com transporte real para autenticação, e prova operacional futura sob autorização. ISAPI tem que produzir identidade nativa autenticada; ONVIF Digest só é declarado resolvido após teste discriminante/aceite correspondente. Lote só é declarado robusto depois de T16–T19 e medição, não por extrapolar 51 testes SINGLE.

### Output estruturado obrigatório

```text
ARCH_AUDIT_01_REPORT
PROJECT = projeto_cam_scanner
AUDIT_TYPE = INDEPENDENT_ARCHITECTURE_AND_COLLECTION_REVIEW
REPOSITORY_REVIEW = PASS
OFFICIAL_RESEARCH = PARTIAL
OFFICIAL_RESEARCH_LIMITS = Dahua native inventory NOT_VERIFIED;
  Panasonic legacy NOT_VERIFIED; Bosch full inventory command IDs NOT_VERIFIED;
  manufacturer endpoint/firmware/permission coverage not proven on real devices
ARCHITECTURE_ASSESSMENT = ACCEPT_WITH_CHANGES
PROBLEM_01_ONVIF_DIGEST = DIAGNOSIS_REQUIRED
PROBLEM_02_NATIVE_ADAPTER = SOLUTION_DEFINED
PROBLEM_03_ERROR_DIAGNOSTICS = SOLUTION_DEFINED
PROBLEM_04_MANUFACTURER_DISCOVERY = SOLUTION_DEFINED
PROBLEM_05_COLLECTION_STRATEGY = SOLUTION_DEFINED
PROBLEM_06_EVIDENCE_MERGE = SOLUTION_DEFINED
PROBLEM_07_SCALABILITY = SOLUTION_DEFINED
COLLECTION_STRATEGY_RECOMMENDATION = HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE
ONVIF_DIGEST_ROOT_CAUSE = UNDETERMINED
CAMERA_RESULT_CONTRACT = CHANGE_RECOMMENDED
NATIVE_ADAPTER_POC_REQUIRED = YES
ARCHITECTURE_CHANGE_REQUIRED = YES (localized orchestration/contracts; modular monolith retained)
CRITICAL_FINDINGS = 0
HIGH_FINDINGS = 3
MEDIUM_FINDINGS = 8
LOW_FINDINGS = 1
RECOMMENDED_TARGET_ARCHITECTURE = modular monolith; bounded discovery;
  deterministic collection policy; native/ONVIF adapters;
  per-target transport/auth/time budgets; typed attempts and evidence merge;
  bounded ThreadPoolExecutor for future batch
RECOMMENDED_FIRST_IMPLEMENTATION = P2 preservation/diagnostics/auth transport slice,
  followed by minimum Hikvision ISAPI deviceInfo integrated into SINGLE
ROADMAP_ADJUSTMENTS = extract minimum P7 proof into P2;
  validate native and controlled ONVIF paths before P3; preserve global phases
OPEN_DECISIONS = approvals listed in section L; no approval inferred
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
REPOSITORY_WRITES = NONE
GIT_WRITES = NONE
REAL_CAMERA_CALLS = NONE
CREDENTIAL_USAGE = NONE
SOURCE_CHANGES = NONE
CONTRACT_CHANGES = NONE
REPORT_ARTIFACT = saved outside repository
P1_STATUS = CLOSED
P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
PYTEST_CURRENT_AUDIT = PASS (51 tests, Python 3.14.0)
RUFF_CURRENT_AUDIT = PASS
NETWORK_ATTEMPTS_TEST_PROCESS = 0
PROJECT_STATE_UPDATE = DEFERRED_NO_AUTHORITY (explicit READ_ONLY restriction)
ACTIVITY_COMPLETE = NOT_DECLARED (formal repository gate not changed)
STATUS = COMPLETED_WITH_FINDINGS (audit deliverable)
ACTIVITY_COMPLETION_PERCENT = 100%
COMPLETION_BASIS = exclusive to repository audit, official research with explicit
  NOT_VERIFIED limits, and recommendations; no implementation completion claim
```

**Limite de fechamento formal:** AGENTS.md exige PROJECT_STATE_UPDATE=PASS antes de ACTIVITY_COMPLETE=YES. A solicitação ARCH-AUDIT-01 proíbe escrita no repositório. Foi cumprido o escopo de entrega READ_ONLY, sem declarar ACTIVITY_COMPLETE=YES, sem alterar PROJECT_STATE e sem transformar essa limitação em pedido para implementar ou fechar P2. O percentual descreve exclusivamente a auditoria entregue.
