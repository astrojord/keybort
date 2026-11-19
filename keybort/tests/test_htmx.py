import json

from django.http import HttpResponse
from django.test import SimpleTestCase

from boards.htmx import bulk_deleted, htmx_swap


class HtmxSwapTests(SimpleTestCase):
    def test_sets_retarget_and_reswap(self):
        response = htmx_swap(HttpResponse(), '#row', 'outerHTML')
        self.assertEqual(response['HX-Retarget'], '#row')
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        self.assertNotIn('HX-Trigger', response)

    def test_sets_trigger_when_given(self):
        response = htmx_swap(HttpResponse(), '#row', 'delete', 'close-dialog')
        self.assertEqual(response['HX-Trigger'], 'close-dialog')


class BulkDeletedTests(SimpleTestCase):
    def test_closes_dialog_and_sends_row_ids(self):
        response = bulk_deleted(['part-1', 'part-2'])
        self.assertEqual(response['HX-Retarget'], '#page-dialog')
        self.assertEqual(response['HX-Reswap'], 'none')
        self.assertEqual(
            json.loads(response['HX-Trigger']),
            {'close-dialog': '', 'rows-deleted': {'ids': ['part-1', 'part-2']}},
        )
