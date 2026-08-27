# RACI Chart — Example

## Scenario: SaaS Product Release Process

A product team of 5 functions releases a new feature every 2 weeks. This RACI eliminates the recurring conflict between Engineering, Product, QA, and Marketing about who owns each step.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="RACI Chart — Feature Release Process" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="800" height="36" as="geometry"/>
    </mxCell>
    <!-- Header row -->
    <mxCell id="h0" value="Task / Activity" style="rounded=0;fillColor=#37474F;strokeColor=#263238;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="10" y="55" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="h1" value="Product Manager" style="rounded=0;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="210" y="55" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="h2" value="Engineering Lead" style="rounded=0;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="320" y="55" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="h3" value="QA Engineer" style="rounded=0;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="430" y="55" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="h4" value="Marketing" style="rounded=0;fillColor=#6A1B9A;strokeColor=#4A148C;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="540" y="55" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="h5" value="CEO / Exec" style="rounded=0;fillColor=#37474F;strokeColor=#263238;fontColor=#ffffff;fontStyle=1;fontSize=11;" vertex="1" parent="1"><mxGeometry x="650" y="55" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 1: Feature Specification -->
    <mxCell id="r1l" value="1. Feature Specification" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="95" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r1c1" value="A" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="95" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r1c2" value="C" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="95" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r1c3" value="C" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="95" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r1c4" value="I" style="rounded=0;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="540" y="95" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r1c5" value="I" style="rounded=0;fillColor=#ECEFF1;strokeColor=#607D8B;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="650" y="95" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 2: Technical Design -->
    <mxCell id="r2l" value="2. Technical Design &amp; Architecture" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FAFAFA;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="135" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r2c1" value="C" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="135" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r2c2" value="A R" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="135" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r2c3" value="C" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="135" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r2c4" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="540" y="135" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r2c5" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="650" y="135" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 3: Development -->
    <mxCell id="r3l" value="3. Development (Build)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="175" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r3c1" value="I" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="175" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r3c2" value="A R" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="175" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r3c3" value="I" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="175" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r3c4" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="540" y="175" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r3c5" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="650" y="175" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 4: QA Testing -->
    <mxCell id="r4l" value="4. QA Testing &amp; Signoff" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FAFAFA;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="215" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r4c1" value="C" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="215" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r4c2" value="R" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="215" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r4c3" value="A R" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="215" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r4c4" value="I" style="rounded=0;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="540" y="215" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r4c5" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="650" y="215" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 5: Release Approval -->
    <mxCell id="r5l" value="5. Release Approval / Go-No-Go" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="255" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r5c1" value="R" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="255" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r5c2" value="C" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="255" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r5c3" value="C" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="255" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r5c4" value="C" style="rounded=0;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="540" y="255" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r5c5" value="A" style="rounded=0;fillColor=#ECEFF1;strokeColor=#607D8B;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="650" y="255" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 6: Production Deploy -->
    <mxCell id="r6l" value="6. Production Deployment" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FAFAFA;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="295" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r6c1" value="I" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="295" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r6c2" value="A R" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="295" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r6c3" value="R" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="295" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r6c4" value="I" style="rounded=0;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="540" y="295" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r6c5" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="650" y="295" width="110" height="40" as="geometry"/></mxCell>

    <!-- Row 7: Customer Communication -->
    <mxCell id="r7l" value="7. Customer Communication &amp; Launch" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;fontSize=10;" vertex="1" parent="1"><mxGeometry x="10" y="335" width="200" height="40" as="geometry"/></mxCell>
    <mxCell id="r7c1" value="C" style="rounded=0;fillColor=#BBDEFB;strokeColor=#1565C0;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="210" y="335" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r7c2" value="I" style="rounded=0;fillColor=#C8E6C9;strokeColor=#2E7D32;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="320" y="335" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r7c3" value="I" style="rounded=0;fillColor=#FFE0B2;strokeColor=#E65100;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="430" y="335" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r7c4" value="A R" style="rounded=0;fillColor=#E1BEE7;strokeColor=#6A1B9A;fontStyle=1;fontSize=14;" vertex="1" parent="1"><mxGeometry x="540" y="335" width="110" height="40" as="geometry"/></mxCell>
    <mxCell id="r7c5" value="" style="rounded=0;fillColor=#F5F5F5;" vertex="1" parent="1"><mxGeometry x="650" y="335" width="110" height="40" as="geometry"/></mxCell>

    <!-- Legend -->
    <mxCell id="leg0" value="A = Accountable (one per task)  |  R = Responsible (does the work)  |  C = Consulted (input required)  |  I = Informed (notified of outcome)" style="text;html=1;strokeColor=none;fillColor=#F5F5F5;align=center;fontSize=10;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="390" width="760" height="28" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## RACI Summary Matrix

| Task | PM | Eng Lead | QA | Marketing | CEO |
|------|----|----------|----|-----------|-----|
| Feature Specification | **A** | C | C | I | I |
| Technical Design | C | **A/R** | C | — | — |
| Development | I | **A/R** | I | — | — |
| QA Testing | C | R | **A/R** | I | — |
| Release Approval | R | C | C | C | **A** |
| Production Deploy | I | **A/R** | R | I | — |
| Customer Launch | C | I | I | **A/R** | — |

## Key Insight for Leaders

Note **Release Approval (Row 5)**: the CEO is the sole **A** — meaning the final go/no-go rests with the executive. This prevents "engineering releasing without alignment." Also check: every task has exactly **one A**. If two people share accountability, escalations will stall and decisions will be delayed. The RACI is the first tool to reach for when you hear "I thought you were handling that."
