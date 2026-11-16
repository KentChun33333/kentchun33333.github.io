from bs4 import BeautifulSoup

from kent_webio.markdown import render_markdown


def test_chat_markdown_formats_text_and_preserves_code():
    markup = render_markdown("""# 報告

**粗體** 與 *斜體* 以及 `value`

1. 第一項
2. 第二項

> 備註

```html
<strong>Literal & text</strong>
```

| 項目 | 數量 |
| --- | --- |
| 文件 | 2 |
""")
    soup = BeautifulSoup(markup, "html.parser")
    assert soup.h1.text == "報告"
    assert soup.strong.text == "粗體"
    assert soup.em.text == "斜體"
    assert [item.text for item in soup.ol.find_all("li")] == ["第一項", "第二項"]
    assert soup.blockquote.get_text(strip=True) == "備註"
    assert soup.pre.code.text.strip() == "<strong>Literal & text</strong>"
    assert soup.table.td.text == "文件"


def test_chat_markdown_only_creates_safe_links_and_keeps_html_literal():
    markup = render_markdown("""<button>literal text</button>

[reference](https://example.invalid/path)
[unsupported](data:text/plain,example)
[relative](/api/state)
![caption](https://example.invalid/image.png)
""")
    soup = BeautifulSoup(markup, "html.parser")
    assert soup.button is None and soup.img is None
    assert "<button>literal text</button>" in soup.get_text()
    assert "caption" in soup.get_text()
    assert [link["href"] for link in soup.find_all("a")] == ["https://example.invalid/path"]
    assert soup.a["target"] == "_blank"
    assert soup.a["rel"] == ["noopener", "noreferrer"]
