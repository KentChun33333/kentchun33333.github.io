# Gantt Chart — Example

## Scenario: SaaS Product Launch (Q3)

A product team is launching a new feature module in 8 weeks. The Gantt chart covers:
- Discovery & design (weeks 1–2)
- Development (weeks 2–5)
- QA testing (weeks 5–6)
- Staging & UAT (weeks 6–7)
- Go-live & hypercare (week 8)

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- Title -->
    <mxCell id="2" value="Q3 Product Launch — Gantt Chart" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=16;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="760" height="40" as="geometry"/>
    </mxCell>

    <!-- Header Row -->
    <mxCell id="10" value="Task" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="60" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="11" value="Owner" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="60" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="12" value="W1" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="250" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="13" value="W2" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="310" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="14" value="W3" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="370" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="15" value="W4" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="430" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="16" value="W5" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="490" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="17" value="W6" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="550" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="18" value="W7" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="610" y="60" width="60" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="19" value="W8" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="670" y="60" width="60" height="30" as="geometry"/>
    </mxCell>

    <!-- Row 1: Discovery -->
    <mxCell id="20" value="Discovery &amp; Requirements" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="90" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="21" value="PM" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="90" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="22" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#00BCD4;strokeColor=#006EAF;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="250" y="95" width="120" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 2: UI Design -->
    <mxCell id="30" value="UI/UX Design" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="120" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="31" value="Design" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="120" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="32" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#9C27B0;strokeColor=#6a1a9a;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="310" y="125" width="120" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 3: Development -->
    <mxCell id="40" value="Backend Development" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="150" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="41" value="Dev" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="150" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="42" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#4CAF50;strokeColor=#2E7D32;" vertex="1" parent="1">
      <mxGeometry x="370" y="155" width="180" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 4: Frontend -->
    <mxCell id="50" value="Frontend Development" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="180" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="51" value="Dev" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="180" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="52" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#4CAF50;strokeColor=#2E7D32;" vertex="1" parent="1">
      <mxGeometry x="430" y="185" width="120" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 5: QA -->
    <mxCell id="60" value="QA Testing" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="210" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="61" value="QA" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="210" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="62" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#FF9800;strokeColor=#E65100;" vertex="1" parent="1">
      <mxGeometry x="490" y="215" width="120" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 6: UAT -->
    <mxCell id="70" value="Staging &amp; UAT" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="240" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="71" value="PM/QA" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="240" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="72" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#FF9800;strokeColor=#E65100;" vertex="1" parent="1">
      <mxGeometry x="610" y="245" width="60" height="20" as="geometry"/>
    </mxCell>

    <!-- Row 7: Go-Live -->
    <mxCell id="80" value="Go-Live &amp; Hypercare" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="270" width="160" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="81" value="All" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="170" y="270" width="80" height="30" as="geometry"/>
    </mxCell>
    <mxCell id="82" value="" style="rounded=4;whiteSpace=wrap;html=1;fillColor=#f44336;strokeColor=#b71c1c;" vertex="1" parent="1">
      <mxGeometry x="670" y="275" width="60" height="20" as="geometry"/>
    </mxCell>

    <!-- Milestone: Go-Live -->
    <mxCell id="90" value="🚀 Go-Live" style="rhombus;whiteSpace=wrap;html=1;fillColor=#f44336;strokeColor=#b71c1c;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="675" y="305" width="50" height="30" as="geometry"/>
    </mxCell>

    <!-- Legend -->
    <mxCell id="100" value="Legend:" style="text;html=1;strokeColor=none;fillColor=none;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="360" width="60" height="20" as="geometry"/>
    </mxCell>
    <mxCell id="101" value="Planning" style="rounded=4;fillColor=#00BCD4;strokeColor=#006EAF;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="80" y="358" width="80" height="24" as="geometry"/>
    </mxCell>
    <mxCell id="102" value="Design" style="rounded=4;fillColor=#9C27B0;strokeColor=#6a1a9a;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="170" y="358" width="80" height="24" as="geometry"/>
    </mxCell>
    <mxCell id="103" value="Development" style="rounded=4;fillColor=#4CAF50;strokeColor=#2E7D32;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="260" y="358" width="100" height="24" as="geometry"/>
    </mxCell>
    <mxCell id="104" value="QA / UAT" style="rounded=4;fillColor=#FF9800;strokeColor=#E65100;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="370" y="358" width="80" height="24" as="geometry"/>
    </mxCell>
    <mxCell id="105" value="Launch" style="rounded=4;fillColor=#f44336;strokeColor=#b71c1c;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="460" y="358" width="80" height="24" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Reading the Chart

- **Cyan bar** (W1–W2): PM leads discovery — no dev dependency yet
- **Purple bar** (W2–W3): Design overlaps with late discovery to compress timeline
- **Green bars** (W3–W6): Backend starts before frontend (API-first approach)
- **Orange bars** (W5–W7): QA begins while frontend is still completing (shift-left testing)
- **Red bar + milestone** (W8): Go-live with hypercare team on standby

## Key Insight for Leaders

The overlapping bars reveal **parallel-tracking** — a 40% timeline compression vs. sequential execution. When you see a flat block with no parallelism, that's where you ask: "Does this really need to wait?"
