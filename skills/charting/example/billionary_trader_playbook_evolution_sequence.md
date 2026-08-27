# Billionary Trader Playbook Evolution - UML Sequence Flow

## Scenario: Champion / Challenger Improvement Loop

This sequence diagram shows how a playbook is frozen, backtested, scored, copied into a candidate, challenged, gated, and promoted only if the scorecard improves without regression.

---

## draw.io XML

Paste into draw.io -> **Extras -> Edit Diagram**

```xml
<mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0" background="#ffffff">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <mxCell id="brand" value="Billionary Trader" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontColor=#C41230;fontSize=24;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="70" y="44" width="270" height="36" as="geometry"/>
    </mxCell>
    <mxCell id="title" value="Playbook Evolution - Champion / Challenger Flow" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontColor=#222222;fontSize=24;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="360" y="80" width="880" height="36" as="geometry"/>
    </mxCell>

    <mxCell id="h_user" value="Researcher" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="310" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_llm" value="LLM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="525" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_champion" value="champion/" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="740" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_candidate" value="candidate/" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="955" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_scorecard" value="scorecard" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1170" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_archive" value="archive/" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1385" y="135" width="150" height="58" as="geometry"/>
    </mxCell>

    <mxCell id="phase1" value="Loop 1: Freeze&#xa;Benchmark + inputs" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#E4F3F8;strokeColor=#B7DDE8;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="220" width="210" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="phase2" value="Loop 2: Score x2&#xa;Champion then candidate" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FFF2CC;strokeColor=#E6D79E;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="330" width="210" height="205" as="geometry"/>
    </mxCell>
    <mxCell id="phase3" value="Loop 3: Gate&#xa;Improve, no regression" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FBE3E5;strokeColor=#E1B2B9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="585" width="210" height="90" as="geometry"/>
    </mxCell>
    <mxCell id="phase4" value="Loop 4: Promote&#xa;Atomic swap + log" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#EAF4E2;strokeColor=#C8DDB9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="735" width="210" height="80" as="geometry"/>
    </mxCell>
    <mxCell id="worktree" value="Folder&#xa;or Worktree" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#111111;strokeWidth=2;fontSize=26;align=left;spacingLeft=12;fontColor=#202124;" vertex="1" parent="1">
      <mxGeometry x="95" y="435" width="170" height="88" as="geometry"/>
    </mxCell>

    <mxCell id="life_user" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="384" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_llm" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="599" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_champion" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="814" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_candidate" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1029" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_scorecard" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1244" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_archive" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1459" y="195" width="1" height="650" as="geometry"/>
    </mxCell>

    <mxCell id="act_llm_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="230" width="16" height="575" as="geometry"/>
    </mxCell>
    <mxCell id="act_champion" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="806" y="340" width="16" height="105" as="geometry"/>
    </mxCell>
    <mxCell id="act_candidate" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1021" y="500" width="16" height="75" as="geometry"/>
    </mxCell>
    <mxCell id="act_scorecard" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1236" y="410" width="16" height="260" as="geometry"/>
    </mxCell>
    <mxCell id="act_archive" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1451" y="735" width="16" height="70" as="geometry"/>
    </mxCell>

    <mxCell id="m1" value="1: freeze inputs / pick playbook" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="245" as="sourcePoint"/><mxPoint x="591" y="245" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m2" value="2: run champion backtest" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="355" as="sourcePoint"/><mxPoint x="806" y="355" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m3" value="3: baseline metrics" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="806" y="395" as="sourcePoint"/><mxPoint x="607" y="395" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m4" value="4: score + weaknesses" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="430" as="sourcePoint"/><mxPoint x="1236" y="430" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="mutate" value="Mutate - copy champion + edit candidate playbook in isolated folder/worktree" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F3E7FB;strokeColor=#AA7CC7;fontSize=16;fontColor=#222222;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="430" y="465" width="860" height="34" as="geometry"/>
    </mxCell>
    <mxCell id="m5" value="5: run candidate backtest" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="525" as="sourcePoint"/><mxPoint x="1021" y="525" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m6" value="6: challenger metrics" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1021" y="565" as="sourcePoint"/><mxPoint x="607" y="565" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m7" value="7: compare scorecards" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="620" as="sourcePoint"/><mxPoint x="1236" y="620" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="gate" value="8: gate check - improvement threshold met? no regression?" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FDECEB;strokeColor=#D59A9A;fontSize=16;fontColor=#A64D4D;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="430" y="655" width="820" height="34" as="geometry"/>
    </mxCell>
    <mxCell id="m9" value="9: present scorecard + rationale" style="endArrow=open;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="705" as="sourcePoint"/><mxPoint x="392" y="705" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m10" value="10: approve promotion" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="735" as="sourcePoint"/><mxPoint x="591" y="735" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m11" value="11: archive old champion" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="765" as="sourcePoint"/><mxPoint x="1451" y="765" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m12" value="12: swap candidate into champion" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="795" as="sourcePoint"/><mxPoint x="806" y="795" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m13" value="13: log changelog + next seed" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="825" as="sourcePoint"/><mxPoint x="1451" y="825" as="targetPoint"/></mxGeometry>
    </mxCell>
  </root>
</mxGraphModel>
```

