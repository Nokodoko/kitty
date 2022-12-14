#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

#
# NOTE: to add a new glyph, add an entry to the `box_chars` dict, then update
# the functions `font_for_cell` and `box_glyph_id` in `kitty/fonts.c`.
#

import math
from functools import partial as p, wraps
from itertools import repeat
from typing import (
    Any, Callable, Dict, Generator, Iterable, List, MutableSequence, Optional,
    Sequence, Tuple, cast
)

scale = (0.001, 1., 1.5, 2.)
_dpi = 96.0
BufType = MutableSequence[int]


def set_scale(new_scale: Sequence[float]) -> None:
    global scale
    scale = (new_scale[0], new_scale[1], new_scale[2], new_scale[3])


def thickness(level: int = 1, horizontal: bool = True) -> int:
    pts = scale[level]
    return int(math.ceil(pts * (_dpi / 72.0)))


def draw_hline(buf: BufType, width: int, x1: int, x2: int, y: int, level: int) -> None:
    ' Draw a horizontal line between [x1, x2) centered at y with the thickness given by level '
    sz = thickness(level=level, horizontal=False)
    start = y - sz // 2
    for y in range(start, start + sz):
        offset = y * width
        for x in range(x1, x2):
            buf[offset + x] = 255


def draw_vline(buf: BufType, width: int, y1: int, y2: int, x: int, level: int) -> None:
    ' Draw a vertical line between [y1, y2) centered at x with the thickness given by level '
    sz = thickness(level=level, horizontal=True)
    start = x - sz // 2
    for x in range(start, start + sz):
        for y in range(y1, y2):
            buf[x + y * width] = 255


def half_hline(buf: BufType, width: int, height: int, level: int = 1, which: str = 'left', extend_by: int = 0) -> None:
    x1, x2 = (0, extend_by + width // 2) if which == 'left' else (width // 2 - extend_by, width)
    draw_hline(buf, width, x1, x2, height // 2, level)


def half_vline(buf: BufType, width: int, height: int, level: int = 1, which: str = 'top', extend_by: int = 0) -> None:
    y1, y2 = (0, height // 2 + extend_by) if which == 'top' else (height // 2 - extend_by, height)
    draw_vline(buf, width, y1, y2, width // 2, level)


def get_holes(sz: int, hole_sz: int, num: int) -> List[Tuple[int, ...]]:
    if num == 1:
        pts = [sz // 2]
    elif num == 2:
        ssz = (sz - 2 * hole_sz) // 3
        pts = [ssz + hole_sz // 2, 2 * ssz + hole_sz // 2 + hole_sz]
    elif num == 3:
        ssz = (sz - 3 * hole_sz) // 4
        pts = [ssz + hole_sz // 2, 2 * ssz + hole_sz // 2 + hole_sz, 3 * ssz + 2 * hole_sz + hole_sz // 2]
    holes = []
    for c in pts:
        holes.append(tuple(range(c - hole_sz // 2, c - hole_sz // 2 + hole_sz)))
    return holes


hole_factor = 8


def add_hholes(buf: BufType, width: int, height: int, level: int = 1, num: int = 1) -> None:
    line_sz = thickness(level=level, horizontal=True)
    hole_sz = width // hole_factor
    start = height // 2 - line_sz // 2
    holes = get_holes(width, hole_sz, num)
    for y in range(start, start + line_sz):
        offset = y * width
        for hole in holes:
            for x in hole:
                buf[offset + x] = 0


def add_vholes(buf: BufType, width: int, height: int, level: int = 1, num: int = 1) -> None:
    line_sz = thickness(level=level, horizontal=False)
    hole_sz = height // hole_factor
    start = width // 2 - line_sz // 2
    holes = get_holes(height, hole_sz, num)
    for x in range(start, start + line_sz):
        for hole in holes:
            for y in hole:
                buf[x + width * y] = 0


def hline(buf: BufType, width: int, height: int, level: int = 1) -> None:
    half_hline(buf, width, height, level=level)
    half_hline(buf, width, height, level=level, which='right')


def vline(buf: BufType, width: int, height: int, level: int = 1) -> None:
    half_vline(buf, width, height, level=level)
    half_vline(buf, width, height, level=level, which='bottom')


def hholes(buf: BufType, width: int, height: int, level: int = 1, num: int = 1) -> None:
    hline(buf, width, height, level=level)
    add_hholes(buf, width, height, level=level, num=num)


def vholes(buf: BufType, width: int, height: int, level: int = 1, num: int = 1) -> None:
    vline(buf, width, height, level=level)
    add_vholes(buf, width, height, level=level, num=num)


def corner(buf: BufType, width: int, height: int, hlevel: int = 1, vlevel: int = 1, which: Optional[str] = None) -> None:
    wh = 'right' if which is not None and which in '??????' else 'left'
    half_hline(buf, width, height, level=hlevel, which=wh, extend_by=thickness(vlevel, horizontal=True) // 2)
    wv = 'top' if which is not None and which in '??????' else 'bottom'
    half_vline(buf, width, height, level=vlevel, which=wv)


def vert_t(buf: BufType, width: int, height: int, a: int = 1, b: int = 1, c: int = 1, which: Optional[str] = None) -> None:
    half_vline(buf, width, height, level=a, which='top')
    half_hline(buf, width, height, level=b, which='left' if which == '???' else 'right')
    half_vline(buf, width, height, level=c, which='bottom')


def horz_t(buf: BufType, width: int, height: int, a: int = 1, b: int = 1, c: int = 1, which: Optional[str] = None) -> None:
    half_hline(buf, width, height, level=a, which='left')
    half_hline(buf, width, height, level=b, which='right')
    half_vline(buf, width, height, level=c, which='top' if which == '???' else 'bottom')


def cross(buf: BufType, width: int, height: int, a: int = 1, b: int = 1, c: int = 1, d: int = 1) -> None:
    half_hline(buf, width, height, level=a)
    half_hline(buf, width, height, level=b, which='right')
    half_vline(buf, width, height, level=c)
    half_vline(buf, width, height, level=d, which='bottom')


def downsample(src: BufType, dest: BufType, dest_width: int, dest_height: int, factor: int = 4) -> None:
    src_width = 4 * dest_width

    def average_intensity_in_src(dest_x: int, dest_y: int) -> int:
        src_y = dest_y * factor
        src_x = dest_x * factor
        total = 0
        for y in range(src_y, src_y + factor):
            offset = src_width * y
            for x in range(src_x, src_x + factor):
                total += src[offset + x]
        return total // (factor * factor)

    for y in range(dest_height):
        offset = dest_width * y
        for x in range(dest_width):
            dest[offset + x] = min(255, dest[offset + x] + average_intensity_in_src(x, y))


def supersampled(supersample_factor: int = 4) -> Callable:
    # Anti-alias the drawing performed by the wrapped function by
    # using supersampling

    class SSByteArray(bytearray):
        supersample_factor = 1

    def create_wrapper(f: Callable) -> Callable:
        @wraps(f)
        def supersampled_wrapper(buf: BufType, width: int, height: int, *args: Any, **kw: Any) -> None:
            w, h = supersample_factor * width, supersample_factor * height
            ssbuf = SSByteArray(w * h)
            ssbuf.supersample_factor = supersample_factor
            f(ssbuf, w, h, *args, **kw)
            downsample(ssbuf, buf, width, height, factor=supersample_factor)
        return supersampled_wrapper
    return create_wrapper


def fill_region(buf: BufType, width: int, height: int, xlimits: Iterable[Iterable[float]]) -> None:
    for y in range(height):
        offset = y * width
        for x, (upper, lower) in enumerate(xlimits):
            buf[x + offset] = 255 if upper <= y <= lower else 0


def line_equation(x1: int, y1: int, x2: int, y2: int) -> Callable[[int], float]:
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    def y(x: int) -> float:
        return m * x + c

    return y


@supersampled()
def triangle(buf: BufType, width: int, height: int, left: bool = True) -> None:
    ay1, by1, y2 = 0, height - 1, height // 2
    if left:
        x1, x2 = 0, width - 1
    else:
        x1, x2 = width - 1, 0
    uppery = line_equation(x1, ay1, x2, y2)
    lowery = line_equation(x1, by1, x2, y2)
    xlimits = [(uppery(x), lowery(x)) for x in range(width)]
    fill_region(buf, width, height, xlimits)


@supersampled()
def corner_triangle(buf: BufType, width: int, height: int, corner: str) -> None:
    if corner == 'top-right' or corner == 'bottom-left':
        diagonal_y = line_equation(0, 0, width - 1, height - 1)
        if corner == 'top-right':
            xlimits = [(0., diagonal_y(x)) for x in range(width)]
        elif corner == 'bottom-left':
            xlimits = [(diagonal_y(x), height - 1.) for x in range(width)]
    else:
        diagonal_y = line_equation(width - 1, 0, 0, height - 1)
        if corner == 'top-left':
            xlimits = [(0., diagonal_y(x)) for x in range(width)]
        elif corner == 'bottom-right':
            xlimits = [(diagonal_y(x), height - 1.) for x in range(width)]
    fill_region(buf, width, height, xlimits)


def thick_line(buf: BufType, width: int, height: int, thickness_in_pixels: int, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
    if p1[0] > p2[0]:
        p1, p2 = p2, p1
    leq = line_equation(*p1, *p2)
    delta, extra = divmod(thickness_in_pixels, 2)

    for x in range(p1[0], p2[0] + 1):
        if 0 <= x < width:
            y_p = leq(x)
            r = range(int(y_p) - delta, int(y_p) + delta + extra)
            for y in r:
                if 0 <= y < height:
                    buf[x + y * width] = 255


@supersampled()
def cross_line(buf: BufType, width: int, height: int, left: bool = True, level: int = 1) -> None:
    if left:
        p1, p2 = (0, 0), (width - 1, height - 1)
    else:
        p1, p2 = (width - 1, 0), (0, height - 1)
    supersample_factor = getattr(buf, 'supersample_factor')
    thick_line(buf, width, height, supersample_factor * thickness(level), p1, p2)


@supersampled()
def half_cross_line(buf: BufType, width: int, height: int, which: str = 'tl', level: int = 1) -> None:
    supersample_factor = getattr(buf, 'supersample_factor')
    thickness_in_pixels = thickness(level) * supersample_factor
    my = (height - 1) // 2
    if which == 'tl':
        p1 = 0, 0
        p2 = width - 1, my
    elif which == 'bl':
        p2 = 0, height - 1
        p1 = width - 1, my
    elif which == 'tr':
        p1 = width - 1, 0
        p2 = 0, my
    else:
        p2 = width - 1, height - 1
        p1 = 0, my
    thick_line(buf, width, height, thickness_in_pixels, p1, p2)


BezierFunc = Callable[[float], float]


def cubic_bezier(start: Tuple[int, int], end: Tuple[int, int], c1: Tuple[int, int], c2: Tuple[int, int]) -> Tuple[BezierFunc, BezierFunc]:

    def bezier_eq(p0: int, p1: int, p2: int, p3: int) -> BezierFunc:

        def f(t: float) -> float:
            tm1 = 1 - t
            tm1_3 = tm1 * tm1 * tm1
            t_3 = t * t * t
            return tm1_3 * p0 + 3 * t * tm1 * (tm1 * p1 + t * p2) + t_3 * p3
        return f

    bezier_x = bezier_eq(start[0], c1[0], c2[0], end[0])
    bezier_y = bezier_eq(start[1], c1[1], c2[1], end[1])
    return bezier_x, bezier_y


def find_bezier_for_D(width: int, height: int) -> int:
    cx = last_cx = width - 1
    start = (0, 0)
    end = (0, height - 1)
    while True:
        c1 = cx, start[1]
        c2 = cx, end[1]
        bezier_x, bezier_y = cubic_bezier(start, end, c1, c2)
        if bezier_x(0.5) > width - 1:
            return last_cx
        last_cx = cx
        cx += 1


def get_bezier_limits(bezier_x: BezierFunc, bezier_y: BezierFunc) -> Generator[Tuple[float, float], None, int]:
    start_x = int(bezier_x(0))
    max_x = int(bezier_x(0.5))
    last_t, t_limit = 0., 0.5

    def find_t_for_x(x: int, start_t: float) -> float:
        if abs(bezier_x(start_t) - x) < 0.1:
            return start_t
        increment = t_limit - start_t
        if increment <= 0:
            return start_t
        while True:
            q = bezier_x(start_t + increment)
            if (abs(q - x) < 0.1):
                return start_t + increment
            if q > x:
                increment /= 2
                if increment < 1e-6:
                    raise ValueError('Failed to find t for x={}'.format(x))
            else:
                start_t += increment
                increment = t_limit - start_t
                if increment <= 0:
                    return start_t

    for x in range(start_x, max_x + 1):
        if x > start_x:
            last_t = find_t_for_x(x, last_t)
        upper, lower = bezier_y(last_t), bezier_y(1 - last_t)
        if abs(upper - lower) <= 2:  # avoid pip on end of D
            break
        yield upper, lower


@supersampled()
def D(buf: BufType, width: int, height: int, left: bool = True) -> None:
    c1x = find_bezier_for_D(width, height)
    start = (0, 0)
    end = (0, height - 1)
    c1 = c1x, start[1]
    c2 = c1x, end[1]
    bezier_x, bezier_y = cubic_bezier(start, end, c1, c2)
    xlimits = list(get_bezier_limits(bezier_x, bezier_y))
    if left:
        fill_region(buf, width, height, xlimits)
    else:
        mbuf = bytearray(width * height)
        fill_region(mbuf, width, height, xlimits)
        for y in range(height):
            offset = y * width
            for src_x in range(width):
                dest_x = width - 1 - src_x
                buf[offset + dest_x] = mbuf[offset + src_x]


def draw_parametrized_curve(buf: BufType, width: int, height: int, thickness_in_pixels: int, xfunc: BezierFunc, yfunc: BezierFunc) -> None:
    num_samples = height*4
    seen = set()
    delta, extra = divmod(thickness_in_pixels, 2)
    for i in range(num_samples + 1):
        t = (i / num_samples)
        p = x_p, y_p = int(xfunc(t)), int(yfunc(t))
        if p in seen:
            continue
        seen.add(p)
        for y in range(int(y_p) - delta, int(y_p) + delta + extra):
            if 0 <= y < height:
                offset = y * width
                for x in range(int(x_p) - delta, int(x_p) + delta + extra):
                    if 0 <= x < width:
                        pos = offset + x
                        buf[pos] = min(255, buf[pos] + 255)


@supersampled()
def rounded_corner(buf: BufType, width: int, height: int, level: int = 1, which: str = '???') -> None:
    supersample_factor = getattr(buf, 'supersample_factor')
    thickness_in_pixels = thickness(level) * supersample_factor
    if which == '???':
        start = width // 2, height - 1
        end = width - 1, height // 2
        c1 = width // 2, int(0.75 * height)
        c2 = width // 2, height // 2 + 1
    elif which == '???':
        start = 0, height // 2
        end = width // 2, height - 1
        c1 = width // 2, height // 2 + 1
        c2 = width // 2, int(0.75 * height)
    elif which == '???':
        start = width // 2, 0
        end = width - 1, height // 2
        c1 = width // 2, int(0.25 * height)
        c2 = width // 2 - 1, height // 2 - 1
    elif which == '???':
        start = 0, height // 2
        end = width // 2, 0
        c1 = width // 2 - 1, height // 2 - 1
        c2 = width // 2, int(0.25 * height)
    xfunc, yfunc = cubic_bezier(start, end, c1, c2)
    draw_parametrized_curve(buf, width, height, thickness_in_pixels, xfunc, yfunc)


def half_dhline(buf: BufType, width: int, height: int, level: int = 1, which: str = 'left', only: Optional[str] = None) -> Tuple[int, int]:
    x1, x2 = (0, width // 2) if which == 'left' else (width // 2, width)
    gap = thickness(level + 1, horizontal=False)
    if only != 'bottom':
        draw_hline(buf, width, x1, x2, height // 2 - gap, level)
    if only != 'top':
        draw_hline(buf, width, x1, x2, height // 2 + gap, level)
    return height // 2 - gap, height // 2 + gap


def half_dvline(buf: BufType, width: int, height: int, level: int = 1, which: str = 'top', only: Optional[str] = None) -> Tuple[int, int]:
    y1, y2 = (0, height // 2) if which == 'top' else (height // 2, height)
    gap = thickness(level + 1, horizontal=True)
    if only != 'right':
        draw_vline(buf, width, y1, y2, width // 2 - gap, level)
    if only != 'left':
        draw_vline(buf, width, y1, y2, width // 2 + gap, level)
    return width // 2 - gap, width // 2 + gap


def dvline(buf: BufType, width: int, height: int, only: Optional[str] = None, level: int = 1) -> Tuple[int, int]:
    half_dvline(buf, width, height, only=only, level=level)
    return half_dvline(buf, width, height, only=only, which='bottom', level=level)


def dhline(buf: BufType, width: int, height: int, only: Optional[str] = None, level: int = 1) -> Tuple[int, int]:
    half_dhline(buf, width, height, only=only, level=level)
    return half_dhline(buf, width, height, only=only, which='bottom', level=level)


def dvcorner(buf: BufType, width: int, height: int, level: int = 1, which: str = '???') -> None:
    hw = 'right' if which in '??????' else 'left'
    half_dhline(buf, width, height, which=hw)
    vw = 'top' if which in '??????' else 'bottom'
    gap = thickness(level + 1, horizontal=False)
    half_vline(buf, width, height, which=vw, extend_by=gap // 2 + thickness(level, horizontal=False))


def dhcorner(buf: BufType, width: int, height: int, level: int = 1, which: str = '???') -> None:
    vw = 'top' if which in '??????' else 'bottom'
    half_dvline(buf, width, height, which=vw)
    hw = 'right' if which in '??????' else 'left'
    gap = thickness(level + 1, horizontal=True)
    half_hline(buf, width, height, which=hw, extend_by=gap // 2 + thickness(level, horizontal=True))


def dcorner(buf: BufType, width: int, height: int, level: int = 1, which: str = '???') -> None:
    hw = 'right' if which in '??????' else 'left'
    vw = 'top' if which in '??????' else 'bottom'
    hgap = thickness(level + 1, horizontal=False)
    vgap = thickness(level + 1, horizontal=True)
    x1, x2 = (0, width // 2) if hw == 'left' else (width // 2, width)
    ydelta = hgap if vw == 'top' else -hgap
    if hw == 'left':
        x2 += vgap
    else:
        x1 -= vgap
    draw_hline(buf, width, x1, x2, height // 2 + ydelta, level)
    if hw == 'left':
        x2 -= 2 * vgap
    else:
        x1 += 2 * vgap
    draw_hline(buf, width, x1, x2, height // 2 - ydelta, level)
    y1, y2 = (0, height // 2) if vw == 'top' else (height // 2, height)
    xdelta = vgap if hw == 'right' else -vgap
    yd = thickness(level, horizontal=True) // 2
    if vw == 'top':
        y2 += hgap + yd
    else:
        y1 -= hgap + yd
    draw_vline(buf, width, y1, y2, width // 2 - xdelta, level)
    if vw == 'top':
        y2 -= 2 * hgap
    else:
        y1 += 2 * hgap
    draw_vline(buf, width, y1, y2, width // 2 + xdelta, level)


def dpip(buf: BufType, width: int, height: int, level: int = 1, which: str = '???') -> None:
    if which in '??????':
        left, right = dvline(buf, width, height)
        x1, x2 = (0, left) if which == '???' else (right, width)
        draw_hline(buf, width, x1, x2, height // 2, level)
    else:
        top, bottom = dhline(buf, width, height)
        y1, y2 = (0, top) if which == '???' else (bottom, height)
        draw_vline(buf, width, y1, y2, width // 2, level)


def inner_corner(buf: BufType, width: int, height: int, which: str = 'tl', level: int = 1) -> None:
    hgap = thickness(level + 1, horizontal=True)
    vgap = thickness(level + 1, horizontal=False)
    vthick = thickness(level, horizontal=True) // 2
    x1, x2 = (0, width // 2 - hgap + vthick + 1) if 'l' in which else (width // 2 + hgap - vthick, width)
    yd = -1 if 't' in which else 1
    draw_hline(buf, width, x1, x2, height // 2 + (yd * vgap), level)
    y1, y2 = (0, height // 2 - vgap) if 't' in which else (height // 2 + vgap, height)
    xd = -1 if 'l' in which else 1
    draw_vline(buf, width, y1, y2, width // 2 + (xd * hgap), level)


def vblock(buf: BufType, width: int, height: int, frac: float = 1., gravity: str = 'top') -> None:
    num_rows = min(height, round(frac * height))
    start = 0 if gravity == 'top' else height - num_rows
    for r in range(start, start + num_rows):
        off = r * width
        for c in range(off, off + width):
            buf[c] = 255


def hblock(buf: BufType, width: int, height: int, frac: float = 1., gravity: str = 'left') -> None:
    num_cols = min(width, round(frac * width))
    start = 0 if gravity == 'left' else width - num_cols
    for r in range(height):
        off = r * width + start
        for c in range(off, off + num_cols):
            buf[c] = 255


def shade(buf: BufType, width: int, height: int, light: bool = False, invert: bool = False) -> None:
    square_sz = max(1, width // 12)
    number_of_rows = height // square_sz
    number_of_cols = width // square_sz
    nums = tuple(range(square_sz))

    dest = bytearray(width * height) if invert else buf

    for r in range(number_of_rows):
        y = r * square_sz
        is_odd = r % 2 != 0
        if is_odd:
            continue
        fill_even = r % 4 == 0
        for yr in nums:
            y = r * square_sz + yr
            if y >= height:
                break
            off = width * y
            for c in range(number_of_cols):
                if light:
                    fill = (c % 4) == (0 if fill_even else 2)
                else:
                    fill = (c % 2 == 0) == fill_even
                if fill:
                    for xc in nums:
                        x = (c * square_sz) + xc
                        if x >= width:
                            break
                        dest[off + x] = 255
    if invert:
        for y in range(height):
            off = width * y
            for x in range(width):
                q = off + x
                buf[q] = 255 - dest[q]


def quad(buf: BufType, width: int, height: int, x: int = 0, y: int = 0) -> None:
    num_cols = width // 2
    left = x * num_cols
    right = width if x else num_cols
    num_rows = height // 2
    top = y * num_rows
    bottom = height if y else num_rows
    for r in range(top, bottom):
        off = r * width
        for c in range(left, right):
            buf[off + c] = 255


box_chars: Dict[str, List[Callable]] = {
    '???': [hline],
    '???': [p(hline, level=3)],
    '???': [vline],
    '???': [p(vline, level=3)],
    '???': [hholes],
    '???': [p(hholes, level=3)],
    '???': [p(hholes, num=2)],
    '???': [p(hholes, num=2, level=3)],
    '???': [p(hholes, num=3)],
    '???': [p(hholes, num=3, level=3)],
    '???': [vholes],
    '???': [p(vholes, level=3)],
    '???': [p(vholes, num=2)],
    '???': [p(vholes, num=2, level=3)],
    '???': [p(vholes, num=3)],
    '???': [p(vholes, num=3, level=3)],
    '???': [half_hline],
    '???': [half_vline],
    '???': [p(half_hline, which='right')],
    '???': [p(half_vline, which='bottom')],
    '???': [p(half_hline, level=3)],
    '???': [p(half_vline, level=3)],
    '???': [p(half_hline, which='right', level=3)],
    '???': [p(half_vline, which='bottom', level=3)],
    '???': [half_hline, p(half_hline, level=3, which='right')],
    '???': [half_vline, p(half_vline, level=3, which='bottom')],
    '???': [p(half_hline, level=3), p(half_hline, which='right')],
    '???': [p(half_vline, level=3), p(half_vline, which='bottom')],
    '???': [triangle],
    '???': [p(triangle, left=False)],
    '???': [D],
    '???': [p(D, left=False)],
    '???': [p(half_cross_line, which='tl'), p(half_cross_line, which='bl')],
    '???': [p(half_cross_line, which='tr'), p(half_cross_line, which='br')],
    '???': [p(corner_triangle, corner='bottom-left')],
    '???': [p(corner_triangle, corner='bottom-right')],
    '???': [p(corner_triangle, corner='top-left')],
    '???': [p(corner_triangle, corner='top-right')],
    '???': [dhline],
    '???': [dvline],

    '???': [vline, p(half_dhline, which='right')],

    '???': [vline, half_dhline],

    '???': [hline, p(half_dvline, which='bottom')],

    '???': [hline, half_dvline],

    '???': [vline, half_dhline, p(half_dhline, which='right')],

    '???': [hline, half_dvline, p(half_dvline, which='bottom')],

    '???': [p(inner_corner, which=x) for x in 'tl tr bl br'.split()],

    '???': [p(inner_corner, which='tr'), p(inner_corner, which='br'), p(dvline, only='left')],

    '???': [p(inner_corner, which='tl'), p(inner_corner, which='bl'), p(dvline, only='right')],

    '???': [p(inner_corner, which='bl'), p(inner_corner, which='br'), p(dhline, only='top')],

    '???': [p(inner_corner, which='tl'), p(inner_corner, which='tr'), p(dhline, only='bottom')],

    '???': [p(cross_line, left=False)],
    '???': [cross_line],
    '???': [cross_line, p(cross_line, left=False)],
    '???': [p(vblock, frac=1/2)],
    '???': [p(vblock, frac=1/8, gravity='bottom')],
    '???': [p(vblock, frac=1/4, gravity='bottom')],
    '???': [p(vblock, frac=3/8, gravity='bottom')],
    '???': [p(vblock, frac=1/2, gravity='bottom')],
    '???': [p(vblock, frac=5/8, gravity='bottom')],
    '???': [p(vblock, frac=3/4, gravity='bottom')],
    '???': [p(vblock, frac=7/8, gravity='bottom')],
    '???': [p(vblock, frac=1, gravity='bottom')],
    '???': [p(hblock, frac=7/8)],
    '???': [p(hblock, frac=3/4)],
    '???': [p(hblock, frac=5/8)],
    '???': [p(hblock, frac=1/2)],
    '???': [p(hblock, frac=3/8)],
    '???': [p(hblock, frac=1/4)],
    '???': [p(hblock, frac=1/8)],
    '???': [p(hblock, frac=1/2, gravity='right')],
    '???': [p(shade, light=True)],
    '???': [shade],
    '???': [p(shade, invert=True)],
    '???': [p(vblock, frac=1/8)],
    '???': [p(hblock, frac=1/8, gravity='right')],
    '???': [p(quad, y=1)],
    '???': [p(quad, x=1, y=1)],
    '???': [quad],
    '???': [quad, p(quad, y=1), p(quad, x=1, y=1)],
    '???': [quad, p(quad, x=1, y=1)],
    '???': [quad, p(quad, x=1), p(quad, y=1)],
    '???': [quad, p(quad, x=1, y=1), p(quad, x=1)],
    '???': [p(quad, x=1)],
    '???': [p(quad, x=1), p(quad, y=1)],
    '???': [p(quad, x=1), p(quad, y=1), p(quad, x=1, y=1)],
}

t, f = 1, 3
for start in '????????????':
    for i, (hlevel, vlevel) in enumerate(((t, t), (f, t), (t, f), (f, f))):
        box_chars[chr(ord(start) + i)] = [p(corner, which=start, hlevel=hlevel, vlevel=vlevel)]
for ch in '????????????':
    box_chars[ch] = [p(rounded_corner, which=ch)]

for i, (a_, b_, c_, d_) in enumerate((
        (t, t, t, t), (f, t, t, t), (t, f, t, t), (f, f, t, t), (t, t, f, t), (t, t, t, f), (t, t, f, f),
        (f, t, f, t), (t, f, f, t), (f, t, t, f), (t, f, t, f), (f, f, f, t), (f, f, t, f), (f, t, f, f),
        (t, f, f, f), (f, f, f, f)
)):
    box_chars[chr(ord('???') + i)] = [p(cross, a=a_, b=b_, c=c_, d=d_)]

for starts, func, pattern in (
        ('??????', vert_t, ((t, t, t), (t, f, t), (f, t, t), (t, t, f), (f, t, f), (f, f, t), (t, f, f), (f, f, f))),
        ('??????', horz_t, ((t, t, t), (f, t, t), (t, f, t), (f, f, t), (t, t, f), (f, t, f), (t, f, f), (f, f, f))),
):
    for start in starts:
        for i, (a_, b_, c_) in enumerate(pattern):
            box_chars[chr(ord(start) + i)] = [p(func, which=start, a=a_, b=b_, c=c_)]

for chars, func_ in (('????????????', dvcorner), ('????????????', dhcorner), ('????????????', dcorner), ('????????????', dpip)):
    for ch in chars:
        box_chars[ch] = [p(cast(Callable, func_), which=ch)]


def render_box_char(ch: str, buf: BufType, width: int, height: int, dpi: float = 96.0) -> BufType:
    global _dpi
    _dpi = dpi
    for func in box_chars[ch]:
        func(buf, width, height)
    return buf


def render_missing_glyph(buf: BufType, width: int, height: int) -> None:
    hgap = thickness(level=0, horizontal=True) + 1
    vgap = thickness(level=0, horizontal=False) + 1
    draw_hline(buf, width, hgap, width - hgap + 1, vgap, 0)
    draw_hline(buf, width, hgap, width - hgap + 1, height - vgap, 0)
    draw_vline(buf, width, vgap, height - vgap + 1, hgap, 0)
    draw_vline(buf, width, vgap, height - vgap + 1, width - hgap, 0)


def test_char(ch: str, sz: int = 48) -> None:
    # kitty +runpy "from kitty.fonts.box_drawing import test_char; test_char('XXX')"
    from .render import display_bitmap, setup_for_testing
    from kitty.fast_data_types import concat_cells, set_send_sprite_to_gpu
    with setup_for_testing('monospace', sz) as (_, width, height):
        buf = bytearray(width * height)
        try:
            render_box_char(ch, buf, width, height)

            def join_cells(*cells: bytes) -> bytes:
                cells = tuple(bytes(x) for x in cells)
                return concat_cells(width, height, False, cells)

            rgb_data = join_cells(buf)
            display_bitmap(rgb_data, width, height)
            print()
        finally:
            set_send_sprite_to_gpu(None)


def test_drawing(sz: int = 48, family: str = 'monospace') -> None:
    from .render import display_bitmap, setup_for_testing
    from kitty.fast_data_types import concat_cells, set_send_sprite_to_gpu

    with setup_for_testing(family, sz) as (_, width, height):
        space = bytearray(width * height)

        def join_cells(cells: Iterable[bytes]) -> bytes:
            cells = tuple(bytes(x) for x in cells)
            return concat_cells(width, height, False, cells)

        def render_chr(ch: str) -> bytearray:
            if ch in box_chars:
                cell = bytearray(len(space))
                render_box_char(ch, cell, width, height)
                return cell
            return space

        pos = 0x2500
        rows = []
        space_row = join_cells(repeat(space, 32))

        try:
            for r in range(10):
                row = []
                for i in range(16):
                    row.append(render_chr(chr(pos)))
                    row.append(space)
                    pos += 1
                rows.append(join_cells(row))
                rows.append(space_row)
            rgb_data = b''.join(rows)
            width *= 32
            height *= len(rows)
            assert len(rgb_data) == width * height * 4, '{} != {}'.format(len(rgb_data), width * height * 4)
            display_bitmap(rgb_data, width, height)
        finally:
            set_send_sprite_to_gpu(None)
