# Billionary Trader Backtest Engine - UML Sequence Flow

## Scenario: Portfolio Backtest Run

This slide-ready diagram summarizes the `PortfolioBacktestEngine.run()` flow from configuration through output files. It is intentionally simplified for PowerPoint: six participants, five phases, and one clear happy-path sequence.

---

## draw.io XML

Paste into draw.io -> **Extras -> Edit Diagram**

```xml
<mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0" background="#ffffff">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- Title -->
    <mxCell id="brand" value="Billionary Trader" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontColor=#C41230;fontSize=24;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="70" y="44" width="260" height="36" as="geometry"/>
    </mxCell>
    <mxCell id="title" value="Portfolio Backtest Engine - Sequential Flow" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontColor=#222222;fontSize=24;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="390" y="80" width="820" height="36" as="geometry"/>
    </mxCell>

    <!-- Participant headers -->
    <mxCell id="h_user" value="Analyst / CLI" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="310" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_engine" value="Backtest Engine" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="525" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_data" value="Data Store" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="740" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_playbook" value="Playbook" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="955" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_state" value="Portfolio State" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1170" y="135" width="150" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="h_outputs" value="Reports" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F7F7F7;strokeColor=#D9D9D9;fontSize=24;fontStyle=1;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="1385" y="135" width="150" height="58" as="geometry"/>
    </mxCell>

    <!-- Phase labels -->
    <mxCell id="phase1" value="1 Setup&#xa;Validate config" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#E4F3F8;strokeColor=#B7DDE8;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="220" width="210" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="phase2" value="2 Load data&#xa;Universe + features" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FFF2CC;strokeColor=#E6D79E;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="335" width="210" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="phase3" value="3 Generate&#xa;Signals" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#F8E4F4;strokeColor=#D7B6D4;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="460" width="210" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="phase4" value="4 Simulate&#xa;Trades + equity" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#EAF4E2;strokeColor=#C8DDB9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="590" width="210" height="58" as="geometry"/>
    </mxCell>
    <mxCell id="phase5" value="5 Finish&#xa;Metrics + outputs" style="rounded=0;whiteSpace=wrap;html=1;align=left;spacingLeft=12;fillColor=#FBE3E5;strokeColor=#E1B2B9;fontSize=18;fontColor=#222222;" vertex="1" parent="1">
      <mxGeometry x="75" y="730" width="210" height="58" as="geometry"/>
    </mxCell>

    <!-- Lifelines -->
    <mxCell id="life_user" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="384" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_engine" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="599" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_data" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="814" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_playbook" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1029" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_state" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1244" y="195" width="1" height="650" as="geometry"/>
    </mxCell>
    <mxCell id="life_outputs" value="" style="shape=line;html=1;strokeColor=#D6A15E;strokeWidth=1;dashed=1;direction=south;" vertex="1" parent="1">
      <mxGeometry x="1459" y="195" width="1" height="650" as="geometry"/>
    </mxCell>

    <!-- Activation bars -->
    <mxCell id="act_user" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="376" y="220" width="16" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="act_engine" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="591" y="230" width="16" height="600" as="geometry"/>
    </mxCell>
    <mxCell id="act_data" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="806" y="330" width="16" height="90" as="geometry"/>
    </mxCell>
    <mxCell id="act_playbook" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1021" y="370" width="16" height="150" as="geometry"/>
    </mxCell>
    <mxCell id="act_state" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1236" y="610" width="16" height="95" as="geometry"/>
    </mxCell>
    <mxCell id="act_outputs" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#55C7BE;strokeColor=#2AA79E;" vertex="1" parent="1">
      <mxGeometry x="1451" y="790" width="16" height="40" as="geometry"/>
    </mxCell>

    <!-- Messages -->
    <mxCell id="m1" value="1: run(config, playbook)" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="392" y="245" as="sourcePoint"/><mxPoint x="591" y="245" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m2" value="2: load universe" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="340" as="sourcePoint"/><mxPoint x="806" y="340" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m3" value="3: select tickers" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="380" as="sourcePoint"/><mxPoint x="1021" y="380" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m4" value="4: tickers" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1021" y="410" as="sourcePoint"/><mxPoint x="607" y="410" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m5" value="5: load daily + earnings" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="445" as="sourcePoint"/><mxPoint x="806" y="445" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m6" value="6: feature frames" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="806" y="480" as="sourcePoint"/><mxPoint x="607" y="480" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m7" value="7: generate_signal per ticker/date" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="520" as="sourcePoint"/><mxPoint x="1021" y="520" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m8" value="8: normalized signals" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1021" y="560" as="sourcePoint"/><mxPoint x="607" y="560" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m9" value="9: simulate entries/exits" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="625" as="sourcePoint"/><mxPoint x="1236" y="625" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m10" value="10: equity + closed trades" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="1236" y="690" as="sourcePoint"/><mxPoint x="607" y="690" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m11" value="11: SPY DCA benchmark" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="720" as="sourcePoint"/><mxPoint x="806" y="720" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m12" value="12: validate + summarize" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="765" as="sourcePoint"/><mxPoint x="607" y="795" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m13" value="13: write json/parquet outputs" style="endArrow=block;html=1;rounded=0;strokeColor=#222222;strokeWidth=1.5;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="607" y="810" as="sourcePoint"/><mxPoint x="1451" y="810" as="targetPoint"/></mxGeometry>
    </mxCell>
    <mxCell id="m14" value="14: PortfolioBacktestResult" style="endArrow=open;html=1;rounded=0;strokeColor=#777777;strokeWidth=1.5;dashed=1;fontSize=15;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry"><mxPoint x="591" y="845" as="sourcePoint"/><mxPoint x="392" y="845" as="targetPoint"/></mxGeometry>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Flow Notes

| Phase | Source in code |
|-------|----------------|
| Setup | `BacktestConfig.validate()` and `PortfolioBacktestEngine.run()` |
| Load data | `BacktestDataStore.load_universe()`, `load_daily()`, `load_earnings()` |
| Generate | `playbook.select_universe()` and `playbook.generate_signal()` |
| Simulate | `_simulate_portfolio()`, `_execute_entry()`, `_execute_exit()`, `_simulate_spy_dca()` |
| Finish | `_validate_run()`, `_build_summary()`, `_write_outputs()` |

## PPT Guidance

Keep this version as the presentation diagram. Put deeper implementation details, such as key-level entry handling and `open_at_end` closure, in speaker notes or a separate technical appendix.
