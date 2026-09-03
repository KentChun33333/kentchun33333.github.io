# Core thought model

TimesFM-3 turns a multivariate forecast into masked grid completion. Time runs across columns and related series run down rows. Past observations occupy the left side of the grid; target and past-only future cells are masked; genuinely known future signals remain visible. Alternating attention answers two different questions: “what in this series' past matters?” and “what do the other series say at this time?” The final representation fills the target horizon simultaneously.

This is the canonical mechanism explanation. The website should link all component descriptions back to it rather than repeat it.
