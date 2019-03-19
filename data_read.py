


'''
Read files saved with osc.TDS3054B.read_all
'''

import cPickle as pickle
import gzip
from struct import unpack
import numpy as np


class OscData(object):

    def __init__(self, file_name):
        self.file = file_name
        self.data = self.load()

    def load(self):
        if self.file is None:
            print('ERROR: specify a file name')
            return None
        with gzip.GzipFile(self.file, 'r') as f:
            data = pickle.load(f)
        return data

    def avg(self, ch=1):
        raw = self.data[ch]['avg_raw']
        pre = self.data[ch]['avg_pre']
        wf = WaveForm(pre, raw)
        return wf

    def env(self, ch=1):
        raw = self.data[ch]['env_raw']
        pre = self.data[ch]['env_pre']
        wf = WaveForm(pre, raw)
        return wf

    def rep(self, ch=1):
        raw_list = self.data[ch]['raw']
        pre = self.data[ch]['pre']
        data = list()
        for raw in raw_list:
            wf = WaveForm(pre, raw)
            data.append(wf.val)
        data = np.array(data).transpose()
        wf.val = data
        return wf


class WaveForm(object):
    def __init__(self, pre, raw):
        self._get_preamble(pre)
        self._get_data(raw)
        self._get_time()

    def _get_preamble(self, pre):
        pre = pre.split(';')
        self.byte = int(pre[0])                         # BYT_Nr <NR1>;
        self.bits = int(pre[1])                         # BIT_Nr <NR1>;
        self.enc = pre[2]                               # ENCdg { ASC | BIN };
        self.fmt = pre[3]                               # BN_Fmt {RI | RP};
        self.order = pre[4]                             # BYT_Or {LSB | MSB};
        self.npts = int(pre[5])                         # NR_Pt < NR1 >;
        self.pt_fmt = pre[7]                            # PT_FMT {ENV | Y};
        self.x_incr = float(pre[8])                     # XINcr < NR3 >;
        self.pt_off = int(pre[9])                       # PT_Off < NR1 >;
        self.x_zero = float(pre[10])                    # XZERo < NR3 >;
        self.x_units = pre[11].strip('"\n')             # XUNit < QString >;
        self.y_mult = float(pre[12])                    # YMUlt < NR3 >;
        self.y_zero = float(pre[13])                    # YZEro < NR3 >;
        self.y_off = float(pre[14])                     # YOFf < NR3 >;
        self.y_units = pre[15].strip('"\n')             # YUNit < QString >

        # Process the WFID
        wfid = pre[6].strip('"').split(',')             # WFID < Qstring >;
        self.name = wfid[0].upper()
        self.coupling = wfid[1]
        self.vert = wfid[2]
        self.hori = wfid[3]
        self.points = wfid[4]
        self.mode = wfid[5]


    def _get_data(self, raw):
        h_len = 2 + int(raw[1])
        data = raw[h_len:-1]
        if self.byte == 2:
            data = np.right_shift(unpack('>%sH' % (len(data) / 2,), data), 0)
        if self.byte == 1:
            data = np.array(unpack('%sB' % len(data), data))
        self.val = (data - self.y_off) * self.y_mult + self.y_zero

    def _get_time(self):
        n = self.npts
        self.t = self.x_zero + self.x_incr * (np.arange(n) - self.pt_off)


def main():
    pass


if __name__ == "__main__":
    # main()
    d = OscData('data/VDC_628_D62_LDE_20190318174044.pkl.gz')