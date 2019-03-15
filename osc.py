


import visa
import numpy as np
from struct import unpack
import pylab

import gzip
import cPickle as pickle
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
        self.ch[ch].update()
        self.ch[ch].get_curve()
        self.ch[ch].scale()
        return self.ch[ch].data

    def read_repeats(self, n=128, ch=None):
        if ch is None:
            ch = [1, 2, 3, 4]
        for c in ch:
            self.ch[c].activate()
            self.ch[c].update()
        acq_mode = self.scope.query('ACQ:MOD?')
        if acq_mode[0:3] != 'SAM':
            self.scope.write('ACQ:MOD SAM')
            print('-----> Changing ACQUISITION mode to: SAMPLE')

        # Stop between wfm gathering
        self.scope.write('ACQ:STOPA SEQ')
        for i in range(n):
            print('SAMPLE: ' + str(i))
            for c in ch:
                self.ch[c].get_curve(reset=False)
            self.scope.write('ACQ:STATE RUN')
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')
        res = list()
        for c in ch:
            self.ch[c].scale()
            res.append(self.ch[c].data)
        return np.array(res).transpose()

    def read_average(self, ch=None, n=512):
        if ch is None:
            ch = [1, 2, 3, 4]
        for c in ch:
            self.ch[c].activate()
            self.ch[c].update()
        acq_mode = self.scope.query('ACQ:MOD?')
        acq_n = self.scope.query('ACQ:NUMAV?')
        if acq_mode[0:3] != 'AVE':
            self.scope.write('ACQ:MOD AVE')
            print('-----> Changing ACQUISITION mode to AVERAGE: N = ' + str(n))
        self.scope.write('ACQ:NUMAV ' + str(n))
        self.scope.write('DATA:WIDTH 2')
        self.scope.write('DATA:ENC RPB')
        self.scope.query('*OPC?')

        # Read all channels
        self.scope.write('ACQ:STOPA SEQ')
        while int(self.scope.query('BUSY?')):
            print('AVERAGE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
            time.sleep(0.05)
        for c in ch:
            print('CHANNEL: ' + str(c))
            self.ch[c].get_envelope(single=False, n=n)

        # Set acquisiton mode back and Run state
        self.scope.write('ACQ:MOD ' + acq_mode)
        self.scope.write('ACQ:NUMAV ' + str(acq_n))
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')

        ret = list()
        for c in ch:
            ret.append(self.ch[c].env)
        return np.array(ret).transpose()

    def read_envelope(self, ch=None, n=512):
        if ch is None:
            ch = [1, 2, 3, 4]
        for c in ch:
            self.ch[c].activate()
            self.ch[c].update()
        acq_mode = self.scope.query('ACQ:MOD?')
        acq_n = self.scope.query('ACQ:NUME?')
        if acq_mode[0:3] != 'ENV':
            self.scope.write('ACQ:MOD ENV')
            print('-----> Changing ACQUISITION mode to ENVELOPE: N = ' + str(n))
        self.scope.write('ACQ:NUME ' + str(n))
        self.scope.write('DATA:WIDTH 2')
        self.scope.write('DATA:ENC RPB')
        self.scope.query('*OPC?')

        # Read all channels
        self.scope.write('ACQ:STOPA SEQ')
        while int(self.scope.query('BUSY?')):
            print('ENVELOPE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
            time.sleep(0.05)
        for c in ch:
            print('CHANNEL: ' + str(c))
            self.ch[c].get_envelope(single=False, n=n)

        # Set acquisiton mode back and Run state
        self.scope.write('ACQ:MOD ' + acq_mode)
        self.scope.write('ACQ:NUME ' + str(acq_n))
        self.scope.write('ACQ:STOPA RUNST')
        self.scope.write('ACQ:STATE RUN')

        ret = list()
        for c in ch:
            ret.append(self.ch[c].env)
        return np.array(ret).transpose()


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

    def save(self, file_name=None):
        if file_name is None:
            file_name = time.strftime("%Y%m%d%H%M%S.pkl.gz")

        data = dict()
        for ch in [1, 2, 3, 4]:
            ch_data = dict()
            ch_data['env'] = self.ch[ch].env
            ch_data['env_n'] = self.ch[ch].env_n
            ch_data['env_raw'] = self.ch[ch].env_raw
            ch_data['env_pre'] = self.ch[ch].env_pre

            ch_data['avg'] = self.ch[ch].avg
            ch_data['avg_n'] = self.ch[ch].avg_n
            ch_data['avg_raw'] = self.ch[ch].avg_raw
            ch_data['avg_pre'] = self.ch[ch].avg_pre

            ch_data['repeats'] = self.ch[ch].repeats
            ch_data['raw'] = self.ch[ch].raw
            ch_data['pre'] = self.ch[ch].pre

            data[ch] = ch_data
        with gzip.GzipFile(file_name, 'w') as f:
            pickle.dump(data, f)

        return 0, file_name

    def load(self, file_name):
        if file_name is None:
            print('ERROR: specify a file name')
            return None
        with gzip.GzipFile(file_name, 'r') as f:
            data = pickle.load(f)

        return data


    def read_all(self, n=512, nr=128, ch=[1, 2, 3, 4]):
        self.read_average(n=n, ch=ch)
        self.read_envelope(n=n, ch=ch)
        self.read_repeats(n=nr, ch=ch)


class OSCChannel(object):
    def __init__(self, scope, ch):
        self.ch = ch
        self.on = False
        self.scope = scope
        self.name = 'CH{0}'.format(ch)
        self.y_scale = 0
        self.y_zero = 0
        self.y_offset = 0
        self.x_inc = 0
        self.data = None
        self.pre = ''
        self.raw = []
        self.repeats = None
        self.avg = None
        self.avg_n = 0
        self.avg_raw = ''
        self.avg_pre = ''
        self.env = None
        self.env_n = 0
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

    def get_average(self, n=None, single=True):
        acq_mode = self.scope.query('ACQ:MOD?')
        acq_n = self.scope.query('ACQ:NUMAV?')
        if n is None:
            n = acq_n
        self.scope.write('ACQ:NUMAV ' + str(n))
        if single:
            if acq_mode[0:3] != 'AVG':
                self.scope.write('ACQ:MOD AVE')
                n = self.scope.query('ACQ:NUMAV?')
                print('-----> Default setting for AVERAGE: N = ' + str(n))
            self.scope.write('DATA:WIDTH 2')
            self.scope.write('DATA:ENC RPB')

        self.activate()
        self.select()

        self.avg_pre = self.scope.query('WFMP?')
        self.y_scale = float(self.scope.query('WFMPRE:YMULT?'))
        self.y_zero = float(self.scope.query('WFMPRE:YZERO?'))
        self.y_offset = float(self.scope.query('WFMPRE:YOFF?'))
        self.x_inc = float(self.scope.query('WFMPRE:XINCR?'))
        self.scope.query('*OPC?')

        # Single sequence and wait
        if single:
            self.scope.write('ACQ:STOPA SEQ')
            while int(self.scope.query('BUSY?')):
                print('AVERAGE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
                time.sleep(0.05)
        self.scope.write('CURVE?')
        self.avg_raw = self.scope.read_raw()
        self.avg_n = n

        # Scale results
        raw = self.avg_raw
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 0)
        self.avg = (data - self.y_offset) * self.y_scale + self.y_zero

        # Set acquisiton mode back and Run state
        if single:
            self.scope.write('ACQ:MOD ' + acq_mode)
            self.scope.write('ACQ:NUMAV ' + str(acq_n))
            self.scope.write('ACQ:STOPA RUNST')
            self.scope.write('ACQ:STATE RUN')

    def get_envelope(self, n=None, single=True):
        acq_mode = self.scope.query('ACQ:MOD?')
        acq_n = self.scope.query('ACQ:NUME?')
        if n is None:
            n = acq_n
        self.scope.write('ACQ:NUME ' + str(n))
        if single:
            if acq_mode[0:3] != 'ENV':
                self.scope.write('ACQ:MOD ENV')
                print('-----> Default setting for ENVELOPE: N = ' + str(n))
            self.scope.write('DATA:WIDTH 2')
            self.scope.write('DATA:ENC RPB')
            self.scope.query('*OPC?')

        self. activate()
        self.select()

        self.env_pre = self.scope.query('WFMP?')
        self.y_scale = float(self.scope.query('WFMPRE:YMULT?'))
        self.y_zero = float(self.scope.query('WFMPRE:YZERO?'))
        self.y_offset = float(self.scope.query('WFMPRE:YOFF?'))
        self.x_inc = float(self.scope.query('WFMPRE:XINCR?'))
        self.scope.query('*OPC?')

        # Single sequence and wait
        if single:
            self.scope.write('ACQ:STOPA SEQ')
            while int(self.scope.query('BUSY?')):
                print('ENVELOPE: ' + str(int(self.scope.query('ACQ:NUMAC?'))))
                time.sleep(0.05)
        self.scope.write('CURVE?')
        self.env_raw = self.scope.read_raw()
        self.env_n = n

        # Scale results
        raw = self.env_raw
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        # data = np.array(unpack('%sB' % len(data), data))
        data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 0)
        self.env = (data - self.y_offset) * self.y_scale + self.y_zero

        # Set acquisition mode back and Run state
        if single:
            self.scope.write('ACQ:MOD ' + acq_mode)
            self.scope.write('ACQ:NUME ' + str(acq_n))
            self.scope.write('ACQ:STOPA RUNST')
            self.scope.write('ACQ:STATE RUN')

    def scale(self, raw=False):
        # Calculate average
        npts = len(self.raw)
        rep = list()
        for i in range(npts):
            raw = self.raw[i]
            h_len = 2 + int(raw[1])
            data = raw[h_len:-1]
            data = np.array(unpack('%sB' % len(data), data))
            # data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 7)
            data = (data - self.y_offset) * self.y_scale + self.y_zero
            rep.append(data)
        self.repeats = np.array(rep).transpose()
        self.data = np.average(self.repeats, axis=1)
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
    scope = TDS3054B()
    ch = [1, 2, 3, 4]
    scope.read_all(ch=ch, n=4, nr=5)
    pylab.clf()
    for c in ch:
        pylab.plot(scope.ch[c].t, scope.ch[c].data)
    pylab.legend(['1', '2', '3', '4'])
    pylab.show()

    ret, file_name = scope.save()
    scope.load(file_name)




if __name__ == "__main__":
    main()
