# UML Sequence Flow — Example

## Scenario: Knowledge Extract Sequential Flow

An AI-assisted workflow scans raw files, generates a script, cooks source material into Markdown, analyzes the cooked output, synthesizes knowledge, and writes a draw.io XML visualization.

**Key Finding**: The clearest executive view is a 16:9 UML sequence-flow diagram with phases on the left, participants across the top, and numbered messages flowing top-to-bottom.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0" background="#ffffff">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- Brand and title -->
    <mxCell id="brand" value="OCBC" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontColor=#C41230;fontSize=26;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="75" y="45" width="160" height="36" as="geometry"/>
    </mxCell>
    <mxCell id="title" value="Knowledge Extract — Sequential Flow" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontColor=#222222;fontSize=22;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="390" y="82" width="820" height="34" as="geometry"/>
    </mxCell>

    <!-- Participant headers -->
    <mxCell id="h_user" value="User" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="310" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_llm" value="LLM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="525" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_raw" value="data-raw" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="740" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_cooked" value="data-cooked" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="955" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_analysis" value="analysis" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1170" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_knowledge" value="knowledge" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1385" y="135" width="150" height="58" as="geometry"/>
    </mxCell>

    <!-- Loop labels -->
    <mxCell id="loop1" value="Loop 1: Discover&#xa;Scan files" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#E4F3F8;strokeColor=#B7DDE8;fontSize=20;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="210" width="210" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="loop2" value="Loop 2: Script&#xa;Generate script" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FFF2CC;strokeColor=#E6D79E;fontSize=20;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="340" width="210" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="loop3" value="Loop 3: Cook&#xa;Run script" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#F8E4F4;strokeColor=#D7B6D4;fontSize=20;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="470" width="210" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="loop4" value="Loop 4: Analyse&#xa;Process .md files" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#EAF4E2;strokeColor=#C8DDB9;fontSize=20;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="610" width="210" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="loop5" value="Loop 5: Synthesize&#xa;Create knowledge" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FBE3E5;strokeColor=#E1B2B9;fontSize=20;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="735" width="210" height="55" as="geometry"/>
    </mxCell>

    <!-- Lifelines -->
    <mxCell id="life_user" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="384" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_llm" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="599" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_raw" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="814" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_cooked" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1029" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_analysis" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1244" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_knowledge" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1459" y="195" width="1" height="650" as="geometry"/>
    </mxCell>

    <!-- Activation bars -->
    <mxCell id="act_user_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="210" width="16" height="110" as="geometry"/>
    </mxCell>
    <mxCell id="act_llm_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="220" width="16" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="act_user_2" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="340" width="16" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="act_llm_2" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="350" width="16" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="act_user_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="470" width="16" height="115" as="geometry"/>
    </mxCell>
    <mxCell id="act_llm_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="480" width="16" height="95" as="geometry"/>
    </mxCell>
    <mxCell id="act_cooked_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1021" y="555" width="16" height="20" as="geometry"/>
    </mxCell>
    <mxCell id="act_user_4" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="610" width="16" height="105" as="geometry"/>
    </mxCell>
    <mxCell id="act_llm_4" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="620" width="16" height="80" as="geometry"/>
    </mxCell>
    <mxCell id="act_analysis_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1236" y="680" width="16" height="20" as="geometry"/>
    </mxCell>
    <mxCell id="act_user_5" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="735" width="16" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="act_llm_5" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="745" width="16" height="100" as="geometry"/>
    </mxCell>
    <mxCell id="act_knowledge_1" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1451" y="760" width="16" height="85" as="geometry"/>
    </mxCell>

    <!-- Messages -->
    <mxCell id="m1" value="1: scan data-raw" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="225" as="sourcePoint"/><mxPoint x="591" y="225" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m2" value="2: read files" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="255" as="sourcePoint"/><mxPoint x="814" y="255" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m3" value="3: return list" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="814" y="275" as="sourcePoint"/><mxPoint x="607" y="275" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m4" value="4: inventory summary" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="305" as="sourcePoint"/><mxPoint x="392" y="305" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m5" value="5: generate script" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="355" as="sourcePoint"/><mxPoint x="591" y="355" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m6" value="6: return script" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="390" as="sourcePoint"/><mxPoint x="392" y="390" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m7" value="7: run script" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="475" as="sourcePoint"/><mxPoint x="591" y="475" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m8" value="8: read files" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="505" as="sourcePoint"/><mxPoint x="814" y="505" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m9" value="9: return content" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="814" y="530" as="sourcePoint"/><mxPoint x="607" y="530" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m10" value="10: write .md" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="560" as="sourcePoint"/><mxPoint x="1021" y="560" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m11" value="11: cook done" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="580" as="sourcePoint"/><mxPoint x="392" y="580" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m12" value="12: analyze" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="625" as="sourcePoint"/><mxPoint x="591" y="625" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m13" value="13: read .md" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="655" as="sourcePoint"/><mxPoint x="1029" y="655" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m14" value="14: return .md" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1029" y="680" as="sourcePoint"/><mxPoint x="607" y="680" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m15" value="15: write analysis" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="700" as="sourcePoint"/><mxPoint x="1236" y="700" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m16" value="16: analysis done" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="720" as="sourcePoint"/><mxPoint x="392" y="720" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m17" value="17: synthesize" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="745" as="sourcePoint"/><mxPoint x="591" y="745" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m18" value="18: write book" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="775" as="sourcePoint"/><mxPoint x="1451" y="775" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="note1" value="Consolidate/conflict checks" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="920" y="780" width="360" height="28" as="geometry"/>
    </mxCell>
    <mxCell id="m19" value="19: knowledge done" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="810" as="sourcePoint"/><mxPoint x="392" y="810" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m20" value="20: visualize" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="830" as="sourcePoint"/><mxPoint x="591" y="830" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m21" value="21: write XML" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="845" as="sourcePoint"/><mxPoint x="1451" y="845" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m22" value="22: diagram done" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=16;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="860" as="sourcePoint"/><mxPoint x="392" y="860" as="targetPoint"/></mxGeometry>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Style Notes

| Element | Style |
|---------|-------|
| Canvas | 16:9, `1600x900`, white background |
| Participant headers | Light grey fill, thin grey border, 24pt bold dark text |
| Lifelines | Warm amber dashed vertical lines |
| Activation bars | Teal fill with darker teal stroke |
| Calls/writes | Solid black arrow |
| Returns/confirmations | Dashed grey arrow |
| Loop labels | Pastel left-side bands grouped by workflow phase |

## Key Insight for Leaders

This diagram makes the workflow auditable: every handoff, read/write action, and completion signal appears in time order. The left-side loop bands summarize the business phases, while the UML lifelines preserve the implementation-level sequence.
