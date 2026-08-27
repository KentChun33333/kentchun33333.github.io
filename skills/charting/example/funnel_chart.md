# Funnel Chart — Example

## Scenario: B2B SaaS Sales Funnel — Q2 Pipeline Review

The VP of Sales presents the weekly pipeline funnel to show conversion rates at each stage and identify where deals are leaking.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="B2B SaaS Sales Funnel — Q2 Pipeline" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="760" height="36" as="geometry"/>
    </mxCell>
    <!-- Stage 1: All Leads -->
    <mxCell id="10" value="All Leads&#xa;2,400 | 100%" style="shape=mxgraph.lean_mapping.electronic_info_flow_edge;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="80" y="60" width="600" height="60" as="geometry"/>
    </mxCell>
    <!-- Conversion label -->
    <mxCell id="15" value="↓ 42% conversion" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontStyle=2;fontColor=#555555;" vertex="1" parent="1">
      <mxGeometry x="360" y="120" width="130" height="20" as="geometry"/>
    </mxCell>
    <!-- Stage 2: MQL -->
    <mxCell id="20" value="Marketing Qualified Leads (MQL)&#xa;1,008 | 42%" style="shape=mxgraph.lean_mapping.electronic_info_flow_edge;fillColor=#1976D2;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="130" y="140" width="500" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="25" value="↓ 35% conversion" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontStyle=2;fontColor=#555555;" vertex="1" parent="1">
      <mxGeometry x="360" y="200" width="130" height="20" as="geometry"/>
    </mxCell>
    <!-- Stage 3: SQL -->
    <mxCell id="30" value="Sales Qualified Leads (SQL)&#xa;353 | 35%" style="shape=mxgraph.lean_mapping.electronic_info_flow_edge;fillColor=#42A5F5;strokeColor=#1565C0;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="180" y="220" width="400" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="35" value="↓ 48% conversion" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontStyle=2;fontColor=#555555;" vertex="1" parent="1">
      <mxGeometry x="360" y="280" width="130" height="20" as="geometry"/>
    </mxCell>
    <!-- Stage 4: Proposal -->
    <mxCell id="40" value="Proposals Sent&#xa;170 | 48%" style="shape=mxgraph.lean_mapping.electronic_info_flow_edge;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="230" y="300" width="300" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="45" value="↓ 38% win rate" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontStyle=2;fontColor=#555555;" vertex="1" parent="1">
      <mxGeometry x="360" y="360" width="130" height="20" as="geometry"/>
    </mxCell>
    <!-- Stage 5: Closed Won -->
    <mxCell id="50" value="Closed Won&#xa;65 | 2.7% overall" style="shape=mxgraph.lean_mapping.electronic_info_flow_edge;fillColor=#388E3C;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="280" y="380" width="200" height="60" as="geometry"/>
    </mxCell>

    <!-- Annotation: biggest drop -->
    <mxCell id="60" value="⚠️ Biggest leak:&#xa;Lead → MQL (58% lost)&#xa;Action: Improve lead scoring" style="callout;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;fontStyle=0;" vertex="1" parent="1">
      <mxGeometry x="690" y="130" width="160" height="60" as="geometry"/>
    </mxCell>

    <!-- Annotation: win rate -->
    <mxCell id="61" value="✅ Win rate 38% is&#xa;above industry avg (25%)&#xa;Sales team performing well" style="callout;fillColor=#C8E6C9;strokeColor=#2E7D32;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="690" y="350" width="160" height="60" as="geometry"/>
    </mxCell>

    <!-- Metric summary -->
    <mxCell id="70" value="Overall funnel conversion: 2.7% | Avg deal size: $28K | Pipeline value: $1.82M" style="text;html=1;strokeColor=none;fillColor=#E8F5E9;align=center;fontSize=11;fontStyle=1;rounded=1;strokeColor=#2E7D32;" vertex="1" parent="1">
      <mxGeometry x="80" y="460" width="600" height="30" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Pipeline Conversion Table

| Stage | Count | Stage Conv. | Overall Conv. | Action |
|-------|-------|------------|--------------|--------|
| All Leads | 2,400 | — | 100% | Source quality review |
| MQL | 1,008 | 42% | 42% | ⚠️ Biggest drop — fix lead scoring |
| SQL | 353 | 35% | 15% | SDR handoff quality |
| Proposal | 170 | 48% | 7.1% | Proposal template optimization |
| **Closed Won** | **65** | **38%** | **2.7%** | ✅ Above industry benchmark |

## Key Insight for Leaders

The **MQL bottleneck** is the critical finding: 58% of leads never qualify, meaning the marketing team is generating volume but not quality. The immediate action is to **tighten lead scoring criteria** — not hire more SDRs. That decision would be invisible without the funnel chart.
