# -*- coding: utf-8 -*-
__author__ = 'jscarbor'
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



from math import ceil
import random
import unittest
from RPiNWR.SAME import *
import logging


class TestSAME(unittest.TestCase):
    @staticmethod
    def add_noise(msg, rate, sd=.02):
        """

        :param msg: A message to mess up
        :param rate: 0-1, a number indicating how much of the message to perturb.  Small is good.  1 would swap
            every bit and 0 would swap none, so .04 with sd .02 is quite a lot of error for a digital system.
        :param sd: standard deviation of error rate
        :return: A tuple containing a bytearray of the noisy message and the confidence hints for its noise
        """
        if rate < 0 or rate > 1:
            raise ValueError("0<=rate<=1")

        def confidence0(r):
            return int(min(3, max(0, ceil(3 - 50 * r))))

        new_message = ''
        confidence = []
        for c in msg:
            byte_noise_rate = random.gauss(rate, sd)
            bits_to_flip_n = int(8 * byte_noise_rate + .5)
            bits_l = list('1' * bits_to_flip_n + '0' * (8 - bits_to_flip_n))
            random.shuffle(bits_l)
            noise_mask = int("".join(bits_l), 2)
            new_message += chr(ord(c) ^ noise_mask)
            confidence.append(confidence0(byte_noise_rate))

        return new_message, confidence

    def _test_add_noise(self):
        random.seed(0)
        clear_message = 'ZCZC-WXR-TOR-039173-039051-139069+0030-1591829-KCLE/NWS-'
        mess, conf = self.add_noise(clear_message, 0.06, .03)
        changed = [[0, 0], [0, 0], [0, 0], [0, 0]]
        for i in range(0, len(clear_message)):
            changed[conf[i]][0] += 1
            changed[conf[i]][1] += (clear_message[i] == mess[i]) & 1
        for i in range(0, 4):
            print("c(%d)=%.0f%%  n=%d\n" % (i, changed[i][1] * 100.0 / changed[i][0], conf.count(i)))
        self.fail(str(msg))

    @staticmethod
    def make_noisy_messages(noise):
        # mimic spotty reception this way.
        clear_message = '-WXR-RWT-020103-020209-020091-020121-029047-029165-029095-029037+0030-3031700-KEAX/NWS'

        random.seed(0)  # ensure a repeatable test
        return clear_message, [
            (TestSAME.add_noise(clear_message, noise)),
            (TestSAME.add_noise(clear_message, noise)),
            (TestSAME.add_noise(clear_message, noise)),
        ]

    def testAverageMessage(self):
        clear_message, messages = self.make_noisy_messages(.03)
        (msg, confidence) = average_message(messages)
        self.assertEqual(clear_message, msg)
        self.assertEqual(1, min(confidence))
        self.assertEqual(8, max(confidence))

    def testAverageMessageOfJunkHasLowConfidence(self):
        clear_message, messages = self.make_noisy_messages(.05)
        (msg, confidence) = average_message(messages)
        for i in range(0, len(clear_message)):
            if clear_message[i] != msg[i]:
                self.assertTrue(confidence[i] < 3, "%s != %s (%d)" % (clear_message[i], msg[i], confidence[i]))

    def testDifferentLengths(self):
        # Sometimes messages come in partial, like in this bad reception example
        messages = [('-E\x00S-RWT', [2, 1, 2, 3, 2, 2, 1, 2]),
                    ('-E\x00S-RWT-0\x007183+', [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 3, 3, 2, 3, 2, 3]),
                    ('-E\x00S-RWT-0\x007183+', [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3])]
        (msg, confidence) = average_message(messages)
        self.assertEquals('-EAS-RWT-017183+', msg)
        self.assertTrue(confidence[2] == 9)  # It's been fixed and verified by the adjacent 2 characters
        self.assertTrue(confidence[10] < 3)

    def testRealRWT(self):
        logging.basicConfig(level=logging.INFO)
        # And here's an RWT with bad reception
        messages = [
            (
                '-W\x00R-RWT-0\x007001-03\x00037-037\x0063-0370\x009-03707\x00-037085\x00037101-\x0037105-0\x007125-03\x00135-037\x0045-0371\x001-03718\x00-037183\x00037185+\x00600-118\x00503-KRA\x00/NWS-\x00\x00\x00öÂ\x1dIù',
                [2, 3, 3, 2, 3, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3,
                 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 0, 0, 0, 0, 0]),
            (
                '-W\x00R-RWT-0\x007001-03\x00037-037\x0063-0370\x009-03707\x00-037085\x00037101-\x0037105-0\x007125-03\x00135-037\x0045-0371\x001-03718\x00-037183\x00037185+\x00600-118\x00503-KRA\x00/NWS-\x00\x00\x00´\x02\x11IX',
                [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 0, 0, 0, 0, 0]),
            (
                '-W\x00R-RWT-0\x007001-03\x00037-037\x0063-0370\x009-03707\x00-037085\x00037101-\x0037105-0\x007125-03\x00135-037\x0045-0371\x001-03718\x00-037183\x00037185+\x00600-118\x00503-KRA\x00/NWS-\x00\x00\x000\x00\x11IP',
                [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                 3, 3, 3, 0, 0, 0, 0, 0]
            )]
        # I figured the clean version out by hand based on received
        clean_message = '-WXR-RWT-037001-037037-037063-037069-037077-037085-037101-037105-037125-037135-037145-037151-037181-037183-037185+0600-1181503-KRAX/NWS-'

        (msg, confidence) = average_message(messages)

        # Now, because this message was so dirty, let's assert a certain level of accuracy, which can be tuned upward
        # as the average_message algorithm is improved.
        changed_bits = self.count_changed_bits(clean_message, msg)
        changed_bytes = self.count_changed_bytes(clean_message, msg)
        wrong_confidence = self.count_wrong_confidence(clean_message, msg, confidence)
        right_confidence = self.count_right_confidence(clean_message, msg, confidence)
        logging.info("wrong_bits=%d wrong_bytes=%d wrong_confidence=%d right_confidence=%d " %
                     (changed_bits, changed_bytes, wrong_confidence, right_confidence))

        logging.info(self.get_errstr(msg, clean_message))
        logging.info(msg)
        logging.info("".join([str(x) for x in confidence]))
        logging.info(clean_message)
        self.assertTrue(changed_bits < 21, changed_bits)
        self.assertTrue(changed_bytes < 12, changed_bytes)
        self.assertTrue(wrong_confidence < 17, wrong_confidence)
        self.assertTrue(right_confidence > 1075,
                        "%d -- %.2f per byte" % (right_confidence, right_confidence / len(msg)))

    def count_changed_bits(self, a, b):
        bits = abs(len(a) - len(b)) * 8
        for i in range(0, min(len(a), len(b))):
            bits += bin(ord(a[i]) ^ ord(b[i])).count('1')
        return bits

    def count_right_confidence(self, clean_message, test_message, confidence):
        rc = 0
        for i in range(0, len(confidence)):
            if (not len(clean_message) < i) and clean_message[i] == test_message[i]:
                rc += confidence[i]
        return rc

    def count_wrong_confidence(self, clean_message, test_message, confidence):
        wc = 0
        for i in range(0, len(confidence)):
            if len(clean_message) < i or clean_message[i] != test_message[i]:
                wc += confidence[i]
        return wc

    def count_changed_bytes(self, a, b):
        bytes = abs(len(a) - len(b))
        for i in range(0, min(len(a), len(b))):
            bytes += (a[i] != b[i]) & 1
        return bytes

    def get_errstr(self, a, b):
        errstr = ''
        for i in range(0, min(len(a), len(b))):
            if a[i] == b[i]:
                errstr += ' '
            else:
                errstr += "_"
        return errstr