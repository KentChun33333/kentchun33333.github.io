# Decision Tree — Example

## Scenario: Startup Fundraising Strategy Decision

A founder with $800K ARR needs to decide whether to bootstrap, raise a Seed round, or go directly to Series A. Each path has different probabilities of success and financial outcomes.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="Decision Tree — Startup Fundraising Strategy" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="900" height="36" as="geometry"/>
    </mxCell>

    <!-- ROOT DECISION NODE -->
    <mxCell id="root" value="📋 DECIDE:&#xa;Fundraising Strategy" style="shape=mxgraph.flowchart.decision;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="380" y="65" width="160" height="80" as="geometry"/>
    </mxCell>

    <!-- BRANCH 1: Bootstrap -->
    <mxCell id="b1" value="🔷 Bootstrap&#xa;(Self-fund)" style="rounded=1;fillColor=#37474F;strokeColor=#263238;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="60" y="195" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="a_root_b1" value="Option A" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#37474F;strokeWidth=2;" edge="1" parent="1" source="root" target="b1"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- BRANCH 2: Seed Round -->
    <mxCell id="b2" value="🔷 Raise Seed&#xa;($2M at $8M cap)" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="390" y="195" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="a_root_b2" value="Option B" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;" edge="1" parent="1" source="root" target="b2"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- BRANCH 3: Series A -->
    <mxCell id="b3" value="🔷 Raise Series A&#xa;($8M at $25M pre)" style="rounded=1;fillColor=#6A1B9A;strokeColor=#4A148C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="730" y="195" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="a_root_b3" value="Option C" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#6A1B9A;strokeWidth=2;" edge="1" parent="1" source="root" target="b3"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- BOOTSTRAP outcomes -->
    <mxCell id="b1_win" value="⭕ High growth&#xa;P = 35%" style="ellipse;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="20" y="320" width="100" height="50" as="geometry"/></mxCell>
    <mxCell id="b1_lose" value="⭕ Stagnate&#xa;P = 65%" style="ellipse;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="130" y="320" width="100" height="50" as="geometry"/></mxCell>
    <mxCell id="a_b1_win" value="35%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;fontSize=9;" edge="1" parent="1" source="b1" target="b1_win"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a_b1_lose" value="65%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#c62828;fontSize=9;" edge="1" parent="1" source="b1" target="b1_lose"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- BOOTSTRAP outcome values -->
    <mxCell id="b1_win_val" value="Outcome: $6M equity value&#xa;(100% ownership retained)" style="rounded=1;fillColor=#E8F5E9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="10" y="390" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b1_lose_val" value="Outcome: $0.8M (sell or close)&#xa;Dilution: 0%" style="rounded=1;fillColor=#FFEBEE;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="120" y="390" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b1_ev" value="EV = (0.35 × $6M) + (0.65 × $0.8M) = $2.62M" style="text;html=1;strokeColor=none;fillColor=#FFF9C4;rounded=1;fontSize=10;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="445" width="250" height="25" as="geometry"/></mxCell>

    <!-- SEED outcomes -->
    <mxCell id="b2_win" value="⭕ Series A&#xa;raised in 18mo&#xa;P = 60%" style="ellipse;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="350" y="320" width="100" height="60" as="geometry"/></mxCell>
    <mxCell id="b2_lose" value="⭕ Pivots or&#xa;shuts down&#xa;P = 40%" style="ellipse;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="460" y="320" width="100" height="60" as="geometry"/></mxCell>
    <mxCell id="a_b2_win" value="60%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;fontSize=9;" edge="1" parent="1" source="b2" target="b2_win"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a_b2_lose" value="40%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#c62828;fontSize=9;" edge="1" parent="1" source="b2" target="b2_lose"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- SEED outcome values -->
    <mxCell id="b2_win_val" value="Outcome: $18M founder equity&#xa;(after 20% seed dilution)" style="rounded=1;fillColor=#E8F5E9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="340" y="400" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b2_lose_val" value="Outcome: $0M (runway expires)&#xa;Dilution: 20%" style="rounded=1;fillColor=#FFEBEE;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="455" y="400" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b2_ev" value="EV = (0.60 × $18M) + (0.40 × $0) = $10.8M" style="text;html=1;strokeColor=none;fillColor=#FFF9C4;rounded=1;fontSize=10;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="340" y="455" width="250" height="25" as="geometry"/></mxCell>

    <!-- SERIES A outcomes -->
    <mxCell id="b3_win" value="⭕ Scales to&#xa;$5M ARR in 2y&#xa;P = 40%" style="ellipse;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="700" y="320" width="100" height="60" as="geometry"/></mxCell>
    <mxCell id="b3_lose" value="⭕ Fails to hit&#xa;Series B metrics&#xa;P = 60%" style="ellipse;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="810" y="320" width="100" height="60" as="geometry"/></mxCell>
    <mxCell id="a_b3_win" value="40%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;fontSize=9;" edge="1" parent="1" source="b3" target="b3_win"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a_b3_lose" value="60%" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#c62828;fontSize=9;" edge="1" parent="1" source="b3" target="b3_lose"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- SERIES A outcome values -->
    <mxCell id="b3_win_val" value="Outcome: $35M founder equity&#xa;(after 32% dilution)" style="rounded=1;fillColor=#E8F5E9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="690" y="400" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b3_lose_val" value="Outcome: $2M (acqui-hire)&#xa;Dilution: 32%" style="rounded=1;fillColor=#FFEBEE;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="800" y="400" width="130" height="45" as="geometry"/></mxCell>
    <mxCell id="b3_ev" value="EV = (0.40 × $35M) + (0.60 × $2M) = $15.2M" style="text;html=1;strokeColor=none;fillColor=#FFF9C4;rounded=1;fontSize=10;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="690" y="455" width="260" height="25" as="geometry"/></mxCell>

    <!-- Recommendation -->
    <mxCell id="rec" value="✅ RECOMMENDATION: Raise Seed ($10.8M EV) unless you can realistically qualify for Series A terms. Series A has higher EV ($15.2M) but 60% failure risk with $8M capital raised is board-level scrutiny at scale." style="rounded=1;fillColor=#E3F2FD;strokeColor=#1565C0;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="490" width="910" height="45" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Expected Value Comparison

| Path | Success Rate | Upside | Downside | **EV** | Dilution |
|------|-------------|--------|---------|--------|---------|
| Bootstrap | 35% | $6M | $0.8M | **$2.62M** | 0% |
| Seed Round | 60% | $18M | $0 | **$10.8M** | 20% |
| Series A | 40% | $35M | $2M | **$15.2M** | 32% |

## Key Insight for Leaders

The decision tree shows that **Series A has the highest EV ($15.2M)** but carries a **60% failure probability**. For a risk-averse founder, Seed Round is the clear choice — good EV with manageable downside. For an aggressive founder who believes they're Series A-ready, the math supports the bet.

The tree forces you to **assign probabilities before deciding** — the most common mistake in strategic decisions is choosing the "highest potential" path without acknowledging its base failure rate.
