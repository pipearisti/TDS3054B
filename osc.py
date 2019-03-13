


import visa
import numpy as np
from struct import unpack
import pylab

import time

class TDS3054B(object):

    def __init__(self):
        rm = visa.ResourceManager()
        self.scope = rm.open_resource('TDS3054B')
        self.ch = [None]
        for ch in range(4):
            self.ch.append(OSCChannel(self.scope, ch + 1))

    def read_ch(self, ch):
        self.ch[ch].activate()
        self.ch[ch].get_curve()
        self.ch[ch].scale()

    def read_avg(self, n=128, ch=None):
        if ch is None:
            ch = [1, 2, 3, 4]
        for c in ch:
            self.ch[c].activate()
            self.ch[c].update()
        # Stop between wfm gathering
        self.scope.write('ACQ:STOPA SEQ')
        for i in range(n):
            print(i)
            for c in ch:
                self.ch[c].get_curve(reset=False)
            self.scope.write('ACQ:STATE RUN')
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')
        for c in ch:
            self.ch[c].scale()

    def plot(self):
        pass

    def set_acquisition(self, acq_mode='SAM', n=64):
        acq_mode = acq_mode.upper()
        acq_types = {'AVE', 'SAM', 'ENV'}
        if acq_mode not in acq_types:
            print('ERROR: ACQ TYPE')

        self.scope.write('ACQ:MOD ' + acq_mode)
        if acq_mode == 'AVE':
            self.scope.write('ACQ:NUMAV ' + str(n))
        if acq_mode == 'ENV':
            self.scope.write('ACQ:NUME ' + str(n))


class OSCChannel(object):
    def __init__(self, scope, ch):
        self.ch = ch
        self.on = False
        self.scope = scope
        self.name = 'CH{0}'.format(ch)
        self.pre = ''
        self.y_scale = 0
        self.y_zero = 0
        self.y_offset = 0
        self.x_inc = 0
        self.data = []
        self.raw = []
        self.avg = 0
        self.avg_raw = ''
        self.avg_pre = ''
        self.env = 0
        self.env_raw = ''
        self.evn_pre = ''
        self.t = []
        self.n = 0

        self.update()

    def activate(self):
        if not self.on:
            self.scope.write('SEL:' + self.name + ' ON')
            self.scope.query('*OPC?')
            self.on = True

    def select(self):
        sel = self.scope.query('SEL:' + self.name + '?')
        self.on = int(sel) == 1
        self.scope.write('DATA:SOU ' + self.name)
        self.scope.query('*OPC?')

    def update(self):
        self.select()
        if not self.on:
            self.activate()

        self.scope.write('DATA:WIDTH 1')
        self.scope.write('DATA:ENC RPB')

        self.pre = self.scope.query('WFMP?')
        self.y_scale = float(self.scope.query('WFMPRE:YMULT?'))
        self.y_zero = float(self.scope.query('WFMPRE:YZERO?'))
        self.y_offset = float(self.scope.query('WFMPRE:YOFF?'))
        self.x_inc = float(self.scope.query('WFMPRE:XINCR?'))

        self.raw = list()

    def get_curve(self, reset=True):
        if reset:
            self.raw = list()
        self.scope.write('DATA:SOU ' + self.name)
        self.scope.query('*OPC?')
        self.scope.write('CURVE?')
        self.raw.append(self.scope.read_raw())

    def get_average(self):
        acq_mode = self.scope.query('ACQ:MOD?')
        if acq_mode[0:3] != 'AVG':
            self.scope.write('ACQ:MOD AVE')
            n = self.scope.query('ACQ:NUMAV?')
            print('-----> Default setting for ENVELOPE: N = ' + str(n))
        self.scope.write('DATA:WIDTH 2')
        self.scope.write('DATA:ENC RPB')

        self.scope.write('DATA:SOU ' + self.name)
        self.scope.query('*OPC?')

        self.avg_pre = self.scope.query('WFMP?')
        self.y_scale = float(self.scope.query('WFMPRE:YMULT?'))
        self.y_zero = float(self.scope.query('WFMPRE:YZERO?'))
        self.y_offset = float(self.scope.query('WFMPRE:YOFF?'))
        self.x_inc = float(self.scope.query('WFMPRE:XINCR?'))
        self.scope.query('*OPC?')

        # Single sequence and wait
        self.scope.write('ACQ:STOPA SEQ')
        while int(self.scope.query('BUSY?')):
            print('AVERAGE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
            time.sleep(0.05)
        self.scope.write('CURVE?')

        self.avg_raw = self.scope.read_raw()
        raw = self.avg_raw
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 0)
        self.avg = (data - self.y_offset) * self.y_scale + self.y_zero

        # Run state
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')

    def get_envelope(self):
        acq_mode = self.scope.query('ACQ:MOD?')
        if acq_mode[0:3] != 'ENV':
            self.scope.write('ACQ:MOD ENV')
            n = self.scope.query('ACQ:NUME?')
            print('-----> Default setting for ENVELOPE: N = ' + str(n))
        self.scope.write('DATA:WIDTH 2')
        self.scope.write('DATA:ENC RPB')
        self.scope.query('*OPC?')

        self.scope.write('DATA:SOU ' + self.name)
        self.scope.query('*OPC?')

        self.env_pre = self.scope.query('WFMP?')
        self.y_scale = float(self.scope.query('WFMPRE:YMULT?'))
        self.y_zero = float(self.scope.query('WFMPRE:YZERO?'))
        self.y_offset = float(self.scope.query('WFMPRE:YOFF?'))
        self.x_inc = float(self.scope.query('WFMPRE:XINCR?'))
        self.scope.query('*OPC?')

        # Single sequence and wait
        self.scope.write('ACQ:STOPA SEQ')
        while int(self.scope.query('BUSY?')):
            print('ENVELOPE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
            time.sleep(0.05)
        self.scope.write('CURVE?')

        self.env_raw = self.scope.read_raw()
        raw = self.env_raw
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        # data = np.array(unpack('%sB' % len(data), data))
        data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 0)
        self.env = (data - self.y_offset) * self.y_scale + self.y_zero

        # Back to Run state
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')

    def scale(self, raw=False):
        # Calculate average
        npts = len(self.raw)
        for i in range(npts):
            raw = self.raw[i]
            h_len = 2 + int(raw[1])
            data = raw[h_len:-1]
            data = np.array(unpack('%sB' % len(data), data))
            # data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 7)
            data = (data - self.y_offset) * self.y_scale + self.y_zero
            if i == 0:
                self.data = data / float(npts)
            else:
                self.data += data / float(npts)
        self.t = np.arange(0, self.x_inc * len(self.data), self.x_inc)

    def auto_scale(self):
        target_max = 223.0
        target_min = 32.0
        self.get_curve()
        data = self.extract_curve()
        val_max = float(max(data))
        val_min = float(min(data))
        m = (target_min - target_max) / (val_min - val_max)
        b = target_max / m - val_max
        scale = float(self.scope.query('CH1:SCAL?'))
        pos = float(self.scope.query('CH1:POS?'))
        npos = b * 10.0 / 255.0 /m*scale + pos
        self.scope.write('CH1:SCALE ' + str(scale / m))

        # self.get_curve()
        # data = self.extract_curve()
        val_min = min(data)
        val_max = max(data)
        if val_min > 0:
            dpos = (val_min * 10. / 255. - 5 + 4)
        else:
            dpos = (val_max * 10. / 255. - 5 - 4)
        npos = pos - dpos
        self.scope.write('CH1:POS ' + str(npos))
        self.scope.write('*WAI')
        print 'abc'



    def extract_curve(self, i=0):
        raw = self.raw[i]
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        data = np.array(unpack('%sB' % len(data), data))
        return data


def main():
    osc = TDS3054B()
    ch = [1, 2, 3, 4]
    osc.read_avg(n=16, ch=ch)
    pylab.clf()
    for c in ch:
        pylab.plot(osc.ch[c].t, osc.ch[c].data)
    pylab.legend(['1', '2', '3', '4'])
    pylab.show()


if __name__ == "__main__":
    main()
