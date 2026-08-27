# Burndown Chart — Example

## Scenario: 2-Week Agile Sprint (Mobile App Feature Release)

A development team of 6 commits to 80 story points for a 2-week sprint. The burndown chart tracks daily progress against the ideal line and surfaces a mid-sprint blocker.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="Sprint 12 Burndown Chart — Mobile App v2.1" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="700" height="36" as="geometry"/>
    </mxCell>
    <!-- Y-axis label -->
    <mxCell id="3" value="Story Points Remaining" style="text;html=1;strokeColor=none;fillColor=none;rotation=-90;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="-20" y="280" width="160" height="20" as="geometry"/>
    </mxCell>
    <!-- X-axis label -->
    <mxCell id="4" value="Sprint Days (Day 1 → Day 10)" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=11;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="100" y="540" width="500" height="20" as="geometry"/>
    </mxCell>

    <!-- Grid lines (horizontal) -->
    <mxCell id="h1" value="80" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="75" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="h2" value="60" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="165" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="h3" value="40" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="255" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="h4" value="20" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="345" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="h5" value="0" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="30" y="435" width="30" height="15" as="geometry"/></mxCell>

    <!-- X-axis day labels -->
    <mxCell id="d1" value="D1" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="65" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d2" value="D2" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="115" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d3" value="D3" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="165" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d4" value="D4" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="215" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d5" value="D5" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="265" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d6" value="D6" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="315" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d7" value="D7" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="365" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d8" value="D8" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="415" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d9" value="D9" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="465" y="460" width="30" height="15" as="geometry"/></mxCell>
    <mxCell id="d10" value="D10" style="text;html=1;strokeColor=none;fillColor=none;fontSize=10;" vertex="1" parent="1"><mxGeometry x="510" y="460" width="30" height="15" as="geometry"/></mxCell>

    <!-- IDEAL LINE (dashed grey): D1=80 → D10=0 -->
    <mxCell id="100" value="" style="edgeStyle=none;html=1;strokeColor=#9E9E9E;strokeWidth=2;dashed=1;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="80" y="82" as="sourcePoint"/>
        <mxPoint x="530" y="442" as="targetPoint"/>
      </mxGeometry>
    </mxCell>

    <!-- ACTUAL LINE (solid blue): D1=80, D2=72, D3=65, D4=63, D5=63 (BLOCKED), D6=55, D7=40, D8=28, D9=15, D10=8 -->
    <mxCell id="200" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="80" y="82" as="sourcePoint"/>
        <mxPoint x="130" y="118" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="201" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="130" y="118" as="sourcePoint"/>
        <mxPoint x="180" y="150" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="202" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="180" y="150" as="sourcePoint"/>
        <mxPoint x="230" y="159" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <!-- Flat line D4-D5: BLOCKED -->
    <mxCell id="203" value="" style="edgeStyle=none;html=1;strokeColor=#c62828;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="230" y="159" as="sourcePoint"/>
        <mxPoint x="280" y="159" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="204" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="280" y="159" as="sourcePoint"/>
        <mxPoint x="330" y="195" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="205" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="330" y="195" as="sourcePoint"/>
        <mxPoint x="380" y="262" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="206" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="380" y="262" as="sourcePoint"/>
        <mxPoint x="430" y="316" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="207" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="430" y="316" as="sourcePoint"/>
        <mxPoint x="480" y="370" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="208" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=3;endArrow=none;" edge="1" parent="1">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="480" y="370" as="sourcePoint"/>
        <mxPoint x="530" y="407" as="targetPoint"/>
      </mxGeometry>
    </mxCell>

    <!-- Blocker annotation -->
    <mxCell id="300" value="🚫 BLOCKED D4–D5&#xa;API dependency on infra team&#xa;8 pts not burned" style="callout;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="240" y="80" width="160" height="60" as="geometry"/>
    </mxCell>

    <!-- End state annotation -->
    <mxCell id="301" value="Sprint end: 8 pts remaining&#xa;Velocity: 72 pts/sprint&#xa;Carry-over to Sprint 13" style="callout;fillColor=#FFF9C4;strokeColor=#F9A825;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="550" y="390" width="160" height="55" as="geometry"/>
    </mxCell>

    <!-- Legend -->
    <mxCell id="400" value="— Ideal" style="text;html=1;strokeColor=#9E9E9E;strokeWidth=2;dashed=1;fillColor=none;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="80" y="490" width="80" height="20" as="geometry"/>
    </mxCell>
    <mxCell id="401" value="— Actual" style="text;html=1;strokeColor=#1565C0;strokeWidth=3;fillColor=none;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="170" y="490" width="80" height="20" as="geometry"/>
    </mxCell>
    <mxCell id="402" value="— Blocked" style="text;html=1;strokeColor=#c62828;strokeWidth=3;fillColor=none;fontSize=11;" vertex="1" parent="1">
      <mxGeometry x="260" y="490" width="90" height="20" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Daily Burndown Data

| Day | Ideal Remaining | Actual Remaining | Status |
|-----|----------------|-----------------|--------|
| Start | 80 | 80 | On track |
| D2 | 72 | 72 | On track |
| D3 | 64 | 65 | Slightly behind |
| D4 | 56 | 63 | Behind |
| D5 | 48 | **63** | 🔴 Blocked — flat line |
| D6 | 40 | 55 | Recovering |
| D7 | 32 | 40 | Catching up |
| D8 | 24 | 28 | Near track |
| D9 | 16 | 15 | Ahead |
| D10 | 0 | **8** | 8 pts carry-over |

## Key Insight for Leaders

The **flat red segment on D4–D5** is the most important signal. Without a burndown, this blocker would be invisible until the sprint review. The chart gives the PM a trigger to **escalate the API dependency on Day 4** — potentially saving the sprint. Sprint velocity = 72 pts; the 8-pt carryover is a clean input for Sprint 13 planning.
