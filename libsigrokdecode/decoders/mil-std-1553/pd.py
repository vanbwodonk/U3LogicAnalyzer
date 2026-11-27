##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2020 Maxim Korzhavin <litlager@mail.ru>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd
from functools import reduce
from math import ceil

class SamplerateError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'mil-std-1553'
    name = 'MIL-STD-1553'
    longname = 'MIL-STD-1553 decoder'
    desc = 'MIL-STD-1553 bus protocol decoder'
    license = 'gplv3+'
    inputs = ['logic']
    outputs = []
    tags = ['Embedded/industrial']

    channels = (
        {'id': 'DP', 'name': 'DP', 'desc': 'Data positive signal'},
    )
    options = (
        {'id': 'device_type', 'desc': 'Type of device', 'default': 'auto',
            'values': ('master', 'slave', 'auto')},
        # Auto-mode role heuristics.  All times are in microseconds.
        # "Measured idle" is (gap between the last edge of one word and the
        # sync edge that is attributed to the next word), which includes about
        # 2 us of sync/edge overhead: a 12 us wire gap measures 14 us.
        {'id': 'idle_bus_us', 'desc': 'Measured idle that starts a new BC message (us)',
            'default': 14.0},
        {'id': 'bc_retry_us', 'desc': 'BC duplicate/retry window (us)',
            'default': 14.0},
        {'id': 'bc_force_us', 'desc': 'Force CW words within this gap to BC (us, 0=off)',
            'default': 0.0},
        {'id': 'response_min_us', 'desc': 'Minimum RT response start (us)',
            'default': 4.0},
        {'id': 'status_check', 'desc': 'Reject status words with reserved bits',
            'default': 'yes', 'values': ('yes', 'no')},
    )
    annotations = (
        ('cw', 'CW'),
        ('dw', 'DW'),
        ('warning', 'WARNING'),
        ('error', 'ERROR'),
        ('cw_details', 'CW DETAILS'),
        ('dw_details', 'DW DETAILS'),
        ('aw_details', 'AW DETAILS'),
    )
    annotation_rows = (
        ('data', 'Data', (0,1,2)),
        ('details', 'Details', (3,4,5,6,)),
    )

    e_parity = ['parity error']
    e_count = ['error bit count']

    e_m_notgroup = ['. not group']

    m_group = ['group:']

    e_m_comm = [' error code of command']
    m_accept = [' accept interface management']
    m_synch = [' synchronization']
    m_sendaw = [' send AW']
    m_selfcontrol = [' start self-control']
    m_blocktx = [' block TX']
    m_unlock = [' unlock TX']
    m_blocksign = [' block sign of malfunction']
    m_reset = [' reset']
    m_sendvec = [' transfer vector word']
    m_lastcomm = [' transfer last command']
    m_sendvsk = [' send VSK word']
    m_synchdw = [' synchronization with DW']
    m_blocki = [' block i TX']
    m_unlocki = [' unlock i TX']
    m_transmit = [' for transmit']
    m_reception = [' for reception']
    
    m_dw = [' DW']

    m_itd = [' to RT']
    m_ftd = [' from RT']

    s_errorinmessage = [' message error.']
    s_instrumentation = [' instrumentation.']
    s_servicereq = [' service request.']
    s_bcrreceived = [' broadcast command received.']
    s_abusy = [' subscriber is busy.']
    s_subsysflag = [' subsystem flag.']
    s_dbcaccept = [' dynamic bus control acceptance.']
    s_termflag = [' terminal flag.']

    def __init__(self):
        self.reset()

    def _reset_stream_state(self):
        """Reset everything that depends on the edge stream, not on options.

        Called from reset() and again from decode(), because PulseView reuses
        the decoder instance across capture runs: stale bit accumulators and
        role history from a previous capture would corrupt a fresh one.
        """
        self.state = 'FIND_BIT_AFTER_10_BIT'

        self.prelastsample = 0
        self.lastsample = 0
        self.actualsample = 0

        self.syncsample = 0
        self.synctype = 'Data'
        self.cwdetailscolour = 4

        self.bits = 0
        self.bitcount = 0
        self.dwcount = 0

        self.last_word_end_sample = 0  # Track last word end for idle calculation

        # Role history used by the auto-mode classifier.
        self.last_command_tr = None
        self.last_command_addr = -1
        self.last_command_count = -1
        self.last_command_bits = None
        self.last_word_was_status = False

        # Response bookkeeping.  expected_status counts the status words this
        # transaction still owes (0 = broadcast, 1 = normal, 2 = RT->RT);
        # transaction_closed is True once every owed status has been seen, so
        # the next CW-sync word cannot be a response any more.
        self.expected_status = 0
        self.transaction_closed = False

    def reset(self):
        self.samplerate = None

        self.halfbit = 5e-7
        self.bitwindow = 4e-7

        # Auto-role thresholds; overridden by decoder options in start().
        self.idle_bus_us = 14e-6
        self.bc_retry_us = 14e-6
        self.bc_force_us = 0.0
        self.response_min_us = 4e-6
        self.status_check = True

        self._reset_stream_state()

    def isparity(self):
        bitsvalue = self.bits
        tmpparity = 0
        for i in range(0,17):
            tmpparity = tmpparity + bitsvalue % 2
            bitsvalue = bitsvalue >> 1
        if tmpparity%2 == 1:
            return True
        else:
            return False

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value
        if not self.samplerate:
            return
        # Always scale from raw constants — safe if metadata() is called
        # more than once (e.g. on samplerate change between captures).
        self.halfbit = max(1.0, ceil(5e-7 * self.samplerate))
        self.bitwindow = max(1.0, ceil(4e-7 * self.samplerate))

    def waitx(self,rftype):
        self.wait({0: rftype})
        self.prelastsample = self.lastsample
        self.lastsample = self.actualsample
        self.actualsample = self.samplenum

    def puthexdata(self):
        hexdatavalue = format(self.bits>>1, 'X')
        for i in range(0,4-len(hexdatavalue)):
            hexdatavalue = '0' + hexdatavalue
        hexdatavalue = '0x' + hexdatavalue
        return hexdatavalue

    def putdwdetails(self):
        dwdetailsvalue = 'DATA-' + format(self.dwcount)
        return dwdetailsvalue

    def modecode_details(self, tr, code):
        # MIL-STD-1553B Table 5. A mode code is selected by subaddress 0 or
        # 31; the word-count field carries the code. Return
        # (name, needs_data_word, broadcast_allowed, defined).
        table = {
            (1, 0): (' dynamic bus control', False, False, True),
            (1, 1): (' synchronize (without data word)', False, True, True),
            (1, 2): (' transmit status word', False, False, True),
            (1, 3): (' initiate self-test', False, True, True),
            (1, 4): (' transmitter shutdown', False, True, True),
            (1, 5): (' override transmitter shutdown', False, True, True),
            (1, 6): (' inhibit terminal flag', False, True, True),
            (1, 7): (' override inhibit terminal flag', False, True, True),
            (1, 8): (' reset remote terminal', False, True, True),
            (1, 16): (' transmit vector word', True, False, True),
            (1, 18): (' transmit last command', True, False, True),
            (1, 19): (' transmit built-in test word', True, False, True),
            (0, 17): (' synchronize with data word', True, True, True),
            (0, 20): (' selected transmitter shutdown', True, True, True),
            (0, 21): (' override selected transmitter shutdown', True, True, True),
        }
        if (tr, code) in table:
            return table[(tr, code)]

        # Everything else is reserved by the standard: T/R=1 codes 9..15,
        # 17 and 20..31, and T/R=0 codes 0..16 and 22..31.  No reserved code
        # defines a data word and none may be broadcast, so report neither.
        return (' reserved mode code %d' % code, False, False, False)

    def putcwdetails(self):
        device_type = getattr(self, 'current_device_type', self.device_type_option)
        if device_type == 'master':
            self.cwdetailscolour = 4
            adrvalue = ((self.bits >> 12) & 0x1F)
            kvalue = ((self.bits >> 11) & 0x1)
            subadrvalue = ((self.bits >> 6) & 0x1F)
            countdwvalue = ((self.bits >> 1) & 0x1F)
            if(adrvalue == 31):
                cwdetailsvalue = self.m_group[self.lang]
            elif kvalue == 1:
                cwdetailsvalue = self.m_ftd[self.lang] + format(adrvalue)
            else:
                cwdetailsvalue = self.m_itd[self.lang] + format(adrvalue)
            if (subadrvalue == 0x0) | (subadrvalue == 0x1F):
                name, needs_data, broadcast_allowed, defined = \
                    self.modecode_details(kvalue, countdwvalue)
                self.cwdetailscolour = 4 if defined else 3
                cmdinfvalue = name
                if not defined:
                    cmdinfvalue += ' (reserved)'
                if adrvalue == 31 and not broadcast_allowed:
                    self.cwdetailscolour = 3
                    cmdinfvalue += self.e_m_notgroup[self.lang]
                cwdetailsvalue = cwdetailsvalue + cmdinfvalue

            else:
                if kvalue == 1:
                    cwdetailsvalue = cwdetailsvalue + self.m_transmit[self.lang]
                else:
                    cwdetailsvalue = cwdetailsvalue + self.m_reception[self.lang]

                if countdwvalue == 0:
                    countdwvalue = 32
                cwdetailsvalue = cwdetailsvalue + ' ' + format(countdwvalue) + self.m_dw[self.lang]
            pass    
            return cwdetailsvalue
        else:
            cwdetailsvalue = ''
            self.cwdetailscolour = 6

            if ((self.bits >> 11) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_errorinmessage[self.lang]
            if ((self.bits >> 10) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_instrumentation[self.lang]
            if ((self.bits >> 9) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_servicereq[self.lang]

            if ((self.bits >> 5) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_bcrreceived[self.lang]
            if ((self.bits >> 4) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_abusy[self.lang]
            if ((self.bits >> 3) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_subsysflag[self.lang]
            if ((self.bits >> 2) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_dbcaccept[self.lang]
            if ((self.bits >> 1) & 0x1):
                cwdetailsvalue = cwdetailsvalue + self.s_termflag[self.lang]

            if cwdetailsvalue == '':
                cwdetailsvalue = 'OK'
                self.cwdetailscolour = 4
            return cwdetailsvalue

    def is_valid_command(self, info):
        """Return True when info forms a legal 1553 command word.

        A status word and a command word share the CW sync. When a status is
        still expected, an invalid command pattern (for example receive mode
        code 0) must not be allowed to steal the status interpretation.
        """
        addr = (info >> 11) & 0x1F
        tr = (info >> 10) & 0x1
        subaddr = (info >> 6) & 0x1F
        code = info & 0x1F

        # RT address 0 is reserved for the bus controller.
        if addr == 0:
            return False

        if subaddr in (0, 31):
            _name, _needs_data, _broadcast, defined = \
                self.modecode_details(tr, code)
            return defined

        return True

    def classify_role(self, info, idle_time):
        """Auto-mode CW/SW decision.

        Command and status words share the same sync pattern, so only context
        can separate them.  A BC can repeat a command before the 14 us
        no-response timeout, and an RT status can arrive late.  The options
        make those assumptions adjustable.

        Note that idle_time is measured between edges, so it includes about
        2 us of sync/edge overhead: a 12 us wire gap measures as 14 us.
        """
        word_tr = (info >> 10) & 1
        word_addr = (info >> 11) & 0x1F
        word_count = info & 0x1F

        # A forced BC window (0 = off) is deliberately blunt: useful for a
        # capture where the BC ignores the RT response timeout.
        if self.bc_force_us > 0 and idle_time <= self.bc_force_us:
            return 'master'

        # Too short for a legal RT response: must be another BC word.  This
        # also covers the second command of an RT->RT transfer.
        if idle_time < self.response_min_us:
            return 'master'

        # RT->RT: receive command then transmit command to another RT with the
        # same word count, sent back-to-back by the BC.
        if (self.last_command_tr == 0 and word_tr == 1 and
                self.last_command_addr != word_addr and
                self.last_command_count == word_count):
            return 'master'

        # Status words have reserved bits 7..5 = 000.  A word with those bits
        # set cannot be a legal status, so treat it as a command.  This alone
        # rejects 0x9F21/0xCC21 and fixes the "SW: 0x9F21" false positive.
        if self.status_check and ((info >> 5) & 0x7) != 0:
            return 'master'

        # Every status this transaction owed has already been received, so
        # this CW-sync word starts a new BC message even when the gap is
        # shorter than idle_bus_us.  Without this a command that follows an
        # RT->BC data burst, to subaddress 0..7 (reserved bits 000), would be
        # mistaken for a status word.
        if self.transaction_closed:
            return 'master'

        # A status is still expected, and this word is not a legal command
        # (for example 0x1800: receive mode code 0 is undefined). This must
        # be checked before the idle rule: in an RT-to-RT transfer the first
        # status can arrive more than idle_bus_us after the second command.
        if self.expected_status > 0 and not self.is_valid_command(info):
            return 'slave'

        # New message after an idle bus.
        if idle_time >= self.idle_bus_us:
            return 'master'

        # Exact duplicate/retry of the previous command inside the retry
        # window (this is the 9F21 -> 9F21 case).
        if (self.last_command_bits is not None and
                info == self.last_command_bits and
                idle_time <= self.bc_retry_us):
            return 'master'

        # After a status word, the next CW-sync word is a new BC command.
        if self.last_word_was_status:
            return 'master'

        return 'slave'

    def putwordlabel(self):
        device_type = getattr(self, 'current_device_type', self.device_type_option)
        wordtype = 'CW'
        if device_type == 'slave':
            wordtype = 'SW'
        if self.synctype == 'CW':
            info = self.bits >> 1
            if wordtype == 'CW':
                tr = (info >> 10) & 0x1
                addr = (info >> 11) & 0x1F
                count = info & 0x1F

                # A transmit command that mirrors the previous receive
                # command (different RT, same word count) is the second
                # command of an RT->RT transfer: the source RT answers with
                # status + data, then the destination RT answers with status.
                rt2rt = (self.last_command_tr == 0 and tr == 1 and
                         self.last_command_addr != addr and
                         self.last_command_count == count)

                if addr == 31:
                    self.expected_status = 0        # broadcast: nobody answers
                elif rt2rt:
                    self.expected_status = 2
                else:
                    self.expected_status = 1
                # A broadcast can never be answered, so its transaction is
                # already closed when the command itself is decoded.
                self.transaction_closed = (self.expected_status == 0)

                self.last_command_tr = tr
                self.last_command_addr = addr
                self.last_command_count = count
                self.last_command_bits = info
                self.last_word_was_status = False
            else:
                self.last_command_tr = None
                self.last_command_bits = None
                self.last_word_was_status = True
                if self.expected_status > 0:
                    self.expected_status -= 1
                # With every owed status received the transaction is over, so
                # the following CW-sync word must be a new command.
                self.transaction_closed = (self.expected_status == 0)
            if(self.isparity()):
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [0, ['%s: %s' % (wordtype, self.puthexdata())]])
                cwdetailswalue = self.putcwdetails()
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [self.cwdetailscolour, ['%s' % (cwdetailswalue)]])
            else:
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [0, ['%s' % (wordtype) ]])
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [3, ['%s' % (self.e_parity[self.lang]) ]])
        elif self.synctype == 'DW':
            self.last_word_was_status = False
            if(self.isparity()):
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [1, ['%s: %s' % (self.synctype, self.puthexdata())]])
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [5, ['%s' % (self.putdwdetails())]])
            else:
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [1, ['%s' % (self.synctype) ]])
                self.put(self.syncsample - 3*self.halfbit, self.actualsample + self.halfbit, self.out_ann, [3, ['%s' % (self.e_parity[self.lang]) ]])
            
    def resetbits(self):
        self.bits = 0
        self.bitcount = 0

    def addbit(self, bitvalue):
        self.bits = self.bits*2 + bitvalue
        self.bitcount = self.bitcount + 1
        if(self.syncsample != 0):
            if self.bitcount == 17:
                # Auto mode: decide device type from role context and timing.
                if self.device_type_option == 'auto':
                    idle_samples = self.syncsample - self.last_word_end_sample
                    idle_time = idle_samples / self.samplerate if self.samplerate else 0
                    info = self.bits >> 1
                    self.current_device_type = self.classify_role(info, idle_time)
                else:
                    self.current_device_type = self.device_type_option
                self.putwordlabel()
                self.last_word_end_sample = self.actualsample  # Update for next word
            else:
                if self.bitcount > 17:
                    self.put(self.actualsample - self.halfbit, self.actualsample + self.halfbit, self.out_ann, [3, ['%s' % (self.e_count[self.lang])]])
                    if self.synctype == 'CW':
                        self.put(self.actualsample - self.halfbit, self.actualsample + self.halfbit, self.out_ann, [0, ['%s' % (self.synctype) ]])
                    else:
                        self.put(self.actualsample - self.halfbit, self.actualsample + self.halfbit, self.out_ann, [1, ['%s' % (self.synctype) ]])
					

    def newsyncword(self,newtype):
        if(self.syncsample != 0):
            if self.bitcount < 17:
                self.put(self.syncsample - 3*self.halfbit, self.prelastsample + self.halfbit, self.out_ann, [2, ['%s sync' % (self.synctype)]])
                self.put(self.syncsample - 3*self.halfbit, self.prelastsample + self.halfbit, self.out_ann, [3, ['%s -%d' % (self.e_count[self.lang], abs(17-self.bitcount))]])
        self.synctype = newtype
        if newtype == 'CW':
            self.state = 'FIND_BIT_AFTER_COMMAND_SYNC'
            self.dwcount = 0
        else:
            self.state = 'FIND_BIT_AFTER_DATA_SYNC'
            self.dwcount = self.dwcount + 1
        self.resetbits()
        self.syncsample = self.actualsample

    def isdiffinwindow(self,timevalue):
        if abs((self.actualsample - self.lastsample) - timevalue*self.halfbit) < self.bitwindow:
            return 1
        else:
            return 0

    def _option(self, name, default):
        # Normally a dict; tolerate harnesses that provide the option tuple.
        try:
            value = self.options[name]
        except (KeyError, TypeError):
            value = default
        if isinstance(value, dict):
            value = value.get('default', default)
        return value

    def _time_option(self, name, default_us):
        try:
            return max(0.0, float(self._option(name, default_us))) * 1e-6
        except (TypeError, ValueError):
            return default_us * 1e-6

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.lang = 0  # Always English
        self.device_type_option = self._option('device_type', 'auto')
        self.idle_bus_us = self._time_option('idle_bus_us', 14.0)
        self.bc_retry_us = self._time_option('bc_retry_us', 14.0)
        self.bc_force_us = self._time_option('bc_force_us', 0.0)
        self.response_min_us = self._time_option('response_min_us', 4.0)
        self.status_check = str(self._option('status_check', 'yes')).lower() not in (
            'no', 'false', '0', '')

    def decode(self):
        if not self.samplerate:
            raise SamplerateError('Cannot decode without samplerate.')

        # Below ~4 MHz a 0.5 us half-bit is under two samples, so the edge
        # windows can no longer separate a 1 from a 0 half.  Fail loudly
        # instead of silently emitting garbage.
        if self.samplerate < 4e6:
            raise SamplerateError(
                'samplerate too low for MIL-STD-1553: %.3f MHz, need >= 4 MHz'
                % (self.samplerate / 1e6))

        # Reset stream state — PulseView reuses the decoder instance across
        # capture runs, so stale state from a previous capture (edge
        # positions, bit accumulation, sync tracking, role history) would
        # corrupt data from a fresh capture.  Options are left untouched.
        self._reset_stream_state()

        while True:
            if self.state == 'FIND_BIT_AFTER_COMMAND_SYNC':
                self.waitx('r')
                if self.isdiffinwindow(4):
                    self.addbit(0)
                    self.state = 'FIND_BIT_AFTER_01_BIT'
                elif self.isdiffinwindow(3):
                    self.waitx('f')
                    if self.isdiffinwindow(1):
                        self.addbit(1)  
                        self.state = 'FIND_BIT_AFTER_10_BIT'

            elif self.state == 'FIND_BIT_AFTER_DATA_SYNC':
                self.waitx('f')
                if self.isdiffinwindow(4):
                    self.addbit(1)
                    self.state = 'FIND_BIT_AFTER_10_BIT'
                elif self.isdiffinwindow(3):
                    self.waitx('r')
                    if self.isdiffinwindow(1):
                        self.addbit(0) 
                        self.state = 'FIND_BIT_AFTER_01_BIT'

            elif self.state == 'FIND_BIT_AFTER_10_BIT':
                self.waitx('r')
                if self.isdiffinwindow(2):
                    self.addbit(0)
                    self.state = 'FIND_BIT_AFTER_01_BIT'
                elif self.isdiffinwindow(4):
                    self.newsyncword('DW')
                elif self.isdiffinwindow(1):
                    self.waitx('f')
                    if self.isdiffinwindow(1):
                        self.addbit(1)  
                        self.state = 'FIND_BIT_AFTER_10_BIT'
                    elif self.isdiffinwindow(3):
                        self.newsyncword('CW')
                else: 
                    self.waitx('f')
                    if self.isdiffinwindow(3):
                        self.newsyncword('CW')

            elif self.state == 'FIND_BIT_AFTER_01_BIT':
                self.waitx('f')
                if self.isdiffinwindow(2):
                    self.addbit(1)
                    self.state = 'FIND_BIT_AFTER_10_BIT'
                elif self.isdiffinwindow(4):
                    self.newsyncword('CW')
                elif self.isdiffinwindow(1):
                    self.waitx('r')
                    if self.isdiffinwindow(1):
                        self.addbit(0)   
                        self.state = 'FIND_BIT_AFTER_01_BIT'
                    elif self.isdiffinwindow(3):
                        self.newsyncword('DW')
                    else:
                        self.waitx('f')
                        if self.isdiffinwindow(3):
                            self.newsyncword('CW')

