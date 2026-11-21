# NightEyes — critérios de anotação: Sonolência (`SLEEPINESS`)

**Versão:** 1.0 · **Protocolo:** NightEyes V0.1 §2.2 · **Data:** 2026-11-21

## 1. Princípio

Sonolência é registrada por **evidência visual observável** em frames catalogados:
fechamento ocular, bocejo e repetição de fechamentos. Autorrelato (KSS) é
complementar e fica **separado** em `data/annotation/self_reports.csv` — nunca é
fundido no rótulo visual (protocolo §2.2).

## 2. Códigos de comportamento

| Código | Evidência visual |
|---|---|
| `SLEEP_001` | Olhos fechados no frame observado (pode ser piscada → confiança MEDIUM). |
| `SLEEP_003` | Bocejo claro: boca escancarada; quando visível, olhos semicerrados. |
| `SLEEP_005` | Abertura de boca ambígua (fala versus bocejo) → `UNCERTAIN`. |
| `SLEEP_006` | Fechamento ocular em frame isolado, sem inferência de duração. |

## 3. Regras de decisão

| Observação | Rótulo |
|---|---|
| Olhos totalmente fechados | `PRESENT` / `SLEEP_001` |
| Bocejo claro (boca bem aberta) | `PRESENT` / `SLEEP_003` |
| Boca aberta, causa ambígua | `UNCERTAIN` / `SLEEP_005` |
| Olhos fechados dentro de sorriso/riso | `ABSENT` (não é sonolência) |
| Desvio leve de olhar sem Sonolência associada | `ABSENT` no domínio SLEEPINESS |
| Óculos escuros / mão / oclusão | `UNOBSERVABLE`, exceto bocejo visível pela boca → `SLEEP_003` com confiança MEDIUM |
| Olhos pesados, mas abertos | `UNCERTAIN` (não `PRESENT`) |

## 4. Direções de olhar

`gaze_direction` é sempre **relativa à imagem** (`RIGHT` = lado direito da imagem),
nunca anatômica do participante. Valores: `FORWARD`, `DOWN`, `RIGHT`, `LEFT`,
`UP`, `RIGHT_DOWN`, `RIGHT_UP`, `LEFT_DOWN`, `LEFT_UP`.

## 5. Unidade temporal

As anotações atuais são **unidades pontuais** de frame: `start_ms = timestamp`,
`end_ms = timestamp + 1`. A extensão temporal do episódio não é inferida;
isso está declarado em `data/reports/annotation_status.md`.

## 6. Independência

Nenhum rótulo foi derivado de scores do motor, nomes de arquivo ou rótulos
automáticos da fonte. Em SRC010 os rótulos heurísticos EAR/MAR da fonte foram
**explicitamente descartados** (compatibilidade `INCOMPATIBLE`, protocolo §7).
