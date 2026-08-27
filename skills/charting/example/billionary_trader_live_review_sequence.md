# Billionary Trader Live Review - UML Sequence Flow

## Scenario: Account-First Trading Review

This slide-ready sequence diagram shows the read-only live review loop: gather broker state, run risk and structure gates, enrich with technical/playbook context, produce a decision packet, then log the recommendation.

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
    <mxCell id="title" value="Live Account Review - Sequential Flow" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontColor=#222222;fontSize=24;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="390" y="80" width="820" height="36" as="geometry"/>
    </mxCell>

    <mxCell id="h_user" value="User" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="310" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_llm" value="LLM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="525" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_broker" value="broker-runtime" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="740" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_risk" value="risk gates" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="955" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_playbooks" value="playbooks" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1170" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_ledger" value="ledger" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1385" y="135" width="150" height="58" as="geometry"/>
    </mxCell>

    <mxCell id="phase1" value="Loop 1: Snapshot&#xa;Account + positions" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#E4F3F8;strokeColor=#B7DDE8;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="220" width="210" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="phase2" value="Loop 2: Risk&#xa;Account before ideas" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FFF2CC;strokeColor=#E6D79E;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="355" width="210" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="phase3" value="Loop 3: Context&#xa;Technical + playbook" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#F8E4F4;strokeColor=#D7B6D4;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="490" width="210" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="phase4" value="Loop 4: Decide&#xa;WAIT / act / reduce" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#EAF4E2;strokeColor=#C8DDB9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="635" width="210" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="phase5" value="Loop 5: Log&#xa;Evidence trail" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FBE3E5;strokeColor=#E1B2B9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="760" width="210" height="70" as="geometry"/>
    </mxCell>

    <mxCell id="life_user" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="384" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_llm" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="599" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_broker" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="814" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_risk" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1029" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_playbooks" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1244" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_ledger" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1459" y="195" width="1" height="650" as="geometry"/>
    </mxCell>

    <mxCell id="act_llm" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="230" width="16" height="590" as="geometry"/>
    </mxCell>
    <mxCell id="act_broker" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="806" y="260" width="16" height="95" as="geometry"/>
    </mxCell>
    <mxCell id="act_risk" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1021" y="375" width="16" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="act_playbooks" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1236" y="520" width="16" height="115" as="geometry"/>
    </mxCell>
    <mxCell id="act_ledger" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1451" y="780" width="16" height="40" as="geometry"/>
    </mxCell>

    <mxCell id="m1" value="1: request live review" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="245" as="sourcePoint"/><mxPoint x="591" y="245" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m2" value="2: account / positions / orders" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="280" as="sourcePoint"/><mxPoint x="806" y="280" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m3" value="3: snapshots" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="806" y="340" as="sourcePoint"/><mxPoint x="607" y="340" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m4" value="4: account-risk + grouping" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="395" as="sourcePoint"/><mxPoint x="1021" y="395" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m5" value="5: gate + operation map" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1021" y="465" as="sourcePoint"/><mxPoint x="607" y="465" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m6" value="6: fvg + top trader playbooks" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="535" as="sourcePoint"/><mxPoint x="1236" y="535" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m7" value="7: setup signals + invalidations" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1236" y="610" as="sourcePoint"/><mxPoint x="607" y="610" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="gate" value="Gate: missing or stale broker/chain data =&gt; WAIT / UNCONFIRMED" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FDECEB;strokeColor=#D59A9A;fontSize=16;fontColor=#A64D4D;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="430" y="650" width="820" height="34" as="geometry"/>
    </mxCell>
    <mxCell id="m8" value="8: decision packet + rationale" style="endArrow=open;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="720" as="sourcePoint"/><mxPoint x="392" y="720" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m9" value="9: approve logging" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="760" as="sourcePoint"/><mxPoint x="591" y="760" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m10" value="10: write recommendation event" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="800" as="sourcePoint"/><mxPoint x="1451" y="800" as="targetPoint"/></mxGeometry>
    </mxCell>
  </root>
</mxGraphModel>
```

