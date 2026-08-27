# Value Stream Map — Example

## Scenario: Software Feature Delivery Pipeline

A tech company maps its current-state feature delivery flow from "Story Created" to "Production Deployed" to find where time is wasted.

**Key Finding**: Total lead time = 23 days. Value-added time = 3.5 days. Only **15% of time is value-adding**.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="Value Stream Map — Software Feature Delivery (Current State)" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=14;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="880" height="36" as="geometry"/>
    </mxCell>

    <!-- Customer (right) -->
    <mxCell id="cust" value="👤 Customer&#xa;(Production)" style="shape=mxgraph.lean_mapping.outside_sources;fillColor=#c8e6c9;strokeColor=#2E7D32;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="780" y="70" width="80" height="60" as="geometry"/>
    </mxCell>

    <!-- Process 1: Story Writing -->
    <mxCell id="p1" value="Story Writing" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="60" y="160" width="100" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="p1d" value="CT: 1d&#xa;Uptime: 90%" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="60" y="225" width="100" height="30" as="geometry"/></mxCell>

    <!-- Queue 1 -->
    <mxCell id="q1" value="⏳ 3d wait&#xa;(backlog grooming)" style="triangle;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=9;direction=east;" vertex="1" parent="1">
      <mxGeometry x="175" y="170" width="50" height="40" as="geometry"/>
    </mxCell>

    <!-- Process 2: Sprint Planning -->
    <mxCell id="p2" value="Sprint Planning" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="240" y="160" width="100" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="p2d" value="CT: 0.5d&#xa;Uptime: 100%" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="240" y="225" width="100" height="30" as="geometry"/></mxCell>

    <!-- Queue 2 -->
    <mxCell id="q2" value="⏳ 4d wait&#xa;(sprint start queue)" style="triangle;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=9;direction=east;" vertex="1" parent="1">
      <mxGeometry x="355" y="170" width="50" height="40" as="geometry"/>
    </mxCell>

    <!-- Process 3: Development -->
    <mxCell id="p3" value="Development" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="420" y="160" width="100" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="p3d" value="CT: 2d&#xa;Uptime: 85%" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="420" y="225" width="100" height="30" as="geometry"/></mxCell>

    <!-- Queue 3 -->
    <mxCell id="q3" value="⏳ 2d wait&#xa;(PR review queue)" style="triangle;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=9;direction=east;" vertex="1" parent="1">
      <mxGeometry x="535" y="170" width="50" height="40" as="geometry"/>
    </mxCell>

    <!-- Process 4: Code Review -->
    <mxCell id="p4" value="Code Review" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="600" y="160" width="100" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="p4d" value="CT: 0.5d&#xa;Uptime: 80%" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="600" y="225" width="100" height="30" as="geometry"/></mxCell>

    <!-- Queue 4 -->
    <mxCell id="q4" value="⏳ 5d wait&#xa;(deploy approval)" style="triangle;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=9;direction=east;" vertex="1" parent="1">
      <mxGeometry x="715" y="170" width="50" height="40" as="geometry"/>
    </mxCell>

    <!-- Process 5: Deploy -->
    <mxCell id="p5" value="Deploy to Prod" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="600" y="70" width="100" height="50" as="geometry"/>
    </mxCell>

    <!-- Arrows -->
    <mxCell id="a1" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="p1" target="q1"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a2" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="q1" target="p2"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a3" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="p2" target="q2"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a4" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="q2" target="p3"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a5" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="p3" target="q3"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a6" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="q3" target="p4"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a7" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="p4" target="q4"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a8" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#333333;strokeWidth=2;" edge="1" parent="1" source="q4" target="p5"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="a9" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;" edge="1" parent="1" source="p5" target="cust"><mxGeometry relative="1" as="geometry"/></mxCell>

    <!-- Timeline bar -->
    <mxCell id="tl" value="Total Lead Time: 23 days  |  Value-Added Time: 3.5 days  |  Efficiency: 15%" style="text;html=1;strokeColor=none;fillColor=#FFCDD2;align=center;fontSize=11;fontStyle=1;rounded=1;strokeColor=#c62828;" vertex="1" parent="1">
      <mxGeometry x="60" y="280" width="800" height="30" as="geometry"/>
    </mxCell>

    <!-- Improvement opportunities -->
    <mxCell id="i1" value="🎯 Kaizen burst:&#xa;Automate deploy approval&#xa;(5d → 1d)" style="shape=mxgraph.lean_mapping.kaizen_lightning_burst;fillColor=#FFEB3B;strokeColor=#F9A825;fontSize=9;" vertex="1" parent="1">
      <mxGeometry x="700" y="100" width="70" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="i2" value="🎯 Kaizen burst:&#xa;Async PR review&#xa;(2d → 0.5d)" style="shape=mxgraph.lean_mapping.kaizen_lightning_burst;fillColor=#FFEB3B;strokeColor=#F9A825;fontSize=9;" vertex="1" parent="1">
      <mxGeometry x="530" y="100" width="70" height="60" as="geometry"/>
    </mxCell>

    <!-- Future state target -->
    <mxCell id="fs" value="Future State Target: Lead Time 8 days | Efficiency 44%" style="text;html=1;strokeColor=none;fillColor=#C8E6C9;align=center;fontSize=11;fontStyle=1;rounded=1;strokeColor=#2E7D32;" vertex="1" parent="1">
      <mxGeometry x="60" y="320" width="800" height="30" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Time Analysis

| Step | Cycle Time (VA) | Wait Time (NVA) | Notes |
|------|----------------|----------------|-------|
| Story Writing | 1.0d | — | Value-adding |
| Backlog queue | — | 3.0d | ⚠️ Waste |
| Sprint Planning | 0.5d | — | Necessary non-VA |
| Sprint queue | — | 4.0d | ⚠️ Waste |
| Development | 2.0d | — | ✅ Core value |
| PR review queue | — | 2.0d | ⚠️ Reduce via async |
| Code Review | 0.5d | — | Necessary non-VA |
| Deploy approval | — | **5.0d** | 🔴 Biggest waste |
| Deploy to Prod | 0.5d | — | Value-adding |
| **Total** | **4.5d** | **14d** | **15% efficiency** |

## Key Insight for Leaders

The **5-day deploy approval queue** is the single biggest bottleneck — a manual gate that can be replaced with an automated policy check. This is the first Kaizen target. The VSM makes this visible in a way that sprint velocity metrics cannot.
