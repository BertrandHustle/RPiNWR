# -*- coding: utf-8 -*-
__author__ = 'ke4roh'
# Copyright © 2016 James E. Scarborough
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from RPiNWR.messages import *
import pickle
import os
from circuits import Component, Debugger, Event, BaseComponent, handler
import time


class ScoreWatcher(Component):
    def __init__(self):
        super().__init__()
        self.score = None

    def new_score(self, score, msg):
        self.score = score


class MockAlerter(Component):
    """
    This component injects messages for testing purposes and keeps a clock.
    """

    def __init__(self, alerts):
        self.alerts = alerts
        self.clock = alerts[0].get_start_time_sec()  # this will report the time of the latest event
        self.aix = 0
        self.eix = 0
        super().__init__()

    def generate_events(self, event):
        event.reduce_time_left(0)
        while self.aix < len(self.alerts) and self.alerts[self.aix].get_start_time_sec() <= self.clock:
            self.fire(new_message(self.alerts[self.aix]))
            self.aix += 1
        self.clock += 15  # these events are marked by the minute, so 15 sec is 4x as fast as necessary, but it needs
        # to be smaller slices so that there are enough trips through generate_events to update score etc.
        if self.clock > self.alerts[-1].get_end_time_sec() + 300:
            self.fire(shutdown())

    def _time(self):
        return self.clock


class shutdown(Event):
    """shut down the manager"""


class CacheMonitor(BaseComponent):
    """
    This component keeps a record of the active messages in the buffer with each change
    """

    def __init__(self, cache):
        self.cache = cache
        self.clock = cache._MessageCache__time
        self.stats = []
        self.score = float("nan")
        super().__init__()

    @handler("update_score", priority=-1000)
    def update_score(self, msg):
        ptime = time.strftime("%j %H:%M  ", time.gmtime(self.clock()))
        here = self.cache.get_active_messages()
        elsewhere = self.cache.get_active_messages(here=False)
        stat = ptime + ",".join([x.event_id for x in here]) \
               + " --- " + ",".join([x.event_id for x in elsewhere]) \
               + " / " + str(self.score)
        if len(self.stats) and self.stats[-1].startswith(ptime):
            self.stats[-1] = stat.strip()
        else:
            self.stats.append(stat.strip())

    @handler("new_score")
    def new_score(self, score, msg):
        self.score = score
        self.update_score(msg)

    @handler("shutdown")
    def shutdown(self):
        self.stop()


class TestCache(unittest.TestCase):
    def setUp(self):
        self.manager = None

    def tearDown(self):
        if self.manager is not None:
            self.manager.stop()
            self.manager = None

    def test_buffer_for_radio_against_storm_system(self):
        # Test to see that the correct events are reported in priority order as a storm progresses
        # This test is a little long in this file, but it's somewhat readable.
        alerts = [SAMEMessage("WXL58", x) for x in [
            "-WXR-SVR-037183+0045-1232003-KRAH/NWS-",
            "-WXR-SVR-037151+0030-1232003-KRAH/NWS-",
            "-WXR-SVR-037037+0045-1232023-KRAH/NWS-",
            "-WXR-SVR-037001-037151+0100-1232028-KRAH/NWS-",
            "-WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS-",
            "-WXR-SVR-037001+0045-1232110-KRAH/NWS-",
            "-WXR-SVR-037069-037181-037185+0045-1232116-KRAH/NWS-",
            "-WXR-FFW-037125+0300-1232209-KRAH/NWS-",
            "-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS-",
            "-WXR-SVR-037001-037037-037151+0045-1242011-KRAH/NWS-",
            "-WXR-SVR-037001-037037-037135+0100-1242044-KRAH/NWS-",
            "-WXR-SVR-037037-037063-037135-037183+0045-1242120-KRAH/NWS-",
            "-WXR-SVR-037183+0100-1242156-KRAH/NWS-",
            "-WXR-TOR-037183+0015-1242204-KRAH/NWS-",
            "-WXR-SVR-037101-037183+0100-1242235-KRAH/NWS-",
            "-WXR-SVR-037151+0100-1242339-KRAH/NWS-",
            "-WXR-SVR-037101+0100-1250011-KRAH/NWS-",
            "-WXR-SVR-037125-037151+0100-1250029-KRAH/NWS-",
            "-WXR-SVR-037085-037105-037183+0100-1250153-KRAH/NWS-",
            "-WXR-SVR-037085-037101+0100-1250218-KRAH/NWS-"
        ]]

        expected = """123 20:03  -WXR-SVR-037183+0045-1232003-KRAH/NWS- --- -WXR-SVR-037151+0030-1232003-KRAH/NWS- / 30
123 20:23  -WXR-SVR-037183+0045-1232003-KRAH/NWS- --- -WXR-SVR-037037+0045-1232023-KRAH/NWS-,-WXR-SVR-037151+0030-1232003-KRAH/NWS- / 30
123 20:28  -WXR-SVR-037183+0045-1232003-KRAH/NWS- --- -WXR-SVR-037001-037151+0100-1232028-KRAH/NWS-,-WXR-SVR-037037+0045-1232023-KRAH/NWS-,-WXR-SVR-037151+0030-1232003-KRAH/NWS- / 30
123 20:33  -WXR-SVR-037183+0045-1232003-KRAH/NWS- --- -WXR-SVR-037001-037151+0100-1232028-KRAH/NWS-,-WXR-SVR-037037+0045-1232023-KRAH/NWS- / 30
123 20:45  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS-,-WXR-SVR-037183+0045-1232003-KRAH/NWS- --- -WXR-SVR-037001-037151+0100-1232028-KRAH/NWS-,-WXR-SVR-037037+0045-1232023-KRAH/NWS- / 30
123 20:48  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS- --- -WXR-SVR-037001-037151+0100-1232028-KRAH/NWS-,-WXR-SVR-037037+0045-1232023-KRAH/NWS- / 30
123 21:08  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS- --- -WXR-SVR-037001-037151+0100-1232028-KRAH/NWS- / 30
123 21:10  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS- --- -WXR-SVR-037001+0045-1232110-KRAH/NWS-,-WXR-SVR-037001-037151+0100-1232028-KRAH/NWS- / 30
123 21:16  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS- --- -WXR-SVR-037069-037181-037185+0045-1232116-KRAH/NWS-,-WXR-SVR-037001+0045-1232110-KRAH/NWS-,-WXR-SVR-037001-037151+0100-1232028-KRAH/NWS- / 30
123 21:28  -WXR-SVR-037069-037077-037183+0045-1232045-KRAH/NWS- --- -WXR-SVR-037069-037181-037185+0045-1232116-KRAH/NWS-,-WXR-SVR-037001+0045-1232110-KRAH/NWS- / 30
123 21:30   --- -WXR-SVR-037069-037181-037185+0045-1232116-KRAH/NWS-,-WXR-SVR-037001+0045-1232110-KRAH/NWS- / 20
123 21:55   --- -WXR-SVR-037069-037181-037185+0045-1232116-KRAH/NWS- / 20
123 22:01   ---  / 0
123 22:09   --- -WXR-FFW-037125+0300-1232209-KRAH/NWS- / 0
124 01:09   ---  / 0
124 18:54  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 20
124 20:11  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037001-037037-037151+0045-1242011-KRAH/NWS- / 20
124 20:44  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037001-037037-037135+0100-1242044-KRAH/NWS-,-WXR-SVR-037001-037037-037151+0045-1242011-KRAH/NWS- / 20
124 20:56  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037001-037037-037135+0100-1242044-KRAH/NWS- / 20
124 21:20  -WXR-SVR-037037-037063-037135-037183+0045-1242120-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037001-037037-037135+0100-1242044-KRAH/NWS- / 30
124 21:44  -WXR-SVR-037037-037063-037135-037183+0045-1242120-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 30
124 21:56  -WXR-SVR-037183+0100-1242156-KRAH/NWS-,-WXR-SVR-037037-037063-037135-037183+0045-1242120-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 30
124 22:04  -WXR-TOR-037183+0015-1242204-KRAH/NWS-,-WXR-SVR-037183+0100-1242156-KRAH/NWS-,-WXR-SVR-037037-037063-037135-037183+0045-1242120-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 40
124 22:05  -WXR-TOR-037183+0015-1242204-KRAH/NWS-,-WXR-SVR-037183+0100-1242156-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 40
124 22:19  -WXR-SVR-037183+0100-1242156-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 30
124 22:35  -WXR-SVR-037101-037183+0100-1242235-KRAH/NWS-,-WXR-SVR-037183+0100-1242156-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 30
124 22:56  -WXR-SVR-037101-037183+0100-1242235-KRAH/NWS-,-WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 30
124 23:35  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- ---  / 20
124 23:39  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037151+0100-1242339-KRAH/NWS- / 20
125 00:11  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037101+0100-1250011-KRAH/NWS-,-WXR-SVR-037151+0100-1242339-KRAH/NWS- / 20
125 00:29  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037125-037151+0100-1250029-KRAH/NWS-,-WXR-SVR-037101+0100-1250011-KRAH/NWS-,-WXR-SVR-037151+0100-1242339-KRAH/NWS- / 20
125 00:39  -WXR-SVA-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1241854-KRAH/NWS- --- -WXR-SVR-037125-037151+0100-1250029-KRAH/NWS-,-WXR-SVR-037101+0100-1250011-KRAH/NWS- / 20
125 00:54   --- -WXR-SVR-037125-037151+0100-1250029-KRAH/NWS-,-WXR-SVR-037101+0100-1250011-KRAH/NWS- / 20
125 01:11   --- -WXR-SVR-037125-037151+0100-1250029-KRAH/NWS- / 20
125 01:29   ---  / 0
125 01:53  -WXR-SVR-037085-037105-037183+0100-1250153-KRAH/NWS- ---  / 30
125 02:18  -WXR-SVR-037085-037105-037183+0100-1250153-KRAH/NWS- --- -WXR-SVR-037085-037101+0100-1250218-KRAH/NWS- / 30
125 02:53   --- -WXR-SVR-037085-037101+0100-1250218-KRAH/NWS- / 20
125 03:18   ---  / 0""".split("\n")

        alerter = MockAlerter(alerts)
        buf = MessageCache({'lat': 35.73, 'lon': -78.85, 'fips6': "037183"},
                           by_score_and_time, clock=alerter._time)
        self.manager = cachemon = CacheMonitor(buf)
        (cachemon + buf + alerter + Debugger()).run()
        self.assertEquals(len(expected), len(cachemon.stats), cachemon.stats)
        for i in range(0, len(expected)):
            self.assertEquals(expected[i].strip(), cachemon.stats[i].strip())

    def test_net_alerts(self):
        # This is more activity than we'd see in a regular setup because it considers every severe thunderstorm
        # and tornado watch nationwide, but that's because those are issued by the Storm Prediction Center from
        # KWNS, so it is harder to filter them for the immediate area when retrieved from a national sample.
        # TODO filter by county adjacency (maybe 2 counties distant for eastern, 1 for western (larger) counties)
        expected = """145 17:17   --- KDDC.FA.W.0014 / nan
145 19:03   --- KDDC.FL.W.0001,KDDC.FA.W.0014 / nan
145 23:54   --- KDDC.FL.W.0001,KDDC.FA.W.0014,TO.A.0204 / 25
146 00:05  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,TO.A.0204 / 35
146 00:09  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,TO.A.0204 / 35
146 00:25  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,TO.A.0204,TO.A.0207 / 35
146 00:58  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,TO.A.0204,TO.A.0207 / 35
146 01:11  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0075,KDDC.SV.W.0077,TO.A.0204,TO.A.0207 / 35
146 01:13  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0075,KDDC.SV.W.0077,KDDC.TO.W.0052,TO.A.0204,TO.A.0207 / 35
146 01:14  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0075,KDDC.SV.W.0077,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 35
146 01:18  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 35
146 01:19  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:21  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:24  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:26  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:28  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0074,KDDC.SV.W.0075,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:30  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:31  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:33  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:41  KGLD.TO.W.0028,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.TO.W.0052,KDDC.TO.W.0053,TO.A.0204,TO.A.0207 / 45
146 01:43  KGLD.TO.W.0028,KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.TO.W.0052,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:44  KGLD.TO.W.0028,KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0076,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0052,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:45  KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:47  KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:55  KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:57  KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 01:58  KGLD.TO.W.0029,TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0077,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.TO.W.0053,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 45
146 02:00  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:03  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:05  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:07  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:08  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:11  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0078,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0029,KDDC.TO.W.0054,TO.A.0204,TO.A.0207 / 35
146 02:15  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KGLD.TO.W.0030,TO.A.0204,TO.A.0207 / 35
146 02:25  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0079,KDDC.SV.W.0080,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0030,TO.A.0204,TO.A.0207 / 35
146 02:30  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0030,TO.A.0204,TO.A.0207 / 35
146 02:31  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0030,KDDC.TO.W.0055,TO.A.0204,TO.A.0207 / 35
146 02:38  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0030,KDDC.TO.W.0055,TO.A.0204,TO.A.0207 / 35
146 02:40  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0030,KDDC.TO.W.0055,TO.A.0204,TO.A.0207 / 35
146 02:45  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KGLD.TO.W.0031,KDDC.TO.W.0055,TO.A.0204,TO.A.0207 / 35
146 02:59  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0081,KDDC.SV.W.0082,KDDC.SV.W.0083,KGLD.TO.W.0031,KDDC.TO.W.0055,TO.A.0204,TO.A.0207 / 35
146 03:00  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0083,KGLD.TO.W.0031,TO.A.0204,TO.A.0207 / 35
146 03:01  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0083,KGLD.TO.W.0031,TO.A.0204,TO.A.0207 / 35
146 03:02  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0083,KGLD.TO.W.0031,TO.A.0204,TO.A.0207 / 35
146 03:05  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.SV.W.0083,KGLD.TO.W.0031,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:09  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0031,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:14  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0031,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:15  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:28  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:33  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:37  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 03:48  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0083,KDDC.SV.W.0084,KGLD.TO.W.0032,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 04:00  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 04:03  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,SV.A.0208,TO.A.0204,TO.A.0207 / 35
146 04:05  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:08  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:20  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:29  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:32  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:36  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:37  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:40  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:43  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0084,KDDC.SV.W.0085,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:45  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 04:53  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0204,TO.A.0207 / 35
146 05:00  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:07  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:13  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0014,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0086,KDDC.SV.W.0087,KGLD.SV.W.0094,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:15  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0087,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:16  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0087,KDDC.SV.W.0088,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:24  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0087,KDDC.SV.W.0088,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:30  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0088,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:31  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,KDDC.SV.W.0088,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:45  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FF.W.0006,KDDC.FF.W.0007,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 05:52  TO.A.0206 --- KDDC.FL.W.0001,KDDC.FA.W.0015,KDDC.FF.W.0006,KDDC.FF.W.0007,SV.A.0208,SV.A.0209,TO.A.0207 / 35
146 06:00   --- KDDC.FL.W.0001,KDDC.FA.W.0015,SV.A.0208,SV.A.0209,TO.A.0207 / 25
146 07:00   --- KDDC.FL.W.0001,KDDC.FA.W.0015,SV.A.0208,SV.A.0209 / 10
146 10:00   --- KDDC.FL.W.0001,KDDC.FA.W.0015 / 0""".split("\n")
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "kddc_kgld_kwns.cap.p"), "rb") as f:
            alerts = pickle.load(f)
        alerts = list([item for sublist in [c.vtec for a, c in alerts] for item in sublist])
        # https://mesonet.agron.iastate.edu/vtec/#2016-O-NEW-KGLD-TO-W-0029/USCOMP-N0Q-201605250145

        alerter = MockAlerter(alerts)
        buf = MessageCache({"lat": 40.321909, "lon": -102.718192, "fips6": "008125"},
                           default_VTEC_sort, clock=alerter._time)
        self.manager = cachemon = CacheMonitor(buf)
        (cachemon + buf + alerter + Debugger()).run()

        self.assertEquals(len(expected), len(cachemon.stats))
        for i in range(0, len(expected)):
            self.assertEquals(expected[i].strip(), cachemon.stats[i].strip())

    def test_not_here_with_polygon(self):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "kddc_kgld_kwns.cap.p"), "rb") as f:
            alerts = pickle.load(f)
        valerts = list(filter(lambda v: v.event_id == "KGLD.TO.W.0028", [item for sublist in [c.vtec for a, c in alerts]
                                                                         for item in sublist]))

        buf = EventMessageGroup()

        buf.add_message(valerts[0])
        self.assertTrue(buf.is_effective((40.321909, -102.718192), "008125", True, lambda: valerts[0].published))
        self.assertFalse(buf.is_effective((40.321909, -102.718192), "008125", False, lambda: valerts[0].published))

    def test_not_here_sans_polygon(self):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "kddc_kgld_kwns.cap.p"), "rb") as f:
            alerts = pickle.load(f)
        valerts = list(filter(lambda v: v.event_id == "TO.A.0206",
                              [item for sublist in [c.vtec for a, c in alerts] for item in sublist]))

        buf = EventMessageGroup()

        buf.add_message(valerts[0])
        self.assertTrue(buf.is_effective((40.321909, -102.718192), "008125", True, lambda: valerts[0].published))
        self.assertFalse(buf.is_effective((40.321909, -102.718192), "008125", False, lambda: valerts[0].published))