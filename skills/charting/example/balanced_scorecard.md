# Balanced Scorecard Map — Example

## Scenario: B2B SaaS Company Annual Strategy Map

Linking the company vision ("Become the #1 workflow automation platform for mid-market") across all four BSC perspectives with cause-and-effect arrows.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="Balanced Scorecard — B2B SaaS Strategy Map" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="860" height="36" as="geometry"/>
    </mxCell>
    <!-- FINANCIAL perspective header -->
    <mxCell id="10" value="FINANCIAL" style="rounded=1;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=13;" vertex="1" parent="1">
      <mxGeometry x="10" y="60" width="120" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="11" value="Grow ARR to $50M" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="150" y="65" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="12" value="Achieve 20% Net Margin" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="330" y="65" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="13" value="Expand NRR to 120%" style="rounded=1;fillColor=#BBDEFB;strokeColor=#1565C0;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="510" y="65" width="160" height="50" as="geometry"/>
    </mxCell>
    <!-- CUSTOMER perspective header -->
    <mxCell id="20" value="CUSTOMER" style="rounded=1;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=13;" vertex="1" parent="1">
      <mxGeometry x="10" y="200" width="120" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="21" value="Achieve NPS &gt; 60" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="150" y="205" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="22" value="Reduce Churn to &lt;5%" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="330" y="205" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="23" value="Grow Enterprise Accounts 40%" style="rounded=1;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="510" y="205" width="160" height="50" as="geometry"/>
    </mxCell>
    <!-- INTERNAL PROCESS perspective header -->
    <mxCell id="30" value="INTERNAL PROCESS" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="10" y="340" width="120" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="31" value="Ship 2 major features/quarter" style="rounded=1;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="150" y="345" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="32" value="Achieve 99.9% uptime SLA" style="rounded=1;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="330" y="345" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="33" value="Reduce onboarding time to &lt;7 days" style="rounded=1;fillColor=#FFE0B2;strokeColor=#E65100;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="510" y="345" width="160" height="50" as="geometry"/>
    </mxCell>
    <!-- LEARNING & GROWTH perspective header -->
    <mxCell id="40" value="LEARNING &amp; GROWTH" style="rounded=1;fillColor=#6A1B9A;strokeColor=#4A148C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="10" y="480" width="120" height="120" as="geometry"/>
    </mxCell>
    <mxCell id="41" value="Hire 20 engineers by Q3" style="rounded=1;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="150" y="485" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="42" value="Launch internal AI upskilling program" style="rounded=1;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="330" y="485" width="160" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="43" value="Achieve eNPS &gt; 50" style="rounded=1;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="510" y="485" width="160" height="50" as="geometry"/>
    </mxCell>
    <!-- Cause-effect arrows (Learning → Internal) -->
    <mxCell id="50" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#6A1B9A;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="41" target="31">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <mxCell id="51" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#6A1B9A;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="42" target="32">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Cause-effect arrows (Internal → Customer) -->
    <mxCell id="52" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="31" target="21">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <mxCell id="53" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#E65100;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="33" target="22">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Cause-effect arrows (Customer → Financial) -->
    <mxCell id="54" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="22" target="13">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <mxCell id="55" value="" style="edgeStyle=orthogonalEdgeStyle;html=1;strokeColor=#2E7D32;strokeWidth=2;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;" edge="1" parent="1" source="23" target="11">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Strategy Map Reading Guide

| Perspective | Focus | Example KPIs |
|-------------|-------|-------------|
| **Financial** | Shareholder value | ARR, Net Margin, NRR |
| **Customer** | Value delivered | NPS, Churn Rate, Enterprise accounts |
| **Internal Process** | Operational excellence | Feature velocity, SLA uptime, Onboarding time |
| **Learning & Growth** | Organizational capability | Headcount, Skills training, eNPS |

## Key Insight for Leaders

The **arrows** are the strategy. They say: "If we hire more engineers (Learning) → we ship faster (Internal) → customers are happier (Customer) → NRR improves → ARR grows (Financial)." Without the arrows, it's just a KPI list.
