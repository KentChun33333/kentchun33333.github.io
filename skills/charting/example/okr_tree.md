# OKR Tree / Goal Cascade — Example

## Scenario: SaaS Company Q3 OKR Cascade

The CEO sets 2 company-level objectives. Each VP breaks them into department KRs, which cascade to team-level KRs. The tree shows every team's line-of-sight to company strategy.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="OKR Goal Cascade — Q3 Company → Department → Team" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=14;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="960" height="36" as="geometry"/>
    </mxCell>

    <!-- COMPANY LEVEL -->
    <!-- Objective 1 -->
    <mxCell id="co1" value="🏢 COMPANY OBJ 1&#xa;Accelerate Revenue Growth" style="rounded=1;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="200" y="60" width="220" height="60" as="geometry"/>
    </mxCell>
    <!-- Objective 2 -->
    <mxCell id="co2" value="🏢 COMPANY OBJ 2&#xa;Achieve World-Class NPS" style="rounded=1;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="560" y="60" width="220" height="60" as="geometry"/>
    </mxCell>

    <!-- KR level for OBJ 1 -->
    <mxCell id="kr1a" value="KR 1.1: Grow ARR to $12M&#xa;(from $9M)" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="60" y="175" width="170" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="kr1b" value="KR 1.2: Close 15 new&#xa;enterprise accounts" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="250" y="175" width="170" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="kr1c" value="KR 1.3: Reduce sales cycle&#xa;from 90 to 60 days" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="440" y="175" width="170" height="50" as="geometry"/>
    </mxCell>

    <!-- KR level for OBJ 2 -->
    <mxCell id="kr2a" value="KR 2.1: Achieve NPS &gt; 65&#xa;(from 54)" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="630" y="175" width="170" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="kr2b" value="KR 2.2: Reduce churn&#xa;to &lt;3% monthly" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="810" y="175" width="170" height="50" as="geometry"/>
    </mxCell>

    <!-- DEPARTMENT LEVEL -->
    <!-- Sales dept under KR 1.1 + 1.2 -->
    <mxCell id="dept1" value="💼 Sales Dept OBJ&#xa;Own pipeline of $4M new ARR" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="60" y="280" width="200" height="50" as="geometry"/>
    </mxCell>
    <!-- Marketing dept under KR 1.1 -->
    <mxCell id="dept2" value="📣 Marketing Dept OBJ&#xa;Generate 800 qualified leads" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="280" y="280" width="200" height="50" as="geometry"/>
    </mxCell>
    <!-- RevOps dept under KR 1.3 -->
    <mxCell id="dept3" value="⚙️ RevOps Dept OBJ&#xa;Streamline sales process" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="500" y="280" width="200" height="50" as="geometry"/>
    </mxCell>
    <!-- CS dept under KR 2.1 + 2.2 -->
    <mxCell id="dept4" value="🤝 Customer Success Dept OBJ&#xa;Drive adoption &amp; expansion" style="rounded=1;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="720" y="280" width="200" height="50" as="geometry"/>
    </mxCell>

    <!-- TEAM LEVEL KRs -->
    <!-- Sales team KRs -->
    <mxCell id="t1a" value="Team KR: 12 demos/week" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="385" width="140" height="38" as="geometry"/></mxCell>
    <mxCell id="t1b" value="Team KR: Win rate 35%" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="180" y="385" width="140" height="38" as="geometry"/></mxCell>
    <!-- Marketing team KRs -->
    <mxCell id="t2a" value="Team KR: 3 campaigns/mo" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="270" y="385" width="140" height="38" as="geometry"/></mxCell>
    <mxCell id="t2b" value="Team KR: MQL rate &gt; 40%" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="420" y="385" width="140" height="38" as="geometry"/></mxCell>
    <!-- RevOps team KRs -->
    <mxCell id="t3a" value="Team KR: CRM auto-log 90% of calls" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="490" y="385" width="170" height="38" as="geometry"/></mxCell>
    <!-- CS team KRs -->
    <mxCell id="t4a" value="Team KR: QBR coverage 80%" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="680" y="385" width="150" height="38" as="geometry"/></mxCell>
    <mxCell id="t4b" value="Team KR: CSAT &gt; 4.5/5.0" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="840" y="385" width="140" height="38" as="geometry"/></mxCell>

    <!-- Connecting arrows: Company → KR -->
    <mxCell id="a1" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#1565C0;strokeWidth=2;" edge="1" parent="1" source="co1" target="kr1a"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a2" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#1565C0;strokeWidth=2;" edge="1" parent="1" source="co1" target="kr1b"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a3" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#1565C0;strokeWidth=2;" edge="1" parent="1" source="co1" target="kr1c"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a4" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;" edge="1" parent="1" source="co2" target="kr2a"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a5" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;" edge="1" parent="1" source="co2" target="kr2b"><mxGeometry relative="1" as="geometry"/></mxCell>
    <!-- KR → Dept -->
    <mxCell id="a6" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;" edge="1" parent="1" source="kr1a" target="dept1"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a7" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;" edge="1" parent="1" source="kr1b" target="dept2"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a8" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;" edge="1" parent="1" source="kr1c" target="dept3"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a9" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;" edge="1" parent="1" source="kr2a" target="dept4"><mxGeometry relative="1" as="geometry"/></mxCell>
    <!-- Dept → Team -->
    <mxCell id="a10" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept1" target="t1a"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a11" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept1" target="t1b"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a12" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept2" target="t2a"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a13" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept2" target="t2b"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a14" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept4" target="t4a"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a15" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#F9A825;strokeWidth=2;" edge="1" parent="1" source="dept4" target="t4b"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- RAG status indicators -->
    <mxCell id="s1" value="🟢 On Track" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="435" width="80" height="20" as="geometry"/></mxCell>
    <mxCell id="s2" value="🟡 At Risk" style="rounded=1;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1"><mxGeometry x="420" y="435" width="80" height="20" as="geometry"/></mxCell>
    <mxCell id="s3" value="🔴 Off Track" style="rounded=1;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;" vertex="1" parent="1"><mxGeometry x="680" y="435" width="80" height="20" as="geometry"/></mxCell>
  </root>
</mxGraphModel>
```

---

## OKR Cascade Summary

| Level | Objective | Key Result | Owner | Status |
|-------|-----------|-----------|-------|--------|
| Company | Accelerate Revenue | ARR → $12M | CEO | 🟡 At Risk (currently $10.2M) |
| Company | World-Class NPS | NPS > 65 | CEO | 🟢 On Track (NPS 61) |
| Dept | New ARR | $4M pipeline | VP Sales | 🟡 At Risk |
| Dept | Lead Generation | 800 MQLs | VP Marketing | 🟢 On Track |
| Team | Demo Velocity | 12 demos/week | Sales Team | 🟢 On Track |
| Team | QBR Coverage | 80% | CS Team | 🔴 Off Track (52%) |

## Key Insight for Leaders

The tree reveals that **QBR coverage (52% vs. 80% target)** is at risk of undermining the NPS objective. Without the cascade, the CEO would only see NPS at 61 and not know the operational root cause. The OKR tree gives executives surgical visibility — they know **which team** to call and **which specific KR** to unblock.
