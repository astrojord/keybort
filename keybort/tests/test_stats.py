from django.test import SimpleTestCase

from boards.helpers.stats import stat_breakdown, stat_leader


class StatHelperTests(SimpleTestCase):
    def test_leader_merges_case_and_ignores_blanks(self):
        leader = stat_leader(['GMK', 'gmk ', 'ePBT', None, '', '  '])
        self.assertEqual(leader, {'label': 'GMK', 'count': 2, 'tied': 0})

    def test_leader_reports_ties(self):
        leader = stat_leader(['b', 'a', 'c', 'c', 'a'])
        self.assertEqual(leader, {'label': 'a', 'count': 2, 'tied': 1})

    def test_leader_without_values(self):
        self.assertIsNone(stat_leader([None, '']))

    def test_breakdown_folds_other_and_not_set(self):
        values = ['a', 'a', 'b', 'c', 'd', 'e', 'f', 'g', None, None]
        breakdown = stat_breakdown('Things', values)
        self.assertEqual(
            [(row['label'], row['count']) for row in breakdown['rows']],
            [
                ('a', 2),
                ('b', 1),
                ('c', 1),
                ('d', 1),
                ('e', 1),
                ('Other', 2),
                ('Not set', 2),
            ],
        )
        self.assertEqual(breakdown['rows'][0]['percent'], 20)
        self.assertEqual(breakdown['total'], 10)
