from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from app.clock import window
from app.feeds import canonical_url, clean_html, parse_feed, parse_published
from ai_service.classifier import classify
from conftest import DAY, entry, rss


def test_beijing_cutoff(env):
    start, end = window(DAY, env[0])
    assert start == datetime(2026,10,11,0,0)
    assert end == datetime(2026,10,12,0,0)


def test_window_excludes_end_and_missing_date(env, source):
    a=entry(published="Sun, 11 Oct 2026 00:00:00 +0000")
    b=entry(url="https://news.example/end",published="Mon, 12 Oct 2026 00:00:00 +0000")
    c=entry(url="https://news.example/missing"); c["published"]=None
    d=entry(url="https://news.example/old",published="Sat, 10 Oct 2026 23:59:59 +0000")
    rows, counts = parse_feed(rss([a,b,c,d]), source, *window(DAY,env[0]))
    assert len(rows)==1 and counts["skipped"]==3


def test_timezone_conversion_and_reject_ambiguous_date():
    assert parse_published("2026-10-12T07:59:59+08:00")==datetime(2026,10,11,23,59,59)
    assert parse_published("2026-10-12T08:00:00") is None
    assert parse_published("garbage") is None


def test_atom_feed(env,source):
    data=b'<feed xmlns="http://www.w3.org/2005/Atom"><title>Fixtures</title><entry><title>AI technology</title><link href="https://news.example/atom"/><published>2026-10-11T20:00:00Z</published><summary>Atom fixture excerpt</summary></entry></feed>'
    rows,_=parse_feed(data,source,*window(DAY,env[0]))
    assert len(rows)==1 and rows[0]["url"].endswith("/atom")


@pytest.mark.parametrize('url',["javascript:alert(1)","file:///tmp/news","https://user:pass@news.example/"])
def test_unsafe_links_rejected(url):
    with pytest.raises(ValueError): canonical_url(url)


def test_tracking_parameters_removed_without_losing_story_id():
    assert canonical_url("https://News.Example/a?id=12&utm_source=test#fragment")=="https://news.example/a?id=12"


def test_html_removed():
    assert clean_html("<p>Hello <b>world</b></p><script>steal()</script><style>p{}</style>")=="Hello world"


def test_html_error_page_and_entities_are_rejected(env,source):
    for data in (b'<html>Sign in</html>',b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss version="2.0"/>'):
        with pytest.raises(ValueError): parse_feed(data,source,*window(DAY,env[0]))


def test_region_by_subject_and_scope_exclusion():
    item={"title":"China announces new chip technology", "text_excerpt":"", "region_hint":"international", "category_hint":"technology"}
    assert classify(item)[:2]==("china","technology")
    assert classify({**item,"title":"Football final results","category_hint":"politics"})[1]=="other"
    assert classify({**item,"title":"美国美联储公布利率政策","region_hint":"china"})[:2]==("international","finance")
