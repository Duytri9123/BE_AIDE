"""Customer-requested cabinet-equipment scope, independent of discovery feeds.

Membership expresses requested scope, not verified prices or technical equivalence.
"""
CUSTOMER_MANUFACTURERS = (
    'Schneider Electric', 'ABB', 'Siemens', 'Hager', 'Legrand', 'BTB Electric',
    'Mitsubishi Electric', 'Fuji Electric', 'LS Electric', 'Shihlin', 'CHINT',
    'Andeli', 'Sino - Vanlock', 'Vinakip', 'Omron', 'Delta', 'Yaskawa', 'Danfoss',
    'INVT', 'IDEC', 'Hanyoung Nux', 'Samwha', 'TDK / EPCOS', 'Shizuki', 'Nuintek',
    'Mikro', 'SK', 'Ducati Energia', 'Selec', 'Delixi', 'Morele', 'EMIC', 'MITEX',
    'Leipole', 'O-Sung / OSEMCO', 'LightStar', 'SmartGen', 'Deep Sea Electronics',
    'Phoenix Contact', 'Rittal', 'Wöhner', 'EMKA', 'CML', 'Omega', 'ROBOT',
    'KDE', 'Master Electric', 'KACON', 'Suntree', 'Trend / Honeywell', 'MEAN WELL',
)

CUSTOMER_ALIASES = {
    'shihlin electric':'Shihlin', 'idec izumi':'IDEC', 'izumi':'IDEC',
    'hanyoung':'Hanyoung Nux', 'hanyoung nux':'Hanyoung Nux',
    'epcos':'TDK / EPCOS', 'tdk':'TDK / EPCOS', 'epcos / tdk':'TDK / EPCOS',
    'sino':'Sino - Vanlock', 'sino - vanlock':'Sino - Vanlock',
    'sino sp vanlock':'Sino - Vanlock', 'sino vanlock':'Sino - Vanlock',
    'vinakip':'Vinakip', 'vinakip electric':'Vinakip',
    'ducati':'Ducati Energia', 'ducati energia':'Ducati Energia',
    'btb':'BTB Electric', 'btb electric':'BTB Electric', 'invt':'INVT',
}
CUSTOMER_ALIASES.update({name.casefold():name for name in CUSTOMER_MANUFACTURERS})
