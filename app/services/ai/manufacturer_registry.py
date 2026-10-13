"""Category evidence guides discovery; missing evidence does not mean no product."""
DISCOVERY_SOURCE = 'https://thietbidiennuochanoi.vn/blogs/news/top-thuong-hieu-thiet-bi-dien-tot-nhat'
# Discovery names are not proof that every manufacturer supplies every category.
DISCOVERED_BRANDS = ('Schneider Electric', 'Panasonic', 'Sino SP Vanlock', 'MPE', 'Nanoco',
    'Siemens', 'LS Electric', 'Legrand', 'Hager', 'ABB', 'Shihlin', 'Mitsubishi Electric',
    'CHINT', 'Mikro', 'Uten', 'Lioa', 'ART', 'VONTA', 'NIVAL', 'Simon', 'AC', 'Roman',
    'Vinakip', 'Philips', 'Rạng Đông', 'Duhal', 'Osami', 'Dobo', 'Edenki', 'TNC')
PORTFOLIOS = {
    'TIMER': {
        'CHINT': 'https://www.chintglobal.com/in/en/products/low-voltage/iec/industrial-control/njs1.html',
        'Omron': 'https://www.ia.omron.com/products/category/control-components/timers/',
        'Autonics': 'https://www.autonics.com/us/product/category/Timers',
    },
    'LIGHT': {
        'CHINT': 'https://www.chintglobal.com/in/en/products/low-voltage/iec/industrial-control/nd16.html',
        'IDEC': 'https://www.idec.com/en-us/switches-indicator-lights/switches-pushbuttons/pushbuttons-pilot-lights',
    },
    'MCB': {
        'LS Electric': 'https://www.ls-electric.com.vn/en/solution/l-series-mcb/',
        'CHINT': 'https://www.chintglobal.com/ae/en/products/low-voltage/iec/final-power-distribution/nxb-63.html',
        'Schneider Electric': 'https://www.se.com/id/id/product/A9F74320/ic60n-miniature-circuit-breaker-3p-20a-c-curve/',
    },
    'CT': {
        'CHINT': 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/ct/bh-i/catalog/BH-I-CT-Catalog.pdf',
    },
}
CHECKED_DATE = '2026-10-13'
# These are discovery/catalogue anchors, NOT approved SKUs or blanket technical
# equivalence. Every selected model still needs its own electrical evidence.
CATALOGUES = {
    'ABB': ('https://new.abb.com/low-voltage/products',
        ('MCB', 'MCCB', 'ACB', 'CONTACTOR', 'OVERLOAD_RELAY', 'RELAY', 'TIMER',
         'LIGHT', 'SELECTOR', 'POWER_SUPPLY', 'FUSE', 'SPD', 'ATS', 'SOFT_STARTER')),
    'LS Electric': ('https://www.ls-electric.com.vn/en/solution/',
        ('MCCB', 'ELCB', 'CONTACTOR', 'OVERLOAD_RELAY')),
    'CHINT': ('https://discover.chintglobal.com/view/330255281',
        ('MCCB', 'ACB', 'CONTACTOR', 'RELAY', 'OVERLOAD_RELAY', 'LIGHT',
         'PUSHBUTTON', 'SOFT_STARTER', 'VFD')),
    'Fuji Electric': ('https://www.fujielectric.com/fcs/document/download/download_catalog.html',
        ('MCCB', 'ELCB', 'ACB', 'FUSE', 'CONTACTOR', 'OVERLOAD_RELAY', 'RELAY',
         'TIMER', 'MOTOR_PROTECTION', 'METER')),
    'Shihlin': ('https://circuit-breaker.seec.com.tw/Templates/att/All_product.pdf',
        ('MCB', 'MCCB', 'ELCB', 'ACB', 'CONTACTOR', 'MOTOR_PROTECTION',
         'ATS', 'SPD', 'METER', 'CAPACITOR', 'VFD')),
    'HD Hyundai Electric': ('https://www.hyundai-electric.com/assets/file/Corporate%20Brochure%28E%2940P.pdf',
        ('MCCB', 'ACB', 'CONTACTOR')),
    'Mitsubishi Electric': ('https://www.mitsubishielectric.com/fa/download/search.page?kisyu=%2Flvcb&mode=catalog',
        ('MCCB', 'ELCB', 'ACB')),
    'Eaton': ('https://www.eaton.com/us/en-us/locate/electrical.html',
        ('CB', 'CONTACTOR', 'RELAY', 'TIMER', 'PUSHBUTTON', 'POWER_SUPPLY',
         'TERMINAL', 'METER', 'ATS', 'SOFT_STARTER', 'VFD')),
    'Hager': ('https://hager.com/intl-en/catalogue/modular-devices/switching-and-signalling-devices',
        ('CONTACTOR', 'RELAY', 'LIGHT', 'PUSHBUTTON', 'TIMER', 'SELECTOR')),
    'Legrand': ('https://www.legrand.com/ecatalogue/en/our-products/energy-distribution-protection-and-management/residential-and-small-commercial-panels/controls/contactors-and-relays',
        ('CONTACTOR', 'RELAY', 'TIMER')),
    'Selec': ('https://webshop.selec.com/us/en/products/ct-operated-em',
        ('METER', 'CT', 'TIMER', 'RELAY', 'POWER_SUPPLY', 'PLC', 'HMI', 'POWER_FACTOR_CONTROLLER')),
    'LOVATO Electric': ('https://www.lovatoelectric.com/us_en/general-catalogue/',
        ('MCB', 'MCCB', 'RCD', 'CONTACTOR', 'OVERLOAD_RELAY', 'MOTOR_PROTECTION',
         'FUSE', 'PUSHBUTTON', 'SELECTOR', 'TIMER', 'RELAY', 'POWER_SUPPLY',
         'METER', 'CT', 'SPD', 'SOFT_STARTER', 'VFD', 'PLC', 'HMI',
         'ATS_CONTROLLER', 'POWER_FACTOR_CONTROLLER', 'LEVEL_RELAY')),
    'Finder': ('https://www.findernet.com/',
        ('RELAY', 'TIMER', 'POWER_SUPPLY', 'METER', 'SPD', 'CONTACTOR', 'TERMINAL')),
    'EMIC': ('https://emic.com.vn/vn/san-pham',
        ('CT', 'AMMETER', 'VOLTMETER', 'ENERGY_METER')),
    'IDEC': ('https://www.idec.com/api/asset/en-eu/3IiYmZaE4LI5RDKk5IopFL/IDEC-PRODUCT-GUIDE-MARCH-2025.pdf',
        ('RELAY', 'TIMER', 'POWER_SUPPLY', 'TERMINAL')),
    'DOLD': ('https://www.dold.com/en/products/relay-modules/timers/', ('TIMER',)),
    'Weidmüller': ('https://eshop.weidmueller.com/',
        ('TERMINAL', 'RELAY', 'POWER_SUPPLY', 'SPD', 'IO')),
    'Phoenix Contact': ('https://www.phoenixcontact.com/en-au/products/relays-and-optocouplers/timer-relays',
        ('TIMER',)),
    'Carlo Gavazzi': ('https://www.gavazziautomation.com/en-us/group/WC000002V60',
        ('ALTERNATING_RELAY',)),
}
for _brand, (_url, _categories) in CATALOGUES.items():
    for _category in _categories:
        PORTFOLIOS.setdefault(_category, {}).setdefault(_brand, _url)

# Direct category pages take precedence over a general catalogue.
for _category, _brand, _url in (
    ('MCCB', 'Schneider Electric', 'https://www.se.com/il/en/product-range/1887-compact-nsx/'),
    ('MCB', 'Legrand', 'https://www.legrand.com/ecatalogue/en/catalog/products/mcb-dx3-2-pole-125a-curve-409777'),
    ('MCCB', 'Legrand', 'https://www.legrand.co.uk/en/catalog/protection'),
    ('MCB', 'Eaton', 'https://www.eaton.com/br/en-us/catalog/electrical-circuit-protection/em-h-xpole-miniature-circuit-breaker.html'),
    ('RCBO', 'CHINT', 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/final-power-distribution/rcbo/nxble-40/manual/2004-NXBLE-40-RCBO-Manual.pdf'),
    ('MCB', 'Siemens', 'https://www.siemens.com/en-gb/products/sentron/miniature-circuit-breakers/'),
    ('MCCB', 'Siemens', 'https://www.siemens.com/en-gb/products/sentron/molded-case-circuit-breakers/'),
    ('TIMER', 'Siemens', 'https://www.siemens.com/es-mx/products/sirius/timing-relays/'),
    ('TIMER', 'Schneider Electric', 'https://www.se.com/us/en/product-range/529-harmony-time/'),
    ('CONTACTOR', 'Schneider Electric', 'https://www.se.com/us/en/product-category/1500-contactors-and-protection-relays/'),
    ('OVERLOAD_RELAY', 'Schneider Electric', 'https://www.se.com/us/en/product-category/1500-contactors-and-protection-relays/'),
    ('FUSE', 'Schneider Electric', 'https://www.se.com/us/en/product-category/1500-contactors-and-protection-relays/'),
    ('LIGHT', 'Schneider Electric', 'https://www.se.com/in/en/product-range/633-harmony-xb5/'),
    ('SELECTOR', 'Schneider Electric', 'https://www.se.com/in/en/product-range/633-harmony-xb5/'),
    ('PUSHBUTTON', 'Schneider Electric', 'https://www.se.com/in/en/product-range/633-harmony-xb5/'),
    ('SELECTOR', 'IDEC', 'https://www.idec.com/en-us/switches-indicator-lights/switches-pushbuttons/pushbuttons-pilot-lights'),
    ('PUSHBUTTON', 'IDEC', 'https://www.idec.com/en-us/switches-indicator-lights/switches-pushbuttons/pushbuttons-pilot-lights'),
    ('MCB', 'Hager', 'https://assets1.sc.hager.com/exports/files/19en_imc_catafr_web_289_chapters_446-561.pdf'),
    ('MCCB', 'Hager', 'https://hager.com/ie/catalogue/switching-and-protective-devices/circuit-breaker-and-switches'),
    ('RCBO', 'Hager', 'https://hager.com/uk/products/'),
    ('ENERGY_METER', 'Hager', 'https://hager.com/uk/products/'),
    ('CT', 'LOVATO Electric', 'https://catalogue.lovatoelectric.com/gb_en/Products/Current-transformers/CAP29/pc'),
    ('TIMER', 'Weidmüller', 'https://www.weidmueller.com/int/products/electronics/relay_modules_solid_state_relays/index.jsp'),
):
    PORTFOLIOS.setdefault(_category, {})[_brand] = _url

TIMER_FUNCTIONS = {
    'on_delay': ('CHINT', 'Omron', 'Autonics', 'Schneider Electric', 'Siemens', 'Legrand', 'IDEC', 'DOLD'),
    'off_delay': ('Omron', 'Autonics', 'Schneider Electric', 'Legrand', 'IDEC', 'DOLD'),
    'cyclic': ('Omron', 'Autonics', 'Legrand', 'DOLD'),
    'star_delta': ('Omron', 'Autonics', 'IDEC', 'DOLD'),
    'calendar': ('Autonics', 'Hager'),
    # Alternating pump starts is a different function from a repeating timer.
    'pump_alternation': ('Finder', 'Carlo Gavazzi'),
}
FUNCTION_SOURCES = {
    'Omron': 'https://www.ia.omron.com/products/category/control-components/timers/analog-timers/',
    'Autonics': 'https://www.autonics.com/us/product/category/Timers',
    'Finder': 'https://www.findernet.com/de/deutschland/series/serie-72-niveauu%CC%88berwachung-16a/type/typ-72-42-steuerrelais-fur-wechselnde-lasten/',
    'Carlo Gavazzi': 'https://www.gavazziautomation.com/en-us/group/WC000002V60',
    'Hager': 'https://hager.com/uk/products/',
}
# Published range names retain their category even when a search result omits
# the generic word MCB from the product's name.
VERIFIED_FAMILIES = {
    ('Schneider Electric','MCB'): ('IC60N','IC60H','IC60L'),
    ('CHINT','MCB'): ('NXB63','NXB63S'),
}
for _brand in TIMER_FUNCTIONS['pump_alternation']:
    PORTFOLIOS.setdefault('ALTERNATING_RELAY', {})[_brand] = FUNCTION_SOURCES[_brand]

ALIASES = {'ls': 'LS Electric', 'ls electric': 'LS Electric', 'chint': 'CHINT',
           'schneider': 'Schneider Electric', 'schneider electric': 'Schneider Electric',
           'idec': 'IDEC', 'omron': 'Omron', 'autonics': 'Autonics', 'siemens': 'Siemens',
           'abb': 'ABB', 'morele': 'Morele', 'andeli': 'Andeli',
           'mitsubishi': 'Mitsubishi Electric', 'mitsubishi electric': 'Mitsubishi Electric',
           'fuji': 'Fuji Electric', 'fuji electric': 'Fuji Electric',
           'hyundai': 'HD Hyundai Electric', 'hyundai electric': 'HD Hyundai Electric',
           'hd hyundai electric': 'HD Hyundai Electric', 'lovato': 'LOVATO Electric',
           'lovato electric': 'LOVATO Electric', 'weidmuller': 'Weidmüller',
           'weidmüller': 'Weidmüller', 'shihlin electric':'Shihlin',
           'selec controls':'Selec', 'hager group':'Hager', 'lsis':'LS Electric',
           'ls industrial systems':'LS Electric', 'lselectric':'LS Electric',
           'chint electric':'CHINT', 'eaton moeller':'Eaton'}
ALIASES.update({name.casefold(): name for rows in PORTFOLIOS.values() for name in rows})


def manufacturer_categories():
    """Return explicit known coverage, with unknown portfolios left unasserted."""
    names = set(DISCOVERED_BRANDS) | {name for rows in PORTFOLIOS.values() for name in rows}
    return {name: {'discovery_source': DISCOVERY_SOURCE if name in DISCOVERED_BRANDS else None,
                   'categories': {category: {'status': 'verified', 'source': rows[name], 'checked_date': CHECKED_DATE}
                                  for category, rows in PORTFOLIOS.items() if name in rows},
                   'timer_functions': [function for function, brands in TIMER_FUNCTIONS.items() if name in brands],
                   'function_evidence': {function: {'status':'verified', 'checked_date':CHECKED_DATE,
                        'source':FUNCTION_SOURCES.get(name, PORTFOLIOS.get('TIMER',{}).get(name))}
                        for function,brands in TIMER_FUNCTIONS.items() if name in brands},
                   'product_families': {kind:list(families) for (brand,kind),families in VERIFIED_FAMILIES.items() if brand==name},
                   'other_categories_status': 'unknown'} for name in sorted(names)}


def canonical_brand(value):
    value = str(value or '').strip()
    return ALIASES.get(value.casefold(), value)


def official_domains(brand):
    from urllib.parse import urlparse
    name=canonical_brand(brand)
    return tuple(sorted({urlparse(url).hostname.removeprefix('www.')
                         for rows in PORTFOLIOS.values() for maker,url in rows.items()
                         if maker==name and urlparse(url).hostname}))


def official_source_owners(url):
    from urllib.parse import urlparse
    def root(host):
        parts=(host or '').casefold().split('.')
        suffix='.'.join(parts[-2:])
        return '.'.join(parts[-3:]) if suffix in {'com.vn','com.tw','co.uk','co.kr','com.au','co.in'} else suffix
    host=root(urlparse(url).hostname)
    return {brand for rows in PORTFOLIOS.values() for brand,source in rows.items()
            if host and root(urlparse(source).hostname)==host}


def known_product_kind(brand,name,sku=''):
    import re
    text=re.sub(r'[^A-Z0-9]','',(str(name)+' '+str(sku)).upper())
    return next((kind for (maker,kind),families in VERIFIED_FAMILIES.items()
                 if maker==canonical_brand(brand) and any(family in text for family in families)),None)


def timer_function(name='', spec=''):
    import unicodedata
    text = unicodedata.normalize('NFKD', (str(name) + ' ' + str(spec)).casefold().replace('đ','d')).encode('ascii', 'ignore').decode()
    if 'luan phien' in text and any(term in text for term in ('bom','pump','may nen','compressor')):
        return 'pump_alternation'
    for function, terms in (
        ('pump_alternation', ('pump alternat', 'alternating load')),
        ('star_delta', ('sao tam giac', 'star delta', 'star-delta')),
        ('calendar', ('24h', '24 h', 'lich', 'calendar', 'time switch')),
        ('off_delay', ('tre tat', 'tre nha', 'off delay', 'off-delay')),
        ('on_delay', ('tre bat', 'tre dong', 'on delay', 'on-delay')),
        ('cyclic', ('chu ky', 'twin timer', 'cyclic', 'lap lai')),
    ):
        if any(term in text for term in terms):
            return function
    return None


def search_portfolios(category, name='', spec=''):
    """Return category/function evidence without inventing negative coverage."""
    category = str(category or '').upper()
    if category in ('TIMER', 'RELAY', 'ALTERNATING_RELAY'):
        function = timer_function(name, spec)
        if function:
            bucket = 'ALTERNATING_RELAY' if function == 'pump_alternation' else 'TIMER'
            return {brand: FUNCTION_SOURCES.get(brand, PORTFOLIOS[bucket].get(brand))
                    for brand in TIMER_FUNCTIONS[function]}
    if category in ('VOLTMETER', 'AMMETER', 'MULTIMETER'):
        return {**PORTFOLIOS.get('METER', {}), **PORTFOLIOS.get(category, {})}
    return dict(PORTFOLIOS.get(category, {}))


def portfolio_hint(category, name='', spec=''):
    rows = search_portfolios(category, name, spec)
    function = timer_function(name, spec) if category in ('TIMER', 'RELAY', 'ALTERNATING_RELAY') else None
    return (('Chức năng cần tìm: ' + function + '. ' if function else '')
            + 'Khoanh vùng hãng có danh mục đã đối chiếu: ' + '; '.join(f'{brand}: {url}' for brand, url in rows.items())
            + '. Tra đúng mã và thông số trong các nguồn này trước; chưa đủ kết quả mới mở rộng hãng khác. '
              'Danh mục chưa xác nhận không có nghĩa hãng không sản xuất. '
              'Timer chu kỳ không mặc nhiên thay relay luân phiên bơm. ') if rows else ''
