# NightEyes — Regras de Integração e Conversão de Rótulos

**Versão do documento:** 1.0
**Data de verificação:** 2026-11-19
**Escopo:** Parte 1 — regras explícitas para conversão (ou recusa de conversão) de rótulos originais de datasets para os estados NightEyes.
**Módulo executável correspondente:** `scripts/label_mapping.py`

---

## 1. Princípios

1. **Nenhuma conversão automática sem regra explícita.** Toda conversão deve estar declarada neste documento e registrada em `scripts/label_mapping.py`. Rótulo sem regra = `PENDING` (não convertido).
2. **Estados padronizados NightEyes:** `PRESENT`, `ABSENT`, `UNCERTAIN`, `UNOBSERVABLE`.
   - `UNCERTAIN` e `UNOBSERVABLE` **nunca** são convertidos em `ABSENT`.
   - `UNCERTAIN` e `UNOBSERVABLE` **nunca** são convertidos em ausência de risco.
3. **Independência do ground truth:** nenhuma conversão pode utilizar scores, classificações ou decisões internas do Risk Engine (EAR, MAR, PERCLOS, frequência de piscadas calculada pelo motor, scores de fadiga/sonolência/distração, classificação global de risco). Fontes proibidas conforme NightEyes V0.1 §7.
4. **KSS e autorrelatos** são sempre armazenados **separadamente** das observações visuais (`SLEEP_004`, nível `COMPLEMENTARY`).
5. **Rótulos originais nunca são sobrescritos.** A conversão gera um novo registro rastreável (`original_labels/` preservado; `normalized/` contém somente saídas novas).
6. **Preservação temporal:** intervalos originais do episódio de origem são sempre mantidos; qualquer reamostragem para janelas (ex.: 5 s) é uma transformação nova, registrada à parte.

---

## 2. Níveis de compatibilidade (matriz de compatibilidade)

| Nível | Significado | Conversão permitida? |
|---|---|---|
| `DIRECT` | Correspondência direta e documentada | Sim, mediante regra registrada |
| `PARTIAL` | Compatibilidade parcial, dependente de condições adicionais | Somente com verificação humana documentada |
| `COMPLEMENTARY` | Informação complementar, não equivalente a rótulo visual | Não gera `PRESENT` visual; armazenar à parte |
| `INCOMPATIBLE` | Não pode ser convertido para a finalidade pretendida | Não |
| `UNVERIFIED` | Correspondência ainda não verificada | Não (aguarda verificação) |

---

## 3. Casos obrigatórios (NightEyes V0.1 / plano Parte 1)

### CASO 1 — Fonte original: `Drowsy` (ou `drowsy`, `low vigilant`, `session condition: Drowsy`)

- **Origem:** UTA-RLDD (rótulo por vídeo ~10 min), UL-DD (condição de sessão 40 min), DMD (`Sleepy driving`), NTHU-DDD (frame `drowsy`).
- **Regra:** `PENDING` para conversão direta em `PRESENT`.
- **Motivo:** rótulo de nível de vídeo/sessão não equivale a evidência observável em cada janela. Converter o vídeo inteiro em `PRESENT` viola a definição de `PRESENT` (evidência observável do comportamento).
- **Procedimento permitido:** (a) preservar o rótulo original como contexto de sessão; (b) submeter o vídeo à anotação humana episódica (Nível A) e de janelas (Nível B); (c) somente a anotação humana produz `PRESENT`/`ABSENT`/`UNCERTAIN`/`UNOBSERVABLE`.
- **Decisão:** `REJECTED (automatic)` / `PENDING (human reannotation)`.

### CASO 2 — Fonte original: `KSS = 8`

- **Origem:** UTA-RLDD (base KSS), DROZY (KSS por sessão PVT), UL-DD (KSS a cada 4 min).
- **Regra:** converter **apenas** para `SLEEP_004` (Self-Reported Sleepiness), nível `COMPLEMENTARY`, com campo `reference_label` **não aplicável a visual** — armazenar valor e timestamp em registro de autorrelato, separado dos episódios visuais.
- **Proibido:** converter diretamente em sonolência visual `PRESENT`.
- **Decisão:** `ALLOWED (complementary only)`.

### CASO 3 — Fonte original: `Yawning`

- **Origem:** YawDD (situação, vídeos **sem** anotação temporal), NTHU-DDD (`mouth: yawning` frame-level), DMD (`Yawn no hand`/`Yawn with hand`).
- **Regra:** relação permitida com `SLEEP_003` **apenas** com:
  1. preservação do intervalo original (quando existir);
  2. verificação temporal humana (o rótulo descreve um episódio observável de bocejo?);
  3. registro de `requires_reannotation = YES` quando não houver intervalo (YawDD).
- **Decisão:** `PENDING (temporal verification)` — nunca conversão cega.

### CASO 4 — Fonte original: `Phone Visible` (ou qualquer classe de mera presença de celular)

- **Regra:** presença de celular **não** converte automaticamente em distração `PRESENT`.
- `DIST_003` (Phone Presence) é código explícito de **não-distração**: registra a presença como evidência de cena, sem classificar atenção.
- `DIST_004` (Phone Usage) exige **uso observável** + **associação temporal com desvio de atenção**.
- **Fontes do inventário:** classes `Phone Right/Left`, `Text Right/Left` (AUC, State Farm), `Talking/Texting on phone` (DMD) são classes de **uso** (`PARTIAL` para `DIST_004`), não de presença — mesmo assim exigem verificação visual da desatenção.
- **Decisão:** `REJECTED (automatic)` para presença; `PENDING` para uso (verificação humana).

### CASO 5 — Informação insuficiente

- **Regra:**
  - Se a captura impede a avaliação (oclusão total, iluminação insuficiente, rosto não detectável) → `UNOBSERVABLE` (códigos `QUALITY_*` como justificativa).
  - Se a evidência existe mas é ambígua/insuficiente → `UNCERTAIN`.
  - **Nunca** preencher `ABSENT` por falta de informação.
- **Decisão:** `ALLOWED (state assignment per manual)` — decisão humana seguindo o manual de anotação.

---

## 4. Tabela-resumo das conversões

| # | Rótulo de origem | Domínio alvo | Comportamento alvo | Decisão | Nível | Condição |
|---|---|---|---|---|---|---|
| 1 | `drowsy` / `Drowsy` / `low vigilant` (vídeo/sessão) | SLEEPINESS | SLEEP_001 | PENDING | PARTIAL | Reanotação humana obrigatória (CASO 1) |
| 2 | `KSS = n` | SLEEPINESS | SLEEP_004 | ALLOWED | COMPLEMENTARY | Armazenar separado; nunca `PRESENT` visual (CASO 2) |
| 3 | `yawning` com intervalo temporal | SLEEPINESS | SLEEP_003 | PENDING | PARTIAL | Verificar intervalo e observabilidade (CASO 3) |
| 4 | `yawning` sem intervalo (YawDD) | SLEEPINESS | SLEEP_003 | PENDING | PARTIAL | Nova anotação episódica obrigatória (CASO 3) |
| 5 | `Phone Visible` / presença de celular | DISTRACTION | DIST_003 | REJECTED (como PRESENT) | — | Presença não é distração (CASO 4) |
| 6 | `Phone/Text usage` (frame/classe) | DISTRACTION | DIST_004 | PENDING | PARTIAL | Exige desvio de atenção verificado (CASO 4) |
| 7 | `talking and laughing` (NTHU-DDD) | DISTRACTION | — | REJECTED | INCOMPATIBLE | Não corresponde a indicadores NightEyes |
| 8 | `talking or singing` (YawDD) | DISTRACTION | — | REJECTED | UNVERIFIED | Nome de classe não establishce desatenção |
| 9 | Sem informação / captura impede avaliação | qualquer | QUALITY_* | ALLOWED | — | `UNOBSERVABLE` (CASO 5) |
| 10 | Evidência ambígua | qualquer | — | ALLOWED | — | `UNCERTAIN` (CASO 5) |
| 11 | Qualquer rótulo usando score do Risk Engine | qualquer | — | FORBIDDEN | — | Viola independência do ground truth (V0.1 §7) |
| 12 | `Gaze on road` invertido (DMD) | DISTRACTION | DIST_001 | PENDING | PARTIAL | Alinhar definição de persistência |
| 13 | `eyes: sleepy` (NTHU-DDD) | FATIGUE / SLEEPINESS | EYE_002 / SLEEP_001 | PENDING | PARTIAL | Verificar limiares nos arquivos de anotação |
| 14 | `nodding` (NTHU-DDD) | SLEEPINESS | SLEEP_001 | PENDING | COMPLEMENTARY | Evidência complementar; não é indicador visual direto |

---

## 5. Estados do módulo `scripts/label_mapping.py`

| Estado | Significado |
|---|---|
| `ALLOWED` | Conversão permitida nas condições documentadas |
| `PENDING` | Só após verificação/anotação humana documentada |
| `REJECTED` | Conversão automática proibida |
| `FORBIDDEN` | Viola princípio do protocolo (nunca executar) |

Função principal: `evaluate_mapping(dataset_id, source_label, target_domain, target_behavior)` → `MappingDecision` (dataclass com estado, nível, condições e referência ao CASO).

Consultas sem regra registrada retornam `PENDING` com aviso — **nunca** convertem silenciosamente.

---

## 6. Registro de mudanças

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-11-19 | Versão inicial com CASOS 1–5 e 14 regras da tabela-resumo. Códigos de comportamento `PROPOSED` — pendentes de revisão no manual de anotação. |
