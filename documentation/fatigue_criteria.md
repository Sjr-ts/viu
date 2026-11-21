# NightEyes — critérios de anotação: Fadiga (`FATIGUE`)

**Versão:** 1.0 · **Protocolo:** NightEyes V0.1 §2.1 · **Data:** 2026-11-21

## 1. Princípio

Fadiga é avaliada como **alteração observável do comportamento ocular ao longo do tempo**,
não como diagnóstico fisiológico. Um único frame **nunca** é suficiente para atribuir
`PRESENT` ou `ABSENT`: o critério exige comparação com o padrão de piscadas do próprio
participante dentro da sessão.

> Isso é uma decisão metodológica explícita: fadiga ≠ sonolência. Olhos fechados
> observados em um único frame são anotados como `SLEEPINESS`, não como `FATIGUE`.

## 2. Indicadores observáveis

| Código | Indicador | Evidência necessária |
|---|---|---|
| `EYE_001` | Piscado normal | Abertura e fechamento completos dentro da faixa de baseline da sessão |
| `EYE_002` | Fechamento prolongado | Fechamento visivelmente mais longo que o baseline |
| `EYE_003` | Fechamentos repetidos | ≥2 fechamentos dentro da janela de observação definida |
| `EYE_004` | Padrão de piscada alterado | Mudança perceptível de ritmo/frequência versus baseline |

## 3. Regra de decisão por unidade

| Situação | Rótulo |
|---|---|
| Sequência de frames disponível + baseline estabelecido + desvio visível | `PRESENT` |
| Sequência disponível, sem desvio visível | `ABSENT` |
| Frame isolado / curtíssima duração / sem baseline | `UNCERTAIN` |
| Olhos cobertos (óculos escuros, mão, oclusão) ou fora do enquadramento | `UNOBSERVABLE` |

**Nunca** converter `UNCERTAIN` ou `UNOBSERVABLE` em `ABSENT` (protocolo §4).

## 4. Janela de observação (configuração inicial)

- Janela de trabalho: **5 s** (compatível com o Nível B do protocolo).
- Baseline: primeiros **10 s** da sessão ou, quando indisponíveis, mediana dos
  frames claramente alertas da mesma sessão.
- Fechamento "prolongado": duração visivelmente superior ao baseline observado;
  o limiar numérico definitivo será fixado após a sessão piloto.

## 5. Independência

É proibido usar EAR, PERCLOS, frequência de piscadas ou qualquer score do motor
para definir estes rótulos (protocolo §7). Estes valores somente entram na
comparação posterior em `scripts/evaluate_engine.py`.

## 6. Estado atual do dataset

Os frame-crops SRC010 são imagens isoladas: recebem `FATIGUE=UNCERTAIN` com a nota
"single frame: blink-rate change/persistence not assessable". Não há nenhum episódio
`FATIGUE=PRESENT` fabricado. Para avaliar fadiga é necessário adquirir sequências
vídeo rotuladas temporalmente (por exemplo DMD/UTA-RLDD após autorização de licença).
