# NightEyes — Risk Lab
# NightEyes Dataset V1.0 — Infraestrutura de Inventário, Anotação e Validação (Parte 1)

**Projeto:** NightEyes — Risk Lab
**Etapa:** Parte 1 — Inventário, organização e padronização das fontes de dados
**Protocolo de referência:** *NightEyes — Anotação de Dataset V0.1* (texto integral, enviado na abertura do projeto)
**Data de verificação dos metadados:** 2026-11-19
**Repositório:** https://github.com/Sjr-ts/viu
**Status:** Parte 1 CONCLUÍDA — validação `PASS`, 43 testes aprovados, interface local operacional

---

# SUMÁRIO

1. [Finalidade do projeto (o que foi pedido no início)](#1-finalidade-do-projeto)
2. [Protocolo NightEyes V0.1 — especificação técnica integral](#2-protocolo-nighteyes-v01--especificação-técnica)
3. [Avanços implementados (Parte 1) — detalhamento técnico](#3-avanços-implementados-parte-1)
4. [Guia de aquisição rápida dos datasets (sites, GitHub, Kaggle)](#4-guia-de-aquisição-rápida-dos-datasets)
5. [Situação das 8 fontes — acesso, licença e pendências](#5-situação-das-8-fontes)
6. [Estrutura de diretórios do repositório](#6-estrutura-de-diretórios)
7. [Como executar (validação, testes, interface)](#7-como-executar)
8. [Vocabulários controlados e integridade de dados](#8-vocabulários-controlados-e-integridade)
9. [Estado dos testes e relatórios](#9-estado-dos-testes-e-relatórios)
10. [Pendências conhecidas (P1–P10) e plano da Parte 2](#10-pendências-e-plano-da-parte-2)

---

# 1. Finalidade do projeto

Construir uma **base de referência independente** para avaliar o comportamento do
**Risk Engine V1.0** (motor de risco NightEyes), permitindo:

- Avaliar os domínios de **fadiga**, **sonolência** e **distração**.
- Comparar os scores calculados pelo motor com **episódios anotados independentemente**.
- Medir **falsos positivos** e **falsos negativos**.
- Avaliar a **resolução temporal** do motor (janelas de referência).
- Investigar o comportamento em **diferentes condições de captura**.

**Restrição central (§7 do protocolo):** os rótulos **NÃO** poderão ser produzidos
com base em scores, classificações ou decisões internas do Risk Engine. O ground
truth é construído apenas a partir da observação visual humana.

**Escopo desta etapa (Parte 1):** somente infraestrutura de catálogo,
organização, compatibilidade, validação e documentação. **Não há** nesta parte:
importação de vídeos, anotação humana, treinamento de IA ou consolidação de dados.

---

# 2. Protocolo NightEyes V0.1 — especificação técnica

Esta seção documenta integralmente o protocolo enviado no início do projeto
(versão 0.1 — status: protocolo inicial proposto; próxima revisão após a
definição dos CSVs definitivos e da sessão piloto).

## 2.1 Domínios de anotação

### 2.1.1 Fadiga (`FATIGUE`)
Identificar **evidências observáveis** compatíveis com alterações de comportamento
ocular associadas à fadiga. Indicadores de referência:

- Alteração perceptível no padrão de piscadas.
- Aumento da duração das piscadas.
- Sequências de fechamento ocular.
- Persistência de alterações ao longo da sessão.

> A anotação de fadiga **não** será confundida automaticamente com sonolência.
> Alterações oculares isoladas **não** constituem diagnóstico fisiológico.

### 2.1.2 Sonolência (`SLEEPINESS`)
Identificar **episódios de sonolência observável**. Indicadores de referência:

- Fechamento prolongado dos olhos.
- Episódios repetidos de fechamento ocular.
- Bocejos observáveis.
- Autorrelato de sonolência, quando disponível.

> A escala **Karolinska Sleepiness Scale (KSS)** é referência **complementar**
> de autorrelato. O autorrelato será armazenado **separadamente** da observação
> visual (nunca fundido no rótulo visual).

### 2.1.3 Distração (`DISTRACTION`)
Identificar situações em que a atenção do motorista deixa de estar direcionada
à tarefa de condução. Indicadores de referência:

- Desvio persistente do olhar.
- Desvio persistente da cabeça.
- Uso de celular.
- Associação temporal entre uso de celular e desvio de atenção.

> A **simples presença de um celular não é suficiente** para rotular distração
> (CASO 5 do mapeamento).

## 2.2 Unidade de anotação

| Nível | Descrição | Uso |
|---|---|---|
| **A — Episódios** | Registro do início e fim de cada comportamento identificado (`start_ms`, `end_ms`) | Fonte primária do ground truth |
| **B — Janelas** | Segmentação dos registros em janelas para comparação com as avaliações do motor | Avaliação offline do Risk Engine |

- **Janela inicial de trabalho: 5 segundos** (configuração inicial do protocolo);
  a duração definitiva será compatibilizada com a frequência de atualização e
  temporalidade do Risk Engine.
- Os **intervalos originais dos episódios são mantidos** para permitir
  re-segmentações posteriores.

## 2.3 Classificação dos rótulos

Cada domínio possui rótulo **independente**:

| Rótulo | Significado |
|---|---|
| `PRESENT` | Evidência observável do comportamento |
| `ABSENT` | Ausência de evidência observável |
| `UNCERTAIN` | Evidência insuficiente ou ambígua |
| `UNOBSERVABLE` | Impossibilidade de avaliar devido à captura |

- `UNCERTAIN` e `UNOBSERVABLE` **nunca** serão convertidos em ausência de risco
  (nem em `ABSENT`).
- Classificação de gravidade poderá ser adicionada posteriormente, desde que
  exista critério de anotação reproduzível.

## 2.4 Metadados obrigatórios (por anotação)

| Campo | Descrição |
|---|---|
| `participant_id` | Identificação anonimizada do participante |
| `session_id` | Sessão de captura |
| `start_ms` | Início (milissegundos, alinhado à referência da sessão) |
| `end_ms` | Fim (milissegundos) |
| `domain` | `FATIGUE` / `SLEEPINESS` / `DISTRACTION` |
| `reference_label` | `PRESENT` / `ABSENT` / `UNCERTAIN` / `UNOBSERVABLE` |
| `annotator_id` | Avaliador responsável |
| `annotation_confidence` | Confiança do avaliador |
| `lighting_condition` | Condição de iluminação |
| `occlusion_condition` | Oclusão facial |
| `annotation_notes` | Observações livres |

## 2.5 Processo de anotação (8 etapas do protocolo)

1. Registrar a sessão com **consentimento** do participante.
2. **Preservar** os vídeos e dados originais (nunca sobrescrever).
3. Separar as sessões em **unidades de anotação**.
4. Disponibilizar os materiais aos avaliadores **sem scores do NightEyes**.
5. Realizar as anotações de forma **independente**.
6. **Comparar** as anotações dos avaliadores.
7. **Resolver divergências** ou manter o caso como `UNCERTAIN`.
8. Consolidar o ground truth em **CSV**.

> Recomendação: **dois avaliadores independentes** sempre que possível.

## 2.6 Independência do ground truth (§7) — proibições

É **proibido** utilizar diretamente os seguintes indicadores do motor para
definir os rótulos de referência:

1. `EAR` (Eye Aspect Ratio)
2. `MAR` (Mouth Aspect Ratio)
3. `PERCLOS` calculado pelo NightEyes
4. Frequência de piscadas calculada pelo motor
5. Score de fadiga
6. Score de sonolência
7. Score de distração
8. Classificação global de risco

Esses indicadores poderão ser usados **apenas depois**, para comparação e
avaliação — nunca para construir a referência. O módulo
`scripts/label_mapping.py` implementa essa regra: consultas com sinais
proibidos retornam `FORBIDDEN`.

## 2.7 Divisão dos dados (§8)

- Divisão **por participante** (nunca misturar sessões da mesma pessoa entre
  conjuntos de calibração e teste):
  - `TRAIN` — desenvolvimento e calibração
  - `VALIDATION` — seleção de parâmetros
  - `TEST` — avaliação final independente
- Os dados de `TEST` permanecem **isolados durante a calibração**.

## 2.8 Condições de captura (§9)

Cada sessão registra, quando aplicável:

- Identificação anonimizada do participante
- Modelo e posição da câmera
- Condições de iluminação
- Uso de óculos
- Oclusão facial
- Condições de captura
- Tipo de atividade executada
- Versão do pipeline de visão

> A coleta deve ocorrer em **ambiente controlado ou simulador**. **Não** serão
> induzidos episódios perigosos de sonolência ou distração em vias públicas.

## 2.9 Avaliação do Risk Engine (§10)

Após a consolidação dos rótulos, serão medidos:

Sensibilidade · Especificidade · Precisão · Falsos positivos · Falsos negativos ·
Matriz de confusão por domínio · Tempo de detecção · Tempo de recuperação ·
Cobertura dos indicadores · Desempenho em condições adversas de captura

> Os scores do motor **não** devem ser interpretados como probabilidades de
> acidente ou diagnósticos clínicos.

## 2.10 Estrutura de arquivos do protocolo (§11)

```
data/
├── raw/
│   ├── sessions/          # originais preservados (vídeos/fotos por sessão)
│   └── metadata/          # metadados originais preservados
├── labels/
│   ├── episodes.csv       # Nível A — episódios
│   ├── windows.csv        # Nível B — janelas temporais
│   └── annotators.csv     # avaliadores
└── processed/
    ├── train.csv
    ├── validation.csv
    └── test.csv
```

- Os **dados originais são preservados sem alterações**.
- Os arquivos processados mantêm **rastreabilidade** até suas sessões de origem.

## 2.11 Critérios para considerar a base utilizável (§12)

A base só será utilizada para calibração ou avaliação quando:

1. Os timestamps estiverem alinhados.
2. Os rótulos possuírem critérios documentados.
3. Os avaliadores **não** tiverem acesso aos scores do motor durante a anotação.
4. Os casos inconclusivos estiverem identificados.
5. A divisão por participante estiver garantida.
6. A origem e as condições dos dados estiverem documentadas.
7. A licença e o consentimento permitirem o uso pretendido.

## 2.12 Registro de histórico do protocolo

| Versão | Status | Próxima revisão |
|---|---|---|
| 0.1 | Protocolo inicial proposto | Após definição da estrutura definitiva dos CSVs e realização de uma sessão piloto de anotação |

---

# 3. Avanços implementados (Parte 1)

## 3.1 Inventário técnico das 8 fontes

Pesquisa em publicações científicas e páginas oficiais, com **data de
verificação (2026-11-19)** registrado por registro. Informações não verificadas
foram marcadas `UNKNOWN` — **nada foi inventado**.

| ID | Fonte | Domínio primário | Acesso | Verificação |
|---|---|---|---|---|
| SRC001 | DMD (Vicomtech) | MULTI_DOMAIN | REQUIRES_PERMISSION | 2026-11-19 |
| SRC002 | UTA-RLDD (UT Arlington) | SLEEPINESS | AVAILABLE | 2026-11-19 |
| SRC003 | YawDD (U. Ottawa) | SLEEPINESS | AVAILABLE | 2026-11-19 |
| SRC004 | DROZY (U. Liège) | SLEEPINESS | UNKNOWN | 2026-11-19 |
| SRC005 | NTHU-DDD (NTHU CV Lab) | MULTI_DOMAIN | REQUIRES_PERMISSION | 2026-11-19 |
| SRC006 | AUC-DISTRACTED (MI-AUC) | DISTRACTION | REQUIRES_PERMISSION | 2026-11-19 |
| SRC007 | STATE-FARM (Kaggle) | DISTRACTION | REVIEW_REQUIRED | 2026-11-19 |
| SRC008 | UL-DD (U. Louisiana) | SLEEPINESS | REQUIRES_PERMISSION | 2026-11-19 |

## 3.2 Catálogo central — `data/catalog/datasets.csv`

- **8 linhas × 22 colunas** (21 campos do plano + `primary_domain`).
- Campos incluem: `dataset_id`, `dataset_name`, `institution`, `year`,
  `primary_domain`, `modalities`, `participants`, `videos`, `recording_setup`,
  `original_labels`, `label_format`, `access_status`, `access_url`,
  `license`, `commercial_use`, `redistribution`, `derivatives`,
  `verification_date`, `notes`, `source_references`, `processing_status`.
- Todas as linhas passam na checagem de nº de campos (CSV íntegro).

## 3.3 Matriz de compatibilidade — `data/catalog/compatibility_matrix.csv`

- **64 mapeamentos** no formato longo (rótulo de origem → comportamento NightEyes).
- Distribuição por fonte: SRC001: 14 · SRC002: 6 · SRC003: 4 · SRC004: 5 ·
  SRC005: 7 · SRC006: 10 · SRC007: 12 · SRC008: 6.
- Níveis presentes: `PARTIAL`, `COMPLEMENTARY`, `INCOMPATIBLE`, `UNVERIFIED`
  (**zero `DIRECT`** — nenhuma fonte fornece episódios visualmente anotados
  compatíveis com o protocolo; todos precisam de reanotação humana).
- **59 de 64** linhas com `requires_reannotation=YES`.
- Cada decisão referencia o **CASO aplicável (1–5)** em `reviewer_notes`.

### CASOS obrigatórios do mapeamento (implementados em `label_mapping.py`)

| CASO | Situação | Decisão |
|---|---|---|
| 1 | Rótulo de nível de vídeo/sessão (ex.: `drowsy`) | `PENDING` — **nunca** conversão automática em `PRESENT` de episódio |
| 2 | Autorrelato KSS | `COMPLEMENTARY` — armazenar **separado** (`SLEEP_004`), nunca como observação visual |
| 3 | Bocejo sem intervalo temporal confiável | Verificação temporal obrigatória antes de rotular episódio |
| 4 | Presença de celular | **Nunca** suficiente para `DIST_00x = PRESENT` sem evidência de desvio de atenção |
| 5 | Informação insuficiente | `UNCERTAIN`/`UNOBSERVABLE` — nunca converter para `ABSENT` |

## 3.4 Registro de licenças — `data/catalog/licenses.csv`

8 registros com: `license`, `license_source`, `commercial_use`,
`redistribution`, `derivatives`, `verification_date`, `notes`.
**Licença pendente (UNKNOWN):** UTA-RLDD e DROZY.

## 3.5 Esquemas de metadados (prontos para a Parte 2)

Cabeçalhos + documentação campo a campo em
`documentation/metadata_dictionary.csv` (**schema v1.0**, 10 esquemas):

| Arquivo | Estado | Conteúdo |
|---|---|---|
| `data/catalog/sources_registry.csv` | esquema (vazio) | 10 colunas: rastreio de arquivos com SHA-256, tamanho, data, permissão, status |
| `data/annotation/participants.csv` | esquema (vazio) | IDs anonimizados, origem, disponibilidade |
| `data/annotation/sessions.csv` | esquema (vazio) | 13 campos: câmera, iluminação, óculos, oclusão, atividade, pipeline (§9) |
| `data/annotation/episodes.csv` | esquema (vazio) | 14 campos: todos os 11 metadados obrigatórios do §5 + rastreio |
| `data/annotation/windows.csv` | esquema (vazio) | 13 campos: Nível B, janelas de 5 s, vínculo com episódio |
| `data/annotation/annotators.csv` | esquema (vazio) | 6 campos: avaliadores e atribuições |

## 3.6 Dicionário de comportamentos — `documentation/behavior_dictionary.csv`

**16 códigos** com status `PROPOSED` (revisão no manual da Parte 2):

| Família | Códigos | Representa |
|---|---|---|
| EYE_001–004 | Padrão/duração de piscada, fechamento ocular | Fadiga (evidência ocular) |
| SLEEP_001–004 | Fechamento prolongado, repetido, bocejo, KSS complementar | Sonolência (SLEEP_004 = KSS, `COMPLEMENTARY`) |
| DIST_001–004 | Desvio de olhar, cabeça, celular, associação temporal | Distração (celular nunca sozinho = PRESENT) |
| QUALITY_001–004 | Iluminação, oclusão, qualidade de captura | Qualidade (suporte a `UNOBSERVABLE`) |

Cada código documenta: definição, critérios de inclusão/exclusão, unidade de
anotação (episódio/janela), relação com rótulos de origem e status.

## 3.7 Regras de conversão de rótulos

- **`documentation/label_mapping_rules.md`** — tabela de conversões aceitas,
  rejeitadas e pendentes; semântica dos 5 níveis; CASOS 1–5.
- **`scripts/label_mapping.py`** — motor executável com **43 regras
  registradas (R001–R043)**:
  - `evaluate_mapping(dataset_id, source_label, domain, ...)` → decisão + nível.
  - Consulta **sem regra** retorna `PENDING` (nunca converte silenciosamente).
  - Detecção de **sinais proibidos** (EAR, MAR, PERCLOS, scores, risco global)
    → `FORBIDDEN` (independência do ground truth, §7).
  - Consolidação de estados e casamento por domínio/comportamento.

## 3.8 Estrutura de diretórios

Todos os diretórios do plano + §11 criados; `data/raw/<FONTES>` **vazios por
design** (importação só na Parte 2, após aquisição autorizada):

```
data/{catalog, raw/{DMD,UTA_RLDD,YawDD,DROZY,NTHU_DDD,AUC_Distracted,State_Farm,UL_DD},
     original_labels, normalized, annotation, quality_control, processed, reports}
```

## 3.9 Validador automático — `scripts/validate_dataset.py`

**14 verificações (V01–V14)**, saída clara no console, relatórios JSON + CSV,
exit code (0 = sem erros; 1 = erros). **Nunca corrige dados silenciosamente.**

| Check | Verifica |
|---|---|
| V01 | IDs duplicados (`dataset_id`, `episode_id`, ...) |
| V02 | Referências inexistente (compatibilidade → dataset; episódio → sessão) |
| V03 | Timestamps negativos ou não inteiros |
| V04 | `end_ms` ≤ `start_ms` |
| V05 | Episódio excede os limites da sessão |
| V06 | Domínio fora do vocabulário (`FATIGUE/SLEEPINESS/DISTRACTION/QUALITY`) |
| V07 | Rótulo/enum inválido (`reference_label`, `compatibility_level`, `requires_reannotation`, `access_status`) |
| V08 | Campo obrigatório vazio |
| V09 | Arquivo órfão em `raw/` sem registro / registro sem caminho |
| V10 | Checksum SHA-256 divergente |
| V11 | Participante sem origem declarada |
| V12 | Comportamento fora do domínio declarado |
| V13 | Sobreposição de janelas/episódios incompatível |
| V14 | Episódio sem sessão |

## 3.10 Interface local — `scripts/serve_catalog.py` + `interface/index.html`

- Servidor **100% local** (stdlib `http.server` + CSV) — sem APIs pagas.
- **Cards de resumo:** total de datasets, por domínio, acesso confirmado,
  exige autorização, licença pendente, compatibilidade direta/parcial,
  fontes que precisam de nova anotação.
- **Filtros:** texto (nome/instituição), instituição, domínio, acesso,
  licença (pendente/definida), compatibilidade.
- **Detalhe por clique:** metadados completos + licença + matriz de
  compatibilidade da fonte.
- Endpoints: `GET /`, `/api/summary`, `/api/datasets?...`, `/api/datasets/<ID>`.

---

# 4. Guia de aquisição rápida dos datasets

> **Aviso de licença:** use os canais **oficiais** sempre que possível.
> Espelhos não-oficiais de datasets restritos (ex.: NTHU-DDD em Kaggle com
> `License: Unknown`) podem violar o EULA original (proibição de redistribuição).
> Prefira o canal oficial; use espelhos apenas quando a licença original permitir.

## 4.1 Acesso imediato (sem formulário)

| Fonte | Canal rápido | Tamanho | Observação |
|---|---|---|---|
| **YawDD** | Download direto UMass Traces (sem login): `http://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar` | ~4,9 GB | Espelho acadêmico do MMSys 2014 — original: IEEE DataPort Open Access |
| **YawDD** | IEEE DataPort (login **gratuito**, sem assinatura paga): https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset | 4,94 GB | Canal oficial — `YawDD.rar.gz` + tabela de participantes |
| **YawDD** | Kaggle espelho: https://www.kaggle.com/datasets/enider/yawdd-dataset | 5,48 GB / 351 arquivos | Estrutura Dash+Mirror completa |
| **UTA-RLDD** | Drive público oficial: https://drive.google.com/drive/folders/1d_QwgpMXnLY_FmLYXDn7TLcw0D-svXEl | **111,3 GB** | 180 vídeos ~10 min — canal oficial do site https://sites.google.com/view/utarldd/home |
| **UTA-RLDD** | Kaggle (frames extraídos, 3 GB): https://www.kaggle.com/datasets/minhngt02/uta-rldd | 3,04 GB | **Não-oficial** (upload de terceiro); bom p/ testes rápidos |
| **UTA-RLDD** | HuggingFace (6.924 imagens): https://huggingface.co/datasets/chbh7051/UTA-RLDD_images | 1,9 GB | **Não-oficial**; splits train/val/test prontos |
| **UTA-RLDD** | Kaggle vídeos cortados no rosto: https://www.kaggle.com/datasets/mathiasviborg/uta-rldd-videos-cropped-by-faces | 6,71 GB | CC BY-NC-SA (declarado pelo uploader) |
| **State Farm** | Kaggle competição (aceitar regras — gratuito): https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/data | 4,31 GB / 102k imagens | `driver_imgs_list.csv` já traz `subject` (split por participante pronto!) |
| **State Farm** | Kaggle dataset espelho: https://www.kaggle.com/datasets/taojingying11/state-farm-distracted-driver-detection | 4,31 GB | Mesmo conteúdo |

## 4.2 Acesso com formulário/EULA (oficial)

| Fonte | Canal oficial | O que precisa |
|---|---|---|
| **DMD** | https://dmd.vicomtech.org/ → formulários `opendatasets.vicomtech.org` (Gaze & Hands / Drowsiness / Distraction) | Formulário + aceite; e-mail com link Box. Licença **CC BY-NC-ND 4.0** (uso acadêmico). Revisão 2026: só RGB do cenário real, IDs de sujeito liberados: 1, 5, 6, 7, 9, 10, 13, 14, 23, 28, 29, 33, 36, 37. Ferramentas/docs: https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset |
| **NTHU-DDD** | http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/ | EULA assinado por chefe/diretor + e-mail `cvlablai636@my.nthu.edu.tw`. Não-comercial, **sem redistribuição**. (Espelhos Kaggle existem: `ikhlaselhamly/nthu-ddd` 817 MB, `samymesbah/nthu-dataset-ddd-multi-class` 2,34 GB — licença `Unknown`, usar por sua conta e risco) |
| **UL-DD** | https://zenodo.org/records/17978727 (DOI 10.5281/zenodo.17978727) | Conta Zenodo + **e-mail institucional** (P&D); acesso restrito com formulário. 14 TB, KSS a cada 4 min, 19 sujeitos |
| **STATE-FARM** | https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/data | Aceitar as regras da competição (gratuito) |
| **DMD (paper)** | Site oficial + citação Ortega et al., ECCVW 2020 | — |

## 4.3 Não verificado / pendente

| Fonte | Situação |
|---|---|
| **DROZY** | Site oficial `drozy.ulg.ac.be` **não respondeu** na data de verificação. Acesso e licença a confirmar com os autores (U. Liège / INTELSIG) |
| **AUC-DISTRACTED** | Licença assinada + e-mail aos representantes do MI-AUC (sem download aberto) |
| **UTA-RLDD (licença)** | Sem declaração de licença na página oficial — confirmar com os autores antes de redistribuir |

## 4.4 Catálogos e comunidade (para agilizar achados)

- **Lista "attention & driving" por aplicação** (GitHub): https://github.com/ykotseruba/attention_and_driving/blob/2.0/datasets_by_application.md — inventário acadêmico com links de DMD, YawDD, NTHU-DDD, SFDDD etc.
- **FatigueView** (GitHub, licença MIT, vídeos + anotações JSON direto no repo): https://github.com/FatigueView/fatigueview — dataset grande de drowsiness multi-câmera, download direto em `dataset/`
- **NITYMED** (CC-BY, noturno — bocejo/microsleep/distração): https://datasets.esdalab.ece.uop.gr/ — 130 vídeos noturnos, ~700 MB–1,6 GB
- **Reddit r/datasets** — thread "Driver Drowsiness Datasets": https://www.reddit.com/r/datasets/comments/1ubthh3/driver_drowsiness_datasets_for_south_asians/ (consenso: NTHU-DDD é a aposta mais próxima p/ diversidade)
- **Espelho Kaggle NTHU-DDD** citado em paper PMC (acesso rápido p/ frames): https://www.kaggle.com/datasets/banudeep/nthuddd2
- **Dryad DD-Database** (sinais fisiológicos + anotações, 260 MB): https://datadryad.org/dataset/doi:10.5061/dryad.5tb2rbp9c
- **TRYOUT/TU Graz** (3,5 GB, drowsiness em simulador): https://repository.tugraz.at/records/a4nsk-qyh91

---

# 5. Situação das 8 fontes

### Acesso confirmado (2)
- **SRC002 UTA-RLDD** — link público de Google Drive no site oficial.
- **SRC003 YawDD** — IEEE DataPort Open Access (login gratuito); licença **CC-BY**;
  restrição de *screenshots* para participantes marcados "No".

### Exigem autorização (4)
- **SRC001 DMD** — formulário + aceite de termos (revisão 2026 restringe o
  conjunto público a IDs de sujeito específicos; só RGB real-car).
- **SRC005 NTHU-DDD** — EULA assinado por chefe de departamento/diretor +
  e-mail. Não-comercial; sem redistribuição; imagens faciais com restrições
  (só sujeitos 010 & 021 em publicações acadêmicas).
- **SRC006 AUC-DISTRACTED** — acordo assinado + e-mail aos representantes.
- **SRC008 UL-DD** — Zenodo Restricted: conta registrada + e-mail institucional.

### Acesso em revisão (1)
- **SRC007 STATE-FARM** — Kaggle com aceite das regras da competição; uso
  além da competição requer revisão dos termos.

### Não verificado (1)
- **SRC004 DROZY** — site oficial fora do ar na data de verificação.

### Licença não permite redistribuição (3)
NTHU-DDD · AUC-DISTRACTED · State Farm (na prática, pelas regras).

### Licença pendente (2)
UTA-RLDD · DROZY — integração bloqueada até esclarecimento.

### Precisam de nova anotação humana (8 de 8)
Zero mapeamentos `DIRECT`. Rótulos de nível de vídeo/sessão (CASO 1),
autorrelato KSS (CASO 2), bocejos sem intervalo (CASO 3) e celular sem
verificação de atenção (CASO 4) exigem reanotação humana independente.

---

# 6. Estrutura de diretórios

```
NightEyes/
├── README.md                          # este arquivo
├── requirements.txt                   # pandas, pytest
├── data/
│   ├── catalog/
│   │   ├── datasets.csv               # catálogo central (8 datasets × 22 campos)
│   │   ├── compatibility_matrix.csv   # 64 mapeamentos rótulo-a-rótulo
│   │   ├── licenses.csv               # registro de licenças (8)
│   │   └── sources_registry.csv       # esquema de rastreio de arquivos (vazio)
│   ├── raw/                           # ORIGINAIS NUNCA modificados (vazio na Parte 1)
│   │   ├── DMD/ UTA_RLDD/ YawDD/ DROZY/ NTHU_DDD/
│   │   ├── AUC_Distracted/ State_Farm/ UL_DD/
│   │   ├── sessions/                  # §11 do protocolo — por sessão
│   │   └── metadata/                  # §11 do protocolo — metadados originais
│   ├── original_labels/               # rótulos originais preservados
│   ├── normalized/                    # só saídas NOVAS de transformação
│   ├── annotation/                    # participants, sessions, episodes, windows, annotators
│   ├── quality_control/
│   ├── processed/                     # train/validation/test (Parte 2)
│   └── reports/                       # validation_report.json / .csv
├── documentation/
│   ├── behavior_dictionary.csv        # 16 códigos (PROPOSED)
│   ├── metadata_dictionary.csv        # dicionário campo a campo (schema v1.0)
│   ├── label_mapping_rules.md         # regras de conversão (CASOS 1–5)
│   └── IMPLEMENTATION_REPORT.md       # relatório de execução da Parte 1
├── scripts/
│   ├── validate_dataset.py            # V01–V14
│   ├── label_mapping.py               # 43 regras R001–R043
│   └── serve_catalog.py               # interface local
├── interface/index.html               # UI do catálogo
├── tests/                             # pytest — 43 testes
│   ├── conftest.py
│   ├── test_validate_dataset.py
│   └── test_label_mapping.py
└── .gitignore
```

---

# 7. Como executar

### Pré-requisitos
- Python 3.10+ (executado com 3.14.2)
- `pip install -r requirements.txt` (pandas, pytest)

### 7.1 Validação
```bash
python scripts/validate_dataset.py
```
- Executa V01–V14; gera `data/reports/validation_report.json` e `.csv`.
- Exit `0` = sem erros (avisos permitidos); `1` = erros.
- **Nunca corrige dados silenciosamente** — apenas reporta.

### 7.2 Testes automatizados
```bash
python -m pytest tests/ -v
```
43 testes: caso base limpo, cada verificação com defeito injetado, geração de
relatórios e os CASOS 1–5 do mapeamento.

### 7.3 Interface local
```bash
python scripts/serve_catalog.py --port 8765
# abra http://127.0.0.1:8765/
```

### 7.4 Mapeamento de rótulos (exemplo)
```python
import sys; sys.path.insert(0, "scripts")
from label_mapping import evaluate_mapping

d = evaluate_mapping("SRC002", "drowsy", "SLEEPINESS", "SLEEP_001")
print(d.decision)   # PENDING — CASO 1, nunca conversão automática
```

---

# 8. Vocabulários controlados e integridade

| Campo | Valores permitidos |
|---|---|
| `access_status` | `AVAILABLE`, `REQUIRES_PERMISSION`, `REVIEW_REQUIRED`, `RESTRICTED`, `UNKNOWN` |
| `reference_label` | `PRESENT`, `ABSENT`, `UNCERTAIN`, `UNOBSERVABLE` |
| `domain` / `mapped_domain` | `FATIGUE`, `SLEEPINESS`, `DISTRACTION`, `QUALITY` |
| `compatibility_level` | `DIRECT`, `PARTIAL`, `COMPLEMENTARY`, `INCOMPATIBLE`, `UNVERIFIED` |
| `requires_reannotation` | `YES`, `NO` |
| `processing_status` | `REGISTERED`, `VERIFIED`, `TRANSFORMED`, `QUARANTINED` |

### Princípios de integridade (protocolo §7 + plano §13)
- Originais em `data/raw/` **nunca** sobrescritos; transformações geram arquivo
  novo com rastreio (`sources_registry.csv` + SHA-256).
- Ground truth **independente**: EAR, MAR, PERCLOS, frequência de piscadas do
  motor, scores de fadiga/sonolência/distração e risco global são **proibidos**
  como origem de rótulo (`label_mapping.py` → `FORBIDDEN`).
- Autorrelato (KSS) armazenado **separado** da observação visual.
- Sem fusão de identidades entre datasets; sem dados fictícios; sem presunção
  de licença; sem rolagem de `UNCERTAIN`→`ABSENT`.
- Versão de esquema registrada em `metadata_dictionary.csv` (`schema_version`).
- Divisão TRAIN/VALIDATION/TEST por participante (implementação na Parte 2).

---

# 9. Estado dos testes e relatórios

| Execução | Comando | Resultado |
|---|---|---|
| Testes automatizados | `python -m pytest tests/ -q` | **43 passed** (~1,8 s) |
| Validação do projeto | `python scripts/validate_dataset.py` | **PASS** — 0 erros, 0 avisos, exit 0 |
| Checagem de integridade CSV | nº de campos por linha (11 arquivos) | todos consistentes |
| Interface | `GET /api/summary`, filtros, detalhe, `/` | 8 datasets; filtros OK; HTTP 200 |

Correções de dados aplicadas durante a execução (nunca o validador):
1. `behavior_dictionary.csv` — 2 linhas com vírgula não escapada (SLEEP_004,
   DIST_004) re-citadas.
2. `compatibility_matrix.csv` — 4 valores `NO (store separately)` violando o
   enum `requires_reannotation` corrigidos para `NO`.

Relatóries: `data/reports/validation_report.json` e `.csv`.

---

# 10. Pendências e plano da Parte 2

## 10.1 Pendências conhecidas

| # | Pendência | Bloqueia |
|---|---|---|
| P1 | Conferência cruzada do PDF NightEyes V0.1 página a página (modelo não lê PDF; texto integral recebido por mensagem) | auditoria fina |
| P2 | Confirmar acesso + licença do DROZY com os autores | SRC004 |
| P3 | Esclarecer licença do UTA-RLDD com os autores | SRC002 redistribuição |
| P4 | Confirmar termos atuais do DMD (revisão 2026) e IDs liberados | SRC001 |
| P5 | Obter EULAs assinados (NTHU, AUC) e aprovação Zenodo (UL-DD) | importação SRC005/006/008 |
| P6 | Revisão dos termos da competição State Farm | SRC007 |
| P7 | Resolver conflitos de contagem (AUC frames 12.977 vs 17.308; NTHU 356 vs 360; YawDD 107 vs 119) após aquisição | metadados definitivos |
| P8 | Revisar códigos `PROPOSED` do dicionário no manual de anotação | anotação |
| P9 | Fixar limiares (persistência de olhar/cabeça, duração de fechamento prolongado) no manual | mapeamentos `PARTIAL`→`DIRECT` |
| P10 | Definir divisão TRAIN/VALIDATION/TEST por participante | splits |

## 10.2 Parte 2 — próximos passos

1. **Aquisição autorizada** pelos canais da seção 4 + registro em
   `sources_registry.csv` (SHA-256, tamanho, data, permissão, status).
2. **Importação** para `data/raw/` preservando originais.
3. **Preenchimento** de `participants.csv`/`sessions.csv` a partir dos
   metadados de origem (sem identificação facial, sem fusão entre fontes).
4. **Extração de rótulos originais** para `original_labels/`; transformações
   apenas em `normalized/` com rastreio.
5. **Sessão piloto de anotação**: dois avaliadores independentes, sem acesso a
   scores do Risk Engine; resolução de divergências mantendo `UNCERTAIN`;
   consolidação em `episodes.csv`/`windows.csv` (janela inicial 5 s).
6. **Revisão do manual**: códigos `PROPOSED` → `APPROVED`; limiares fixados.
7. **Divisão por participante** TRAIN/VALIDATION/TEST; `test.csv` isolado.
8. **Consolidação NightEyes** com colunas de origem (`dataset_id`,
   `original_*`) para rastreabilidade total.
9. **Avaliação do Risk Engine** (§10): sensibilidade, especificidade,
   precisão, FP/FN, matriz de confusão por domínio, tempo de detecção e
   recuperação, cobertura, condições adversas.

---

*Documento técnico do NightEyes Dataset V1.0 — Parte 1. Atualizado em 2026-11-19.*
*Dados protegidos NÃO são distribuídos por este repositório.*
