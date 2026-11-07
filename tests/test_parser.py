import pytest

from crawler.parser import parse_html

BASE = "http://site.test/dir/page"


def test_title_and_visible_text():
    parsed = parse_html(BASE, "<html><head><title> My  Page </title></head><body><p>Hello</p><p>world</p></body></html>")
    assert parsed.title == "My Page"
    assert parsed.text == "Hello world"


def test_hidden_content_is_ignored():
    html = """
    <body>seen
      <script>var hiddenscript = 1;</script>
      <style>.hiddenstyle {}</style>
      <noscript>hiddennoscript</noscript>
      <template>hiddentemplate</template>
      <svg><title>hiddensvg</title><text>hiddensvgtext</text></svg>
      also seen
    </body>"""
    parsed = parse_html(BASE, html)
    assert parsed.text == "seen also seen"
    assert parsed.title == ""


def test_self_closing_svg_does_not_hide_the_rest():
    assert parse_html(BASE, "<svg/><p>visible</p>").text == "visible"


@pytest.mark.parametrize("tag", ["p", "div", "li", "td", "h1", "section", "header", "footer", "nav", "main", "aside", "blockquote"])
def test_block_elements_separate_words(tag):
    assert parse_html(BASE, f"<{tag}>first</{tag}><{tag}>second</{tag}>").text == "first second"


def test_links_side_by_side_are_separate_words():
    assert parse_html(BASE, '<a href="/a">Home</a><a href="/b">About</a>').text == "Home About"


def test_inline_elements_do_not_split_a_word():
    assert parse_html(BASE, "<p>un<b>believ</b>able</p>").text == "unbelievable"


def test_entities_are_decoded():
    assert parse_html(BASE, "<title>A &amp; B</title><p>T&uuml;rkiye&nbsp;&#304;stanbul</p>").text == "Türkiye İstanbul"


def test_links_are_resolved_cleaned_and_unique():
    html = """
    <a href="/a">1</a><a href="/a#top">2</a><a href="b">3</a>
    <a href="mailto:x@y.test">4</a><a href="javascript:void(0)">5</a><a href="http://[broken/">6</a><a>7</a>
    <a href="/my page">8</a>
    """
    assert parse_html(BASE, html).links == [
        "http://site.test/a",
        "http://site.test/dir/b",
        "http://site.test/my%20page",
    ]


def test_base_tag_changes_where_links_resolve():
    html = '<head><base href="http://site.test/other/"></head><a href="x">1</a>'
    assert parse_html(BASE, html).links == ["http://site.test/other/x"]


def test_nofollow_links_are_not_followed():
    html = '<a href="/yes">1</a><a href="/no" rel="nofollow">2</a><a href="/no2" rel="noopener NoFollow">3</a>'
    assert parse_html(BASE, html).links == ["http://site.test/yes"]


def test_canonical_is_read():
    assert parse_html(BASE, '<link rel="canonical" href="/real">').canonical == "http://site.test/real"
    assert parse_html(BASE, '<link rel="stylesheet" href="/x.css">').canonical is None


@pytest.mark.parametrize(
    "content, noindex, nofollow",
    [
        ("noindex", True, False),
        ("nofollow", False, True),
        ("noindex, nofollow", True, True),
        ("NONE", True, True),
        ("index, follow", False, False),
    ],
)
def test_meta_robots(content, noindex, nofollow):
    parsed = parse_html(BASE, f'<meta name="robots" content="{content}">')
    assert (parsed.noindex, parsed.nofollow) == (noindex, nofollow)


def test_meta_for_another_crawler_is_ignored():
    assert parse_html(BASE, '<meta name="googlebot" content="noindex">').noindex is False


def test_rules_addressed_to_this_crawler_count():
    assert parse_html(BASE, '<meta name="MiniGoogleCrawler" content="noindex">').noindex is True


@pytest.mark.parametrize(
    "html",
    [
        "<p>unclosed <b>tags <i>everywhere",
        "</div></div>text",
        "<![foo[ broken section ]]><p>text</p>",
        "<![if IE]>text<![endif]>",
        "<!doctype><p>text",
        "<a href=>empty</a>",
        "<title>never closed",
        '<a href="http://[::1">x</a>',
        "\x00\x01 binary \xff garbage",
    ],
)
def test_broken_html_never_raises(html):
    parse_html(BASE, html)


def test_text_before_a_broken_section_is_kept():
    assert "kept" in parse_html(BASE, "<p>kept</p><![foo[ x ]]>").text
