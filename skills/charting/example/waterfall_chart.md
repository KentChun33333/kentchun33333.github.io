# Waterfall Chart — Example

## Scenario: SaaS Company Quarterly P&L Bridge

Walking from **Gross Revenue ($5.2M)** to **Net Income ($0.8M)** for Q2. Used in board meetings to explain margin compression vs. prior quarter.

---

## draw.io XML

Paste into draw.io → **Extras → Edit Diagram**

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="Q2 P&amp;L Waterfall (USD $000s)" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=15;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="10" y="10" width="700" height="36" as="geometry"/>
    </mxCell>
    <!-- Gross Revenue -->
    <mxCell id="10" value="$5,200" style="rounded=2;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="60" y="80" width="80" height="260" as="geometry"/>
    </mxCell>
    <mxCell id="11" value="Gross Revenue" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="50" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- COGS deduction -->
    <mxCell id="20" value="-$1,560" style="rounded=2;fillColor=#c62828;strokeColor=#b71c1c;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="180" y="158" width="80" height="78" as="geometry"/>
    </mxCell>
    <mxCell id="21" value="COGS" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="170" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- Gross Profit subtotal -->
    <mxCell id="30" value="$3,640" style="rounded=2;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="300" y="158" width="80" height="182" as="geometry"/>
    </mxCell>
    <mxCell id="31" value="Gross Profit" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="290" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- S&M -->
    <mxCell id="40" value="-$1,092" style="rounded=2;fillColor=#c62828;strokeColor=#b71c1c;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="420" y="213" width="80" height="55" as="geometry"/>
    </mxCell>
    <mxCell id="41" value="Sales &amp; Mktg" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="410" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- R&D -->
    <mxCell id="50" value="-$910" style="rounded=2;fillColor=#c62828;strokeColor=#b71c1c;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="540" y="259" width="80" height="45" as="geometry"/>
    </mxCell>
    <mxCell id="51" value="R&amp;D" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="530" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- Net Income -->
    <mxCell id="60" value="$838" style="rounded=2;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="660" y="300" width="80" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="61" value="Net Income" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1">
      <mxGeometry x="650" y="348" width="100" height="20" as="geometry"/>
    </mxCell>
    <!-- Legend -->
    <mxCell id="100" value="Increases/Totals" style="rounded=2;fillColor=#2E7D32;strokeColor=#1B5E20;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="60" y="390" width="130" height="28" as="geometry"/>
    </mxCell>
    <mxCell id="101" value="Decreases" style="rounded=2;fillColor=#c62828;strokeColor=#b71c1c;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="200" y="390" width="110" height="28" as="geometry"/>
    </mxCell>
    <mxCell id="102" value="Starting Value" style="rounded=2;fillColor=#1565C0;strokeColor=#0D47A1;fontColor=#ffffff;" vertex="1" parent="1">
      <mxGeometry x="320" y="390" width="120" height="28" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## P&L Summary Table

| Step | Value | % of Revenue |
|------|-------|-------------|
| Gross Revenue | $5,200K | 100% |
| – COGS | –$1,560K | 30% |
| = Gross Profit | $3,640K | **70%** |
| – Sales & Marketing | –$1,092K | 21% |
| – R&D | –$910K | 17.5% |
| – G&A | –$838K | 16.1% |
| = **Net Income** | **$800K** | **15.4%** |

## Key Insight for Leaders

The largest cost after COGS is **Sales & Marketing at 21%** — higher than R&D. This immediately prompts the board question: "Is our CAC improving, and when does S&M as % of revenue normalize?" The waterfall makes the cost conversation precise and fast.
