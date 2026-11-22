# NightEyes Dataset V1.0 — Relatório de Implementação (Parte 1)

> **Nota de atualização (2026-11-19, pós-Parte 1):** este relatório documenta
> a **Parte 1 como executada** (histórico). O estado corrente do projeto —
> **Parte 2 em andamento** (aquisição licenciada, `extract`, ferramentas de
> anotação, runbook, **68 testes**, download YawDD ativo) — está em
> `README.md` **§9** (testes) e **§11 HANDOFF** (continuação).

**Projeto:** NightEyes — Risk Lab
**Etapa:** Parte 1 — Inventário, organização e padronização das fontes de dados
**Modelo executor:** Claude Sonnet (opencode)
**Data de execução:** 2026-11-19
**Status da execução:** CONCLUÍDA com pendências registradas (ver §6)

---

## 1. O que foi implementado

1. **Inventário técnico das 8 fontes** com pesquisa em publicações científicas e
   páginas oficiais (DMD, UTA-RLDD, YawDD, DROZY, NTHU-DDD, AUC-DISTRACTED,
   STATE-FARM, UL-DD). Informações não verificadas foram registradas como
   `UNKNOWN` — nada foi inventado.
2. **Catálogo central** (`data/catalog/datasets.csv`) com os 21 campos exigidos
   + `primary_domain`, incluindo data de verificação e notas de proveniência.
3. **Matriz de compatibilidade** (`data/catalog/compatibility_matrix.csv`) em
   formato longo: 64 mapeamentos rótulo-a-rótulo com os 5 níveis
   (`DIRECT`/`PARTIAL`/`COMPLEMENTARY`/`INCOMPATIBLE`/`UNVERIFIED`),
   método de mapeamento, resolução temporal e necessidade de reanotação.
   Cada decisão referencia o CASO aplicável (1–5) quando pertinente.
4. **Registro de licenças** (`data/catalog/licenses.csv`) com fonte de
   verificação, uso comercial, redistribuição, derivados e data.
5. **Esquemas de metadados** prontos para a Parte 2:
   `sources_registry.csv`, `participants.csv`, `sessions.csv`,
   `episodes.csv`, `windows.csv`, `annotators.csv` (cabeçalhos + esquema
   documentado em `documentation/metadata_dictionary.csv`, schema v1.0).
6. **Estrutura de diretórios** completa conforme o plano
   (`data/catalog|raw|original_labels|normalized|annotation|quality_control|processed|reports`).
   Os 8 diretórios `data/raw/<FONTES>` estão criados e **vazios**.
7. **Dicionário de comportamentos** (`documentation/behavior_dictionary.csv`):
   16 códigos (EYE_001–004, SLEEP_001–004, DIST_001–004, QUALITY_001–004)
   com definição, critérios de inclusão/exclusão, unidade de anotação,
   relação com rótulos de origem e status `PROPOSED`.
8. **Regras de conversão de rótulos**: documento
   `documentation/label_mapping_rules.md` (CASOS 1–5 + tabela de 14 conversões)
   e módulo executável `scripts/label_mapping.py` com 43 regras registradas.
   Consultas sem regra retornam `PENDING` — nunca convertem silenciosamente.
   Sinais do Risk Engine (EAR, MAR, PERCLOS, scores, risco global) retornam
   `FORBIDDEN` (independência do ground truth, V0.1 §7).
9. **Validador automático** `scripts/validate_dataset.py` com as 14 verificações
   (V01–V14), saída clara no console, relatórios JSON + CSV e exit code.
10. **43 testes automatizados** (pytest) cobrindo o caso limpo, cada verificação
    com defeito injetado, geração de relatórios e os CASOS 1–5.
11. **Interface local** `scripts/serve_catalog.py` + `interface/index.html`:
    existiu apenas na Parte 1 (cards, filtros e detalhe dos datasets) e foi
    removida na limpeza final por não fazer parte do dataset catalogado.
12. **README** com instruções de execução e vocabulários controlados.

---

## 2. Arquivos criados

```
README.md
requirements.txt
data/catalog/datasets.csv
data/catalog/compatibility_matrix.csv
data/catalog/licenses.csv
data/catalog/sources_registry.csv            (esquema, vazio)
data/raw/{DMD,UTA_RLDD,YawDD,DROZY,NTHU_DDD,AUC_Distracted,State_Farm,UL_DD}/
data/annotation/{participants,sessions,episodes,windows,annotators}.csv (esquemas, vazios)
data/original_labels/  data/normalized/  data/quality_control/  data/processed/
data/reports/validation_report.json          (gerado pelo validador)
data/reports/validation_report.csv           (gerado pelo validador)
documentation/behavior_dictionary.csv
documentation/metadata_dictionary.csv
documentation/label_mapping_rules.md
documentation/IMPLEMENTATION_REPORT.md       (este arquivo)
scripts/validate_dataset.py
scripts/label_mapping.py
(interface local da Parte 1 removida na limpeza final)
tests/conftest.py
tests/test_validate_dataset.py
tests/test_label_mapping.py
```

Observação: o relatório de validação fica em `data/reports/` conforme a
estrutura da seção 6 do plano (`data/ ... reports/`).

---

## 3. Testes executados e resultados

| Execução | Comando | Resultado |
|---|---|---|
| Testes automatizados | `python -m pytest tests/ -q` | **43 passed** (1,8 s) |
| Validação do projeto | `python scripts/validate_dataset.py` | **PASS** — 0 erros, 0 avisos, exit 0 |
| Integridade dos CSV | checagem de nº de campos por linha (11 arquivos) | todos consistentes |
| Interface — resumo | `GET /api/summary` | 8 datasets; domínios 2/4/2; acesso 2/4/1/1 |
| Interface — filtros | `GET /api/datasets?access=AVAILABLE` | 2 resultados |
| Interface — detalhe | `GET /api/datasets/SRC005` | metadados + 7 linhas de compatibilidade |
| Interface — página | `GET /` | index.html servido (11.062 bytes) |

Cobertura dos testes de validação: caso base limpo (PASS), V01 duplicado,
V02 referência inexistente (compatibilidade e episódio), V03 timestamp negativo
e não inteiro, V04 fim ≤ início, V05 episódio excede sessão, V06 domínio
inválido, V07 rótulo/enum inválido, V08 campo obrigatório vazio, V09 arquivo
órfão em `raw/` e registro sem caminho, V10 checksum divergente (e
não-divergente), V11 participante sem origem, V12 comportamento fora do
domínio, V13 sobreposição de janelas e de episódios (e caso legítimo de
sobreposição entre comportamentos diferentes), V14 episódio sem sessão,
geração dos relatórios JSON/CSV.

Correções aplicadas durante a execução (dados, nunca o validador):
- `behavior_dictionary.csv`: 2 linhas com vírgula não escapada (SLEEP_004,
  DIST_004) — campos re-citados.
- `compatibility_matrix.csv`: 4 valores `NO (store separately)` violavam o enum
  `requires_reannotation` — corrigidos para `NO` (o detalhe já constava em
  `reviewer_notes`).

---

## 4. Situação das fontes (verificação 2026-11-19)

### 4.1 Acesso confirmado (2)
- **SRC002 UTA-RLDD** — link público de Google Drive no site oficial.
- **SRC003 YawDD** — IEEE DataPort Open Access (login gratuito); licença CC-BY
  exibida na página; restrição de screenshots para participantes marcados "No".

### 4.2 Exigem autorização (4)
- **SRC001 DMD** — formulário de download + aceite de termos (revisão 2026
  restringe o conjunto público a IDs de sujeito específicos).
- **SRC005 NTHU-DDD** — EULA assinado por chefe de departamento/diretor de
  laboratório + envio por e-mail.
- **SRC006 AUC-DISTRACTED** — acordo de licença assinado + e-mail aos
  representantes do MI-AUC.
- **SRC008 UL-DD** — Zenodo Restricted: solicitação com conta registrada +
  e-mail institucional de P&D.

### 4.3 Acesso em revisão (1)
- **SRC007 STATE-FARM** — dados no Kaggle mediante aceite das regras da
  competição; uso além da competição requer revisão dos termos.

### 4.4 Não verificado (1)
- **SRC004 DROZY** — site oficial `drozy.ulg.ac.be` não respondeu na data de
  verificação; publicações descrevem o banco como público. Acesso e licença
  a confirmar com os autores (University of Liège / INTELSIG).

### 4.5 Licenças não permitem redistribuição (3)
- **NTHU-DDD** — `RESTRICTED`: não pode ser distribuído a terceiros; uso não
  comercial; restrições de imagens faciais.
- **AUC-DISTRACTED** — `RESTRICTED`: uso comercial proibido; transferência/
  distribuição sem autorização prévia proibida.
- **STATE-FARM** — `RESTRICTED` de fato: regras da competição proíbem
  compartilhamento privado de dados; vinculam o uso à competição.

### 4.6 Licença pendente (2)
- **UTA-RLDD** (sem declaração de licença na página oficial) e
  **DROZY** (não verificada). Integração bloqueada até esclarecimento.

### 4.7 Precisam de nova anotação humana (8 de 8)
Nenhuma fonte fornece episódios visualmente anotados compatíveis com o
protocolo NightEyes (os 64 mapeamentos estão como `PARTIAL`,
`COMPLEMENTARY`, `INCOMPATIBLE` ou `UNVERIFIED` — **zero `DIRECT`**).
Rótulos de nível de vídeo/sessão (CASO 1), autorrelato KSS (CASO 2),
bocejos sem intervalo (CASO 3) e uso de celular sem verificação de atenção
(CASO 4) exigem reanotação humana independente.

---

## 5. Pendências conhecidas

| # | Pendência | Bloqueia |
|---|---|---|
| P1 | Ler/integrar o PDF NightEyes V0.1 diretamente (modelo não aceita PDF; texto integral foi recebido por mensagem) | conferência cruzada página a página |
| P2 | Confirmar acesso + licença do DROZY junto aos autores | SRC004 |
| P3 | Esclarecer licença do UTA-RLDD junto aos autores | SRC002 integração/redistribuição |
| P4 | Confirmar termos atuais do DMD (revisão 2026) e IDs de sujeitos liberados | SRC001 |
| P5 | Obter EULAs assinados (NTHU-DDD, AUC) e aprovação Zenodo (UL-DD) | importação SRC005/006/008 |
| P6 | Revisão dos termos da competição State Farm | SRC007 |
| P7 | Resolver conflitos de contagem reportados (AUC frames V1: 12.977 vs 17.308; NTHU vídeos 356 vs 360; YawDD participantes 107 vs 119) após aquisição | metadados definitivos |
| P8 | Revisar códigos `PROPOSED` do dicionário de comportamentos no manual de anotação | anotação |
| P9 | Fixar limiares de persistência (gaze/head) e duração (prolonged closure) no manual | mapeamentos `PARTIAL` → `DIRECT` |
| P10 | Definição da divisão TRAIN/VALIDATION/TEST por participante (somente Parte 2) | splits |

---

## 6. Critérios de aceitação — verificação

| Critério | Situação |
|---|---|
| 8 datasets cadastrados | ✅ SRC001–SRC008 |
| Informações desconhecidas identificadas | ✅ campos `UNKNOWN` + notas de origem |
| Licenças documentadas com fontes | ✅ `licenses.csv` com `license_source` e data (2 pendentes sinalizadas) |
| Matriz de compatibilidade preenchida | ✅ 64 linhas, todos os datasets (vocabulário de 5 níveis; 4 presentes, zero DIRECT) |
| Estrutura de dados criada | ✅ todos os diretórios do plano |
| Esquemas documentados | ✅ `metadata_dictionary.csv` (schema v1.0, 10 esquemas) |
| Rastreabilidade funcionando | ✅ `sources_registry.csv` + SHA-256 (teste V10 com arquivo real) |
| Módulo de validação executando | ✅ 14 verificações, exit 0 |
| Testes automatizados passando | ✅ 43/43 |
| Interface consulta o catálogo | ✅ testada via HTTP (resumo, filtros, detalhe) |
| Projeto documentado | ✅ README + label_mapping_rules + IMPLEMENTATION_REPORT |
| Nenhum dado protegido distribuído | ✅ repositório sem mídia; `data/raw/` vazio |

**Ressalva honesta:** o critério "não declarar concluído só porque arquivos
existentes" é atendido porque validação, testes e interface foram **executados**
e os resultados registrados acima; as pendências P1–P10 permanecem abertas e
não bloqueiam a Parte 1 (nenhuma importação de dados foi feita).

---

## 7. O que será desenvolvido na Parte 2

1. **Aquisição autorizada:** formulários (DMD), EULAs (NTHU, AUC), solicitação
   Zenodo (UL-DD), confirmações pendentes (DROZY, UTA-RLDD).
2. **Importação** para `data/raw/<FONTES>/` com registro em
   `sources_registry.csv` (SHA-256, tamanho, data, permissão, status).
3. **Preenchimento** de `participants.csv` e `sessions.csv` a partir dos
   metadados de origem (sem identificação facial, sem fusão entre fontes).
4. **Extração de rótulos originais** para `data/original_labels/`
   (preservados) e transformações apenas em `data/normalized/` com rastreio.
5. **Sessão piloto de anotação:** dois avaliadores independentes, sem acesso a
   scores do Risk Engine; resolução de divergências mantendo `UNCERTAIN`
   quando aplicável; consolidação em `episodes.csv` e `windows.csv`
   (janela inicial de 5 s, intervalos originais preservados).
6. **Revisão do manual:** códigos `PROPOSED` → `APPROVED`; definição de
   limiares (persistência, duração).
7. **Divisão por participante** TRAIN/VALIDATION/TEST após identificação
   confiável dos participantes; dados de TEST isolados durante calibração.
8. **Consolidação NightEyes:** novo dataset derivado, mantendo colunas de
   origem (`dataset_id`, `original_*`) para rastreabilidade total.

---

## 8. Sincronização GitHub e avanços adicionais (2026-11-19)

### 8.1 Push para o GitHub
- Repositório: https://github.com/Sjr-ts/viu (branch `main`, commit `d1859c8`).
- Git 2.56.0 instalado via winget na máquina de execução.
- 39 arquivos versionados: catálogos, esquemas, documentação, scripts, testes,
  interface, relatórios de validação e `.gitkeep` nos diretórios vazios.
- `.gitignore` criado: exclui `data/raw/**` (exceto `.gitkeep`), caches Python
  e arquivos de segredo. Varredura confirmou **zero tokens/segredos** staged.
- Dados brutos (`data/raw/`) permanecem fora do repositório por
  licença/privacidade.

### 8.2 README técnico integral
- `README.md` reescrito com 10 seções: finalidade; especificação técnica do
  Protocolo V0.1 (domínios, unidades de anotação, rótulos, metadados,
  processo, independência, splits, condições de captura, avaliação,
  estrutura §11, critérios §12); avanços da Parte 1 com estatísticas; guia
  de aquisição rápida; situação das fontes; estrutura; execução;
  vocabulários; testes; pendências.

### 8.3 Guia de aquisição rápida (pesquisa sites/GitHub/Kaggle/Reddit)
Varredura para agilizar downloads (detalhes na seção 4 do README):
- **YawDD**: download direto sem login em
  `skuld.cs.umass.edu/traces/mmsys/2014/user06.tar` (~4,9 GB) + espelho
  Kaggle `enider/yawdd-dataset` (5,48 GB) + oficial IEEE DataPort.
- **UTA-RLDD**: Drive público oficial (111 GB) + espelhos Kaggle e
  HuggingFace para frames rápidos (1,9–6,7 GB).
- **NTHU-DDD**: EULA oficial; espelhos Kaggle de frames (817 MB–2,34 GB,
  licença `Unknown` — risco de violação de EULA).
- **State Farm**: Kaggle competição (aceitar regras) — `driver_imgs_list.csv`
  já traz o split por participante.
- **DMD**: formulários em `opendatasets.vicomtech.org` + GitHub oficial de
  ferramentas (Vicomtech/DMD-Driver-Monitoring-Dataset).
- **UL-DD**: Zenodo restricted com e-mail institucional.
- **Extras achados**: FatigueView (GitHub MIT, vídeos + anotações JSON),
  NITYMED (CC-BY, noturno), lista `ykotseruba/attention_and_driving`,
  thread Reddit r/datasets sobre datasets de drowsiness.

### 8.4 Pendência de segurança
- O token de acesso (PAT) foi fornecido em texto plano na conversa: usado
  apenas na URL do remote local (não versionado). **Recomendação: revogar e
  rotacionar o token** após a sincronização (GitHub → Settings → Developer
  settings → Personal access tokens).
