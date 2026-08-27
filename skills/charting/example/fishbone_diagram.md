# Fishbone / Ishikawa Diagram — Example

## Scenario: Customer Churn Spike Investigation

A SaaS company sees monthly churn jump from 2.1% to 4.8% in Q3. The leadership team runs a fishbone session to identify root causes before prescribing solutions.

**Effect (head)**: Customer Churn Rate increased from 2.1% → 4.8% in Q3

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Title -->
    <mxCell id="2" value="Fishbone Diagram — Customer Churn Spike Q3" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="860" height="36" as="geometry"/>
    </mxCell>
    <!-- Effect box (fish head) -->
    <mxCell id="10" value="EFFECT:&#xa;Churn 2.1% → 4.8%" style="rounded=1;fillColor=#c62828;strokeColor=#b71c1c;fontColor=#ffffff;fontStyle=1;fontSize=13;" vertex="1" parent="1">
      <mxGeometry x="710" y="270" width="140" height="60" as="geometry"/>
    </mxCell>
    <!-- Main spine -->
    <mxCell id="11" value="" style="edgeStyle=none;html=1;strokeColor=#333333;strokeWidth=3;exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;" edge="1" parent="1" source="10" target="10">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="700" y="300"/>
          <mxPoint x="50" y="300"/>
        </Array>
      </mxGeometry>
    </mxCell>
    <!-- Spine line explicit -->
    <mxCell id="12" value="" style="line;strokeColor=#333333;strokeWidth=3;" vertex="1" parent="1">
      <mxGeometry x="50" y="295" width="660" height="10" as="geometry"/>
    </mxCell>
    <!-- Arrow to head -->
    <mxCell id="13" value="" style="edgeStyle=none;html=1;strokeColor=#333333;strokeWidth=3;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" edge="1" parent="1" target="10">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="650" y="300" as="sourcePoint"/>
      </mxGeometry>
    </mxCell>

    <!-- CATEGORY 1: Product (top-left) -->
    <mxCell id="20" value="PRODUCT" style="rounded=1;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="60" y="140" width="110" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="21" value="" style="edgeStyle=none;html=1;strokeColor=#1565C0;strokeWidth=2;exitX=1;exitY=1;exitDx=0;exitDy=0;" edge="1" parent="1" source="20">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="200" y="300" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="22" value="Poor mobile UX" style="text;html=1;strokeColor=none;fillColor=#BBDEFB;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="70" y="195" width="110" height="25" as="geometry"/>
    </mxCell>
    <mxCell id="23" value="Missing integrations" style="text;html=1;strokeColor=none;fillColor=#BBDEFB;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="70" y="225" width="120" height="25" as="geometry"/>
    </mxCell>

    <!-- CATEGORY 2: Support (bottom-left) -->
    <mxCell id="30" value="SUPPORT" style="rounded=1;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="60" y="400" width="110" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="31" value="" style="edgeStyle=none;html=1;strokeColor=#2E7D32;strokeWidth=2;exitX=1;exitY=0;exitDx=0;exitDy=0;" edge="1" parent="1" source="30">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="200" y="300" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="32" value="Slow ticket resolution (3+ days)" style="text;html=1;strokeColor=none;fillColor=#C8E6C9;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="70" y="355" width="140" height="25" as="geometry"/>
    </mxCell>
    <mxCell id="33" value="No proactive CSM outreach" style="text;html=1;strokeColor=none;fillColor=#C8E6C9;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="70" y="445" width="140" height="25" as="geometry"/>
    </mxCell>

    <!-- CATEGORY 3: Pricing (top-center) -->
    <mxCell id="40" value="PRICING" style="rounded=1;fillColor=#E65100;strokeColor=#BF360C;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="280" y="110" width="110" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="41" value="" style="edgeStyle=none;html=1;strokeColor=#E65100;strokeWidth=2;exitX=1;exitY=1;exitDx=0;exitDy=0;" edge="1" parent="1" source="40">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="380" y="300" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="42" value="Price hike 20% in June" style="text;html=1;strokeColor=none;fillColor=#FFE0B2;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="280" y="160" width="120" height="25" as="geometry"/>
    </mxCell>
    <mxCell id="43" value="No grandfathering for early users" style="text;html=1;strokeColor=none;fillColor=#FFE0B2;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="280" y="190" width="140" height="25" as="geometry"/>
    </mxCell>

    <!-- CATEGORY 4: Onboarding (bottom-center) -->
    <mxCell id="50" value="ONBOARDING" style="rounded=1;fillColor=#6A1B9A;strokeColor=#4A148C;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="280" y="420" width="120" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="51" value="" style="edgeStyle=none;html=1;strokeColor=#6A1B9A;strokeWidth=2;exitX=1;exitY=0;exitDx=0;exitDy=0;" edge="1" parent="1" source="50">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="380" y="300" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="52" value="No in-app guidance for new users" style="text;html=1;strokeColor=none;fillColor=#E1BEE7;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="280" y="375" width="150" height="25" as="geometry"/>
    </mxCell>
    <mxCell id="53" value="Avg activation &gt;14 days" style="text;html=1;strokeColor=none;fillColor=#E1BEE7;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="280" y="465" width="130" height="25" as="geometry"/>
    </mxCell>

    <!-- CATEGORY 5: Competition (top-right) -->
    <mxCell id="60" value="COMPETITION" style="rounded=1;fillColor=#37474F;strokeColor=#263238;fontColor=#ffffff;fontStyle=1;fontSize=12;" vertex="1" parent="1">
      <mxGeometry x="500" y="120" width="120" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="61" value="" style="edgeStyle=none;html=1;strokeColor=#37474F;strokeWidth=2;exitX=1;exitY=1;exitDx=0;exitDy=0;" edge="1" parent="1" source="60">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="580" y="300" as="targetPoint"/>
      </mxGeometry>
    </mxCell>
    <mxCell id="62" value="Competitor launched free tier" style="text;html=1;strokeColor=none;fillColor=#ECEFF1;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="495" y="170" width="140" height="25" as="geometry"/>
    </mxCell>
    <mxCell id="63" value="Head-to-head features gap" style="text;html=1;strokeColor=none;fillColor=#ECEFF1;rounded=1;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="495" y="200" width="130" height="25" as="geometry"/>
    </mxCell>

    <!-- Priority annotation -->
    <mxCell id="70" value="⚠️ ROOT CAUSE #1&#xa;Price hike without&#xa;grandfathering" style="callout;fillColor=#FFCDD2;strokeColor=#c62828;fontSize=10;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="160" y="100" width="130" height="50" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## Root Cause Summary

| Category | Key Causes Found | Priority |
|----------|-----------------|----------|
| Pricing | 20% price hike, no grandfathering | 🔴 Critical |
| Competition | Free tier from competitor | 🔴 Critical |
| Support | 3+ day ticket SLA | 🟠 High |
| Product | Missing mobile features | 🟡 Medium |
| Onboarding | 14-day activation lag | 🟡 Medium |

## Key Insight for Leaders

The fishbone session reveals that **pricing and competitive response** are the immediate fires — not product quality. Without the diagram, the team would have defaulted to "let's ship more features." The chart re-focuses the conversation on the real lever: **immediate pricing relief for affected customers** while competitive strategy is planned.
