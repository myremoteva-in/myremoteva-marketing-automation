"""Original flat cartoon generator (Pillow). Same style as the cartoons we drew earlier: black outlines,
a tired office worker, a speech bubble, a small scene on the laptop. Nothing is copied from anyone else's artwork.

Usage: from cartoon import make_cartoon; make_cartoon("out.png", "Speech text", "inbox", "sweater1")
"""
import os
from PIL import Image, ImageDraw, ImageFont

W = H = 1080
S = 2  # supersampling factor for smooth edges
INK = "#111111"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size * S)
    try:  # Pillow 10.1+ ships a scalable built-in font
        return ImageFont.load_default(size=size * S)
    except TypeError:
        return ImageFont.load_default()


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W * S, H * S), "#E8E6E1")
        self.d = ImageDraw.Draw(self.img)

    def _s(self, *v):
        return [x * S for x in v]

    def ell(self, x, y, w, h, fill, width=6):
        self.d.ellipse(self._s(x, y, x + w, y + h), fill=fill, outline=INK, width=width * S)

    def rect(self, x, y, w, h, fill, width=6):
        self.d.rectangle(self._s(x, y, x + w, y + h), fill=fill, outline=INK, width=width * S)

    def rrect(self, x, y, w, h, r, fill, width=6):
        self.d.rounded_rectangle(self._s(x, y, x + w, y + h), radius=r * S, fill=fill, outline=INK, width=width * S)

    def poly(self, pts, fill, width=6):
        p = [(a * S, b * S) for a, b in pts]
        self.d.polygon(p, fill=fill)
        self.d.line(p + [p[0]], fill=INK, width=width * S, joint="curve")

    def line(self, x1, y1, x2, y2, width=4, color=INK):
        self.d.line(self._s(x1, y1, x2, y2), fill=color, width=width * S)

    def thick(self, x1, y1, x2, y2, width, color="#1B1B1B"):
        self.d.line(self._s(x1, y1, x2, y2), fill=color, width=width * S)
        r = width / 2
        for (x, y) in ((x1, y1), (x2, y2)):
            self.d.ellipse(self._s(x - r, y - r, x + r, y + r), fill=color)

    def text(self, x, y, s, size, fill=INK, anchor="la"):
        self.d.text((x * S, y * S), s, font=font(size), fill=fill, anchor=anchor)

    def wrapped(self, box, s, size, fill=INK):
        x0, y0, x1, y1 = box
        f = font(size)
        words, lines, cur = s.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if self.d.textlength(t, font=f) <= (x1 - x0) * S:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        lh = size * 1.25 * S
        total = lh * len(lines)
        y = (y0 + y1) * S / 2 - total / 2
        for ln in lines:
            tw = self.d.textlength(ln, font=f)
            self.d.text(((x0 + x1) * S / 2 - tw / 2, y), ln, font=f, fill=fill)
            y += lh

    def save(self, path):
        self.img.resize((W, H), Image.LANCZOS).save(path, "PNG", optimize=True)


STYLES = {
    "sweater1": {"body": "#1B1B1B", "skin": "#F6F1E6", "glasses": True},
    "sweater2": {"body": "#2F4B6E", "skin": "#F1DCC4", "glasses": False},
    "sweater3": {"body": "#6B3E3E", "skin": "#E9CBA7", "glasses": True},
    "sweater4": {"body": "#3F5F4A", "skin": "#F6F1E6", "glasses": False},
}


def make_cartoon(path, speech, scene="inbox", style="sweater1", brand="myremoteva.com"):
    st = STYLES.get(style, STYLES["sweater1"])
    c = Canvas()
    skin, body = st["skin"], st["body"]
    c.d.rectangle([0, 700 * S, W * S, H * S], fill="#D9D6CF")
    c.line(0, 700, W, 700)
    # window and plant
    c.rrect(800, 470, 200, 190, 8, "#F4F3EF", 5)
    c.line(900, 470, 900, 660)
    c.line(800, 565, 1000, 565)
    c.rect(60, 640, 90, 90, "#A67C52")
    c.ell(40, 540, 70, 120, "#7FA37C")
    c.ell(95, 520, 70, 140, "#6F946C")
    c.ell(70, 500, 60, 130, "#86AD82")
    # speech bubble
    c.rrect(50, 40, 980, 330, 70, "#FFFFFF", 6)
    c.d.polygon([(330 * S, 364 * S), (460 * S, 364 * S), (410 * S, 470 * S)], fill="#FFFFFF")
    c.line(330, 367, 410, 470, 6)
    c.line(460, 367, 410, 470, 6)
    c.d.rectangle([336 * S, 360 * S, 456 * S, 372 * S], fill="#FFFFFF")
    size = 46 if len(speech) <= 70 else 40 if len(speech) <= 110 else 34
    c.wrapped((80, 55, 1000, 355), speech, size)
    # desk
    c.rect(0, 880, W, 200, "#BEB7AB")
    # body, neck, head, ears
    c.ell(190, 640, 440, 420, body)
    c.rect(360, 560, 90, 110, "#EDE6D6")
    c.ell(290, 450, 240, 250, skin)
    c.ell(262, 545, 44, 70, skin)
    c.ell(514, 545, 44, 70, skin)
    c.line(390, 455, 380, 425)
    c.line(410, 452, 410, 420)
    c.line(430, 455, 440, 426)
    # face
    if st["glasses"]:
        c.ell(320, 535, 80, 72, "#FFFFFF")
        c.ell(420, 535, 80, 72, "#FFFFFF")
        c.line(400, 568, 420, 568, 6)
    c.d.ellipse([352 * S, 562 * S, 366 * S, 576 * S], fill=INK)
    c.d.ellipse([452 * S, 562 * S, 466 * S, 576 * S], fill=INK)
    c.line(322, 520, 392, 505, 6)
    c.line(428, 505, 498, 522, 6)
    c.ell(395, 590, 50, 55, "#EBD9C1")
    c.d.ellipse([390 * S, 650 * S, 448 * S, 684 * S], fill="#2A1B1B", outline=INK, width=4 * S)
    # arms
    c.thick(250, 820, 280, 600, 46)
    c.ell(255, 480, 90, 90, skin)
    c.thick(560, 840, 520, 760, 46)
    c.rrect(470, 690, 90, 150, 18, "#3A3A3A", 5)
    c.d.rectangle([482 * S, 706 * S, 548 * S, 816 * S], fill="#CFE3F0")
    # mug
    c.rect(70, 800, 100, 100, "#9A7352")
    c.d.arc([150 * S, 825 * S, 200 * S, 875 * S], -90, 90, fill=INK, width=6 * S)
    # laptop
    c.poly([(650, 640), (1000, 640), (1030, 860), (620, 860)], "#3C3F44")
    c.poly([(672, 662), (978, 662), (1004, 840), (646, 840)], "#F2F4F7")
    c.poly([(590, 860), (1060, 860), (1085, 905), (565, 905)], "#6A6E75")
    # laptop scene
    if scene == "robot":
        c.rect(700, 700, 56, 56, "#FFFFFF")
        c.text(770, 712, "I'm not a robot", 22)
    elif scene == "inbox":
        for y in (690, 732, 774):
            c.rect(700, y, 250, 36, "#FFFFFF")
        c.text(702, 650, "Inbox (1,284)", 22, "#B00020")
    elif scene == "sheet":
        for r in range(4):
            for col in range(3):
                c.rect(700 + col * 88, 690 + r * 36, 88, 36, "#FFFFFF")
    elif scene == "calendar":
        for r in range(4):
            for col in range(5):
                c.rect(700 + col * 52, 700 + r * 34, 52, 34, "#FFFFFF")
        c.d.rectangle([(700 + 4 * 52 + 2) * S, (702 + 3 * 34) * S, (700 + 4 * 52 + 50) * S, (702 + 3 * 34 + 30) * S], fill="#F4A4A4")
    elif scene == "mail":
        c.rect(710, 700, 220, 130, "#FFFFFF")
        c.line(710, 700, 820, 770)
        c.line(930, 700, 820, 770)
    elif scene == "invoice":
        c.rect(720, 680, 200, 150, "#FFFFFF")
        for i in range(4):
            c.line(735, 705 + i * 28, 905, 705 + i * 28, 3)
        c.text(740, 806, "Unpaid", 20, "#B00020")
    elif scene == "chart":
        for i, h in enumerate((40, 70, 55, 100, 85)):
            c.rect(710 + i * 50, 830 - h, 34, h, "#8FB3D9", 4)
    elif scene == "clock":
        c.ell(760, 690, 130, 130, "#FFFFFF")
        c.line(825, 755, 825, 710, 5)
        c.line(825, 755, 860, 770, 5)
    # notepad and pen
    c.poly([(240, 940), (440, 940), (420, 1010), (220, 1010)], "#FFFFFF")
    c.line(250, 960, 425, 960)
    c.line(245, 980, 410, 980)
    c.line(470, 1000, 620, 975, 12, "#4A5057")
    # brand strip
    c.d.rectangle([0, 1030 * S, W * S, H * S], fill=INK)
    c.text(W / 2, 1055, brand + "  |  managed virtual assistants", 22, "#FFFFFF", anchor="mm")
    c.save(path)
    return path


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "test-cartoon.png"
    make_cartoon(out, "It is not a spreadsheet problem. It is a who-does-the-spreadsheet problem.", "sheet", "sweater2")
    print("wrote", out)
