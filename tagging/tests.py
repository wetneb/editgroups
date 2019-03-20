import unittest
from django.test import TestCase
from store.models import Edit
from store.models import Batch
from .models import Tag
from .models import action_re
from .models import property_re
from .models import language_re
from .diffinspector import DiffInspector
from .diffdigest import DiffDigest
from caching import invalidation
import requests_mock
import os

cache = invalidation.cache

class TagTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_action_re(self):
        self.assertEquals('wbsetdescription-add', action_re.match('/* wbsetdescription-add:1|eu */ Indonesiako herria, #quickstatements').group(1))

    def test_property_re(self):
        examples = {
            "/* wbremoveclaims-remove:1| */ [[Property:P4135]]: 70, #quickstatements; [[:toollabs:quickstatements/#/batch/9509|batch #9509]] by [[User:Tibbs001|]]": "P4135",
            "/* wbcreateclaim-create:1| */ [[Property:P106]]: [[Q1650915]], #quickstatements; [[:toollabs:quickstatements/#/batch/9516|batch #9516]] by [[User:Sic19|]]": "P106",
            "/* wbsetreference-add:2| */ [[Property:P1433]]: [[Q3186921]], #quickstatements; #temporary_batch_1553059981737": "P1433",
            "/* wbsetclaim-update:2||1|2 */ [[Property:P159]]: [[Q3887146]]": "P159",
        }
        for example, expected in examples.items():
            self.assertEquals(expected, property_re.match(example).group(1))

    def test_extract(self):
        Edit.ingest_jsonlines('store/testdata/one_qs_batch.json')
        batch = Batch.objects.get()
        last_edit = batch.edits.order_by('-timestamp')[0]
        # tag extraction on the latest edit does not return any *new* tag
        self.assertEquals([], [tag.id for tag in Tag.extract(last_edit)])
        self.assertEquals(['wbcreateclaim-create', 'prop-P18', 'prop-P2534', 'prop-P3896', 'prop-P856'], list(batch.tag_ids))

    def test_extract_editentity(self):
        Edit.ingest_jsonlines('store/testdata/one_or_batch.json')
        batch = Batch.objects.get()
        self.assertEquals(['wbeditentity-update'], list(batch.tag_ids))

    def test_tag_former_batches(self):
        Edit.ingest_jsonlines('store/testdata/one_qs_batch.json')
        Tag.objects.all().delete()
        Tag.retag_all_batches()
        batch = Batch.objects.get()
        self.assertEquals(['wbcreateclaim-create', 'prop-P18', 'prop-P2534', 'prop-P3896', 'prop-P856'], list(batch.tag_ids))

    def test_language_re(self):
        self.assertEquals('ru', language_re.match('/* wbsetlabel-add:1|ru */ Eupelops brevicuspis').group(1))

    def test_tags_with_languages(self):
        Edit.ingest_jsonlines('store/testdata/qs_batch_with_terms.json')
        batch = Batch.objects.get()
        self.assertEquals(['wbsetdescription-add', 'lang-eu'], list(batch.tag_ids))
        lang_tag = batch.tags.order_by('priority')[0]
        self.assertEquals('eu', lang_tag.display_name)

    def test_deletion_batch(self):
        Edit.ingest_jsonlines('store/testdata/deletion_edit.json')
        self.assertEquals(1, Batch.objects.count())
        batch = Batch.objects.get()
        self.assertEquals(['delete'], list(batch.tag_ids))

class MockDiffInspector(DiffInspector):

    def __init__(self):
        super(MockDiffInspector, self).__init__()
        self.responses = {}

    def _retrieve_html_diff(self, oldrevid, newrevid):
        return self.responses.get((oldrevid, newrevid))

class DiffDigestTest(unittest.TestCase):
    def test_json(self):
        self.assertEqual({'statements':{'P31'},
            'qualifiers':set(),
            'labels':set(),
            'descriptions':set(),
            'aliases':set(),
        }, DiffDigest(statements=['P31']).json())

    def test_repr(self):
        self.assertEqual('<DiffDigest: empty>',repr(DiffDigest()))
        self.assertEqual("<DiffDigest: statements: {'P31'}>",repr(DiffDigest(statements=['P31'])))

    def test_equal(self):
        self.assertEqual(DiffDigest(), DiffDigest())
        self.assertNotEqual(DiffDigest(labels=['fr']), DiffDigest(labels=['de']))

class DiffInspectorTest(unittest.TestCase):
    def setUp(self):
        self.html = """
        <tr><td colspan="2" class="diff-lineno">aliases / en / 0</td><td colspan="2" class="diff-lineno">aliases / en / 0</td></tr><tr><td colspan="2">&nbsp;</td><td class="diff-marker">+</td><td class="diff-addedline"><div><ins class="diffchange diffchange-inline">PF3D7_0720400</ins></div></td></tr><tr><td colspan="2" class="diff-lineno">aliases / en / 1</td><td colspan="2" class="diff-lineno">aliases / en / 1</td></tr><tr><td class="diff-marker">-</td><td class="diff-deletedline"><div><del class="diffchange diffchange-inline">PF07_0085</del></div></td></tr><!-- diff cache key wikidatawiki:diff:wikidiff2:1.12:old-888082520:rev-888696170:1.7.3:25:lang-en -->
        """.strip()
        self.testdir = os.path.dirname(os.path.abspath(__file__))

    def get_test_diff(self, name):
        with open(os.path.join(self.testdir, 'data', name), 'r') as f:
            return f.read()

    def test_retrieve_html_diff(self):
        di = DiffInspector()

        response = '{"compare":{"fromid":20525554,"fromrevid":888082520,"fromns":0,"fromtitle":"Q18968698","toid":20525554,"torevid":888696170,"tons":0,"totitle":"Q18968698","*":"'+self.html.replace('"', '\\"')+'"}}'

        with requests_mock.mock() as m:
            m.get('https://www.wikidata.org/w/api.php?action=compare&fromrev=1234&torev=12345&uselang=en&format=json',
                text=response)

            self.assertEqual(self.html, di._retrieve_html_diff(1234, 12345))

    def test_extract_properties(self):
        di = MockDiffInspector()
        di.responses[(12,34)] = self.html
        diff_digest = DiffDigest(aliases={'en'})
        self.assertEqual(diff_digest, di.extract(12, 34))

    def test_extract_digest(self):
        di = DiffInspector()
        examples = {
            self.get_test_diff('ice_skating.html'):
                DiffDigest(
                    statements={'P710'},
                    qualifiers={'P1351', 'P4826', 'P4815', 'P1545', 'P1352', 'P4825', 'P1532'}),
            self.get_test_diff('death.html'):
                DiffDigest(statements={'P723', 'P570', 'P569'}),
            self.get_test_diff('patronage.html'):
                DiffDigest(
                    statements={'P3872'},
                    qualifiers={'P585'},
                    aliases={'fr'}),
            self.get_test_diff('head_coach.html'):
                DiffDigest(
                    statements={'P286'},
                    qualifiers={'P580', 'P582'}
                    ),
        }
        for html, digest in examples.items():
            self.assertEqual(digest, di._extract_digest(html))

