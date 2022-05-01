# -*- coding: utf-8 -*-

import datetime
import pickle
from ps9404 import pico_init, R
from fpm_analysis3 import *
from epics import PV
import numpy as np

MIN_CURRENT = 30.0 # mA
COUNT_MAX = 10

# 빔전류가 nontype으로 나오는 일 생김
pv_curr = PV('SR:G00:BEAMCURRENT_T')

def get_current_safely():
    count = 0
    while True:
        count += 1
        ring_current = pv_curr.get()

        if count == COUNT_MAX:
            return 0.0

        if ring_current is None:
            time.sleep(1.0)
            print(f'DCCT update fault{datetime.datetime.now()}')
            continue
        else:
            return ring_current


pv_raw = PV('1B:PD:RAW')
pv_bunch_length = PV('1B:PD:BUNCH_LENGTH')
pv_bunch_length_err = PV('1B:PD:BUNCH_LENGTH_ERR')
pv_bunch_current = PV('1B:PD:BUNCH_CURRENT')
pv_bunch_current_err = PV('1B:PD:BUNCH_CURRENT_ERR')
pv_bunch_amp = PV('1B:PD:BUNCH_AMP')

pv_bunch_length_ave = PV('1B:PD:BUNCH_LENGTH_AVE')
pv_bunch_length_min = PV('1B:PD:BUNCH_LENGTH_MIN')
pv_bunch_length_max = PV('1B:PD:BUNCH_LENGTH_MAX')
pv_bunch_length_std = PV('1B:PD:BUNCH_LENGTH_STD')

pv_rfgap1 = PV('SR:RF:FCGAPV1')
pv_rfgap2 = PV('SR:RF:FCGAPV2')
pv_rfgap3 = PV('SR:RF:FCGAPV3')

pico_handler = pico_init()
print('PS9404-16 was initialized.')

STRFORMAT= "%y%m%d%H%M%S"
TEMP_PREFIX = "R:\\"
DATA_PREFIX = "D:\\FPMDATA\\"

# COUNT_ = 43200/24/12 # 60 sec/min x 60 min/hours x 24 hours/day x 0.5 count/sec = 43200 count / day
COUNT_ = 40
count = COUNT_
while True:
    BEAMCURRENT_T = get_current_safely()
    
    if BEAMCURRENT_T < MIN_CURRENT:
        zero_buckets = [0]*N_BUNCH_REAL
        now = datetime.datetime.now()
        dt = now.strftime(STRFORMAT)
        res = {
            'raw': [0]*100000,
            'bunch_length': zero_buckets,
            'bunch_length_err': zero_buckets,
            'bunch_amp': 0,
            'bunch_amp_norm': zero_buckets,
            'bunch_amp_norm_err': zero_buckets,
            'bunch_length_ave': 0,
            'bunch_length_min': 0,
            'bunch_length_max': 0,
            'bunch_length_std': 0
        }
        time.sleep(10)
    else:
        now = datetime.datetime.now()
        dt = now.strftime(STRFORMAT)
        fpath_temp = f"{TEMP_PREFIX:s}{dt:s}"
        R(pico_handler, f"Save:Disk:FileName {fpath_temp:s}")
        R(pico_handler, "Save:Disk:ExecSave")
        # R(pico_handler, "*ClrDispl")
        res = ana211228(fpath_temp)

    try:
        pv_raw.put( res['raw'] )
        pv_bunch_length.put( res['bunch_length'] )
        pv_bunch_length_err.put( res['bunch_length_err'] )

        pv_bunch_length_ave.put( res['bunch_length_ave'])
        pv_bunch_length_min.put( res['bunch_length_min'])
        pv_bunch_length_max.put( res['bunch_length_max'])
        pv_bunch_length_std.put( res['bunch_length_std'])

        # 1. bunch length ave, max, min
        # 2. 흘러내린 번치 디텍션 << 이온 클리어링 갭 [A,B] << 이런 운전 정보를 어디서 세세히 얻지?
        #

        # ring_current = BEAMCURRENT_T
        bunch_current = (np.array(res['bunch_amp_norm'])*BEAMCURRENT_T).tolist()
        bunch_current_err = (np.array(res['bunch_amp_norm_err'])*BEAMCURRENT_T).tolist()

        pv_bunch_amp.put( res['bunch_amp'] )
        pv_bunch_current.put( bunch_current )
        pv_bunch_current_err.put( bunch_current_err )

        rf_gap_vs = [pv_rfgap1.get(), pv_rfgap1.get(), pv_rfgap1.get()]

    except:
        print('epics error')

    try:
        os.remove(fpath_temp)
        # R(pico_handler, "*ClrDispl")
        # time.sleep(5)
    except:
        # print(f'failed to remove {fpath_temp:s}')
        pass

    data = {'raw': res['raw'],
            'bunch_length': res['bunch_length'],
            'bunch_length_err': res['bunch_length_err'],
            'ring_current': BEAMCURRENT_T,
            'bunch_current': bunch_current,
            'bunch_current_err': bunch_current_err,
            'rf_gap_voltage': rf_gap_vs,
            'bunch_length_ave': res['bunch_length_ave'],
            'bunch_length_min': res['bunch_length_min'],
            'bunch_length_max': res['bunch_length_max'],
            'bunch_length_std': res['bunch_length_std'],
            'bunch_amp': res['bunch_amp']
            }
    # RF Voltage 정보 포함.

    # check data
    # inf or nan...

    count -= 1
    if count == 20:
        R(pico_handler, "*ClrDispl")
        time.sleep(10)
    if count == 0:
        count = COUNT_
        R(pico_handler, "*ClrDispl")
        time.sleep(10)
        with open(f'{DATA_PREFIX:s}{dt:s}.pickle', 'wb') as fo:
            pickle.dump(data, fo, pickle.HIGHEST_PROTOCOL)
    # with open(f'{DATA_PREFIX:s}{dt:s}.pickle', 'wb') as fo:
    #     pickle.dump(data, fo, pickle.HIGHEST_PROTOCOL)
