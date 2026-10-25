"""The "Datasheet" look of the figures in this repository: a white sheet in a thin ink frame, IBM Plex type (fonts in ./fonts,
SIL Open Font License), figures in Plex Mono, one cobalt accent, a title block bottom right and a dated source line bottom left.
Used by make_charts.py and make_charts_mac.py. Formats (pixels): substack 3200x1800 (16:9 at 2x)."""
from datetime import date
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np

HERE = Path(__file__).resolve().parent
for _f in (HERE / "fonts").glob("*.ttf"):
    fm.fontManager.addfont(str(_f))

SANS, COND, MONO = "IBM Plex Sans", "IBM Plex Sans Condensed", "IBM Plex Mono"
INK, MUTED, GRID, PAPER = "#111418", "#5B6470", "#E6E8EB", "#FFFFFF"
ACCENT, BEFORE, WARN = "#2440D6", "#C9CED6", "#B3261E"  # cobalt = now or the point; grey = before; red only for losses
SIZES = {"x": (16, 9), "substack": (16, 9), "linkedin": (10.8, 13.5), "youtube": (10.8, 10.8)}


def money(v):
    return f"${v:g}" if float(v).is_integer() else f"${v:.2f}"


class Sheet:
    """One branded image. Draw into `sheet.body` (a figure-fraction rect [x, y, w, h])."""

    def __init__(self, channel, title, subtitle, sources, day=None):
        self.channel = channel
        w, h = SIZES[channel]
        self.fig = plt.figure(figsize=(w, h), dpi=100, facecolor=PAPER)
        self.u = w / 16 if h <= w else w / 12          # type scale unit: 1.0 at 16:9
        self.portrait = h > w
        self.day = day or date.today()
        u, fig = self.u, self.fig
        m = .025  # frame margin, same visual width on every format
        mx, my = (m, m * w / h) if h > w else (m * h / w, m)
        fig.add_artist(plt.Rectangle((mx, my), 1 - 2 * mx, 1 - 2 * my, fill=False, ec=INK, lw=1.2, transform=fig.transFigure))
        self.mx, self.my = mx, my
        wide = channel in ("x", "substack")
        wrap = 40 if self.portrait else (44 if channel == "youtube" else 60)
        tsize = 31 * u * (1 if wide else 1.3)
        step = tsize * 1.18 / 72 / h
        y = .9 if wide else .93
        for line in textwrap.wrap(title, wrap):
            fig.text(.06, y, line, font=COND, fontsize=tsize, fontweight="bold", color=INK, va="top")
            y -= step
        fig.text(.06, y - .012, subtitle.upper(), font=MONO, fontsize=12 * u * (1 if wide else 1.35), color=MUTED, va="top")
        self.wide = wide
        self.top = y - (.05 if wide else .04)
        self._title_block()
        self._sources(sources)
        bottom = .27 if self.wide else self.sources_top + .07
        self.body = [.07, bottom, .87, self.top - bottom - .03]

    def _title_block(self):
        fig, u = self.fig, self.u * (1.3 if self.channel != "x" and self.channel != "substack" else 1)
        iso = self.day.isocalendar()
        cells = (("JULIEN SIMON", "@julsimon"), (f"SHEET {iso[0]}-{iso[1]:02d}", self.day.strftime("%d %b %Y").upper()), ("AI REALIST", "airealist.ai"))
        w = .36 if self.wide else .6
        h = .085 if self.wide else (.055 if self.portrait else .07)
        x0, y0 = 1 - self.mx - .015 - w, self.my + .018
        fig.add_artist(plt.Rectangle((x0, y0), w, h, fill=False, ec=INK, lw=1.2, transform=fig.transFigure))
        widths = (.37, .33, .30)
        x = x0
        for i, ((top, bot), cw) in enumerate(zip(cells, widths)):
            if i:
                fig.add_artist(plt.Line2D([x, x], [y0, y0 + h], color=INK, lw=.8, transform=fig.transFigure))
            fig.text(x + .008, y0 + h * .6, top, font=MONO, fontsize=11.5 * u, fontweight="semibold", color=INK)
            fig.text(x + .008, y0 + h * .2, bot, font=MONO, fontsize=10.5 * u, color=MUTED)
            x += w * cw
        self.block_left = x0
        self.block_top = y0 + h

    def _sources(self, sources):
        fig = self.fig
        if self.wide:  # bottom left, beside the title block
            u, width_chars, y, gap = self.u, int((self.block_left - .08) * 150 / self.u), self.my + .03, .022
        else:          # full width, just above the title block
            u = self.u * 1.25
            width_chars, y, gap = int(.88 * 95 / u), self.block_top + .015, .018
        lines = textwrap.wrap("Sources: " + sources, max(30, width_chars))[:4]
        for line in reversed(lines):
            fig.text(.06, y, line, font=MONO, fontsize=9.5 * u, color=MUTED)
            y += gap
        self.sources_top = y

    def save(self, path):
        self.fig.savefig(path, facecolor=PAPER, dpi=200 if self.channel == "substack" else 100)  # Substack posts at 2x
        plt.close(self.fig)
        return path

    # ---------- chart types ----------
    def _axes(self, rect):
        ax = self.fig.add_axes(rect)
        ax.set_facecolor(PAPER)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(INK)
        ax.tick_params(left=False, labelleft=False, bottom=False, pad=8)
        return ax

    def before_after(self, panels, before_label, after_label):
        """Grouped bars, one panel per like-for-like comparison.
        panels: [{head, items: [(label, before, after)], fmt}] ; before/after = grey/cobalt."""
        x0, y0, w, h = self.body
        n = len(panels)
        rects = ([[x0 + i * w / n + .01, y0, w / n - .05, h - .04] for i in range(n)] if not self.portrait
                 else [[x0 + .01, y0 + (n - 1 - i) * h / n + .055, w - .02, h / n - .115] for i in range(n)])
        u = self.u * (1 if self.wide else 1.35)
        for p, r in zip(panels, rects):
            ax = self._axes(r)
            fmt = p.get("fmt", money)
            labels, old, new = zip(*p["items"])
            ymax = max(max(old), max(new)) * 1.32
            xs = np.arange(len(labels)); bw = .36
            ax.bar(xs - bw / 2, old, bw, color=BEFORE, zorder=3)
            ax.bar(xs + bw / 2, new, bw, color=ACCENT, zorder=3)
            ax.yaxis.grid(True, color=GRID, lw=.8, zorder=0); ax.set_yticks(np.linspace(0, ymax, 6)[1:-1])
            for xi, o, nv in zip(xs, old, new):
                ax.text(xi - bw / 2, o + ymax * .02, fmt(o), ha="center", va="bottom", color=MUTED, font=MONO, fontsize=14 * u)
                ax.text(xi + bw / 2, nv + ymax * .02, fmt(nv), ha="center", va="bottom", color=INK, font=MONO, fontsize=16 * u, fontweight="semibold")
                ax.text(xi, max(o, nv) + ymax * .12, f"{(nv - o) / o:+.0%}", ha="center", color=ACCENT, font=MONO, fontsize=15 * u, fontweight="bold")
            ax.set_xticks(xs, labels, font=SANS, fontsize=12.5 * u, color=INK)
            ax.set_ylim(0, ymax)
            ax.set_title(p["head"].upper() + f"  ·  {before_label} vs {after_label}".upper(), loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=12)

    def ranking(self, items, fmt=money, highlight=None, head=""):
        """Horizontal bars, sorted as given (top first). highlight: {label: color}."""
        x0, y0, w, h = self.body
        gutter = .15 if self.wide else .27  # room for the row labels, inside the frame
        ax = self._axes([x0 + gutter, y0, w - gutter, h])
        ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK)
        labels, vals = zip(*items)
        u = self.u * (1.35 if self.channel != "x" and self.channel != "substack" else 1)
        ys = np.arange(len(labels))[::-1]
        colors = [(highlight or {}).get(l, "#9AA3AE") for l in labels]
        ax.barh(ys, vals, color=colors, height=.62, zorder=3)
        ax.xaxis.grid(True, color=GRID, lw=.8, zorder=0)
        for y, v in zip(ys, vals):
            ax.text(v + max(vals) * .015, y, fmt(v), va="center", font=MONO, fontsize=16 * u, fontweight="semibold", color=INK)
        ax.set_yticks(ys, labels, font=SANS, fontsize=15 * u, color=INK); ax.tick_params(left=False, labelleft=True, bottom=False, labelbottom=False)
        ax.set_xlim(0, max(vals) * 1.18)
        if head:
            ax.set_title(head.upper(), loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=12)

    def table(self, header, rows, emphasis_col=None):
        """A datasheet table: mono figures, hairline rules. emphasis_col is drawn in cobalt."""
        x0, y0, w, h = self.body
        fig = self.fig
        u = self.u * (1.3 if self.channel != "x" and self.channel != "substack" else 1)
        ncol = len(header); colw = w / ncol
        rowh = min(h / (len(rows) + 1), .09 if not self.portrait else .06)
        y = y0 + h - rowh * .6
        for c, t in enumerate(header):
            fig.text(x0 + c * colw, y, t.upper(), font=MONO, fontsize=11 * u, color=MUTED)
        for r in rows:
            y -= rowh
            fig.add_artist(plt.Line2D([x0, x0 + w], [y + rowh * .62, y + rowh * .62], color=GRID, lw=1, transform=fig.transFigure))
            for c, t in enumerate(r):
                fig.text(x0 + c * colw, y, str(t), font=MONO if c else COND, fontsize=(15 if c else 18) * u,
                         fontweight="bold" if c == 0 else ("semibold" if c == emphasis_col else "regular"),
                         color=ACCENT if c == emphasis_col else INK)

    def screenshot(self, png_path, caption=""):
        """A screenshot inside a hairline frame, with an optional mono caption."""
        img = plt.imread(str(png_path))
        x0, y0, w, h = self.body
        if self.wide:  # a screenshot is the whole message: use the height down to the title block
            y0 = self.block_top + .03
            h = self.top - .03 - y0
        ih, iw = img.shape[:2]
        fw, fh = self.fig.get_size_inches()
        box_ratio = (w * fw) / (h * fh); img_ratio = iw / ih
        if img_ratio > box_ratio:
            nw, nh = w, w * fw / img_ratio / fh
        else:
            nh, nw = h, h * fh * img_ratio / fw
        ax = self.fig.add_axes([x0 + (w - nw) / 2, y0 + (h - nh), nw, nh])
        ax.imshow(img); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(INK); s.set_linewidth(1)
        if caption:
            self.fig.text(x0 + (w - nw) / 2, y0 + (h - nh) - .03, caption.upper(), font=MONO, fontsize=11 * self.u, color=MUTED, va="top")
