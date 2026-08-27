# Heat Map — Example

## Scenario: Enterprise Risk Register (IT Security Audit)

The CISO presents a 5×5 risk heat map to the board covering the top 12 identified cybersecurity risks, scored by likelihood and business impact.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="IT Security Risk Heat Map — Q3 Audit" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="700" height="36" as="geometry"/>
    </mxCell>
    <!-- Y-axis label -->
    <mxCell id="3" value="Likelihood ▲" style="text;html=1;strokeColor=none;fillColor=none;rotation=-90;fontSize=12;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="-20" y="340" width="120" height="20" as="geometry"/>
    </mxCell>
    <!-- X-axis label -->
    <mxCell id="4" value="Business Impact ▶" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=12;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="70" y="575" width="560" height="20" as="geometry"/>
    </mxCell>

    <!-- Row/Col headers -->
    <mxCell id="h1" value="5\n(Almost Certain)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=right;" vertex="1" parent="1"><mxGeometry x="5" y="75" width="55" height="80" as="geometry"/></mxCell>
    <mxCell id="h2" value="4\n(Likely)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=right;" vertex="1" parent="1"><mxGeometry x="5" y="155" width="55" height="80" as="geometry"/></mxCell>
    <mxCell id="h3" value="3\n(Possible)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=right;" vertex="1" parent="1"><mxGeometry x="5" y="235" width="55" height="80" as="geometry"/></mxCell>
    <mxCell id="h4" value="2\n(Unlikely)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=right;" vertex="1" parent="1"><mxGeometry x="5" y="315" width="55" height="80" as="geometry"/></mxCell>
    <mxCell id="h5" value="1\n(Rare)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=right;" vertex="1" parent="1"><mxGeometry x="5" y="395" width="55" height="80" as="geometry"/></mxCell>

    <mxCell id="c1" value="1\nMinor" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=center;" vertex="1" parent="1"><mxGeometry x="60" y="475" width="80" height="30" as="geometry"/></mxCell>
    <mxCell id="c2" value="2\nModerate" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=center;" vertex="1" parent="1"><mxGeometry x="140" y="475" width="80" height="30" as="geometry"/></mxCell>
    <mxCell id="c3" value="3\nSignificant" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=center;" vertex="1" parent="1"><mxGeometry x="220" y="475" width="80" height="30" as="geometry"/></mxCell>
    <mxCell id="c4" value="4\nMajor" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=center;" vertex="1" parent="1"><mxGeometry x="300" y="475" width="80" height="30" as="geometry"/></mxCell>
    <mxCell id="c5" value="5\nCritical" style="text;html=1;strokeColor=none;fillColor=none;fontSize=9;align=center;" vertex="1" parent="1"><mxGeometry x="380" y="475" width="80" height="30" as="geometry"/></mxCell>

    <!-- Grid cells: 5x5 -->
    <!-- Row 5 (Almost Certain) -->
    <mxCell id="r5c1" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="60" y="75" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r5c2" value="" style="fillColor=#FFCC80;strokeColor=#E65100;" vertex="1" parent="1"><mxGeometry x="140" y="75" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r5c3" value="" style="fillColor=#EF9A9A;strokeColor=#c62828;" vertex="1" parent="1"><mxGeometry x="220" y="75" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r5c4" value="" style="fillColor=#EF5350;strokeColor=#b71c1c;" vertex="1" parent="1"><mxGeometry x="300" y="75" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r5c5" value="" style="fillColor=#B71C1C;strokeColor=#7f0000;" vertex="1" parent="1"><mxGeometry x="380" y="75" width="80" height="80" as="geometry"/></mxCell>
    <!-- Row 4 (Likely) -->
    <mxCell id="r4c1" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="60" y="155" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r4c2" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="140" y="155" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r4c3" value="" style="fillColor=#FFCC80;strokeColor=#E65100;" vertex="1" parent="1"><mxGeometry x="220" y="155" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r4c4" value="" style="fillColor=#EF9A9A;strokeColor=#c62828;" vertex="1" parent="1"><mxGeometry x="300" y="155" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r4c5" value="" style="fillColor=#EF5350;strokeColor=#b71c1c;" vertex="1" parent="1"><mxGeometry x="380" y="155" width="80" height="80" as="geometry"/></mxCell>
    <!-- Row 3 (Possible) -->
    <mxCell id="r3c1" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="60" y="235" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r3c2" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="140" y="235" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r3c3" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="220" y="235" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r3c4" value="" style="fillColor=#FFCC80;strokeColor=#E65100;" vertex="1" parent="1"><mxGeometry x="300" y="235" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r3c5" value="" style="fillColor=#EF9A9A;strokeColor=#c62828;" vertex="1" parent="1"><mxGeometry x="380" y="235" width="80" height="80" as="geometry"/></mxCell>
    <!-- Row 2 (Unlikely) -->
    <mxCell id="r2c1" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="60" y="315" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r2c2" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="140" y="315" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r2c3" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="220" y="315" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r2c4" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="300" y="315" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r2c5" value="" style="fillColor=#FFCC80;strokeColor=#E65100;" vertex="1" parent="1"><mxGeometry x="380" y="315" width="80" height="80" as="geometry"/></mxCell>
    <!-- Row 1 (Rare) -->
    <mxCell id="r1c1" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="60" y="395" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r1c2" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="140" y="395" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r1c3" value="" style="fillColor=#F1F8E9;strokeColor=#558B2F;" vertex="1" parent="1"><mxGeometry x="220" y="395" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r1c4" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="300" y="395" width="80" height="80" as="geometry"/></mxCell>
    <mxCell id="r1c5" value="" style="fillColor=#FFF9C4;strokeColor=#F9A825;" vertex="1" parent="1"><mxGeometry x="380" y="395" width="80" height="80" as="geometry"/></mxCell>

    <!-- Risk items plotted -->
    <mxCell id="risk1" value="R1: Phishing\n(5,4)" style="ellipse;fillColor=#B71C1C;strokeColor=#7f0000;fontColor=#ffffff;fontSize=9;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="310" y="82" width="60" height="38" as="geometry"/></mxCell>
    <mxCell id="risk2" value="R2: Ransomware\n(4,5)" style="ellipse;fillColor=#EF5350;strokeColor=#b71c1c;fontColor=#ffffff;fontSize=9;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="388" y="163" width="64" height="38" as="geometry"/></mxCell>
    <mxCell id="risk3" value="R3: SQL Inject\n(3,4)" style="ellipse;fillColor=#FFCC80;strokeColor=#E65100;fontColor=#333333;fontSize=9;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="305" y="248" width="65" height="38" as="geometry"/></mxCell>
    <mxCell id="risk4" value="R4: Data Leak\n(4,3)" style="ellipse;fillColor=#FFCC80;strokeColor=#E65100;fontColor=#333333;fontSize=9;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="225" y="163" width="65" height="38" as="geometry"/></mxCell>
    <mxCell id="risk5" value="R5: DDoS\n(2,5)" style="ellipse;fillColor=#FFCC80;strokeColor=#E65100;fontColor=#333333;fontSize=9;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="388" y="323" width="60" height="38" as="geometry"/></mxCell>
    <mxCell id="risk6" value="R6: Insider\n(3,3)" style="ellipse;fillColor=#FFF9C4;strokeColor=#F9A825;fontColor=#333333;fontSize=9;" vertex="1" parent="1"><mxGeometry x="228" y="248" width="60" height="38" as="geometry"/></mxCell>

    <!-- Legend -->
    <mxCell id="leg1" value="🔴 Critical (score 15-25)" style="text;html=1;strokeColor=none;fillColor=#B71C1C;fontColor=#ffffff;rounded=1;fontSize=10;" vertex="1" parent="1"><mxGeometry x="470" y="85" width="170" height="25" as="geometry"/></mxCell>
    <mxCell id="leg2" value="🟠 High (score 8-14)" style="text;html=1;strokeColor=none;fillColor=#EF9A9A;fontColor=#333333;rounded=1;fontSize=10;" vertex="1" parent="1"><mxGeometry x="470" y="118" width="170" height="25" as="geometry"/></mxCell>
    <mxCell id="leg3" value="🟡 Medium (score 4-7)" style="text;html=1;strokeColor=none;fillColor=#FFF9C4;fontColor=#333333;rounded=1;fontSize=10;" vertex="1" parent="1"><mxGeometry x="470" y="151" width="170" height="25" as="geometry"/></mxCell>
    <mxCell id="leg4" value="🟢 Low (score 1-3)" style="text;html=1;strokeColor=none;fillColor=#C8E6C9;fontColor=#333333;rounded=1;fontSize=10;" vertex="1" parent="1"><mxGeometry x="470" y="184" width="170" height="25" as="geometry"/></mxCell>
  </root>
</mxGraphModel>
```

---

## Risk Register Table

| ID | Risk | Likelihood | Impact | Score | Status |
|----|------|-----------|--------|-------|--------|
| R1 | Phishing / Social Engineering | 5 | 4 | **20** 🔴 | Immediate action |
| R2 | Ransomware Attack | 4 | 5 | **20** 🔴 | Immediate action |
| R3 | SQL Injection via legacy app | 3 | 4 | **12** 🟠 | Q3 remediation plan |
| R4 | Sensitive Data Leak | 4 | 3 | **12** 🟠 | DLP tool evaluation |
| R5 | DDoS attack on API | 2 | 5 | **10** 🟠 | CDN + rate limiting |
| R6 | Insider Threat | 3 | 3 | **9** 🟠 | Access review audit |

## Key Insight for Leaders

The heat map instantly shows the **top-right corner** as the board's focus area. R1 and R2 (Phishing + Ransomware) are in the critical zone — these are the agenda items that need budget and a decision, not just monitoring. Everything in the green zone can be handled at the operational level without board involvement.
