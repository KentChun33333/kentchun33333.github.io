# Sequence Playback Pattern

Use [Pi swarm sequence](../assets/pi-agent-swarm-sequence.html) as an offline adaptation template, not a source of facts about other systems. Its visual style comes from the sibling [charting skill](../../charting/skill.md).

The example separates participant definitions, `makeFrames(mode, fails)`, diagram rendering, and playback state. Frames have phase, title, input, mechanism, output, and messages. Messages identify source/target participants and solid calls, dashed returns, or self-calls. Geometry follows the message list so a scenario updates the diagram and explanation together.

## Scenarios

- Parallel: independent children overlap; the lead joins both results.
- Chain: the first child's result becomes input to the next task.
- Failed verification: revision precedes another check and final delivery. The teaching scenario assumes the retry succeeds; it does not execute repository tools.

Separate process/context behavior follows the [official Pi subagent example](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent/examples/extensions/subagent). Synthesis, verification, and delivery are a proposed surrounding workflow. Separate contexts do not imply separate worktrees. The playback makes no quantitative performance claims.

## Behavioral checks

Manual controls stop playback. Playback ends in a stable final frame. The chain introduces a prerequisite result before starting the dependent agent. The failure option adds revision and another check rather than merely recoloring success. Narrow screens retain input → mechanism → output order. Reduced motion disables transitions; playback remains opt-in.
