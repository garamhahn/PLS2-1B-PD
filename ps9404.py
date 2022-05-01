#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 런 시켜놓고 측정해보자
import win32com.client as com
import time
import datetime


def R(h, st):
    res = h.ExecCommand(st)
    #print(res)
    return res

def pico_init():
    ph = com.Dispatch("PicoSample4.COMRC")
    time.sleep(1)

    batchcmd = """
Header On
Ch2:Display? Off
Ch3:Display? Off
Ch4:Display? Off
Wfm:Source? Ch1
Acq:HiResChs Ch1
    
Trig:Mode? Trig # Free
Trig:HoldoffBy Time
Trig:HoldoffTime 1e-6 # 1 us

Trig:Analog:Source? CH4
Trig:Analog:Style? Edge
Trig:Analog:Ch4:Level? 0.4
Trig:Analog:Ch4:Slope? Pos
Trig:Analog:Ch4:Sensitivity? High
    
Ch1:Scale? 0.050
Ch1:Position? -2
Ch1:Band? Full #0.01 to 0.25
    
TB:Priority:Primary? HorScale
TB:Priority:Secondary? SmplRate #RecLength,SmplRate,HorScale
TB:Delay? 340e-9 #340, 540
Instr:TimeBase:SampleModeSet? RandomET #RealTime,RandomET,Roll,Auto
Instr:TimeBase:ScaleT? 100e-9; SmplRate? 100e9; RecLen 1e5
Acq:Mode Average #Sample, Average, EnvMinMax, EnvMin, EnvMax, PeakDetect, HighRes, Segmented
Acq:NAvg 4096

Save:Disk:FileType Wfm
Save:Disk:Source Ch1
Save:Disk:FileFormat? YOnly
Save:Disk:NameMode? Manual
*RunControl? Run #Stop, Single, Run
#Save:Setup:SvAsDefault
    """

    for cmd in batchcmd.split("\n"):
        if cmd.startswith(" ") or cmd.startswith("#") or len(cmd) < 2:
            continue
        comment_index = cmd.find("#")
        if comment_index != -1:
            execmd = cmd[:comment_index]
        else:
            execmd = cmd
        R(ph, execmd)
        print(execmd)
        time.sleep(0.25)

    return ph



#
# import numpy as np
# import matplotlib.pyplot as plt
#
# STRFORMAT= "%y%m%d%H%M%S"
# i = 0
# #while True:
# for k in range(2):
#     now = datetime.datetime.now()
#     dt = now.strftime(STRFORMAT)
#     fname = f"D:\\FPMDATA\\{dt:s}"
#     fdata = list()
#     R(f"Save:Disk:FileName {fname:s}")
#     time.sleep(0.1)
#     res = R("Save:Disk:ExecSave")
#     print(res)
#     time.sleep(2) # 현재 작동 중인지 끝났는지 알 방법이 없음.
#     # with open(f"{fname:s}") as fi:
#     #     for line in fi.readlines():
#     #         try:
#     #             fdata.append(float(line.replace(' ', '').strip()))
#     #         except:
#     #             break
#     #plt.figure()
#     #plt.plot(np.arange(len(fdata)), fdata, '.')
#     #plt.title(f'{fname:s}')
#     #plt.tight_layout()
#     #plt.savefig(f'{fname}.png')
#     #plt.close()
#
#
#

