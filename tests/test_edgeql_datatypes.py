##
# Copyright (c) 2012-present MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


from edgedb.server import _testbase as tb
from edgedb.client import exceptions as exc


class TestEdgeQLDT(tb.QueryTestCase):

    async def test_edgeql_dt_datetime_01(self):
        await self.assert_query_result('''
            SELECT <datetime>'2017-10-10' + <timedelta>'1 day';
            SELECT <timedelta>'1 day' + <datetime>'2017-10-10';
            SELECT <datetime>'2017-10-10' - <timedelta>'1 day';
            SELECT <timedelta>'1 day' + <timedelta>'1 day';
            SELECT <timedelta>'4 days' - <timedelta>'1 day';
        ''', [
            ['2017-10-11T00:00:00+00:00'],
            ['2017-10-11T00:00:00+00:00'],
            ['2017-10-09T00:00:00+00:00'],
            ['2 days'],
            ['3 days'],
        ])

        with self.assertRaisesRegex(exc.EdgeQLError,
                                    'operator does not exist.*timedelta'):

            await self.con.execute("""
                SELECT <timedelta>'1 day' - <datetime>'2017-10-10';
            """)

    async def test_edgeql_dt_datetime_02(self):
        await self.assert_query_result('''
            SELECT <str><datetime>'2017-10-10';
            SELECT <str>(<datetime>'2017-10-10' - <timedelta>'1 day');
        ''', [
            ['2017-10-10T00:00:00+00:00'],
            ['2017-10-09T00:00:00+00:00'],
        ])

    async def test_edgeql_dt_datetime_03(self):
        await self.assert_query_result('''
            SELECT <map<str,datetime>>['foo' -> '2020-10-10'];
            SELECT (<map<str,datetime>>['foo' -> '2020-10-10'])['foo'] +
                   <timedelta>'1 month';
        ''', [
            [{'foo': '2020-10-10T00:00:00+00:00'}],
            ['2020-11-10T00:00:00+00:00'],
        ])