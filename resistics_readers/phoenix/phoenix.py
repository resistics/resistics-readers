# import os
# import glob
# import re, struct
# import collections
# import copy
# from datetime import datetime, timedelta
# import numpy as np
# from typing import List, Dict, Tuple

# from resistics.common.checks import consistentChans, isMagnetic, isElectric
# from resistics.common.math import intdiv
# from resistics.common.print import blockPrint
# from resistics.time.data import TimeData
# from resistics.time.reader import TimeReader
# from resistics.time.writer_internal import TimeWriterInternal
# from resistics.time.clean import removeZerosChan, removeNansChan


# from typing import Dict


# def getPhoenixHeaders() -> Dict[str, Dict]:
#     """Returns dictionary of Phoenix format headers

#     Returns
#     -------
#     Dict
#         Returns a dictionary with header words as keys and dictionary as values. The value dictionaries have type information for header values.
#     """
#     headerDict = {
#         "TBVO": {"no": 1, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TBVI": {"no": 2, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SGIN": {"no": 3, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EGNC": {"no": 4, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "HGNC": {"no": 5, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EGN": {"no": 6, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "HGN": {"no": 7, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ACDC": {"no": 8, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ACDH": {"no": 9, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LPFR": {"no": 10, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LFRQ": {"no": 11, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "V5SR": {"no": 12, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MTSR": {"no": 13, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "L2NS": {"no": 14, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "L3NS": {"no": 15, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "L4NS": {"no": 16, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "COMBON": {"no": 17, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MXSC": {"no": 18, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TCMB": {"no": 19, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TALS": {"no": 20, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RN1X": {"no": 21, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RN1Y": {"no": 22, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RN2X": {"no": 23, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RN2Y": {"no": 24, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CSSN": {"no": 25, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CRSS": {"no": 26, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EXED": {"no": 27, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "EXET": {"no": 28, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "INIT": {"no": 29, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TDSP": {"no": 30, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "RQST": {"no": 31, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MODE": {"no": 32, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DISK": {"no": 33, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "XDOS": {"no": 34, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "REBOOT": {"no": 35, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SNUM": {"no": 36, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "VER": {"no": 37, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "HW": {"no": 38, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMPY": {"no": 39, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "SRVY": {"no": 40, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "PMIT": {"no": 41, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "LOUT": {"no": 42, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "SITN": {"no": 43, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "SITF": {"no": 44, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "ATYP": {"no": 45, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FILE": {"no": 46, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "FLEN": {"no": 47, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FILR": {"no": 48, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "FLER": {"no": 49, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FILS": {"no": 50, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "FLES": {"no": 51, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RCBADR": {"no": 52, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "STTOTL": {"no": 53, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "STBADR": {"no": 54, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRCIERR": {"no": 55, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RCIERR": {"no": 56, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LGRIERR": {"no": 57, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "AQST": {"no": 58, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "STIM": {"no": 59, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "ETIM": {"no": 60, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "HTIM": {"no": 61, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "ETMH": {"no": 62, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "HSMP": {"no": 63, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CPTH": {"no": 64, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "EPTH": {"no": 65, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "DPTH": {"no": 66, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "SPTH": {"no": 67, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "SWRT": {"no": 68, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "NPTH": {"no": 69, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "LPTH": {"no": 70, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "TOTL": {"no": 71, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NOBF": {"no": 72, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BADR": {"no": 73, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BADR4": {"no": 74, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SATR": {"no": 75, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTIM": {"no": 76, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "LTIM": {"no": 77, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "STDE": {"no": 78, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "STDH": {"no": 79, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CALS": {"no": 80, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CCLS": {"no": 81, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CALR": {"no": 82, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "BAT1": {"no": 83, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BAT2": {"no": 84, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BAT3": {"no": 85, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TEMP": {"no": 86, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "GFPG": {"no": 87, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FETDEM": {"no": 88, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL1": {"no": 89, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL2": {"no": 90, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL3": {"no": 91, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL4": {"no": 92, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL5": {"no": 93, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL6": {"no": 94, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL7": {"no": 95, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL8": {"no": 96, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL9": {"no": 97, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL10": {"no": 98, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL11": {"no": 99, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRL12": {"no": 100, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FFPG": {"no": 101, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DSP": {"no": 102, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EXAC": {"no": 103, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EXDC": {"no": 104, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EYAC": {"no": 105, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EYDC": {"no": 106, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HXAC": {"no": 107, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HXDC": {"no": 108, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HYAC": {"no": 109, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HYDC": {"no": 110, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HZAC": {"no": 111, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HZDC": {"no": 112, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HAZM": {"no": 113, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HXSN": {"no": 114, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "HYSN": {"no": 115, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "HZSN": {"no": 116, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DECL": {"no": 117, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TSTV": {"no": 118, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FSCV": {"no": 119, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CCLT": {"no": 120, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CFMN": {"no": 121, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CFMX": {"no": 122, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CCMN": {"no": 123, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CCMX": {"no": 124, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HATT": {"no": 125, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HNOM": {"no": 126, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "HAMP": {"no": 127, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CPHC": {"no": 128, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CNOM": {"no": 129, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CAMP": {"no": 130, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NUTC": {"no": 131, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "NSAT": {"no": 132, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LFIX": {"no": 133, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "TSYN": {"no": 134, "ptyp": "AmxPT", "typ": "8b", "vSize": 8},
#         "CLST": {"no": 135, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "OCTR": {"no": 136, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TERR": {"no": 137, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ELEV": {"no": 138, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LATG": {"no": 139, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "LNGG": {"no": 140, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "WFRM": {"no": 141, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ERRW": {"no": 142, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FREQ": {"no": 143, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FACT": {"no": 144, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "PREQ": {"no": 145, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "AUTO": {"no": 146, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FPOC": {"no": 147, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FEND": {"no": 148, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TPFR": {"no": 149, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CPFR": {"no": 150, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TTOT": {"no": 151, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CRMX": {"no": 152, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FCMX": {"no": 153, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CREQ": {"no": 154, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TADJ": {"no": 155, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CRQF": {"no": 156, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ0": {"no": 157, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ1": {"no": 158, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ2": {"no": 159, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ3": {"no": 160, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ4": {"no": 161, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ5": {"no": 162, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ6": {"no": 163, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ7": {"no": 164, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ8": {"no": 165, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FRQ9": {"no": 166, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR10": {"no": 167, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR11": {"no": 168, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR12": {"no": 169, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR13": {"no": 170, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR14": {"no": 171, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR15": {"no": 172, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR16": {"no": 173, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR17": {"no": 174, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR18": {"no": 175, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FR19": {"no": 176, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ASCH": {"no": 177, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SNTX": {"no": 178, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SNTXCOM": {"no": 179, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SNNR": {"no": 180, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SNNRCOM": {"no": 181, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN01": {"no": 182, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN01COM": {"no": 183, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN02": {"no": 184, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN02COM": {"no": 185, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN03": {"no": 186, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN03COM": {"no": 187, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN04": {"no": 188, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN04COM": {"no": 189, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN05": {"no": 190, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SN05COM": {"no": 191, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "COMSTAT": {"no": 192, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "IPSRV0": {"no": 193, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "IPSRV1": {"no": 194, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "IPSRV2": {"no": 195, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "IPSRV3": {"no": 196, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "IPSRVEC": {"no": 197, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "IPSRVTO": {"no": 198, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ENET": {"no": 199, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "ENETIP": {"no": 200, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DHCPUSE": {"no": 201, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "GNET": {"no": 202, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "GNETIP": {"no": 203, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "GNETAP0": {"no": 204, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "GNETAP1": {"no": 205, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "GNETAP2": {"no": 206, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "GNETAP3": {"no": 207, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "PNET": {"no": 208, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "PNETIP": {"no": 209, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "PHNE": {"no": 210, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "PPPNAME": {"no": 211, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "PPPPSWD": {"no": 212, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "FTPSUSR": {"no": 213, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "FTPSPWD": {"no": 214, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "FTPCTIM": {"no": 215, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPCMIN": {"no": 216, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPCSR0": {"no": 217, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPCSR1": {"no": 218, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPCSR2": {"no": 219, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPCSR3": {"no": 220, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPCPRT": {"no": 221, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC1EN": {"no": 222, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC2EN": {"no": 223, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC1P0": {"no": 224, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC1P1": {"no": 225, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC1P2": {"no": 226, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC1P3": {"no": 227, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC2P0": {"no": 228, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC2P1": {"no": 229, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC2P2": {"no": 230, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC2P3": {"no": 231, "ptyp": "LStPT", "typ": "13s", "vSize": 13},
#         "FTPC1DL": {"no": 232, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC1CN": {"no": 233, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC2CN": {"no": 234, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC1ST": {"no": 235, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPC2ST": {"no": 236, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FTPCUSR": {"no": 237, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "FTPCPWD": {"no": 238, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "FILELST": {"no": 239, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "RNET": {"no": 240, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RNETIP": {"no": 241, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "MSTR": {"no": 242, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MSTRSNM": {"no": 243, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MSTRLAT": {"no": 244, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "MSTRLNG": {"no": 245, "ptyp": "PosPT", "typ": "13s", "vSize": 13},
#         "MSTRRNG": {"no": 246, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MSTRBRG": {"no": 247, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EKEY": {"no": 248, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RPWR": {"no": 249, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NADR": {"no": 250, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "UADR": {"no": 251, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MXAD": {"no": 252, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TECH": {"no": 253, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TMSK": {"no": 254, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NUMITEM": {"no": 255, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LIFESTK": {"no": 256, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LIFESTN": {"no": 257, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SITEINC": {"no": 258, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TXTYPE": {"no": 259, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FIXNEG": {"no": 260, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FDRIFT": {"no": 261, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RAMPLEN": {"no": 262, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TXTURN": {"no": 263, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LLENGTH": {"no": 264, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "LWIDTH": {"no": 265, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ARRYTYP": {"no": 266, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NREF": {"no": 267, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN": {"no": 268, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "LINE": {"no": 269, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "SITE": {"no": 270, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "WLOG": {"no": 271, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RLOG": {"no": 272, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SLOG": {"no": 273, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NRXPOS": {"no": 274, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ERXPOS": {"no": 275, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NTXCSRX": {"no": 276, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ETXCSRX": {"no": 277, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TXAZIM": {"no": 278, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "PAZM": {"no": 279, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CHDEF1": {"no": 280, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF2": {"no": 281, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF3": {"no": 282, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "GFC1": {"no": 283, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC2": {"no": 284, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC3": {"no": 285, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS1": {"no": 286, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS1": {"no": 287, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS1": {"no": 288, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ1": {"no": 289, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG1": {"no": 290, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG1": {"no": 291, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS2": {"no": 292, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS2": {"no": 293, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS2": {"no": 294, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ2": {"no": 295, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG2": {"no": 296, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG2": {"no": 297, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS3": {"no": 298, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS3": {"no": 299, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS3": {"no": 300, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ3": {"no": 301, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG3": {"no": 302, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG3": {"no": 303, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES1": {"no": 304, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES2": {"no": 305, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES3": {"no": 306, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV1": {"no": 307, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV2": {"no": 308, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV3": {"no": 309, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV1": {"no": 310, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV2": {"no": 311, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV3": {"no": 312, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG1": {"no": 313, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG2": {"no": 314, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG3": {"no": 315, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TXRES": {"no": 316, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOSTX": {"no": 317, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOSTX": {"no": 318, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOSTX": {"no": 319, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TXLEN": {"no": 320, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEGTX": {"no": 321, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEGTX": {"no": 322, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAGTX": {"no": 323, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHDEFTX": {"no": 324, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "TXCTL": {"no": 325, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHDEFN1": {"no": 326, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEFN2": {"no": 327, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "NPOSN1": {"no": 328, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOSN1": {"no": 329, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEGN1": {"no": 330, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEGN1": {"no": 331, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOSN2": {"no": 332, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOSN2": {"no": 333, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEGN2": {"no": 334, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEGN2": {"no": 335, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RESN1": {"no": 336, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RESN2": {"no": 337, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCVN1": {"no": 338, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCVN2": {"no": 339, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACVN1": {"no": 340, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACVN2": {"no": 341, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAGN1": {"no": 342, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAGN2": {"no": 343, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "REFCTL": {"no": 344, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SRVY1": {"no": 345, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "SRVY2": {"no": 346, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "SRVY3": {"no": 347, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "SRVY4": {"no": 348, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMPY1": {"no": 349, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMPY2": {"no": 350, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMPY3": {"no": 351, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMPY4": {"no": 352, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CLIENT1": {"no": 353, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CLIENT2": {"no": 354, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CLIENT3": {"no": 355, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CLIENT4": {"no": 356, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "AREA1": {"no": 357, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "AREA2": {"no": 358, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "AREA3": {"no": 359, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "AREA4": {"no": 360, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "LOUT1": {"no": 361, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "LOUT2": {"no": 362, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "LOUT3": {"no": 363, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "LOUT4": {"no": 364, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT1": {"no": 365, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT2": {"no": 366, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT3": {"no": 367, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT4": {"no": 368, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT5": {"no": 369, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT6": {"no": 370, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT7": {"no": 371, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CMMNT8": {"no": 372, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHEX": {"no": 373, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHEY": {"no": 374, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHEZ": {"no": 375, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHHX": {"no": 376, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHHY": {"no": 377, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CHHZ": {"no": 378, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TCHN": {"no": 379, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EXR": {"no": 380, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EYR": {"no": 381, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "EZR": {"no": 382, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DXAC": {"no": 383, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DXDC": {"no": 384, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DYAC": {"no": 385, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DYDC": {"no": 386, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EAZM": {"no": 387, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EXLN": {"no": 388, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EYLN": {"no": 389, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "CHDEF4": {"no": 390, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF5": {"no": 391, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF6": {"no": 392, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF7": {"no": 393, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "CHDEF8": {"no": 394, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "GFC4": {"no": 395, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC5": {"no": 396, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC6": {"no": 397, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC7": {"no": 398, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "GFC8": {"no": 399, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS4": {"no": 400, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS4": {"no": 401, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS4": {"no": 402, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ4": {"no": 403, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG4": {"no": 404, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG4": {"no": 405, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS5": {"no": 406, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS5": {"no": 407, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS5": {"no": 408, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ5": {"no": 409, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG5": {"no": 410, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG5": {"no": 411, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS6": {"no": 412, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS6": {"no": 413, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS6": {"no": 414, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ6": {"no": 415, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG6": {"no": 416, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG6": {"no": 417, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS7": {"no": 418, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS7": {"no": 419, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS7": {"no": 420, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ7": {"no": 421, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG7": {"no": 422, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG7": {"no": 423, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS8": {"no": 424, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS8": {"no": 425, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS8": {"no": 426, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SENSIZ8": {"no": 427, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG8": {"no": 428, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG8": {"no": 429, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES4": {"no": 430, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES5": {"no": 431, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES6": {"no": 432, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES7": {"no": 433, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES8": {"no": 434, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV4": {"no": 435, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV5": {"no": 436, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV6": {"no": 437, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV7": {"no": 438, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV8": {"no": 439, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV4": {"no": 440, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV5": {"no": 441, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV6": {"no": 442, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV7": {"no": 443, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV8": {"no": 444, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG4": {"no": 445, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG5": {"no": 446, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG6": {"no": 447, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG7": {"no": 448, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "FLAG8": {"no": 449, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN1R": {"no": 450, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN2R": {"no": 451, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN3R": {"no": 452, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN4R": {"no": 453, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NCHN5R": {"no": 454, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DEF1R1": {"no": 455, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF1R2": {"no": 456, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF1R3": {"no": 457, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF2R1": {"no": 458, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF2R2": {"no": 459, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF2R3": {"no": 460, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF3R1": {"no": 461, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF3R2": {"no": 462, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF3R3": {"no": 463, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF4R1": {"no": 464, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF4R2": {"no": 465, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF4R3": {"no": 466, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF5R1": {"no": 467, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF5R2": {"no": 468, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "DEF5R3": {"no": 469, "ptyp": "StrPT", "typ": "13s", "vSize": 13},
#         "1RCTL": {"no": 470, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NPOS1R1": {"no": 471, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS1R1": {"no": 472, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS1R1": {"no": 473, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ1R1": {"no": 474, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG1R1": {"no": 475, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG1R1": {"no": 476, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS1R2": {"no": 477, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS1R2": {"no": 478, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS1R2": {"no": 479, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ1R2": {"no": 480, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG1R2": {"no": 481, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG1R2": {"no": 482, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS1R3": {"no": 483, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS1R3": {"no": 484, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS1R3": {"no": 485, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ1R3": {"no": 486, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG1R3": {"no": 487, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG1R3": {"no": 488, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "2RCTL": {"no": 489, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NPOS2R1": {"no": 490, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS2R1": {"no": 491, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS2R1": {"no": 492, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ2R1": {"no": 493, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG2R1": {"no": 494, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG2R1": {"no": 495, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS2R2": {"no": 496, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS2R2": {"no": 497, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS2R2": {"no": 498, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ2R2": {"no": 499, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG2R2": {"no": 500, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG2R2": {"no": 501, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS2R3": {"no": 502, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS2R3": {"no": 503, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS2R3": {"no": 504, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ2R3": {"no": 505, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG2R3": {"no": 506, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG2R3": {"no": 507, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "3RCTL": {"no": 508, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NPOS3R1": {"no": 509, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS3R1": {"no": 510, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS3R1": {"no": 511, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ3R1": {"no": 512, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG3R1": {"no": 513, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG3R1": {"no": 514, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS3R2": {"no": 515, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS3R2": {"no": 516, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS3R2": {"no": 517, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ3R2": {"no": 518, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG3R2": {"no": 519, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG3R2": {"no": 520, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS3R3": {"no": 521, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS3R3": {"no": 522, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS3R3": {"no": 523, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ3R3": {"no": 524, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG3R3": {"no": 525, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG3R3": {"no": 526, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "4RCTL": {"no": 527, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NPOS4R1": {"no": 528, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS4R1": {"no": 529, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS4R1": {"no": 530, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ4R1": {"no": 531, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG4R1": {"no": 532, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG4R1": {"no": 533, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS4R2": {"no": 534, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS4R2": {"no": 535, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS4R2": {"no": 536, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ4R2": {"no": 537, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG4R2": {"no": 538, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG4R2": {"no": 539, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS4R3": {"no": 540, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS4R3": {"no": 541, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS4R3": {"no": 542, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ4R3": {"no": 543, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG4R3": {"no": 544, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG4R3": {"no": 545, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "5RCTL": {"no": 546, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NPOS5R1": {"no": 547, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS5R1": {"no": 548, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS5R1": {"no": 549, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ5R1": {"no": 550, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG5R1": {"no": 551, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG5R1": {"no": 552, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS5R2": {"no": 553, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS5R2": {"no": 554, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS5R2": {"no": 555, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ5R2": {"no": 556, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG5R2": {"no": 557, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG5R2": {"no": 558, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NPOS5R3": {"no": 559, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "EPOS5R3": {"no": 560, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ZPOS5R3": {"no": 561, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SSIZ5R3": {"no": 562, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "NNEG5R3": {"no": 563, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ENEG5R3": {"no": 564, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "RES1R1": {"no": 565, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV1R1": {"no": 566, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV1R1": {"no": 567, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG1R1": {"no": 568, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES1R2": {"no": 569, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV1R2": {"no": 570, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV1R2": {"no": 571, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG1R2": {"no": 572, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES1R3": {"no": 573, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV1R3": {"no": 574, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV1R3": {"no": 575, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG1R3": {"no": 576, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES2R1": {"no": 577, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV2R1": {"no": 578, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV2R1": {"no": 579, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG2R1": {"no": 580, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES2R2": {"no": 581, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV2R2": {"no": 582, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV2R2": {"no": 583, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG2R2": {"no": 584, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES2R3": {"no": 585, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV2R3": {"no": 586, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV2R3": {"no": 587, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG2R3": {"no": 588, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES3R1": {"no": 589, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV3R1": {"no": 590, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV3R1": {"no": 591, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG3R1": {"no": 592, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES3R2": {"no": 593, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV3R2": {"no": 594, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV3R2": {"no": 595, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG3R2": {"no": 596, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES3R3": {"no": 597, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV3R3": {"no": 598, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV3R3": {"no": 599, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG3R3": {"no": 600, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES4R1": {"no": 601, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV4R1": {"no": 602, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV4R1": {"no": 603, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG4R1": {"no": 604, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES4R2": {"no": 605, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV4R2": {"no": 606, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV4R2": {"no": 607, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG4R2": {"no": 608, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES4R3": {"no": 609, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV4R3": {"no": 610, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV4R3": {"no": 611, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG4R3": {"no": 612, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES5R1": {"no": 613, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV5R1": {"no": 614, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV5R1": {"no": 615, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG5R1": {"no": 616, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES5R2": {"no": 617, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV5R2": {"no": 618, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV5R2": {"no": 619, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG5R2": {"no": 620, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RES5R3": {"no": 621, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "DCV5R3": {"no": 622, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "ACV5R3": {"no": 623, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "FLAG5R3": {"no": 624, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "V8SE": {"no": 625, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RESTYP": {"no": 626, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WDISK": {"no": 627, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WBAT1": {"no": 628, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WBAT2": {"no": 629, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WBAT3": {"no": 630, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WTEMP": {"no": 631, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TMZONE": {"no": 632, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "TMDIFF": {"no": 633, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BCKLIT": {"no": 634, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "CONTST": {"no": 635, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "OFFCFM": {"no": 636, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DFTTECH": {"no": 637, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "RXLEN": {"no": 638, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "TXTCLR": {"no": 639, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SYMCLR": {"no": 640, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BARCLR": {"no": 641, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "PEAKCLR": {"no": 642, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "WARNCLR": {"no": 643, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MINFREQ": {"no": 644, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXFREQ": {"no": 645, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MINRES": {"no": 646, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXRES": {"no": 647, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MINA": {"no": 648, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXA": {"no": 649, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MINE": {"no": 650, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXE": {"no": 651, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MINH": {"no": 652, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXH": {"no": 653, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MINPHS": {"no": 654, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "MAXPHS": {"no": 655, "ptyp": "FltPT", "typ": "d", "vSize": 8},
#         "SYMSIZE": {"no": 656, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SYMSHAP": {"no": 657, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "NGRDPHS": {"no": 658, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "PLOTTYP": {"no": 659, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "BARWND": {"no": 660, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "MAXVWCH": {"no": 661, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "SLAYOUT": {"no": 662, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "DECSCAL": {"no": 663, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "AUTOPHS": {"no": 664, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "AUTOSCL": {"no": 665, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "KPLWMEM": {"no": 666, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#         "KPLSMEM": {"no": 667, "ptyp": "IntPT", "typ": "i", "vSize": 4},
#     }
#     return headerDict




# class TimeReaderPhoenix(TimeReader):
#     """Data reader for Phoenix data

#     The Phoenix data and recording format is different and does not nicely fit with the way resistics tries to model data.
    
#     There are three frequencies recorded concurrently (e.g. 2400Hz, 150Hz, 15Hz). The lowest sampling frequency is continuous whilst the others record data files at regular intervals. There is no issue with the continous sampling frequency. 
    
#     However, as resistics separates out data into continuous recordings, the consistent gaps for the higher frequencies will lead to lots of small data folders if converted to internal data format.

#     This class returns the lowest frequency recording (the continuous one) when time series data is requested. However, higher frequencies can be converted to the internal data format using the methods available here.

#     Warnings
#     --------
#     The appropriate scaling for Phoenix data to return field units has not yet been verified.

#     It is not actually recommended to reformat the high frequency recordings as this will lead to potentially thousands of data folders. There is currently no straight-forward way to support the high-frequency Phoenix recordings.

#     Attributes
#     ----------
#     recChannels : Dict
#         Channels in each data file
#     dtype : np.float32
#         The data type
#     numHeaderFiles : int
#         The number of header files
#     numDataFiles : int
#         The number of data files

#     Methods
#     -------
#     setParameters()
#         Set data reader parameters for Phoenix files
#     getSamplesRatesTS()
#         Get the sampling frequencies of the time series data
#     getNumberSamplesTS()
#         Get the number of samples for each time series file
#     getUnscaledSamples(**kwargs)
#         Get raw data from data file
#     getRecordsForSamples(startSample, endSample)
#         Get the records to read for a sample range
#     readTag(dataFile)
#         Read the tag from a data file
#     readRecord(dataFile, numChans, numScans)
#         Read numScans from a record
#     twosComplement(dataBytes)
#         Read the two's complement data from the file
#     getPhysicalSamples(**kwargs)
#         Get data scaled to physical values
#     chanDefaults()
#         Get defaults for channel headers
#     readHeader()
#         Read header file
#     readTable()
#         Read table file
#     removeControl(inBytes)
#         Remove control characters from a byte string
#     headersFromTable(tableData)
#         Parse the information in the table file to get headers
#     getDates(tableData)
#         Get recording dates (start and end time)
#     checkSamples()
#         Check the number of samples for all the timeseries (ts) files
#     reformatHigh(path, **kwargs)
#         Write out high frequency time series in internal format
#     reformatContinuous(path)
#         Write out the continuous time series in internal format
#     reformat(path)
#         Write out all recorded time series to internal format
#     printDataFileList()  
#         Information about the data files as a list of strings
#     printDataFileInfo()
#         Print a list of the data files
#     printTableFileList()
#         Information about the table file as a list of strings
#     printTableFileInfo()
#         Print table file info

#     Notes
#     -----
#     Phoenix data is stored in 3 bytes two's-complement format.
#     """

#     def setParameters(self) -> None:
#         """Set data reader parameters for Phoenix files
        
#         Phoenix time series data is not contiguous in the file and is separated into records. There are multiple time series data files, one for the continuous recording and two others for the other frequencies. Therefore, there are a few other class variables defined here than in the parent DataReader class.
#         """
#         # get a list of the header and data files in the folder
#         self.headerF = glob.glob(os.path.join(self.dataPath, "*.TBL"))
#         self.dataF = glob.glob(os.path.join(self.dataPath, "*.TS*"))
#         # set the sample byte size
#         self.sampleByteSize = 3  # two's complement
#         self.tagByteSize = 32
#         self.dtype = int
#         # there will be multiple TS files in here
#         # need to figure out
#         self.numHeaderFiles = len(self.headerF)
#         self.numDataFiles = len(self.dataF)

#     def getSamplesRatesTS(self) -> Dict:
#         """Get the sampling frequencies of the time series data

#         Returns
#         -------
#         Dict
#             Dictionary with the time series file number as keys and their sampling frequencies in Hz as values
#         """
#         info: Dict = {}
#         for num, sr in zip(self.tsNums, self.tsSampleFreqs):
#             info[num] = sr
#         return info

#     def getNumberSamplesTS(self) -> Dict:
#         """Get the number of samples for each time series file

#         Returns
#         -------
#         Dict
#             Dictionary with the time series file number as keys and their number of samples as values
#         """
#         info = {}
#         for num, ns in zip(self.tsNums, self.tsNumSamples):
#             info[num] = ns
#         return info

#     def getUnscaledSamples(self, **kwargs) -> TimeData:
#         """Get raw data from data file

#         Only returns the continuous data. The continuous data is in 24 bit two's complement (3 bytes) format and is read in using struct as this is not supported by numpy.
        
#         Parameters
#         ----------
#         chans : List[str], optional
#             List of channels to return if not all are required
#         startSample : int, optional
#             First sample to return
#         endSample : int, optional
#             Last sample to return

#         Returns
#         -------
#         TimeData
#             Time data object
#         """
#         # initialise chans, startSample and endSample with the whole dataset
#         options = self.parseGetDataKeywords(kwargs)

#         # get the files to read and the samples to take from them, in the correct order
#         recordsToRead, samplesToRead = self.getRecordsForSamples(
#             options["startSample"], options["endSample"]
#         )
#         numSamples = options["endSample"] - options["startSample"] + 1
#         # set up the dictionary to hold the data
#         data = {}
#         for chan in options["chans"]:
#             data[chan] = np.zeros(shape=(numSamples), dtype=self.dtype)

#         # open the file
#         dFile = open(self.continuousF, "rb")

#         # loop through chans and get data
#         sampleCounter = 0
#         for record, sToRead in zip(recordsToRead, samplesToRead):
#             # number of samples to read in record
#             dSamples = sToRead[1] - sToRead[0] + 1
#             # find the byte read start and byte read end
#             recordByteStart = self.recordBytes[self.continuous][record]
#             recordSampleStart = self.recordSampleStarts[self.continuous][record]
#             # find the offset on the readFrom bytes
#             # now recall, each sample is recorded as a scan (all channels recorded at the same time)
#             # so multiply by number of channels to get the number of bytes to read
#             byteReadStart = (
#                 recordByteStart
#                 + (sToRead[0] - recordSampleStart)
#                 * self.sampleByteSize
#                 * self.getNumChannels()
#             )
#             bytesToRead = dSamples * self.sampleByteSize * self.getNumChannels()
#             # read the data - numpy does not support 24 bit two's complement (3 bytes) - hence use struct
#             dFile.seek(byteReadStart, 0)  # seek to start byte from start of file
#             dataBytes = dFile.read(bytesToRead)
#             dataRead = self.twosComplement(dataBytes)
#             # now need to unpack this
#             for chan in options["chans"]:
#                 # check to make sure channel exists
#                 self.checkChan(chan)
#                 # get the channel index - the chanIndex should give the right order in the data file
#                 # as it is the same order as in the header file
#                 chanIndex = self.chanMap[chan]
#                 # now populate the channel data appropriately
#                 data[chan][sampleCounter : sampleCounter + dSamples] = dataRead[
#                     chanIndex : dSamples * self.getNumChannels() : self.getNumChannels()
#                 ]
#             # increment sample counter
#             sampleCounter = sampleCounter + dSamples  # get ready for the next data read
#         # close file
#         dFile.close()

#         # return data
#         startTime, stopTime = self.sample2time(
#             options["startSample"], options["endSample"]
#         )
#         comment = "Unscaled data {} to {} read in from measurement {}, samples {} to {}".format(
#             startTime,
#             stopTime,
#             self.dataPath,
#             options["startSample"],
#             options["endSample"],
#         )
#         return TimeData(
#             sampleFreq=self.getSampleFreq(),
#             startTime=startTime,
#             stopTime=stopTime,
#             data=data,
#             comments=comment,
#         )

#     def getRecordsForSamples(
#         self, startSample: int, endSample: int
#     ) -> Tuple[List, List]:
#         """Get the records to read for a sample range

#         Parameters
#         ----------
#         startSample : int
#             The starting sample of the range
#         endSample : int
#             The ending sample of the range
        
#         Returns
#         -------
#         recordsToRead : List
#             The records to read from the time series data files
#         samplesToRead : List
#             The samples to read from each record
#         """
#         recordsToRead = []
#         samplesToRead = []
#         for record, timeStart in enumerate(self.recordStarts[self.continuous]):
#             recordStartSamp = self.recordSampleStarts[self.continuous][record]
#             recordEndSamp = self.recordSampleStops[self.continuous][record]
#             if recordStartSamp > endSample or recordEndSamp < startSample:
#                 continue  # nothing to read from this file
#             # in this case, there is some overlap with the samples to read
#             recordsToRead.append(record)
#             readFrom = recordStartSamp  # i.e. the first sample in the datafile
#             readTo = recordEndSamp  # this the last sample in the file
#             if recordStartSamp < startSample:
#                 readFrom = startSample
#             if recordEndSamp > endSample:
#                 readTo = endSample
#             # this is an inclusive number readFrom to readTo including readTo
#             samplesToRead.append([readFrom, readTo])
#         return recordsToRead, samplesToRead

#     def readTag(self, dataFile) -> Tuple[str]:
#         """Read the tag from a data file

#         Parameters
#         ----------
#         dataFile : file handle
#             File handle of the data file
        
#         Returns
#         -------
#         numScans : List
#             Number of scans in the tag
#         numChans : List
#             Number of channels in the tag
#         dateString : str
#             The dataString of the tag
#         """
#         second = struct.unpack("b", dataFile.read(1))[0]
#         minute = struct.unpack("b", dataFile.read(1))[0]
#         hour = struct.unpack("b", dataFile.read(1))[0]
#         day = struct.unpack("b", dataFile.read(1))[0]
#         month = struct.unpack("b", dataFile.read(1))[0]
#         year = struct.unpack("b", dataFile.read(1))[0]
#         dayOfWeek = struct.unpack("b", dataFile.read(1))[0]
#         century = struct.unpack("b", dataFile.read(1))[0]
#         dateString = "{:02d}{:02d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.000".format(
#             century, year, month, day, hour, minute, second
#         )
#         # serial number
#         serialNum = struct.unpack("h", dataFile.read(2))
#         # num scans
#         numScans = struct.unpack("h", dataFile.read(2))[0]
#         # channels per scan
#         numChans = struct.unpack("b", dataFile.read(1))[0]
#         # tag length
#         tagLength = struct.unpack("b", dataFile.read(1))
#         # status code
#         statusCode = struct.unpack("b", dataFile.read(1))
#         # bit-wise saturation flags
#         saturationFlag = struct.unpack("b", dataFile.read(1))
#         # reserved
#         reserved = struct.unpack("b", dataFile.read(1))
#         # sample length
#         sampleLength = struct.unpack("b", dataFile.read(1))
#         # sample rate
#         sampleRate = struct.unpack("h", dataFile.read(2))
#         # units of sample rate: 0 = Hz, 1 = minute, 2 = hour, 3 = day
#         sampleUnits = struct.unpack("b", dataFile.read(1))
#         # clock status
#         clockStatus = struct.unpack("b", dataFile.read(1))
#         # clock error in micro seconds
#         clockError = struct.unpack("i", dataFile.read(4))
#         # reserved
#         res1 = struct.unpack("b", dataFile.read(1))
#         res2 = struct.unpack("b", dataFile.read(1))
#         res3 = struct.unpack("b", dataFile.read(1))
#         res4 = struct.unpack("b", dataFile.read(1))
#         res5 = struct.unpack("b", dataFile.read(1))
#         res6 = struct.unpack("b", dataFile.read(1))
#         # returnt the important variables
#         return numScans, numChans, dateString

#     def readRecord(self, dataFile, numChans, numScans):
#         """Read numScans from a record

#         Parameters
#         ----------
#         dataFile : file handle
#             File handle of the data file
#         numScans : List
#             Number of scans in the tag
#         numChans : List
#             Number of channels in the tag

#         Returns
#         -------
#         data : np.ndarray(int)
#             Record data
#         """
#         data = np.zeros(shape=(numChans, numScans), dtype="int")
#         for scan in range(0, numScans):
#             for chan in range(0, numChans):
#                 dataBytes = dataFile.read(3)
#                 data[chan, scan] = self.twosComplement(dataBytes)
#         return data

#     def twosComplement(self, dataBytes):
#         """Read the two's complement data from the file

#         This parses two's complement 24-bit integer, little endian, unsigned and signed. The method is to pad out 3 bytes out with a null byte and read as unsigned integer with little endian (<).        

#         Parameters
#         ----------
#         dataByes : bytes
#             The bytes to parse

#         Returns
#         -------
#         data : np.ndarray(int)
#             Record data
#         """
#         if len(dataBytes) % self.sampleByteSize != 0:
#             self.printError(
#                 "The number of bytes divided by the sample byte size does not give an exact number",
#                 quitrun=True,
#             )
#         # calculate num samples, this should be exact
#         numSamples = intdiv(len(dataBytes), self.sampleByteSize)
#         dataRead = np.zeros(shape=(numSamples), dtype=self.dtype)
#         for i in range(0, numSamples):
#             sampleBytes = dataBytes[
#                 i * self.sampleByteSize : (i + 1) * self.sampleByteSize
#             ]
#             unsigned = struct.unpack("<I", sampleBytes + b"\x00")[0]
#             signed = unsigned if not (unsigned & 0x800000) else unsigned - 0x1000000
#             dataRead[i] = signed
#         return dataRead

#     def getPhysicalSamples(self, **kwargs) -> TimeData:
#         """Get data scaled to physical values

#         Parameters
#         ----------
#         chans : List[str]
#             List of channels to return if not all are required
#         startSample : int
#             First sample to return
#         endSample : int
#             Last sample to return
#         remaverage : bool
#             Remove average from the data
#         remzeros : bool
#             Remove zeroes from the data
#         remnans: bool
#             Remove NanNs from the data

#         Returns
#         -------
#         TimeData
#             Time data object
#         """
#         options = self.parseGetDataKeywords(kwargs)
#         # get data
#         timeData = self.getUnscaledSamples(
#             chans=options["chans"],
#             startSample=options["startSample"],
#             endSample=options["endSample"],
#         )
#         # need to remove the gain
#         for chan in options["chans"]:
#             # remove the gain
#             timeData[chan] = 1.0 * timeData[chan] / self.getChanGain1(chan)
#             timeData.addComment(
#                 "Scaling channel {} with scalar {} to give mV".format(
#                     chan, 1.0 / self.getChanGain1(chan)
#                 )
#             )

#             # divide by distance in km
#             if chan == "Ex":
#                 # multiply by 1000/self.getChanDx same as dividing by dist in km
#                 timeData[chan] = 1000 * timeData[chan] / self.getChanDx(chan)
#                 timeData.addComment(
#                     "Dividing channel {} by electrode distance {} km to give mV/km".format(
#                         chan, self.getChanDx(chan) / 1000.0
#                     )
#                 )
#             if chan == "Ey":
#                 # multiply by 1000/self.getChanDy same as dividing by dist in km
#                 timeData[chan] = 1000 * timeData[chan] / self.getChanDy(chan)
#                 timeData.addComment(
#                     "Dividing channel {} by electrode distance {} km to give mV/km".format(
#                         chan, self.getChanDy(chan) / 1000.0
#                     )
#                 )

#             # if remove zeros - False by default
#             if options["remzeros"]:
#                 timeData[chan] = removeZerosChan(timeData[chan])
#             # if remove nans - False by default
#             if options["remnans"]:
#                 timeData[chan] = removeNansChan(timeData[chan])
#             # remove the average from the data - True by default
#             if options["remaverage"]:
#                 timeData[chan] = timeData[chan] - np.average(
#                     timeData[chan]
#                 )

#         # add comments
#         timeData.addComment(
#             "The required Phoneix scaling to field units is still unverified. This is experimental and use cautiously."
#         )
#         timeData.addComment(
#             "Remove zeros: {}, remove nans: {}, remove average: {}".format(
#                 options["remzeros"], options["remnans"], options["remaverage"]
#             )
#         )
#         return timeData

#     def chanDefaults(self):
#         """Get defaults for channel headers

#         Returns
#         -------
#         Dict[str, Any]
#             Dictionary of headers for channels and default values
#         """
#         chanH = {}
#         chanH["gain_stage1"] = 1
#         chanH["gain_stage2"] = 1
#         chanH["hchopper"] = 0  # this depends on sample frequency
#         chanH["echopper"] = 0
#         # channel output information (sensor_type, channel_type, ts_lsb, pos_x1, pos_x2, pos_y1, pos_y2, pos_z1, pos_z2, sensor_sernum)
#         chanH["ats_data_file"] = ""
#         chanH["num_samples"] = 0
#         chanH["sensor_type"] = ""
#         chanH["channel_type"] = ""
#         chanH["ts_lsb"] = 1
#         chanH["scaling_applied"] = False
#         chanH["pos_x1"] = 0
#         chanH["pos_x2"] = 0
#         chanH["pos_y1"] = 0
#         chanH["pos_y2"] = 0
#         chanH["pos_z1"] = 0
#         chanH["pos_z2"] = 0
#         chanH["sensor_sernum"] = 0
#         return chanH

#     def readHeader(self):
#         """Read header file

#         For phoenix data, the header file is the table file and it is binary formatted.
#         """
#         # first, find which ts files are available (2,3,4,5)
#         # and the continuous recording frequency (the max)
#         self.tsNums = []
#         for tsfile in self.dataF:
#             self.tsNums.append(int(tsfile[-1]))
#         self.continuous = max(self.tsNums)
#         self.continuousI = self.tsNums.index(self.continuous)
#         self.continuousF = self.dataF[self.continuousI]
#         # read the table data
#         self.tableData = self.readTable()
#         # and then populate the headers
#         self.headers, self.chanHeaders = self.headersFromTable(self.tableData)
#         # finally, check the number of samples in each file
#         self.checkSamples()

#     def readTable(self) -> Dict:
#         """Read a header table

#         Returns
#         -------
#         OrderedDict
#             An ordered dictionary of header table data
#         """
#         from resistics.time.phoenix import getPhoenixHeaders

#         if len(self.headerF) > 1:
#             self.printWarning(
#                 "More table files than expected. Using: {}".format(self.headerF[0])
#             )
#         numBytes = os.path.getsize(self.headerF[0])
#         tableFile = open(self.headerF[0], "rb")
#         tableData = collections.OrderedDict()
#         headerDict = getPhoenixHeaders()
#         # loop through file and read
#         headerWordSize = 4
#         headerSize = 12
#         dataSize = 13
#         increment = headerSize + dataSize
#         bytesRead = 0
#         headerCount = 0        
#         # increment over headers in table file
#         while bytesRead <= numBytes - increment:
#             header = struct.unpack(
#                 "{}s".format(headerWordSize), tableFile.read(headerWordSize)
#             )
#             header = self.removeControl(header[0])
#             # check if header is known
#             if header not in headerDict:
#                 self.printWarning("Phoenix header num {:d}, name '{:s}' not known".format(headerCount, header))
#                 tableFile.seek(headerSize - headerWordSize + dataSize, 1)
#                 headerCount += 1
#                 bytesRead += increment
#                 continue
#             headerInfo = headerDict[header]
#             # seek to data
#             tableFile.seek(headerSize - headerWordSize, 1)
#             if headerInfo["ptyp"] == "AmxPT":
#                 value = struct.unpack(headerInfo["typ"], tableFile.read(headerInfo["vSize"]))
#             else:
#                 value = struct.unpack(headerInfo["typ"], tableFile.read(headerInfo["vSize"]))[0]
#             if "s" in headerInfo["typ"]:
#                 value = self.removeControl(value)
#             # set header value
#             tableData[header] = value
#             # move to end of this header word
#             tableFile.seek(dataSize - headerInfo["vSize"], 1)
#             # increment bytes read
#             headerCount += 1
#             bytesRead += increment            

#             # if header == "":
#             #     break  # get rid of empty lines at the end
#             # if header in ints:
#             #     value = struct.unpack("i", tableFile.read(4))[0]
#             #     tableFile.seek(dataSize - 4, 1)
#             # elif header in ints1_8:
#             #     value = struct.unpack("8b", tableFile.read(8))
#             #     tableFile.seek(dataSize - 8, 1)
#             # elif header in doubles:
#             #     value = struct.unpack("d", tableFile.read(8))[0]
#             #     tableFile.seek(dataSize - 8, 1)
#             # else:
#             #     value = struct.unpack("{}s".format(dataSize), tableFile.read(dataSize))
#             #     value = self.removeControl(value[0])
#         tableFile.close()
#         return tableData

#     def removeControl(self, inBytes: bytes) -> str:
#         """Remove control characters from byte strings
        
#         Parameters
#         ----------
#         inBytes : bytes
#             Bytes from which to remove control 
        
#         Returns
#         -------
#         str :
#             Decodes bytes object with control character removed
#         """
#         inBytes = inBytes.strip(b"\x00")
#         return inBytes.decode()

#     def headersFromTable(self, tableData: Dict) -> Tuple[Dict, List]:
#         """Populate the headers from the table values
        
#         Parameters
#         ----------
#         tableData : OrderedDictDict
#             Ordered dictionary with table data
        
#         Returns
#         -------
#         headers : Dict
#             Dictionary of general headers
#         chanHeaders : Dict
#             List of channel headers
#         """
#         # initialise storage
#         headers = {}
#         chanHeaders = []
#         # get the sample freqs for each ts file
#         self.tsSampleFreqs = []
#         for tsNum in self.tsNums:
#             self.tsSampleFreqs.append(tableData["SRL{}".format(tsNum)])
#         # for sample frequency, use the continuous channel
#         headers["sample_freq"] = self.tsSampleFreqs[self.continuousI]
#         # these are the unix time stamps
#         firstDate, firstTime, lastDate, lastTime = self.getDates(tableData)
#         # the start date is equal to the time of the first record
#         headers["start_date"] = firstDate
#         headers["start_time"] = firstTime
#         datetimeStart = datetime.strptime(
#             "{} {}".format(firstDate, firstTime), "%Y-%m-%d %H:%M:%S.%f"
#         )
#         # the stop date
#         datetimeLast = datetime.strptime(
#             "{} {}".format(lastDate, lastTime), "%Y-%m-%d %H:%M:%S.%f"
#         )
#         # records are usually equal to one second (beginning on 0 and ending on the last sample before the next 0)
#         datetimeStop = datetimeLast + timedelta(
#             seconds=(1.0 - 1.0 / headers["sample_freq"])
#         )
#         # put the stop date and time in the headers
#         headers["stop_date"] = datetimeStop.strftime("%Y-%m-%d")
#         headers["stop_time"] = datetimeStop.strftime("%H:%M:%S.%f")
#         # here calculate number of samples
#         deltaSeconds = (datetimeStop - datetimeStart).total_seconds()
#         # calculate number of samples - have to add one because the time given in SPAM recording is the actual time of the last sample
#         numSamples = round(deltaSeconds * headers["sample_freq"]) + 1
#         headers["num_samples"] = numSamples
#         headers["ats_data_file"] = self.continuousF
#         # deal with the channel headers
#         # now want to do this in the correct order
#         # chan headers should reflect the order in the data
#         chans = ["Ex", "Ey", "Hx", "Hy", "Hz"]
#         chanOrder = []
#         for chan in chans:
#             chanOrder.append(tableData["CH{}".format(chan.upper())])
#         # sort the lists in the right order based on chanOrder
#         chanOrder, chans = (
#             list(x)
#             for x in zip(*sorted(zip(chanOrder, chans), key=lambda pair: pair[0]))
#         )
#         for chan in chans:
#             chanH = self.chanDefaults()
#             # set the sample frequency from the main headers
#             chanH["sample_freq"] = headers["sample_freq"]
#             # channel output information (sensor_type, channel_type, ts_lsb, pos_x1, pos_x2, pos_y1, pos_y2, pos_z1, pos_z2, sensor_sernum)
#             chanH["ats_data_file"] = self.dataF[self.continuousI]
#             chanH["num_samples"] = numSamples
#             # channel information
#             chanH["channel_type"] = consistentChans(chan)  # consistent chan naming

#             # magnetic channels only
#             if isMagnetic(chanH["channel_type"]):
#                 chanH["sensor_sernum"] = tableData["{}SN".format(chan.upper())][-4:]
#                 chanH["sensor_type"] = "Phoenix"
#                 # channel input information (gain_stage1, gain_stage2, hchopper, echopper)
#                 chanH["gain_stage1"] = tableData["HGN"]
#                 chanH["gain_stage2"] = 1

#             # electric channels only
#             if isElectric(chanH["channel_type"]):
#                 # the distances
#                 if chan == "Ex":
#                     chanH["pos_x1"] = float(tableData["EXLN"]) / 2.0
#                     chanH["pos_x2"] = chanH["pos_x1"]
#                 if chan == "Ey":
#                     chanH["pos_y1"] = float(tableData["EYLN"]) / 2.0
#                     chanH["pos_y2"] = chanH["pos_y1"]
#                 # channel input information (gain_stage1, gain_stage2, hchopper, echopper)
#                 chanH["gain_stage1"] = tableData["EGN"]
#                 chanH["gain_stage2"] = 1

#             # append chanHeaders to the list
#             chanHeaders.append(chanH)

#         # data information (meas_channels, sample_freq)
#         headers["meas_channels"] = len(chans)  # this gets reformatted to an int later
#         # return the headers and chanHeaders from this file
#         return headers, chanHeaders

#     def getDates(self, tableData) -> Tuple[str, str, str, str]:
#         """Get recording dates (start and end time)
        
#         Parameters
#         ----------
#         tableData : OrderedDictDict
#             Ordered dictionary with table data
        
#         Returns
#         -------
#         firstDate : str
#             Date of first sample as string
#         firstTime : str
#             Time of first sample as string
#         lastDate : str
#             Date of last sample as string
#         lastTime : str
#             Time of last sample as string
#         """
#         firstSecond = tableData["FTIM"][0]
#         firstMinute = tableData["FTIM"][1]
#         firstHour = tableData["FTIM"][2]
#         firstDay = tableData["FTIM"][3]
#         firstMonth = tableData["FTIM"][4]
#         firstYear = tableData["FTIM"][5]
#         firstCentury = tableData["FTIM"][-1]
#         firstDate = "{:02d}{:02d}-{:02d}-{:02d}".format(
#             firstCentury, firstYear, firstMonth, firstDay
#         )
#         firstTime = "{:02d}:{:02d}:{:02d}.000".format(
#             firstHour, firstMinute, firstSecond
#         )
#         # this is the start time of the last record
#         lastSecond = tableData["LTIM"][0]
#         lastMinute = tableData["LTIM"][1]
#         lastHour = tableData["LTIM"][2]
#         lastDay = tableData["LTIM"][3]
#         lastMonth = tableData["LTIM"][4]
#         lastYear = tableData["LTIM"][5]
#         lastCentury = tableData["LTIM"][-1]
#         lastDate = "{:02d}{:02d}-{:02d}-{:02d}".format(
#             lastCentury, lastYear, lastMonth, lastDay
#         )
#         lastTime = "{:02d}:{:02d}:{:02d}.000".format(lastHour, lastMinute, lastSecond)
#         return firstDate, firstTime, lastDate, lastTime

#     def checkSamples(self) -> None:
#         """Check the number of samples for all the timeseries (ts) files
        
#         Recall, the format is 3 bytes two's complement per sample
#         """
#         self.recordStarts = {}
#         self.recordScans = {}
#         self.recordBytes = {}
#         self.recordSampleStarts = {}
#         self.recordSampleStops = {}
#         # loop over the tsNums
#         samplesDict = {}
#         for dFileName in self.dataF:
#             ts = int(dFileName[-1])
#             self.recordStarts[ts] = []
#             self.recordScans[ts] = []
#             self.recordBytes[ts] = []
#             self.recordSampleStarts[ts] = []
#             self.recordSampleStops[ts] = []
#             # start number of samples at 0
#             samples = 0
#             # get file size in samples
#             numBytes = os.path.getsize(dFileName)
#             bytesread = 0
#             # now run through the file and figure out the number of samples
#             dFile = open(dFileName, "rb")
#             while bytesread < numBytes:
#                 # read 32 bytes tag
#                 numScans, numChans, dateString = self.readTag(dFile)
#                 self.recordBytes[ts].append(bytesread + self.tagByteSize)
#                 dataBytes = numScans * numChans * self.sampleByteSize
#                 dFile.seek(dataBytes, 1)
#                 bytesread += self.tagByteSize + dataBytes
#                 # save the record start times and scan lengths
#                 self.recordStarts[ts].append(dateString)
#                 self.recordScans[ts].append(numScans)
#                 # save the sample starts
#                 self.recordSampleStarts[ts].append(samples)
#                 # increment the number of samples
#                 # recall, a scan is all channels recorded at one time
#                 # this is equivalent to one sample
#                 samples += numScans  # this is the count
#                 # sample stop is samples -1 because inclusive of the current sample
#                 self.recordSampleStops[ts].append(samples - 1)
#             dFile.close()
#             # save number of samples in dict
#             samplesDict[ts] = samples
#             # logFile.close()

#         self.tsNumSamples = []
#         for tsNum in self.tsNums:
#             self.tsNumSamples.append(samplesDict[tsNum])

#         # check the samples of the continuous file
#         if self.tsNumSamples[self.continuousI] != self.getNumSamples():
#             self.printWarning(
#                 "Number of samples calculated from times is different to that in file"
#             )
#             self.printWarning(
#                 "{} samples in file, {} calculated from time".format(
#                     self.tsNumSamples[self.continuousI], self.getNumSamples()
#                 )
#             )

#     def reformatHigh(self, path: str, **kwargs) -> None:
#         """Write out high frequency time series in internal format
        
#         Parameters
#         ----------
#         path : str
#             Directory to write out the reformatted time series
#         ts : List[int], optional
#             A list of the high frequency ts files to reformat. By default, all of the higher frequency recordings are reformatted
#         """
#         writer = TimeWriterInternal()
#         for idx, ts in enumerate(self.tsNums):
#             if "ts" in kwargs and ts not in kwargs["ts"]:
#                 continue  # do not reformat this one
#             # let's get the headers
#             headers = self.getHeaders()
#             chanHeaders, chanMap = self.getChanHeaders()
#             chans = self.getChannels()
#             # now go through the different ts files to get ready to output
#             if ts == self.continuous:
#                 continue
#             sampleFreq = self.tsSampleFreqs[idx]
#             # set sample frequency in headers
#             headers["sample_freq"] = sampleFreq
#             for cH in chanHeaders:
#                 cH["sample_freq"] = sampleFreq
#             # now open the data file
#             dFile = open(self.dataF[idx], "rb")
#             # each record has to be read separately and then compare time to previous
#             outStartTime = datetime.strptime(
#                 self.recordStarts[ts][0], "%Y-%m-%d %H:%M:%S.%f"
#             )
#             # set up the data dictionary
#             data = {}
#             for record, startDate in enumerate(self.recordStarts[ts]):
#                 # start date is a string
#                 startByte = self.recordBytes[ts][record]
#                 startDateTime = datetime.strptime(startDate, "%Y-%m-%d %H:%M:%S.%f")
#                 # read the record - numpy does not support 24 bit two's complement (3 bytes) - hence use struct
#                 bytesToRead = (
#                     self.recordScans[ts][record]
#                     * self.sampleByteSize
#                     * self.getNumChannels()
#                 )
#                 dFile.seek(startByte, 0)  # seek to start byte from start of file
#                 dataBytes = dFile.read(bytesToRead)
#                 dataRead = self.twosComplement(dataBytes)
#                 dataRecord = {}
#                 for chan in chans:
#                     # as it is the same order as in the header file
#                     chanIndex = self.chanMap[chan]
#                     dataRecord[chan] = dataRead[
#                         chanIndex : self.recordScans[ts][record]
#                         * self.getNumChannels() : self.getNumChannels()
#                     ]
#                 # need to compare to previous record
#                 if record != 0 and startDateTime != prevEndTime:
#                     # then need to write out the current data before saving the new data
#                     # write out current data
#                     outStopTime = prevEndTime - timedelta(
#                         seconds=1.0 / sampleFreq
#                     )  # because inclusive of first sample (previous end time for continuity comparison)
#                     # calculate number of samples
#                     numSamples = data[chans[0]].size
#                     headers["start_date"] = outStartTime.strftime("%Y-%m-%d")
#                     headers["start_time"] = outStartTime.strftime("%H:%M:%S.%f")
#                     headers["stop_date"] = outStopTime.strftime("%Y-%m-%d")
#                     headers["stop_time"] = outStopTime.strftime("%H:%M:%S.%f")
#                     headers["num_samples"] = numSamples
#                     for cH in chanHeaders:
#                         cH["start_date"] = headers["start_date"]
#                         cH["start_time"] = headers["start_time"]
#                         cH["stop_date"] = headers["stop_date"]
#                         cH["stop_time"] = headers["stop_time"]
#                         cH["num_samples"] = numSamples
#                     # get the outpath
#                     dataOutpath = os.path.join(
#                         path,
#                         "meas_ts{}_{}_{}".format(
#                             ts,
#                             outStartTime.strftime("%Y-%m-%d-%H-%M-%S"),
#                             outStopTime.strftime("%Y-%m-%d-%H-%M-%S"),
#                         ),
#                     )
#                     # create the timeData object
#                     comment = "Unscaled samples for interval {} to {} read in from measurement {}".format(
#                         outStartTime, outStopTime, self.dataF[idx]
#                     )
#                     timeData = TimeData(
#                         sampleFreq=self.getSampleFreq(),
#                         startTime=outStartTime,
#                         stopTime=outStopTime,
#                         data=data,
#                         comments=comment,
#                     )
#                     # write out
#                     writer.setOutPath(dataOutpath)
#                     writer.writeData(headers, chanHeaders, timeData)
#                     # then save current data
#                     outStartTime = startDateTime
#                     data = copy.deepcopy(dataRecord)
#                     prevEndTime = startDateTime + timedelta(
#                         seconds=((1.0 / sampleFreq) * self.recordScans[ts][record])
#                     )
#                 else:
#                     # then record == 0 or startDateTime == prevEndTime
#                     # update prevEndTime
#                     prevEndTime = startDateTime + timedelta(
#                         seconds=((1.0 / sampleFreq) * self.recordScans[ts][record])
#                     )
#                     if record == 0:
#                         data = copy.deepcopy(dataRecord)
#                         continue
#                     # otherwise, want to concatenate the data
#                     for chan in chans:
#                         data[chan] = np.concatenate((data[chan], dataRecord[chan]))
#             # close the data file
#             dFile.close()

#     def reformatContinuous(self, path: str):
#         """Write out the continuous time series in internal format
        
#         Parameters
#         ----------
#         path : str
#             Path to write out reformatted continuous recording
#         """
#         writer = TimeWriterInternal()
#         outpath = "meas_ts{}_{}_{}".format(
#             self.continuous,
#             self.getStartDatetime().strftime("%Y-%m-%d-%H-%M-%S"),
#             self.getStopDatetime().strftime("%Y-%m-%d-%H-%M-%S"),
#         )
#         outpath = os.path.join(path, outpath)
#         writer.setOutPath(outpath)
#         headers = self.getHeaders()
#         chanHeaders, chanMap = self.getChanHeaders()
#         writer.writeData(headers, chanHeaders, self.getPhysicalSamples(), physical=True)

#     def reformat(self, path):
#         """Write out all recorded time series to internal format
        
#         Parameters
#         ----------
#         path : str
#             Path to write out reformatted recordings
#         """
#         self.reformatContinuous(path)
#         self.reformatHigh(path)

#     def printDataFileList(self) -> List[str]:
#         """Information about the data files as a list of strings
        
#         Returns
#         -------
#         List[str]
#             List of information about the data files
#         """
#         textLst = []
#         textLst.append("TS File\t\tSampling frequency (Hz)\t\tNum Samples")
#         for dF, tsF, tsN in zip(self.dataF, self.tsSampleFreqs, self.tsNumSamples):
#             textLst.append("{}\t\t{}\t\t{}".format(os.path.basename(dF), tsF, tsN))
#         textLst.append(
#             "Continuous data file: {}".format(os.path.basename(self.continuousF))
#         )
#         return textLst

#     def printDataFileInfo(self):
#         """Print a list of the data files"""
#         blockPrint(
#             "{} Data File List".format(self.__class__.__name__),
#             self.printDataFileList(),
#         )

#     def printTableFileList(self) -> List[str]:
#         """Information about the table file as a list of strings
        
#         Returns
#         -------
#         List[str]
#             List of information about table file content
#         """
#         textLst = []
#         for h, v in list(self.tableData.items()):
#             textLst.append("{} = {}".format(h, v))
#         return textLst

#     def printTableFileInfo(self):
#         """Print table file info"""
#         blockPrint(
#             "{} Table File Info".format(self.__class__.__name__),
#             self.printTableFileList(),
#         )
