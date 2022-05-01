# -*- coding: utf-8 -*-
import os, time
from constants import *

import numpy as np
from scipy.signal import filtfilt, butter, freqs
from scipy.optimize import curve_fit

# PSF_DIODE2 = pow(29.05, 2) # 기존
PSF_DIODE2 = pow(28.4, 2) # 재측정
# PSF_DIODE2 = pow(27.7, 2)

def ana211228plot(filepath):
    from matplotlib import pyplot as plt

    # 파일 찾기
    while not os.path.exists(filepath):
        # print(f'waiting for {filepath:s} is ready')
        time.sleep(0.25)
    time.sleep(2)

    # 파일 열어서 전부 숫자로 바꾸고 배열화
    raw = []
    with open(filepath) as fin:
        for line in fin.readlines():
            try:
                raw.append(float(line.replace(' ', '').strip()))
            except:
                pass

    DATALENGTH = len(raw)
    FREQ_DOMAIN_MAX = DATALENGTH / DT

    ts_, vs_ = np.linspace(0., DT, DATALENGTH), np.array(raw)
    nyqf = 0.5 * FREQ_DOMAIN_MAX
    b_, a_ = butter(5, fCUTOFF / nyqf)
    vs_filt0 = filtfilt(b_, a_, vs_)
    # dT = t_total / DATALENGTH

    # 1. 필링패턴 뽑기
    #  항상 250k data point를 가져오면, 2 ns 마다 peak는 하나씩 있어야 한다.
    #  1 us time window는 500 MHz 번치가 500 개 들어있다.
    #  250,000 데이터 포인트면 500 개의 점이 2 ns 다.
    N_BUNCH = int(DT * RF_FREQ) # 한 바퀴에 있는 번치 개수가 아니라 1 us 안에 있는 번치
    N_POINTS_FOR_BUCKET = int(DATALENGTH / N_BUNCH)
    p_phase_shift = int(150/2.5) # 250k data sample시 150, 100k sample시 150/2.5
    # print(t_total, RF_FREQ)
    # print(DATALENGTH, N_POINTS_FOR_BUCKET, N_BUNCH)

    bunches = []
    bunches_raw = []
    # 320ns delay인 경우, trigger position에 의해 첫 번째 번치는 2번 건너뛰고 시작함
    first_bunch_id = 2
    for i in range(N_BUNCH_REAL):
        j = (first_bunch_id+i)*N_POINTS_FOR_BUCKET + p_phase_shift
        bunches_raw.append(np.array(raw[j:j+N_POINTS_FOR_BUCKET]))
        bunches.append(np.array(vs_filt0[j:j+N_POINTS_FOR_BUCKET]))

    # # 파형
    # ts_single_bucket = np.linspace(0., BUCKET_LENGTH/pico, N_POINTS_FOR_BUCKET)
    # for bunch in bunches:
    #     plt.plot(ts_single_bucket, bunch, color='k', alpha=0.5)
    # plt.xlabel('time [ps]')
    # plt.ylabel('voltage [V]')

    # histogram, 평소에는 이걸로 ground level을 detection 하면 된다.
    n_, bins_ = np.histogram(vs_filt0, bins=500)
    idx = np.argmax(n_)
    ground_level = bins_[idx]

    #  - 개별 데이터 핏
    #    룹 돌면서 threshold 넘는 데이터들에서 피크 하나씩 찾고 각각을 핏팅 이때는 로데이터로,
    #    결과물 : t위치, 높이, 너비 및 각각의 에러바
    def gaussf(x, *p):
        A, mu, sigma = p
        return A * np.exp(-(x - mu) ** 2 / (2. * sigma ** 2)) + ground_level

    bunch_amp_norm = []
    bunch_amp_norm_err = []
    bunch_length = []
    bunch_length_err = []
    # bunch_center = []
    # bunch_center_err = []

    sigma_init = 20 * pico
    t_arr = np.linspace(0., BUCKET_LENGTH, N_POINTS_FOR_BUCKET)
    for i_b, bunch in enumerate(bunches):

        ii = np.argmax(bunch)
        mu_init = t_arr[ii]
        A_init = bunch[ii]
        b_amp=0.0
        b_center=0.0
        b_length=0.0
        b_amp_err=0.0
        b_center_err=0.0
        b_length_err=0.0

        if A_init < V_THRESHOLD:
            bunch_amp_norm.append(b_amp)
            # bunch_center.append(b_center)
            bunch_length.append(b_length)

            bunch_amp_norm_err.append(b_amp_err)
            # bunch_center_err.append(b_center_err)
            bunch_length_err.append(b_length_err)
            continue

        try:
            popt, pcov = curve_fit(gaussf, t_arr, bunch,
                                   p0=[A_init, mu_init, sigma_init])
            b_amp, b_center, b_length = popt
            b_amp_err, b_center_err, b_length_err = np.sqrt(np.diag(pcov))
        except:
            print('optimization error!')

        # b_amp -= ground_level
        filt_max = max(bunch)
        #bunch_amp_norm.append( b_amp ) # fit value

        bunch_amp_norm.append( filt_max )
        bunch_amp_norm_err.append(b_amp_err)
        #bunch_amp_norm_diff.append( b_amp - filt_max )

        # bunch_center.append( b_center*TO_PICO_SECOND )
        # bunch_center_err.append(b_center_err * TO_PICO_SECOND)

        bunch_length.append( np.sqrt(pow(b_length*TO_PICO_SECOND,2) - PSF_DIODE2) )
        bunch_length_err.append(b_length_err*TO_PICO_SECOND)

        if i_b == 1:
            plt.plot(t_arr/pico, bunches_raw[i_b], '.',
                     c='blue', label='raw data')
            plt.plot(t_arr/pico, bunch, '-',
                     c='k', label='filtered')
            plt.plot(t_arr/pico, gaussf(t_arr, b_amp, b_center, b_length), '--',
                     c='red', label='Gaussian fit')
            plt.xlabel('time [ps]')
            plt.ylabel('voltage [V]')
            plt.legend()
            plt.title(f'Bunch Sample ({i_b:d}/470)')

    norm_const = 1.0 / np.sum(bunch_amp_norm) #* CHARGE
    bunch_amp_norm = np.array(bunch_amp_norm) * norm_const
    bunch_amp_norm_err = np.array(bunch_amp_norm_err) * norm_const

    # for i in range(470):
    #     if bunch_length[i] > 0.0:
    #         print(f' {i:d}({bunch_amp_norm[i]*1e9:.2f} nC) : {bunch_length[i]:.2f}+-{bunch_length_err[i]:.2f} ps')

    # RING_CURRENT = 250.1e-3 # pv 호출로 대체
    # RING_CHARGE = RING_CURRENT * (1.0 * micro * second)


    ids = np.arange(N_BUNCH_REAL)
    # print(len(bunch_amp_norm))
    plt.figure()
    plt.plot(ids, bunch_amp_norm, '.')
    plt.title('Bunch Amplitude, normalized')
    plt.xlabel('bunch id [-]')
    plt.ylabel('arb unit [-]')
    # plt.legend(loc='upper left')
    plt.tight_layout()

    # plt.figure()
    # plt.errorbar(ids, bunch_center, yerr=bunch_center_err,
    #              fmt='o',
    #              markeredgecolor='black',
    #              markerfacecolor='red',
    #              label='Laser')
    # plt.title(f'Bunch Center')
    # plt.xlabel('bunch id [-]')
    # plt.ylabel('bunch center [ps]')
    # plt.grid()
    # plt.legend()

    # plt.figure()
    # plt.plot(ids, bunch_amp_norm, '+', c='k')
    # plt.title(f'Normalized bunch current')
    # plt.xlabel('bunch id [-]')
    # plt.ylabel('current [-]')


    plt.figure()
    plt.errorbar(ids, bunch_length, yerr=bunch_length_err,
                 fmt='o',
                 markeredgecolor='black',
                 markerfacecolor='red',
                 label='PhotoDiode')
    # plt.errorbar(ids, bunch_length2, yerr=bunch_length_err,
    #              fmt='o', markeredgecolor='black',
    #              markerfacecolor='black', label='Cal. using Streak Cam.')
    plt.title(f'Bunch Length')
    plt.xlabel('bunch id [-]')
    plt.ylabel('bunch length [ps]')
    plt.grid()
    plt.legend()
    plt.show()

    pvs = {
        'raw': raw,
        'bunch_length': bunch_length,
        'bunch_length_err': bunch_length_err,
        'bunch_amp_norm': bunch_amp_norm.tolist(),
        'bunch_amp_norm_err': bunch_amp_norm_err.tolist()
    }
    return pvs


def ana211228(filepath):

    # 파일 찾기
    while not os.path.exists(filepath):
        # print(f'waiting for {filepath:s} is ready')
        time.sleep(0.25)
    time.sleep(2)

    # 파일 열어서 전부 숫자로 바꾸고 배열화
    raw = []
    with open(filepath) as fin:
        for line in fin.readlines():
            try:
                raw.append(float(line.replace(' ', '').strip()))
            except:
                pass

    DATALENGTH = len(raw)
    FREQ_DOMAIN_MAX = DATALENGTH / DT

    ts_, vs_ = np.linspace(0., DT, DATALENGTH), np.array(raw)
    nyqf = 0.5 * FREQ_DOMAIN_MAX
    b_, a_ = butter(5, fCUTOFF / nyqf)
    vs_filt0 = filtfilt(b_, a_, vs_)
    # dT = t_total / DATALENGTH

    # 1. 필링패턴 뽑기
    #  항상 250k data point를 가져오면, 2 ns 마다 peak는 하나씩 있어야 한다.
    #  1 us time window는 500 MHz 번치가 500 개 들어있다.
    #  250,000 데이터 포인트면 500 개의 점이 2 ns 다.
    N_BUNCH = int(DT * RF_FREQ) # 한 바퀴에 있는 번치 개수가 아니라 1 us 안에 있는 번치
    N_POINTS_FOR_BUCKET = int(DATALENGTH / N_BUNCH)
    p_phase_shift = int(150/2.5) # 250k data sample시 150, 100k sample시 150/2.5
    # print(t_total, RF_FREQ)
    # print(DATALENGTH, N_POINTS_FOR_BUCKET, N_BUNCH)

    bunches = []
    bunches_raw = []
    # 320ns delay인 경우, trigger position에 의해 첫 번째 번치는 2번 건너뛰고 시작함
    first_bunch_id = 2
    for i in range(N_BUNCH_REAL):
        j = (first_bunch_id+i)*N_POINTS_FOR_BUCKET + p_phase_shift
        bunches_raw.append(np.array(raw[j:j+N_POINTS_FOR_BUCKET]))
        bunches.append(np.array(vs_filt0[j:j+N_POINTS_FOR_BUCKET]))

    # # 파형
    # ts_single_bucket = np.linspace(0., BUCKET_LENGTH/pico, N_POINTS_FOR_BUCKET)
    # for bunch in bunches:
    #     plt.plot(ts_single_bucket, bunch, color='k', alpha=0.5)
    # plt.xlabel('time [ps]')
    # plt.ylabel('voltage [V]')

    # histogram, 평소에는 이걸로 ground level을 detection 하면 된다.
    n_, bins_ = np.histogram(vs_filt0, bins=500)
    idx = np.argmax(n_)
    ground_level = bins_[idx]

    #  - 개별 데이터 핏
    #    룹 돌면서 threshold 넘는 데이터들에서 피크 하나씩 찾고 각각을 핏팅 이때는 로데이터로,
    #    결과물 : t위치, 높이, 너비 및 각각의 에러바
    def gaussf(x, *p):
        A, mu, sigma = p
        return A * np.exp(-(x - mu) ** 2 / (2. * sigma ** 2)) + ground_level

    bunch_amp = []
    bunch_amp_norm = []
    bunch_amp_norm_err = []
    bunch_length = []
    bunch_length_err = []
    # bunch_center = []
    # bunch_center_err = []

    sigma_init = 20 * pico
    t_arr = np.linspace(0., BUCKET_LENGTH, N_POINTS_FOR_BUCKET)
    for i_b, bunch in enumerate(bunches):
        ii = np.argmax(bunch)
        mu_init = t_arr[ii]
        A_init = bunch[ii]
        b_amp=0.0
        b_center=0.0
        b_length=0.0
        b_amp_err=0.0
        b_center_err=0.0
        b_length_err=0.0

        if A_init < V_THRESHOLD:
            bunch_amp.append(b_amp)
            # bunch_center.append(b_center)
            bunch_length.append(b_length)

            bunch_amp_norm_err.append(b_amp_err)
            # bunch_center_err.append(b_center_err)
            bunch_length_err.append(b_length_err)
            continue

        try:
            popt, pcov = curve_fit(gaussf, t_arr, bunch,
                                   p0=[A_init, mu_init, sigma_init])
            b_amp, b_center, b_length = popt
            b_amp_err, b_center_err, b_length_err = np.sqrt(np.diag(pcov))
        except:
            print('optimization error!')

        # b_amp -= ground_level
        filt_max = max(bunch)
        #bunch_amp_norm.append( b_amp ) # fit value

        bunch_amp.append( filt_max )
        bunch_amp_norm_err.append(b_amp_err)
        #bunch_amp_norm_diff.append( b_amp - filt_max )

        # bunch_center.append( b_center*TO_PICO_SECOND )
        # bunch_center_err.append(b_center_err * TO_PICO_SECOND)

        bunch_length.append( np.sqrt(pow(b_length*TO_PICO_SECOND,2) - PSF_DIODE2) )
        bunch_length_err.append(b_length_err*TO_PICO_SECOND)

    if np.sum(bunch_amp) == 0:
        norm_const = 1 # SUM 0이면 1/0 생겨서 계산안됨
    else:
        norm_const = 1.0 / np.sum(bunch_amp) #* CHARGE
    bunch_amp_norm = np.array(bunch_amp) * norm_const
    bunch_amp_norm_err = np.array(bunch_amp_norm_err) * norm_const

    pvs = {
        'raw': raw,
        'bunch_length': bunch_length,
        'bunch_length_err': bunch_length_err,
        'bunch_amp': np.sum(bunch_amp),
        'bunch_amp_norm': bunch_amp_norm.tolist(),
        'bunch_amp_norm_err': bunch_amp_norm_err.tolist()
    }

    b_ = []
    for length in bunch_length:
        if length != 0.0:
            b_.append(length)
    try:
        pvs['bunch_length_ave'] = np.average(b_)
        pvs['bunch_length_min'] = np.min(b_)
        pvs['bunch_length_max'] = np.max(b_)
        pvs['bunch_length_std'] = np.std(b_)
    except:
        pvs['bunch_length_ave'] = 0
        pvs['bunch_length_min'] = 0
        pvs['bunch_length_max'] = 0
        pvs['bunch_length_std'] = 0

    return pvs


if __name__ == "__main__":
    # plt.figure()
    #ana211027(None, "211027161322", 1.0e-6)
    # ana211027(None, "D:/FPMDATA/211110152532", 1.0e-6)
    # plt.show()
    pass
