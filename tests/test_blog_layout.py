import datetime as dt
import unittest
from unittest.mock import patch
from starlette.requests import Request
from app import blog_layout, site

NOW = dt.datetime(2026, 11, 19, tzinfo=dt.timezone.utc)
def post(slug, title, status="published", published="2026-11-18T12:00:00+00:00"):
    return dict(slug=slug, title=title, status=status, published=published, updated="2026-11-19T10:00:00+00:00", author="EstateHawk", body="## Scope\nText.\n\n## Scope\nMore.\n\n### Next question\nAnswer.", description="Records guide", excerpt="", hero_image="", hero_alt="")

class BlogLayoutTests(unittest.TestCase):
    def test_duplicate_and_escaped_heading_anchors(self):
        rendered = '<h2>Scope &amp; facts</h2><p>Body</p><h2>Scope &amp; facts</h2><h3>Next?</h3>'
        body, headings, minutes = blog_layout.article_body(rendered)
        self.assertEqual([h[1] for h in headings], ['section-scope-facts', 'section-scope-facts-2', 'section-next'])
        self.assertIn('Scope &amp; facts', body)
        self.assertEqual(minutes, 1)
        _, collision, _ = blog_layout.article_body("<h2>Scope</h2><h2>Scope 2</h2><h2>Scope</h2>")
        self.assertEqual(len(set(h[1] for h in collision)), 3)

    def test_related_excludes_self_draft_future_unrelated_and_caps_three(self):
        current = post('quiet-title', 'Quiet Title Action')
        rows = [current, post('draft','Municipal Lien Search','draft'), post('future','Title Search','published','2099-01-01T00:00:00+00:00'), post('no-date','Title Search',published=None), post('unrelated','Real Estate Lead Follow Up')]
        rows += [post('match-'+str(i),'Municipal Lien Search '+str(i)) for i in range(5)]
        selected = blog_layout.related(current, rows, NOW)
        self.assertEqual(len(selected), 3)
        self.assertTrue(all(x['slug'].startswith('match-') for x in selected))
        self.assertEqual(blog_layout.related(current, [current], NOW), [])
        self.assertEqual(blog_layout.related(current, [post('x','Real Estate Investing Guide')], NOW), [])

    def test_template_recomputes_related_when_publication_changes(self):
        current = post('quiet-title','Quiet Title Action',status='draft',published=None)
        candidate = post('municipal','Municipal Lien Search')
        request = Request(dict(type='http',method='GET',path='/blog/quiet-title',headers=[],query_string=b'',scheme='https',server=('getestatehawk.com',443)))
        with patch('app.content.related_candidates',return_value=[]) as query:
            first = site.blog_article(request,current['slug'],current)
            query.assert_called_once_with()
        self.assertNotIn('aria-label="Related reading"', first)
        self.assertNotIn('datePublished', first)
        self.assertIn('href="#section-scope-2"', first)
        self.assertIn('href="/about"', first)
        self.assertEqual(first.count('<h1'),1)
        self.assertIn('content="article"', first)
        with patch('app.content.related_candidates',return_value=[candidate]):
            second = site.blog_article(request,current['slug'],current)
        self.assertIn('href="/blog/municipal"',second)
        candidate['status']='draft'
        with patch('app.content.related_candidates',return_value=[candidate]):
            third=site.blog_article(request,current['slug'],current)
        self.assertNotIn('aria-label="Related reading"',third)

    def test_metadata_escapes_author_and_no_fake_profile(self):
        item=post('example','Quiet Title Example');item['author']='A <script>'
        request=Request(dict(type='http',method='GET',path='/blog/example',headers=[],query_string=b'',scheme='https',server=('getestatehawk.com',443)))
        with patch('app.content.related_candidates',return_value=[]):
            result=site.blog_article(request,'example',item)
        self.assertIn('A &lt;script&gt;',result)
        self.assertNotIn('By A <script>',result)

if __name__=='__main__':unittest.main()
