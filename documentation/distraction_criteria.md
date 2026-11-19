# NightEyes — Critérios de Anotação: DISTRAÇÃO e USO DE CELULAR

**Domínio:** `DISTRACTION` · **Códigos:** `DIST_001`–`DIST_004`
**Status:** **PROPOSED** — limiares fixados oficialmente na sessão piloto (pendência P9 do README §10.1).
**Base normativa:** Protocolo V0.1 §2.1.3 (distração), CASOS 4–5 do mapeamento,
`documentation/behavior_dictionary.csv`, `scripts/label_mapping.py` (R008–R043).
**Uso:** este documento é a seção de distração do *manual de anotação*. Avaliadores
recebem este arquivo **junto com** os vídeos — **nunca** com scores do Risk Engine.

---

## 1. Princípio reitor (CASO 4)

> **A simples presença de um celular NÃO é distração.**
> `DIST_003` (presença) **nunca** gera `DISTRACTION = PRESENT`.
> Só `DIST_004` (uso associado a desvio de atenção) sustenta `PRESENT`.

Isso é regra de projeto, não preferência: as regras R008/R009/R038–R043 do
`label_mapping.py` **rejeitam** (`REJECTED/INCOMPATIBLE`) qualquer conversão de
presença em uso, e de uso em presença.

## 2. Códigos e o que cada um significa

| Código | Nome | Registra | Gera `PRESENT` no domínio DISTRACTION? |
|---|---|---|---|
| `DIST_001` | Gaze Deviation | desvio **persistente** do olhar da cena frontal | Sim, se critério §3.1 for atendido |
| `DIST_002` | Head Deviation | desvio **persistente** da cabeça da postura de direção | Sim, se critério §3.2 for atendido |
| `DIST_003` | Phone Presence | celular **visível** (mão, bancada, suporte) **sem** uso demonstrado | **Nunca** — código explícito de *não-distração* |
| `DIST_004` | Phone Usage | uso observável (ligar/textar) **com** evidência de desvio de atenção no mesmo intervalo | Sim, se critério §4 for atendido |

> Um mesmo intervalo pode conter mais de um código (ex.: `DIST_001` + `DIST_004`
> durante texting). Cada código vira sua própria linha de episódio.

## 3. Limiares operacionais (PROPOSED — fixar na piloto, P9)

### 3.1 `DIST_001` — desvio de olhar
- **Critério:** olhar desviado da cena frontal por **≥ 2.000 ms contínuos**.
- **Âncora de literatura:** faixa "eyes off road ≥ 2 s" amplamente usada em
  segurança de tráfego; serve como candidato inicial — o valor definitivo é
  calibrado na sessão piloto com os dois avaliadores.
- **Exclui:** varredura normal (< 2.000 ms), olhar não avaliável → `UNOBSERVABLE`,
  ambíguo → `UNCERTAIN`.
- **Nota:** olhar no retrovisor/espe-lhos por tarefa de condução = varredura
  normal (exclusão).

### 3.2 `DIST_002` — desvio de cabeça
- **Critério:** orientação da cabeça fora da postura frontal por **≥ 2.000 ms contínuos**.
- **Exclui:** movimentos normais, assentir (sonolência → domínio `SLEEPINESS`,
  não aqui), cabeça não visível → `UNOBSERVABLE`.

### 3.3 `DIST_003` — presença de celular
- **Critério:** celular visível no quadro (mão, colo, bancada, suporte).
- **Duração:** qualquer — o episódio cobre enquanto a presença é visível.
- **Efeito no rótulo do domínio:** **nenhum**. Presença sozinha mantém o
  domínio `DISTRACTION` como `ABSENT` (ou `UNCERTAIN` se a cena for ambígua),
  conforme CASO 4/5. O episódio `DIST_003` fica registrado como **evidência de
  não-uso** — útil para medir falsos positivos do motor.

### 3.4 `DIST_004` — uso de celular (regra da associação temporal)
- **Critério cumulativo (ambos obrigatórios):**
  1. **Uso visível:** gesto de uso — celular na orelha, olhar para o aparelho
     com manipulação, texting com olhar descer para o aparelho;
  2. **Associação temporal:** evidência de desvio de atenção (olhar/cabeça
     fora da cena frontal) **sobreposto ao intervalo de uso**.
- **Duração mínima:** **≥ 1.000 ms** de uso visível.
- **Ligação mãos-livres com olhar fixo na via:** uso do aparelho *não* está
  visível e o desvio de atenção *não* é observável → **não** rotular `DIST_004`
  (falta de evidência visual; `UNOBSERVABLE` só se a captura impedir avaliar a
  cena inteira).
- **Celular no suporte com tela acesa, sem interação:** vira `DIST_003`
  (presença), não `DIST_004`.

## 4. Árvore de decisão — celular na cena

```
Celular visível?
├── NÃO ──► sem código de celular (avaliar DIST_001/002 normalmente)
└── SIM
    ├── Uso visível (gesto de ligar/textar/manipular)?
    │   ├── NÃO ──► DIST_003 (presença) → domínio NÃO vira PRESENT por isso
    │   └── SIM
    │       ├── Desvio de atenção sobreposto ao uso (≥1 s)?
    │       │   ├── SIM ──► DIST_004 → domínio DISTRACTION = PRESENT
    │       │   ├── NÃO (olhar segue na via, uso não clarifica atenção)?
    │       │   │         ──► DIST_003 + dúvida ⇒ UNCERTAIN (CASO 5)
    │       │   └── Cena inavaliável (rosto/cena perdida)? ──► UNOBSERVABLE
    │       └── Uso ambíguo (mão perto do rosto, não dá para afirmar)?
    │                 ──► UNCERTAIN (CASO 5) — nunca ABSENT "para fechar"
    └── (presença sem uso também pode coexistir com DIST_001/002
         em outro intervalo — avaliar cada intervalo independentemente)
```

## 5. Casos-limite (decisão já tomada — seguir à risca)

| Situação | Decisão |
|---|---|
| Celular na mão, tela desligada, sem olhar para ele | `DIST_003`; domínio não é PRESENT |
| Texting: olhar desce ao aparelho ≥ 1 s com desvio da via | `DIST_004` + provavelmente `DIST_001` no mesmo intervalo |
| Celular no suporte, GPS em uso, olhar alternado | `DIST_003`; só vira `DIST_004` se houver uso visível **e** desvio associado |
| Ligação com fone, olhar permanece na via | sem código de celular (sem evidência visual de desvio) |
| Passageiro conversando, motorista olha para o passageiro | `DIST_001` (não é celular; não é `DIST_004`) |
| Celular visível mas rosto/cena ilegível | `DIST_003` se celular claríssimo; atenção `UNOBSERVABLE` |
| Dúvida entre uso e presença | `UNCERTAIN` (CASO 5) — **nunca** converter para `ABSENT` |

## 6. Relação com rótulos de origem (só referência — reanotação obrigatória)

| Fonte | Rótulo de origem | Mapeia para | Nível | Regra |
|---|---|---|---|---|
| State Farm | `c1/c3` texting L/R | `DIST_004` | PARTIAL (imagem → episódio) | R027/R028, CASO 4 |
| State Farm | `c2/c4` talking phone L/R | `DIST_004` | PARTIAL | R029/R030, CASO 4 |
| State Farm | `c0` safe | `DIST_004` ausente | PENDING | R026 — verificar visualmente a ausência |
| AUC-DISTRACTED | phone/text classes | `DIST_004` | PARTIAL | R010–R015, CASO 4 |
| DMD | talking/texting (VCD temporal) | `DIST_004` | PARTIAL | R014/R015 |
| Qualquer fonte | "phone visible"/"phone presence" | `DIST_003` | **REJECTED** como distração | R008/R009, CASO 4 |

> Rótulo de nível de vídeo/imagem **nunca** vira episódio automaticamente
> (CASO 1). Os rótulos acima servem para **localizar** trechos candidatos;
> o episódio é o que o avaliador vê.

## 7. Metadados obrigatórios por episódio de distração

Iguais aos do protocolo (§2.4): `start_ms`/`end_ms` em ms relativos à sessão,
`domain=DISTRACTION`, `behavior_code` (um dos DIST_00x), `reference_label`,
`annotator_id`, `annotation_confidence`, condições de captura,
`annotation_notes` (ex.: `uso_visivel=SIM; desvio_associado=SIM; obs=...`).

## 8. Como isto alimenta a avaliação de detecção (§10 do protocolo)

- O **ground truth** de celular/distração são os episódios `DIST_004`
  (positivos) e os intervalos sem eles (negativos), consolidados por dois
  avaliadores (`merge_annotations.py` → divergências = `UNCERTAIN`).
- A **detecção do Risk Engine** (scores de distração) é comparada **depois**:
  precision/recall/F1 por domínio, FP/FN, tempo de detecção — os scores
  **nunca** entram na construção dos rótulos (§7 do protocolo; `FORBIDDEN` no
  `label_mapping.py`).
- `DIST_003` (presença sem uso) é o conjunto natural de **falsos positivos
  esperados** de um detector ingênuo de "celular" — é para isso que o código
  existe como evidência explícita.

---

**Checklist do avaliador (distração/celular):**
- [ ] Presença de celular **sozinha** marcou `DIST_003`, não `PRESENT`?
- [ ] `DIST_004` tem uso visível **e** desvio de atenção sobreposto?
- [ ] Intervalos ≥ 1.000 ms (uso) / ≥ 2.000 ms (olhar/cabeça — limiar PROPOSED)?
- [ ] Dúvida gravada como `UNCERTAIN` (nunca `ABSENT`)?
- [ ] Sem nenhum score do motor consultado durante a anotação?
