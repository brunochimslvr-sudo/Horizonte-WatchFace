"""Gera o projeto WFF "Horizonte" (res/ + AndroidManifest.xml) em resolução nativa 480x480 do Galaxy Watch 8 (44mm).

Uso: python gen.py   ->  escreve em ./src
"""
import math
import os
import random
import re
import shutil

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
RES = os.path.join(SRC, 'res')
SOURCE_XSD = os.path.join(HERE, '..', 'build', 'schema', 'v4', 'common', 'simpleTypes', 'sourceType.xsd')

PACKAGE = 'com.brunochim.horizonte'
WEATHER_APP = 'com.samsung.android.watch.weather/com.samsung.android.watch.weather.ui.WeatherActivity'
WFF_VERSION = 4

# --- Resolução nativa 1:1 do Galaxy Watch 8 44mm (480x480) -----------------
W_FACE = 480
CX = 240.0
K480 = 480 / 450                 # converte medidas de 450 para 480 nativo
SUNRISE, SUNSET = 5.5, 18.25     # horas locais usadas para o arco do sol

# Cores de destaque oferecidas na personalização: (id da string, cor)
ACCENTS = [
    ('acc_sky', '#8FD3FF'), ('acc_white', '#FFFFFF'), ('acc_lime', '#C6EF6A'),
    ('acc_orange', '#FFA24C'), ('acc_pink', '#FF7AA8'), ('acc_lilac', '#B9A5FF'),
]

STRINGS = {
    'watch_face_name': 'Horizonte',
    'cfg_accent': 'Cor de destaque', 'acc_sky': 'Azul céu', 'acc_white': 'Branco', 'acc_lime': 'Lima',
    'acc_orange': 'Laranja', 'acc_pink': 'Rosa', 'acc_lilac': 'Lilás',
    'cfg_sky': 'Fundo', 'sky_auto': 'Céu do dia', 'sky_dark': 'Escuro',
    'cfg_wxsky': 'Céu acompanha o clima',
    'cfg_seconds': 'Segundos',
    'cfg_fc': 'Previsão', 'fc_hours': 'Próximas horas', 'fc_days': 'Próximos dias',
    'slot_tl': 'Canto superior esquerdo', 'slot_tr': 'Canto superior direito',
    'slot_bl': 'Canto inferior esquerdo', 'slot_br': 'Canto inferior direito',
    'slot_top': 'Topo', 'slot_bottom': 'Base',
}

# --- Paleta do céu (mesma do protótipo) ----------------------------------
KF = [
    (0,   ['#0b1026', '#141b3d', '#1d2552']),
    (4.5, ['#0f1433', '#24264f', '#3b2f63']),
    (5.6, ['#3a3a7a', '#c06c9a', '#f7a98b']),
    (7,   ['#5aa9e6', '#9fd3f0', '#fbd3b0']),
    (10,  ['#2f8fe8', '#4fc3f7', '#a8e6cf']),
    (13,  ['#29a8e0', '#46d0c6', '#c6ef6a']),
    (15.5, ['#3f86d6', '#8fc7e8', '#f5c46a']),
    (17.9, ['#4b3b8f', '#e0558a', '#ff8a3d']),
    (19,  ['#1e1f5a', '#5a2d82', '#b04a7a']),
    (20.5, ['#0d1430', '#1a2150', '#2b2d6b']),
    (24,  ['#0b1026', '#141b3d', '#1d2552']),
]


def hx(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def mix(a, b, f):
    return [x + (y - x) * f for x, y in zip(a, b)]


def n(v):
    """Número curto para atributos XML."""
    return ('%.2f' % v).rstrip('0').rstrip('.')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# --- Expressões ------------------------------------------------------------
HF = '([HOUR_0_23] + [MINUTE] / 60)'
HZ = 262.0
ARC_RX, ARC_RY = 180.0, 185.0
WEEKDAYS = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB']
MONTHS = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']


def pick(expr, names):
    """Expressão que devolve names[expr - 1] (expr vai de 1 a len(names))."""
    out = f'"{names[-1]}"'
    for i in range(len(names) - 2, -1, -1):
        out = f'({expr} == {i + 1} ? "{names[i]}" : {out})'
    return out


def day_frac():
    return f'(({HF} - {SUNRISE}) / {SUNSET - SUNRISE})'


def night_frac():
    return f'(({HF} >= {SUNSET} ? {HF} - {SUNSET} : {HF} + {24 - SUNSET}) / {24 - (SUNSET - SUNRISE)})'


def body_x(frac):
    return f'{CX} - {n(ARC_RX)} * cos(rad(180 * {frac}))'


def body_y(frac):
    return f'{n(HZ)} - {n(ARC_RY)} * sin(rad(180 * {frac}))'


def is_day():
    return f'({HF} >= {SUNRISE} ? ({HF} < {SUNSET} ? 1 : 0) : 0)'


def darkness():
    """0 de dia, 1 de noite, com rampa nos dois crepúsculos."""
    return (f'({HF} < 4.5 ? 1 : ({HF} < 6.5 ? (6.5 - {HF}) / 2 : ({HF} < 18.5 ? 0 : '
            f'({HF} < 20.5 ? ({HF} - 18.5) / 2 : 1))))')


ACCENT = '[CONFIGURATION.accent.0]'
SOFT_SHADOW = '#40000000'


def text(x, y, w, h, size, template, params=(), align='CENTER', weight='NORMAL', color='#FFFFFFFF', extra='', spacing=None,
         shadow=False):
    """Texto simples; quando shadow=True usa <Shadow> nativo com raio suave em vez de cópia deslocada."""
    ps = ''.join(f'<Parameter expression="{esc(p)}"/>' for p in params)
    ls = f' letterSpacing="{spacing}"' if spacing else ''
    body = f'<Template>{template}{ps}</Template>' if params else template
    if shadow:
        body = f'<Shadow color="{SOFT_SHADOW}" offsetX="0" offsetY="1.5" radius="3.5">{body}</Shadow>'
    return (f'<PartText x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"{extra}><Text align="{align}">'
            f'<Font family="SYNC_TO_DEVICE" size="{round(size)}" weight="{weight}" color="{color}"{ls}>{body}</Font></Text></PartText>')


# --- Complicações (em coordenadas 480x480) ---------------------------------
R_ARC = 227.0
THICK = 7.0          # faixa fina e elegante
R_ICON = 225.0       # alinhado à ponta do arco, sem bolinha escura
ICON = 21            # ícone proporcional à espessura da faixa
QUADS = [   # a0, a1, ângulo do ícone (ponta perto do horizonte), progresso cresce a partir do fim, parte de baixo
    (290, 340, 280, False, False),
    (20, 70, 80, True, False),
    (200, 250, 260, True, True),
    (110, 160, 100, False, True),
]
R_TXT_TOP, R_TXT_BOT = 199.0, 211.0     # linha de base do texto curvo, acompanhando o arco com folga limpa
SLOT_NAMES = ['slot_tl', 'slot_tr', 'slot_bl', 'slot_br']
DEFAULTS = [
    ('WATCH_BATTERY', 'RANGED_VALUE'),
    ('HEART_RATE', 'SHORT_TEXT'),
    ('SUNRISE_SUNSET', 'SHORT_TEXT'),
    ('STEP_COUNT', 'GOAL_PROGRESS'),
]
SUPPORTED = 'RANGED_VALUE GOAL_PROGRESS SHORT_TEXT EMPTY'
RANGED = ('(clamp([COMPLICATION.RANGED_VALUE_VALUE], [COMPLICATION.RANGED_VALUE_MIN], [COMPLICATION.RANGED_VALUE_MAX])'
          ' - [COMPLICATION.RANGED_VALUE_MIN]) / ([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])')
GOAL = ('clamp([COMPLICATION.GOAL_PROGRESS_VALUE], 0, [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE])'
        ' / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]')


def comp_icon(cx, cy, size, alpha=215):
    """Ícone da complicação sem bolinha escura, dessaturado via HsbFilter para ficar monocromático e uniforme."""
    return ('<Condition><Expressions><Expression name="tem_icone"><![CDATA[[COMPLICATION.MONOCHROMATIC_IMAGE] != null]]>'
            f'</Expression></Expressions><Compare expression="tem_icone"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="icone">'
            f'<PartImage x="{n(cx - size / 2)}" y="{n(cy - size / 2)}" width="{size}" height="{size}" alpha="{alpha}" '
            'tintColor="#FFFFFFFF"><ImageFilters><HsbFilter saturate="0" brightness="1"/></ImageFilters>'
            '<Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]"/></PartImage></Group></Compare></Condition>')


def quad_box(a0, a1, ia):
    """Caixa (x, y, w, h) que envolve arco, ícone e texto do canto."""
    pts = []
    for a in range(min(a0, ia) - 8, max(a1, ia) + 9, 2):
        r = math.radians(a)
        for rad_ in (R_TXT_TOP - 24, R_ARC + THICK / 2 + 6):
            pts.append((CX + rad_ * math.sin(r), CX - rad_ * math.cos(r)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = max(0, min(xs)), max(0, min(ys))
    return x0, y0, min(W_FACE, max(xs)) - x0, min(W_FACE, max(ys)) - y0


def corner_xml(i):
    a0, a1, ia, from_end, bottom = QUADS[i]
    bx, by, bw, bh = quad_box(a0, a1, ia)
    ccx, ccy = CX - bx, CX - by      # centro do relógio em coordenadas do slot
    span = a1 - a0
    arc_attr = f'centerX="{n(ccx)}" centerY="{n(ccy)}" width="{n(2 * R_ARC)}" height="{n(2 * R_ARC)}" startAngle="{a0}" endAngle="{a1}"'
    track_col = '#22FFFFFF' if bottom else '#2EFFFFFF'

    def arcs(frac_expr):
        target, value = (('startAngle', f'{a1} - {span} * ({frac_expr})') if from_end
                         else ('endAngle', f'{a0} + {span} * ({frac_expr})'))
        fill = '' if frac_expr is None else (
            f'<PartDraw x="0" y="0" width="{n(bw)}" height="{n(bh)}"><Arc {arc_attr}>'
            f'<Stroke thickness="{n(THICK)}" color="{ACCENT}" cap="ROUND"/>'
            f'<Transform target="{target}" value="{esc(value)}"/></Arc></PartDraw>')
        return (f'<Group x="0" y="0" width="{n(bw)}" height="{n(bh)}" name="arco{i}"><Variant mode="AMBIENT" target="alpha" value="0"/>'
                f'<PartDraw x="0" y="0" width="{n(bw)}" height="{n(bh)}"><Arc {arc_attr}>'
                f'<Stroke thickness="{n(THICK)}" color="{track_col}" cap="ROUND"/></Arc></PartDraw>{fill}</Group>')

    # texto curvo acompanhando o arco, sempre "de pé", mais leve e com janela angular mais ampla
    if bottom:
        t0, t1, direction, r_txt = a1 + 8, a0 - 8, 'COUNTER_CLOCKWISE', R_TXT_BOT
    else:
        t0, t1, direction, r_txt = a0 - 8, a1 + 8, 'CLOCKWISE', R_TXT_TOP

    inner = '<Template>%s<Parameter expression="[COMPLICATION.TEXT]"/></Template>'
    if not bottom:
        inner = f'<Shadow color="{SOFT_SHADOW}" offsetX="0" offsetY="1" radius="3">{inner}</Shadow>'
    label = (f'<PartText x="0" y="0" width="{n(bw)}" height="{n(bh)}"><TextCircular centerX="{n(ccx)}" centerY="{n(ccy)}" '
             f'width="{n(2 * r_txt)}" height="{n(2 * r_txt)}" startAngle="{t0 % 360}" endAngle="{t1 % 360}" direction="{direction}" '
             f'align="CENTER" ellipsis="TRUE"><Font family="SYNC_TO_DEVICE" size="16" weight="MEDIUM" letterSpacing="0.02" '
             f'color="#D9FFFFFF">{inner}</Font></TextCircular></PartText>')

    r = math.radians(ia)
    icon = comp_icon(CX + R_ICON * math.sin(r) - bx, CX - R_ICON * math.cos(r) - by, ICON, alpha=210)

    body = (f'<Complication type="RANGED_VALUE">{arcs(RANGED)}{icon}{label}</Complication>'
            f'<Complication type="GOAL_PROGRESS">{arcs(GOAL)}{icon}{label}</Complication>'
            f'<Complication type="SHORT_TEXT">{arcs(None)}{icon}{label}</Complication>'
            f'<Complication type="EMPTY">{arcs(None)}</Complication>')
    prov, typ = DEFAULTS[i]
    return (f'<ComplicationSlot slotId="{i}" name="canto{i}" displayName="{SLOT_NAMES[i]}" x="{n(bx)}" y="{n(by)}" '
            f'width="{n(bw)}" height="{n(bh)}" supportedTypes="{SUPPORTED}">'
            f'<DefaultProviderPolicy defaultSystemProvider="{prov}" defaultSystemProviderType="{typ}"/>'
            f'<BoundingBox x="0" y="0" width="{n(bw)}" height="{n(bh)}"/>{body}</ComplicationSlot>')


def center_slot_xml(slot_id, name, x, y, w, h, prov, typ, top=False):
    """Espaço discreto no topo/base: ícone compacto em cima, texto leve embaixo."""
    icon = comp_icon(w / 2, 13, 19, alpha=210)
    col = '#E6FFFFFF' if top else '#CCFFFFFF'
    label = text(0, 26, w, h - 26, 16, '%s', ['[COMPLICATION.TEXT]'], weight='MEDIUM', color=col, shadow=top)
    body = ''.join(f'<Complication type="{t}">{icon}{label}</Complication>' for t in ('SHORT_TEXT', 'RANGED_VALUE', 'GOAL_PROGRESS'))
    return (f'<ComplicationSlot slotId="{slot_id}" name="{name}" displayName="{name}" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'supportedTypes="{SUPPORTED}"><DefaultProviderPolicy defaultSystemProvider="{prov}" defaultSystemProviderType="{typ}"/>'
            f'<BoundingBox x="0" y="0" width="{n(w)}" height="{n(h)}"/>{body}<Complication type="EMPTY"/></ComplicationSlot>')


# --- Ícones de clima e elementos gráficos de alta definição ----------------
ICONS = ['sun', 'moon', 'cloud', 'cloudsun', 'cloudmoon', 'rain', 'snow', 'storm', 'fog', 'wind', 'drop']
COND = {
    0: ('cloud', 'cloud'), 1: ('sun', 'moon'), 2: ('cloud', 'cloud'), 3: ('fog', 'fog'), 4: ('rain', 'rain'),
    5: ('snow', 'snow'), 6: ('rain', 'rain'), 7: ('snow', 'snow'), 8: ('sun', 'moon'), 9: ('storm', 'storm'),
    10: ('snow', 'snow'), 11: ('snow', 'snow'), 12: ('rain', 'rain'), 13: ('fog', 'fog'),
    14: ('cloudsun', 'cloudmoon'), 15: ('wind', 'wind'),
}


class StrokeCanvas:
    """Desenha curvas e linhas com traço único, perfeitamente arredondado (round cap / round join) em 8x."""
    def __init__(self, size=96, scale=8):
        self.size = size
        self.k = scale
        self.s = size * scale
        self.u = self.s / 96.0
        self.im = Image.new('RGBA', (self.s, self.s), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def disc(self, x, y, r, col=(255, 255, 255, 255)):
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=col)

    def seg(self, x0, y0, x1, y1, w, col=(255, 255, 255, 255)):
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(dist / (self.k * 0.35)))
        r = w / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, col)

    def poly(self, pts, w, closed=False, col=(255, 255, 255, 255)):
        pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
        for (x0, y0), (x1, y1) in pairs:
            self.seg(x0, y0, x1, y1, w, col)

    def arc(self, cx, cy, r, a0_deg, a1_deg, w, col=(255, 255, 255, 255)):
        span = abs(a1_deg - a0_deg)
        steps = max(8, int(span * 2.5))
        hr = w / 2.0
        for i in range(steps + 1):
            a = math.radians(a0_deg + (a1_deg - a0_deg) * (i / steps))
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a), hr, col)

    def finish(self):
        return self.im.resize((self.size, self.size), Image.LANCZOS)


def _cloud_pts(cx, cy, u, sc=1.0):
    """Geometria limpa de uma nuvem de traço contínuo com base reta e 2 cúpulas suaves."""
    pts = []
    for i in range(25):
        t = i / 24
        pts.append((cx + (17 - 28 * t) * u * sc, cy + 12 * u * sc))
    for a in range(90, 253, 4):
        r = math.radians(a)
        pts.append((cx + (-11 + 11 * math.cos(r)) * u * sc, cy + (1 + 11 * math.sin(r)) * u * sc))
    for a in range(205, 339, 3):
        r = math.radians(a)
        pts.append((cx + (4 + 15 * math.cos(r)) * u * sc, cy + (-5 + 15 * math.sin(r)) * u * sc))
    for a in range(285, 451, 4):
        r = math.radians(a)
        pts.append((cx + (17 + 9 * math.cos(r)) * u * sc, cy + (3 + 9 * math.sin(r)) * u * sc))
    return pts


def draw_icon(name, size=96):
    c = StrokeCanvas(size=size, scale=8)
    u = c.u
    w = 5.2 * u       # traço único, fino e arredondado para toda a família de ícones
    W = (255, 255, 255, 255)
    SOFT = (255, 255, 255, 36)

    def draw_sun(cx, cy, r_core, r_in, r_out, sw=w):
        c.disc(cx, cy, r_core, SOFT)
        c.arc(cx, cy, r_core, 0, 360, sw, W)
        for i in range(8):
            a = i * math.pi / 4
            c.seg(cx + r_in * math.cos(a), cy + r_in * math.sin(a),
                  cx + r_out * math.cos(a), cy + r_out * math.sin(a), sw * 0.92, W)

    def draw_moon(cx, cy, r, sw=w):
        cx2, cy2, r2 = cx + r * 0.52, cy - r * 0.34, r * 0.88
        outer = []
        for deg in range(360):
            a = math.radians((deg + 25) % 360)
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            if math.hypot(px - cx2, py - cy2) >= r2:
                outer.append((px, py))
        inner = []
        for deg in range(360):
            a = math.radians((deg + 25) % 360)
            px, py = cx2 + r2 * math.cos(a), cy2 + r2 * math.sin(a)
            if math.hypot(px - cx, py - cy) <= r:
                inner.append((px, py))
        inner.reverse()
        poly_pts = outer + inner
        c.d.polygon(poly_pts, fill=SOFT)
        c.poly(poly_pts, sw, closed=True, col=W)

    def draw_cloud(cx, cy, sc=1.0, sw=w, cutout_gap=0):
        pts = _cloud_pts(cx, cy, u, sc)
        if cutout_gap > 0:
            mask = Image.new('L', (c.s, c.s), 0)
            md = ImageDraw.Draw(mask)
            md.polygon(pts, fill=255)
            r_clear = (sw + cutout_gap) / 2.0
            for px, py in pts[::2]:
                md.ellipse((px - r_clear, py - r_clear, px + r_clear, py + r_clear), fill=255)
            c.im.paste((0, 0, 0, 0), (0, 0), mask)
        c.d.polygon(pts, fill=SOFT)
        c.poly(pts, sw, closed=True, col=W)

    if name == 'sun':
        draw_sun(48 * u, 48 * u, 14 * u, 22.5 * u, 31 * u)
    elif name == 'moon':
        draw_moon(50 * u, 48 * u, 23 * u)
    elif name == 'cloud':
        draw_cloud(46 * u, 50 * u, sc=1.12)
    elif name == 'cloudsun':
        draw_sun(33 * u, 34 * u, 10.5 * u, 16.5 * u, 22.5 * u, sw=w * 0.92)
        draw_cloud(51 * u, 54 * u, sc=0.95, cutout_gap=6.5 * u)
    elif name == 'cloudmoon':
        draw_moon(35 * u, 35 * u, 16 * u, sw=w * 0.92)
        draw_cloud(51 * u, 54 * u, sc=0.95, cutout_gap=6.5 * u)
    elif name == 'rain':
        draw_cloud(46 * u, 39 * u, sc=1.0)
        for x in (31, 47, 63):
            c.seg(x * u, 60 * u, (x - 6) * u, 77 * u, w * 0.88, W)
    elif name == 'snow':
        draw_cloud(46 * u, 39 * u, sc=1.0)
        for cx_f, cy_f in ((30, 68), (47, 73), (64, 68)):
            for i in range(3):
                a = i * math.pi / 3
                r_f = 6.2 * u
                c.seg(cx_f * u - r_f * math.cos(a), cy_f * u - r_f * math.sin(a),
                      cx_f * u + r_f * math.cos(a), cy_f * u + r_f * math.sin(a), w * 0.52, W)
    elif name == 'storm':
        draw_cloud(46 * u, 38 * u, sc=1.0)
        bolt = [(49 * u, 55 * u), (39 * u, 69 * u), (49 * u, 69 * u), (43 * u, 84 * u)]
        c.poly(bolt, w * 0.9, closed=False, col=W)
    elif name == 'fog':
        draw_cloud(46 * u, 37 * u, sc=0.96)
        for y, x0, x1 in ((62, 24, 72), (74, 30, 66)):
            c.seg(x0 * u, y * u, x1 * u, y * u, w * 0.88, W)
    elif name == 'wind':
        c.seg(16 * u, 36 * u, 62 * u, 36 * u, w * 0.9, W)
        c.arc(62 * u, 28 * u, 8 * u, 90, -110, w * 0.9, W)
        c.seg(14 * u, 50 * u, 72 * u, 50 * u, w * 0.9, W)
        c.arc(72 * u, 58 * u, 8 * u, -90, 110, w * 0.9, W)
        c.seg(22 * u, 64 * u, 52 * u, 64 * u, w * 0.9, W)
    elif name == 'drop':
        sw = 6.2 * u
        cx_d, cy_d, r_d = 48 * u, 58 * u, 19 * u
        top_y = 18 * u
        pts = [(cx_d, top_y)]
        for a in range(-28, 209, 4):
            rad = math.radians(a)
            pts.append((cx_d + r_d * math.cos(rad), cy_d + r_d * math.sin(rad)))
        c.d.polygon(pts, fill=(255, 255, 255, 64))
        c.poly(pts, sw, closed=True, col=W)
    return c.finish()


def draw_sky_sun(size=136):
    """Sol com halo em degradê radial contínuo (sem anéis visíveis) e leve dithering."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    px = im.load()
    cx = cy = (size - 1) / 2.0
    r_disc = 12.2
    r_max = size / 2.0 - 1.0
    rng = random.Random(42)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy)
            if d <= r_disc - 0.8:
                px[x, y] = (255, 247, 218, 255)
            elif d <= r_disc + 0.8:
                t = (d - (r_disc - 0.8)) / 1.6
                halo_a = 145.0
                a = int(round(255 * (1 - t) + halo_a * t))
                px[x, y] = (255, int(round(247 * (1 - t) + 255 * t)), int(round(218 * (1 - t) + 255 * t)), a)
            elif d < r_max:
                u = (d - r_disc) / (r_max - r_disc)
                fade = (1.0 - u * u) ** 2
                alpha = 145.0 * math.exp(-3.2 * u) * fade
                a = int(max(0, min(255, round(alpha + (rng.random() - 0.5) * 0.9))))
                if a > 0:
                    px[x, y] = (255, 252, 240, a)
    return im


def draw_sky_moon(size=102):
    """Lua do céu com halo suave em degradê radial e crescente nítido."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    px = im.load()
    cx = cy = (size - 1) / 2.0
    r_max = size / 2.0 - 1.0
    rng = random.Random(99)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy)
            if d < r_max:
                u = d / r_max
                fade = (1.0 - u * u) ** 2
                alpha = 75.0 * math.exp(-3.0 * u) * fade
                a = int(max(0, min(255, round(alpha + (rng.random() - 0.5) * 0.8))))
                if a > 0:
                    px[x, y] = (235, 232, 255, a)
    k = 4
    m_im = Image.new('RGBA', (size * k, size * k), (0, 0, 0, 0))
    md = ImageDraw.Draw(m_im)
    mcx, mcy, mr = size * k / 2.0, size * k / 2.0, 11.2 * k
    md.ellipse((mcx - mr, mcy - mr, mcx + mr, mcy + mr), fill=(244, 242, 255, 255))
    mask = Image.new('L', (size * k, size * k), 0)
    ImageDraw.Draw(mask).ellipse((mcx - mr * 0.25, mcy - mr * 1.08, mcx + mr * 1.55, mcy + mr * 0.72), fill=255)
    m_im.paste((0, 0, 0, 0), (0, 0), mask)
    m_im = m_im.resize((size, size), Image.LANCZOS)
    return Image.alpha_composite(im, m_im)


def draw_sky_arc():
    """Arco da trajetória do sol renderizado em 4x (em 480x262) com pontos redondos anti-aliased e fade no horizonte."""
    w, h = W_FACE, round(HZ)
    k = 4
    im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n_dots = 56
    r_dot = 1.2 * k
    for i in range(1, n_dots):
        frac = i / n_dots
        ang = math.pi * frac
        x = (CX - ARC_RX * math.cos(ang)) * k
        y = (HZ - ARC_RY * math.sin(ang)) * k
        edge_fade = math.sin(ang) ** 0.55
        alpha = int(round(105 * edge_fade))
        if alpha > 4 and 0 <= y <= h * k:
            d.ellipse((x - r_dot, y - r_dot, x + r_dot, y + r_dot), fill=(255, 255, 255, alpha))
    return im.resize((w, h), Image.LANCZOS)


# --- watchface.xml ---------------------------------------------------------
_FLOAT_OK = ('Arc', 'TextCircular', 'BoundingArc', 'Shadow', 'OutGlow', 'LinearGradient')


def ints(xml):
    """O esquema exige inteiros em x/y/width/height das partes; arredonda tudo, menos elementos geométricos/decoração."""
    def fix_tag(m):
        tag = m.group(0)
        name = re.match(r'<(\w+)', tag).group(1)
        if name in _FLOAT_OK:
            return tag

        def rnd(a):
            v = max(1, round(float(a.group(2)))) if a.group(1) in ('width', 'height') else round(float(a.group(2)))
            return f'{a.group(1)}="{v}"'
        return re.sub(r'(?<![A-Za-z])(x|y|width|height)="(-?[0-9.]+)"', rnd, tag)
    return re.sub(r'<\w+[^<>]*>', fix_tag, xml)


def check_sources(xml):
    """Falha se o XML usar uma fonte de dados que não existe no esquema (isso deixa a tela preta no relógio)."""
    src = open(SOURCE_XSD, encoding='utf-8').read()
    names = set(re.findall(r'<xs:enumeration value="([^"]+)"', src))
    patterns = [re.compile(p.replace('\\\\', '\\') + '$') for p in re.findall(r'<xs:pattern value="([^"]+)"', src)]
    names |= {'WEATHER.DAY_TEMPERATURE_HIGH', 'WEATHER.DAY_TEMPERATURE_LOW'}
    used = set(re.findall(r'\[([A-Z][A-Z0-9_.]*)\]', xml))
    bad = [u for u in used if not (u in names or u.startswith(('CONFIGURATION.', 'COMPLICATION.'))
                                   or any(p.match(u) for p in patterns))]
    if bad:
        raise SystemExit('Fontes de dados desconhecidas: ' + ', '.join(sorted(bad)))


def weather_icon(prefix, x, y, size, name, color='#FFFFFFFF'):
    idx = f'[WEATHER.{prefix}CONDITION] &lt;= 15 ? [WEATHER.{prefix}CONDITION] : 0'

    def part(fam):
        return (f'<PartText x="{n(x)}" y="{n(y)}" width="{size}" height="{size}"><Text><BitmapFont family="{fam}" size="{size}" color="{color}">'
                f'<Template>%s<Parameter expression="{idx}"/></Template></BitmapFont></Text></PartText>')
    return (f'<Condition><Expressions><Expression name="{name}">[WEATHER.{prefix}IS_DAY]</Expression></Expressions>'
            f'<Compare expression="{name}">{part("wx_day")}</Compare><Default>{part("wx_night")}</Default></Condition>')


def day_icon(k, x, y, size, color='#E6FFFFFF'):
    idx = f'[WEATHER.DAYS.{k}.CONDITION_DAY] &lt;= 15 ? [WEATHER.DAYS.{k}.CONDITION_DAY] : 0'
    return (f'<PartText x="{n(x)}" y="{n(y)}" width="{size}" height="{size}"><Text><BitmapFont family="wx_day" size="{size}" color="{color}">'
            f'<Template>%s<Parameter expression="{idx}"/></Template></BitmapFont></Text></PartText>')


def sky_layers():
    """Uma camada de gradiente fixo por momento-chave; a próxima aparece por cima com alpha em smoothstep."""
    out = []
    times = [t for t, _ in KF]
    last = len(KF) - 1
    for j, (t, cols) in enumerate(KF):
        stops = ' '.join('#FF' + c[1:].upper() for c in cols)
        hold = '255' if j == last else f'({HF} < {times[j + 1]} ? 255 : 0)'
        if j == 0:
            alpha = hold
        else:
            a, b = times[j - 1], t
            f = f'(({HF} - {a}) / {b - a})'
            alpha = f'({HF} >= {a} ? ({HF} < {b} ? 255 * {f} * {f} * (3 - 2 * {f}) : {hold}) : 0)'
        out.append(f'<PartDraw x="0" y="0" width="{W_FACE}" height="{n(HZ)}"><Transform target="alpha" value="{esc(alpha)}"/>'
                   f'<Rectangle x="0" y="0" width="{W_FACE}" height="{n(HZ)}"><Fill color="#FF000000">'
                   f'<LinearGradient startX="0" startY="0" endX="0" endY="{n(HZ)}" colors="{stops}" positions="0 0.6 1"/>'
                   f'</Fill></Rectangle></PartDraw>')
    return ''.join(out)


def gradient_rect(y, h, colors, positions='0 1', alpha_expr=None):
    tr = f'<Transform target="alpha" value="{esc(alpha_expr)}"/>' if alpha_expr else ''
    return (f'<PartDraw x="0" y="{n(y)}" width="{W_FACE}" height="{n(h)}">{tr}<Rectangle x="0" y="0" width="{W_FACE}" height="{n(h)}">'
            f'<Fill color="#FF000000"><LinearGradient startX="0" startY="0" endX="0" endY="{n(h)}" colors="{colors}" '
            f'positions="{positions}"/></Fill></Rectangle></PartDraw>')


def build_watchface():
    out = []
    A = out.append
    A('<?xml version="1.0" encoding="UTF-8"?>')
    A(f'<WatchFace width="{W_FACE}" height="{W_FACE}">')
    A('<Metadata key="CLOCK_TYPE" value="DIGITAL"/><Metadata key="PREVIEW_TIME" value="10:08:30"/>')

    # ---------- opções da tela "Personalizar" ----------
    A('<UserConfigurations>')
    A('<ColorConfiguration id="accent" displayName="cfg_accent" defaultValue="0">')
    for k, (name, col) in enumerate(ACCENTS):
        A(f'<ColorOption id="{k}" displayName="{name}" colors="{col}"/>')
    A('</ColorConfiguration>')
    A('<ListConfiguration id="sky" displayName="cfg_sky" defaultValue="auto">'
      '<ListOption id="auto" displayName="sky_auto"/><ListOption id="dark" displayName="sky_dark"/></ListConfiguration>')
    A('<BooleanConfiguration id="wxsky" displayName="cfg_wxsky" defaultValue="TRUE"/>')
    A('<ListConfiguration id="fc" displayName="cfg_fc" defaultValue="hours">'
      '<ListOption id="hours" displayName="fc_hours"/><ListOption id="days" displayName="fc_days"/></ListConfiguration>')
    A('<BooleanConfiguration id="seconds" displayName="cfg_seconds" defaultValue="TRUE"/>')
    A('</UserConfigurations>')

    # fontes bitmap com os ícones do clima (0-9 são Character, 10+ são Word)
    A('<BitmapFonts>')
    for fam, idx in (('wx_day', 0), ('wx_night', 1)):
        A(f'<BitmapFont name="{fam}">')
        for code in range(16):
            tag = 'Character' if code < 10 else 'Word'
            A(f'<{tag} name="{code}" resource="wx_{COND[code][idx]}" width="96" height="96"/>')
        A('</BitmapFont>')
    A('</BitmapFonts>')

    A('<Scene backgroundColor="#ff000000">')

    # ---------- camada interativa (some no modo ambiente) ----------
    A(f'<Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="interativo"><Variant mode="AMBIENT" target="alpha" value="0"/>')

    # céu (opção "Fundo")
    A('<ListConfiguration id="sky">')
    A(f'<ListOption id="auto"><Group x="0" y="0" width="{W_FACE}" height="{n(HZ)}" name="ceu_dia">{sky_layers()}</Group></ListOption>')
    A(f'<ListOption id="dark"><Group x="0" y="0" width="{W_FACE}" height="{n(HZ)}" name="ceu_escuro">'
      f'{gradient_rect(0, HZ, "#FF05070E #FF0B1022 #FF162040", "0 0.6 1")}</Group></ListOption>')
    A('</ListConfiguration>')

    # céu acinzentado quando está nublado, chovendo ou nevando
    c = '[WEATHER.CONDITION]'
    rain = ' || '.join(f'{c} == {k}' for k in (4, 6, 9, 12))
    grey = ' || '.join(f'{c} == {k}' for k in (2, 3, 13))
    snow = ' || '.join(f'{c} == {k}' for k in (5, 7, 10, 11))
    wx_alpha = f'[WEATHER.IS_AVAILABLE] ? (({rain}) ? 165 : (({grey}) ? 120 : (({snow}) ? 95 : 0))) : 0'
    A(f'<BooleanConfiguration id="wxsky"><BooleanOption id="TRUE"><Group x="0" y="0" width="{W_FACE}" height="{n(HZ)}" name="ceu_clima">'
      f'{gradient_rect(0, HZ, "#FF3C434F #FF6E7682 #FF9AA1AA", "0 0.6 1", wx_alpha)}</Group></BooleanOption></BooleanConfiguration>')

    # estrelas
    stars = [(90, 120), (140, 70), (200, 105), (300, 60), (350, 115), (390, 170), (120, 190), (260, 140), (400, 140),
             (70, 220), (180, 40), (420, 230)]
    A(f'<Group x="0" y="0" width="{W_FACE}" height="{n(HZ)}" name="estrelas">'
      f'<Transform target="alpha" value="{esc(f"255 * {darkness()}")}"/>')
    for k, (sx, sy) in enumerate(stars):
        r = 1.6 if k % 3 == 0 else 1.1
        al = 'E6' if k % 2 == 0 else '80'
        A(f'<PartDraw x="{n(sx - r)}" y="{n(sy - r)}" width="{n(2 * r)}" height="{n(2 * r)}">'
          f'<Ellipse x="0" y="0" width="{n(2 * r)}" height="{n(2 * r)}"><Fill color="#{al}FFFFFF"/></Ellipse></PartDraw>')
    A('</Group>')

    # arco pontilhado do sol (pré-renderizado em 4x com fade suave no horizonte)
    A(f'<PartImage x="0" y="0" width="{W_FACE}" height="{round(HZ)}"><Image resource="sky_arc"/></PartImage>')

    # sol com brilho em degradê radial suave (PNG sem anéis)
    gl = 136
    fd = day_frac()
    A(f'<PartImage x="0" y="0" width="{gl}" height="{gl}"><Transform target="x" value="{esc(body_x(fd) + f" - {gl / 2}")}"/>'
      f'<Transform target="y" value="{esc(body_y(fd) + f" - {gl / 2}")}"/><Transform target="alpha" value="{esc(f"255 * {is_day()}")}"/>'
      '<Image resource="sky_sun"/></PartImage>')

    # lua com brilho suave
    fnt = night_frac()
    ms = 102
    A(f'<PartImage x="0" y="0" width="{ms}" height="{ms}"><Transform target="x" value="{esc(body_x(fnt) + f" - {ms / 2}")}"/>'
      f'<Transform target="y" value="{esc(body_y(fnt) + f" - {ms / 2}")}"/>'
      f'<Transform target="alpha" value="{esc(f"255 * (1 - {is_day()})")}"/><Image resource="sky_moon"/></PartImage>')

    # bruma suave logo acima do horizonte para dar profundidade ao céu
    A(gradient_rect(HZ - 38, 38, '#00FFFFFF #26FFFFFF', '0 1'))

    # chão com acabamento em múltiplos tons escuros e linha do horizonte com brilho central suave
    A(gradient_rect(HZ, W_FACE - HZ, '#FF171B24 #FF0C0E14 #FF050609', '0 0.48 1'))
    A(f'<PartDraw x="0" y="{round(HZ)}" width="{W_FACE}" height="2"><Rectangle x="0" y="0" width="{W_FACE}" height="2">'
      f'<Fill color="#FF000000"><LinearGradient startX="0" startY="0" endX="{W_FACE}" endY="0" '
      'colors="#14FFFFFF #78FFFFFF #14FFFFFF" positions="0.08 0.5 0.92"/></Fill></Rectangle></PartDraw>')

    # ---- clima atual: ícone, temperatura principal em destaque, máx/mín e chance de chuva em tom secundário
    A(f'<Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="clima"><Condition><Expressions><Expression name="wx_ok">[WEATHER.IS_AVAILABLE]</Expression></Expressions>'
      f'<Compare expression="wx_ok"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="clima_ok">')
    A(weather_icon('', 115, 275, 40, 'dnow'))
    A(text(162, 269, 92, 50, 42, '%s°', ['[WEATHER.TEMPERATURE]'], align='START', weight='SEMI_BOLD', color='#FFFFFFFF'))
    A(text(256, 273, 128, 24, 17, '↑%s°  ↓%s°', ['[WEATHER.DAY_TEMPERATURE_HIGH]', '[WEATHER.DAY_TEMPERATURE_LOW]'],
           align='START', weight='MEDIUM', color='#B3FFFFFF'))
    A(f'<PartImage x="256" y="299" width="15" height="15" tintColor="{ACCENT}"><Image resource="wx_drop"/></PartImage>')
    A(text(275, 294, 96, 24, 17, '%s%%', ['[WEATHER.CHANCE_OF_PRECIPITATION]'], align='START', weight='MEDIUM', color='#B3FFFFFF'))

    # linha divisória sutil entre o clima atual e a grade de previsão
    A('<PartDraw x="122" y="324" width="236" height="1"><Rectangle x="0" y="0" width="236" height="1">'
      '<Fill color="#FF000000"><LinearGradient startX="0" startY="0" endX="236" endY="0" '
      'colors="#00FFFFFF #24FFFFFF #00FFFFFF" positions="0 0.5 1"/></Fill></Rectangle></PartDraw>')

    # ---- previsão (opção "Previsão": próximas horas ou próximos dias)
    cols = [150 + k * 60 for k in range(4)]
    A(f'<ListConfiguration id="fc"><ListOption id="hours"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="prev_horas">')
    for k, cx in enumerate(cols):
        hr = k + 1
        A(f'<Condition><Expressions><Expression name="h{hr}">[WEATHER.HOURS.{hr}.IS_AVAILABLE]</Expression></Expressions>'
          f'<Compare expression="h{hr}"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="hora{hr}">')
        A(weather_icon(f'HOURS.{hr}.', cx - 15, 332, 30, f'dh{hr}', color='#E6FFFFFF'))
        A(text(cx - 30, 364, 60, 24, 18, '%s°', [f'[WEATHER.HOURS.{hr}.TEMPERATURE]'], weight='MEDIUM', color='#F2FFFFFF'))
        A(text(cx - 27, 386, 54, 20, 14, '%sh', [f'([HOUR_0_23] + {hr}) % 24'], weight='NORMAL', color='#8CFFFFFF'))
        A('</Group></Compare></Condition>')
    A(f'</Group></ListOption><ListOption id="days"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="prev_dias">')
    for k, cx in enumerate(cols):
        d = k + 1
        A(f'<Condition><Expressions><Expression name="d{d}">[WEATHER.DAYS.{d}.IS_AVAILABLE]</Expression></Expressions>'
          f'<Compare expression="d{d}"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="dia{d}">')
        A(day_icon(d, cx - 15, 332, 30, color='#E6FFFFFF'))
        A(text(cx - 30, 364, 60, 24, 16, '%s°/%s°', [f'[WEATHER.DAYS.{d}.TEMPERATURE_HIGH]', f'[WEATHER.DAYS.{d}.TEMPERATURE_LOW]'],
               weight='MEDIUM', color='#F2FFFFFF'))
        A(text(cx - 27, 386, 54, 20, 14, '%s', [pick(f'(([DAY_OF_WEEK] - 1 + {d}) % 7 + 1)', WEEKDAYS)],
               weight='NORMAL', color='#8CFFFFFF'))
        A('</Group></Compare></Condition>')
    A('</Group></ListOption></ListConfiguration>')

    A('</Group></Compare><Default>')
    A(text(80, 311, 320, 28, 17, 'Toque para atualizar o clima', color='#8CFFFFFF'))
    A('</Default></Condition></Group>')

    # tocar no clima abre o app de clima do relógio
    A(f'<Group x="96" y="266" width="288" height="142" name="abre_clima"><Launch target="{WEATHER_APP}"/>'
      '<PartDraw x="0" y="0" width="288" height="142"><Rectangle x="0" y="0" width="288" height="142"><Fill color="#00000000"/>'
      '</Rectangle></PartDraw></Group>')

    # data em maiúsculas com ponto separador e peso médio para dar protagonismo à hora
    date_params = [pick('[DAY_OF_WEEK]', WEEKDAYS), '[DAY]', pick('[MONTH]', MONTHS)]
    A(text(80, 104, 320, 30, 19, '%s · %s %s', date_params, weight='MEDIUM', color='#E6FFFFFF', spacing='0.12', shadow=True))
    A('</Group>')  # fim interativo

    # ---------- relógio (sem cópia deslocada dura) ----------
    A(f'<DigitalClock x="0" y="0" width="{W_FACE}" height="{W_FACE}">')
    A(f'<TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="130" width="{W_FACE}" height="115" alpha="255">'
      '<Variant mode="AMBIENT" target="alpha" value="0"/><Font family="SYNC_TO_DEVICE" size="96" weight="SEMI_BOLD" color="#FFFFFFFF"/></TimeText>')
    A(f'<TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="130" width="{W_FACE}" height="115" alpha="0">'
      '<Variant mode="AMBIENT" target="alpha" value="255"/><Font family="SYNC_TO_DEVICE" size="96" weight="THIN" color="#FFB9BEC9"/></TimeText>')
    A('</DigitalClock>')
    A(f'<BooleanConfiguration id="seconds"><BooleanOption id="TRUE"><Group x="0" y="0" width="{W_FACE}" height="{W_FACE}" name="segundos">'
      f'<Variant mode="AMBIENT" target="alpha" value="0"/><DigitalClock x="0" y="0" width="{W_FACE}" height="{W_FACE}">'
      f'<TimeText format="ss" align="START" x="371" y="179" width="64" height="38"><Font family="SYNC_TO_DEVICE" size="27" weight="MEDIUM" color="{ACCENT}"/></TimeText>'
      '</DigitalClock></Group></BooleanOption></BooleanConfiguration>')

    # data e horizonte no modo ambiente
    A(text(80, 104, 320, 30, 19, '%s · %s %s', date_params, weight='NORMAL', color='#FF8A8F9C', spacing='0.12',
           extra=' alpha="0"').replace('<Text ', '<Variant mode="AMBIENT" target="alpha" value="255"/><Text ', 1))
    A(f'<PartDraw x="0" y="{round(HZ)}" width="{W_FACE}" height="1" alpha="0"><Variant mode="AMBIENT" target="alpha" value="255"/>'
      f'<Rectangle x="0" y="0" width="{W_FACE}" height="1"><Fill color="#FF2A2D35"/></Rectangle></PartDraw>')

    # ---------- complicações ----------
    for i in range(4):
        A(corner_xml(i))
    A(center_slot_xml(4, 'slot_top', 186, 11, 108, 52, 'UNREAD_NOTIFICATION_COUNT', 'SHORT_TEXT', top=True))
    A(center_slot_xml(5, 'slot_bottom', 170, 414, 140, 54, 'NEXT_EVENT', 'SHORT_TEXT', top=False))

    A('</Scene></WatchFace>')
    xml = ints('\n'.join(out))
    check_sources(xml)
    return xml


# --- manifest / recursos ---------------------------------------------------
def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def preview():
    """Prévia 480x480 de alta definição gerada com os novos elementos visuais."""
    k = 2
    S = W_FACE * k
    im = Image.new('RGBA', (S, S), (5, 6, 9, 255))
    d = ImageDraw.Draw(im)
    top, mid, bot = [hx(c) for c in KF[5][1]]
    hz = round(HZ) * k
    for y in range(hz):
        t = y / hz
        c = mix(top, mid, t / .6) if t < .6 else mix(mid, bot, (t - .6) / .4)
        if y > hz - 38 * k:
            haze = (y - (hz - 38 * k)) / (38 * k) * 0.15
            c = mix(c, [255, 255, 255], haze)
        d.line((0, y, S, y), fill=tuple(round(v) for v in c) + (255,))
    for y in range(hz, S):
        t = (y - hz) / (S - hz)
        c = mix([23, 27, 36], [12, 14, 20], t / .48) if t < .48 else mix([12, 14, 20], [5, 6, 9], (t - .48) / .52)
        d.line((0, y, S, y), fill=tuple(round(v) for v in c) + (255,))

    arc_im = draw_sky_arc().resize((W_FACE * k, round(HZ) * k), Image.LANCZOS)
    im.alpha_composite(arc_im, (0, 0))
    frac = (13.2 - SUNRISE) / (SUNSET - SUNRISE)
    sx = int(round((CX - ARC_RX * math.cos(math.pi * frac) - 68) * k))
    sy = int(round((HZ - ARC_RY * math.sin(math.pi * frac) - 68) * k))
    sun_im = draw_sky_sun(136 * k)
    im.alpha_composite(sun_im, (sx, sy))

    for x in range(S):
        u = abs(x / S - 0.5) * 2
        a = int(round(120 * max(0, 1 - u * 1.1)))
        d.line((x, hz, x, hz + k), fill=(255, 255, 255, a))

    fonts = 'C:/Windows/Fonts/'
    def font(name, sz):
        try:
            return ImageFont.truetype(fonts + name, int(round(sz * k)))
        except OSError:
            return ImageFont.load_default()

    f_date = font('segoeuib.ttf', 18)
    txt_date = 'QUA · 28 OUT'
    w_date = d.textlength(txt_date, font=f_date)
    d.text(((S - w_date) / 2, 108 * k), txt_date, font=f_date, fill=(255, 255, 255, 230))

    f_time = font('segoeuib.ttf', 92)
    txt_time = '13:12'
    w_time = d.textlength(txt_time, font=f_time)
    d.text(((S - w_time) / 2, 126 * k), txt_time, font=f_time, fill=(255, 255, 255, 255))
    d.text((371 * k, 179 * k), '52', font=font('segoeuisl.ttf', 27), fill=(143, 211, 255, 255))

    wx_now = draw_icon('cloudsun', 40 * k)
    im.alpha_composite(wx_now, (115 * k, 275 * k))
    d.text((162 * k, 269 * k), '20°', font=font('segoeuib.ttf', 40), fill=(255, 255, 255, 255))
    d.text((256 * k, 275 * k), '↑21°  ↓14°', font=font('segoeui.ttf', 16), fill=(255, 255, 255, 185))
    drop_ic = draw_icon('drop', 15 * k)
    r, g, b, a = drop_ic.split()
    drop_tinted = Image.merge('RGBA', (r.point(lambda v: v * 143 // 255), g.point(lambda v: v * 211 // 255), b, a))
    im.alpha_composite(drop_tinted, (256 * k, 299 * k))
    d.text((275 * k, 295 * k), '9%', font=font('segoeui.ttf', 16), fill=(255, 255, 255, 185))

    for x in range(122 * k, 358 * k):
        u = abs((x - 240 * k) / (118 * k))
        d.point((x, 324 * k), fill=(255, 255, 255, int(36 * (1 - u))))

    for idx, (ic_name, temp_s, hr_s) in enumerate([('cloudsun', '20°', '14h'), ('cloudsun', '20°', '15h'),
                                                   ('cloud', '19°', '16h'), ('moon', '18°', '17h')]):
        cx_col = (150 + idx * 60) * k
        ic_im = draw_icon(ic_name, 30 * k)
        im.alpha_composite(ic_im, (int(cx_col - 15 * k), 332 * k))
        f_t = font('segoeuib.ttf', 17)
        wt = d.textlength(temp_s, font=f_t)
        d.text((cx_col - wt / 2, 364 * k), temp_s, font=f_t, fill=(255, 255, 255, 240))
        f_h = font('segoeui.ttf', 14)
        wh = d.textlength(hr_s, font=f_h)
        d.text((cx_col - wh / 2, 386 * k), hr_s, font=f_h, fill=(255, 255, 255, 140))

    def draw_round_arc(a_start, a_end, col):
        layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        steps = max(12, int(abs(a_end - a_start) * 3))
        hr = THICK * k / 2.0
        for s_i in range(steps + 1):
            ang = math.radians(a_start + (a_end - a_start) * (s_i / steps) - 90)
            ax = (CX + R_ARC * math.cos(ang)) * k
            ay = (CX + R_ARC * math.sin(ang)) * k
            ld.ellipse((ax - hr, ay - hr, ax + hr, ay + hr), fill=col)
        im.alpha_composite(layer)

    for (a0, a1, ia, from_end, bottom), prog in zip(QUADS, (0.68, 0.08, 0.60, 0.35)):
        track_a = 34 if bottom else 46
        draw_round_arc(a0, a1, (255, 255, 255, track_a))
        if prog > 0:
            span = (a1 - a0) * prog
            s0, s1 = (a1 - span, a1) if from_end else (a0, a0 + span)
            draw_round_arc(s0, s1, (143, 211, 255, 255))

    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S - 1, S - 1), fill=255)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out.resize((W_FACE, W_FACE), Image.LANCZOS)


def main():
    if os.path.isdir(SRC):
        shutil.rmtree(SRC)
    write(os.path.join(SRC, 'AndroidManifest.xml'), f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{PACKAGE}">
    <uses-feature android:name="android.hardware.type.watch" />
    <application android:label="@string/watch_face_name" android:hasCode="false">
        <meta-data android:name="com.google.android.wearable.standalone" android:value="true" />
        <property android:name="com.google.wear.watchface.format.version" android:value="{WFF_VERSION}" />
    </application>
</manifest>
''')
    strings = ''.join(f'    <string name="{k}">{v}</string>\n' for k, v in STRINGS.items())
    write(os.path.join(RES, 'values', 'strings.xml'), f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n{strings}</resources>\n')
    write(os.path.join(RES, 'xml', 'watch_face_info.xml'),
          '<?xml version="1.0" encoding="utf-8"?>\n<WatchFaceInfo>\n    <Preview value="@drawable/preview" />\n'
          '    <Editable value="true" />\n</WatchFaceInfo>\n')
    write(os.path.join(RES, 'raw', 'watchface.xml'), build_watchface())
    os.makedirs(os.path.join(RES, 'drawable'), exist_ok=True)
    preview().save(os.path.join(RES, 'drawable', 'preview.png'))
    draw_sky_sun().save(os.path.join(RES, 'drawable', 'sky_sun.png'))
    draw_sky_moon().save(os.path.join(RES, 'drawable', 'sky_moon.png'))
    draw_sky_arc().save(os.path.join(RES, 'drawable', 'sky_arc.png'))
    for name in ICONS:
        draw_icon(name).save(os.path.join(RES, 'drawable', f'wx_{name}.png'))
    print('ok ->', SRC)


if __name__ == '__main__':
    main()
