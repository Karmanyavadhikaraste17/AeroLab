"""Build a faculty-ready, IEEE-style conference manuscript from project evidence."""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont
import math
import random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "deliverables" / "paper" / "AeroLab_IEEE_Conference_Paper.docx"
FIG = ROOT / "deliverables" / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

NAVY = "#14263D"
INK = "#233447"
MUTED = "#627487"
GRID = "#DCE4EA"
TEAL = "#118A8A"
BLUE = "#3976B9"
AMBER = "#D38A1F"
RED = "#C84C4C"
PALE = "#F3F7FA"


def _font(size, bold=False):
    name = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
    return ImageFont.truetype(name, size)


def _label(draw, xy, text, size=24, fill=INK, bold=False, anchor=None):
    draw.text(xy, text, font=_font(size, bold), fill=fill, anchor=anchor)


def _line_chart_frame(draw, box, y_ticks, y_min, y_max, x_ticks, x_min, x_max,
                      y_format, x_format, y_label, x_label):
    x0, y0, x1, y1 = box
    for v in y_ticks:
        yy = y1 - (v-y_min)/(y_max-y_min)*(y1-y0)
        draw.line((x0, yy, x1, yy), fill=GRID, width=2)
        _label(draw, (x0-16, yy), y_format(v), 24, MUTED, anchor="rm")
    for v in x_ticks:
        xx = x0 + (v-x_min)/(x_max-x_min)*(x1-x0)
        draw.line((xx, y0, xx, y1), fill="#EAF0F4", width=1)
        _label(draw, (xx, y1+14), x_format(v), 23, MUTED, anchor="mt")
    draw.rectangle(box, outline="#AAB8C4", width=2)
    _label(draw, ((x0+x1)//2, y1+43), x_label, 25, INK, bold=True, anchor="mt")
    _label(draw, (x0, y0-12), y_label, 24, INK, bold=True, anchor="lb")


def _xy(box, x, y, x_min, x_max, y_min, y_max):
    x0,y0,x1,y1=box
    return (x0+(x-x_min)/(x_max-x_min)*(x1-x0),
            y1-(y-y_min)/(y_max-y_min)*(y1-y0))


def _polyline(draw, points, color, width=5, joint="curve"):
    if len(points) > 1:
        draw.line(points, fill=color, width=width, joint=joint)


def make_python_control_figure():
    """Independent, deterministic Python simulation using exported firmware matrices."""
    path=FIG/"python_discrete_lqr_response.png"
    W,H=1000,700
    im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,84),fill=NAVY)
    _label(d,(35,18),"DISCRETE CONTROL RESPONSE",27,"white",True)
    _label(d,(35,53),"Python reimplementation · ESP32 coefficients · Ts = 50 ms",17,"#D8E3EE")
    A=[[-0.141176217,-0.00125611878],[9.94971689,-0.0405611024]]
    B=[1.14117622,-9.94971689]; K=[-0.422821226,0.00066655456]; nbar=0.577178774
    x=[0.0,0.0]; t=[]; y=[]; u=[]
    for k in range(17):
        tk=k*0.05
        uk=max(0.0,min(1.0,nbar-(K[0]*x[0]+K[1]*x[1])))
        t.append(tk); y.append(x[0]); u.append(uk)
        if k<16:
            x=[A[0][0]*x[0]+A[0][1]*x[1]+B[0]*uk,
               A[1][0]*x[0]+A[1][1]*x[1]+B[1]*uk]
    top=(120,165,960,335); bot=(120,445,960,580)
    _line_chart_frame(d,top,[0,.25,.5,.75,1.0],0,1.08,[0,.2,.4,.6,.8],0,.8,
                      lambda z:f"{z:.2f}",lambda z:f"{z:.1f}","Normalized model state x1","Time (s)")
    _line_chart_frame(d,bot,[0,.25,.5,.75,1.0],0,1.05,[0,.2,.4,.6,.8],0,.8,
                      lambda z:f"{z:.2f}",lambda z:f"{z:.1f}","Saturated command u","Time (s)")
    points=[_xy(top,tt,yy,0,.8,0,1.08) for tt,yy in zip(t,y)]
    _polyline(d,points,TEAL,7)
    d.line((top[0],_xy(top,0,1,0,.8,0,1.08)[1],top[2],_xy(top,0,1,0,.8,0,1.08)[1]),fill=AMBER,width=3)
    for i in range(len(t)-1):
        p0=_xy(bot,t[i],u[i],0,.8,0,1.05); p1=_xy(bot,t[i+1],u[i],0,.8,0,1.05); p2=_xy(bot,t[i+1],u[i+1],0,.8,0,1.05)
        d.line((p0,p1),fill=BLUE,width=6); d.line((p1,p2),fill=BLUE,width=6)
    d.rounded_rectangle((600,100,960,145),radius=10,fill=PALE,outline=GRID,width=2)
    d.line((617,122,655,122),fill=TEAL,width=5); _label(d,(664,122),"Model state",16,INK,anchor="lm")
    d.line((810,122,840,122),fill=AMBER,width=4); _label(d,(849,122),"r=1",16,INK,anchor="lm")
    _label(d,(35,674),"Assumed model · u clipped to [0,1] · not a measured servo angle",16,MUTED)
    im.save(path,dpi=(300,300)); return path


def make_python_monitor_figure():
    """Recreate one configured injected-offset scenario; no live sensor values are used."""
    path=FIG/"python_fault_monitor_simulation.png"
    W,H=1000,610
    im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,84),fill=NAVY)
    _label(d,(35,18),"MODEL-RESIDUAL FAULT MONITOR",27,"white",True)
    _label(d,(35,53),"Python scripted simulation · offset 0.145 at t = 2.50 s",17,"#D8E3EE")
    box=(120,175,960,430); xmin,xmax=0,2.75; ymin,ymax=0,13
    _line_chart_frame(d,box,[0,2,4,6,8,10,12],ymin,ymax,[0,.5,1,1.5,2,2.5],xmin,xmax,
                      lambda z:f"{z:.1f}",lambda z:f"{z:.1f}","Detector statistic / threshold","Time (s)")
    rng=random.Random(7); residual=[]; cusum=[]; s=0.0
    for k in range(56):
        tt=k*0.05; e=rng.gauss(0,.003)+(0.145 if tt>=2.5 else 0.0)
        residual.append((tt,abs(e)/.1))
        s=max(0.0,s+e-.020); cusum.append((tt,s/.060))
    p_res=[_xy(box,x,y,xmin,xmax,ymin,ymax) for x,y in residual]
    p_cus=[_xy(box,x,y,xmin,xmax,ymin,ymax) for x,y in cusum]
    _polyline(d,p_res,RED,5); _polyline(d,p_cus,BLUE,5)
    ythr=_xy(box,0,1,xmin,xmax,ymin,ymax)[1]
    for xx in range(box[0],box[2],24): d.line((xx,ythr,min(xx+12,box[2]),ythr),fill=AMBER,width=3)
    fault_x=_xy(box,2.5,0,xmin,xmax,ymin,ymax)[0]
    for yy in range(box[1],box[3],24): d.line((fault_x,yy,fault_x,min(yy+12,box[3])),fill="#7C5AA6",width=3)
    d.rounded_rectangle((535,100,960,147),radius=9,fill=PALE,outline=GRID,width=2)
    for x,color,label in [(552,RED,"|e|/0.10"),(690,BLUE,"S+/0.06"),(820,AMBER,"limit=1")]:
        d.line((x,123,x+25,123),fill=color,width=4); _label(d,(x+32,123),label,14,INK,anchor="lm")
    _label(d,(35,568),"First 250 ms shown · σ=0.003 · κ=0.020 · simulated crossing, not hardware latency",15,MUTED)
    im.save(path,dpi=(300,300)); return path


def make_python_range_evidence_figure():
    """Plot documented USB bridge-poll summaries; denominator is polls, not acquisitions."""
    path=FIG/"python_live_range_evidence.png"
    W,H=1000,690
    im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,84),fill=NAVY)
    _label(d,(35,18),"DUAL-RANGE TELEMETRY EVIDENCE",27,"white",True)
    _label(d,(35,53),"Read-only bridge observations · 24 Oct 2026 · sampled polls",17,"#D8E3EE")
    box=(130,175,960,410); ymax=100
    for v in [0,20,40,60,80,100]:
        yy=box[3]-v/ymax*(box[3]-box[1]); d.line((box[0],yy,box[2],yy),fill=GRID,width=2)
        _label(d,(box[0]-14,yy),str(v),18,MUTED,anchor="rm")
    d.rectangle(box,outline="#AAB8C4",width=2)
    _label(d,(130,158),"Fresh polls (%)",18,INK,True,anchor="lb")
    series=[("Clear scene\n10 s · n=40",[("US1",100,TEAL),("US2",100,BLUE)]),
            ("Later monitor\n10 s · n=145",[("US1",100,TEAL),("US2",131/145*100,BLUE)]),
            ("Later monitor\n20 s · n=285",[("US2",72/285*100,BLUE)])]
    group_centers=[340,610,860]
    for gi,(label,bars) in enumerate(series):
        cx=group_centers[gi]
        for bi,(name,val,color) in enumerate(bars):
            x=cx+(bi-(len(bars)-1)/2)*66; y=box[3]-val/ymax*(box[3]-box[1])
            d.rounded_rectangle((x-24,y,x+24,box[3]),radius=8,fill=color)
            # Exact observation counts are assigned by group to avoid inferring acquisitions.
            text=("40/40" if gi==0 else ("145/145" if name=="US1" else "131/145") if gi==1 else "72/285")
            _label(d,(x,y-12),f"{val:.1f}%",17,INK,True,anchor="mb")
            _label(d,(x,box[3]+10),name,16,color,True,anchor="mt")
        label_lines=label.split("\n")
        for j,line in enumerate(label_lines): _label(d,(cx,box[3]+43+j*22),line,16,INK,anchor="mt")
    _label(d,(35,515),"US2 freshness declined across separate sessions; latest packet: US1 fresh, US2 no fresh echo.",16,INK,True)
    d.rounded_rectangle((35,548,965,680),radius=10,fill="#FDF4E8",outline="#E8C98F",width=2)
    _label(d,(52,565),"LATEST SNAPSHOT · separate from chart intervals",16,"#714C13",True)
    _label(d,(52,590),"US1 148.83 cm fresh  ·  US2 timeout  ·  RANGE UNKNOWN",16,"#714C13",True)
    _label(d,(52,620),"Polls may repeat acquisitions; distances are not reference-calibrated.",14,"#714C13")
    im.save(path,dpi=(300,300)); return path


def make_dashboard_publication_plate():
    """Pair the real UI capture with a clearly separate, source-backed packet snapshot."""
    path=FIG/"dashboard_publication_plate.png"
    source=ROOT/"results"/"verification"/"dashboard-demo-render.png"
    if not source.exists(): source=FIG/"dashboard_original_capture.png"
    shot=Image.open(source).convert("RGB")
    W,H=2200,1390
    im=Image.new("RGB",(W,H),"#08111B"); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,112),fill=NAVY)
    _label(d,(56,30),"AEROLAB  /  CONTROL & TELEMETRY DASHBOARD",32,"white",True)
    _label(d,(2140,55),"INTERFACE + VERIFIED PACKET SUMMARY",18,"#B9C8D8",anchor="rm")
    # Main native UI screenshot remains unaltered and identifiable.
    sw,sh=1510,850; shot.thumbnail((sw,sh),Image.Resampling.LANCZOS)
    x0,y0=42,160
    d.rounded_rectangle((x0-10,y0-10,x0+sw+10,y0+sh+10),radius=12,fill="#111F2D",outline="#41566D",width=2)
    im.paste(shot,(x0,y0))
    _label(d,(x0,y0+sh+34),"PROJECT DASHBOARD CAPTURE",19,"#C9D6E2",True)
    _label(d,(x0,y0+sh+62),"This archived render shows NO LINK / AWAITING TELEMETRY.",17,"#AAB8C6")
    # Separate evidence card: values and status copied from the latest dated record.
    cx,cy,cw=1590,160,560
    d.rounded_rectangle((cx,cy,cx+cw,cy+950),radius=18,fill="#0E1B28",outline="#41566D",width=2)
    d.rounded_rectangle((cx,cy,cx+cw,cy+95),radius=18,fill="#162B40")
    _label(d,(cx+28,cy+27),"LATEST RECORDED LIVE SNAPSHOT",20,"white",True)
    _label(d,(cx+28,cy+61),"24 OCT 2026  ·  USB / COM14",17,"#B9C8D8")
    rows=[("PACKET SOURCE","ESP32_FIRMWARE","#7BE0B0"),
          ("BRIDGE LINK","connected · receive age ~0.01 s","#7BE0B0"),
          ("MODE / SERVO","0 · 90° commanded","#8DC8FF"),
          ("US1 FIXED","FRESH · 148.83 cm","#7BE0B0"),
          ("US2 SERVO","NO FRESH ECHO · 0 μs","#F0B56A"),
          ("FIRMWARE STATUS","RANGE UNKNOWN","#F0B56A")]
    yy=cy+125
    for title,value,color in rows:
        d.line((cx+26,yy+76,cx+cw-26,yy+76),fill="#2A3A4A",width=2)
        _label(d,(cx+28,yy),title,16,"#91A5B8",True)
        _label(d,(cx+28,yy+39),value,19,color,True)
        yy+=122
    d.rounded_rectangle((cx+22,cy+868,cx+cw-22,cy+928),radius=10,fill="#17283A")
    _label(d,(cx+40,cy+888),"Separate record snapshot—not simultaneous with UI capture.",15,"#C9D6E2")
    _label(d,(42,1325),"UI screenshot and telemetry snapshot are different evidence objects. No unavailable sensor values are filled or fabricated.",18,"#B9C8D8")
    im.save(path,dpi=(300,300)); return path


def set_font(run, name="Times New Roman", size=9, bold=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def shade(cell, color):
    pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    pr.append(shd)


def border_table(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "8B969D")
        borders.append(el)
    tbl_pr.append(borders)


def set_columns(section, count=2, space="360"):
    cols = section._sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        section._sectPr.append(cols)
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), space)


def add_page_field(paragraph):
    r = paragraph.add_run()
    begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t"); txt.text = "1"
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, txt, end):
        r._r.append(el)
    set_font(r, size=8)


def make_architecture():
    path = FIG / "ieee_architecture.png"
    W, H = 1800, 900
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    regular = r"C:\Windows\Fonts\arial.ttf"
    bold = r"C:\Windows\Fonts\arialbd.ttf"
    f_title = ImageFont.truetype(bold, 42)
    f_head = ImageFont.truetype(bold, 27)
    f_body = ImageFont.truetype(regular, 24)
    d.text((W//2, 55), "AeroLab system architecture and signal provenance", font=f_title,
           fill="#152b3b", anchor="mm")
    boxes = [
        (75, 175, 520, 485, "PHYSICAL RIG", ["US1 fixed + US2 servo-mounted", "IMU, DHT, MQ-135 / MQ-2", "LDR (raw ADC), servo, LEDs, buzzer"]),
        (675, 175, 1120, 485, "ESP32 FIRMWARE", ["50 ms scheduled control tick", "range freshness + alarm logic", "model states and JSON telemetry"]),
        (1275, 175, 1720, 485, "LIVE INTERFACES", ["Browser dashboards", "Python / MATLAB scopes", "USB bridge or ESP32 network"]),
        (375, 600, 820, 815, "MATLAB DESIGN", ["assumed plant; ZOH model", "LQR / observer coefficients", "simulation figures" ]),
        (980, 600, 1425, 815, "SYNTHETIC TESTS", ["injected offset and noise", "demo-mode traces", "not physical HIL evidence"]),
    ]
    for x1,y1,x2,y2,head,lines in boxes:
        d.rounded_rectangle((x1,y1,x2,y2), radius=20, fill="#f3f7fa", outline="#26759a", width=4)
        d.rounded_rectangle((x1,y1,x2,y1+68), radius=18, fill="#155d83")
        d.text(((x1+x2)//2,y1+34),head,font=f_head,fill="white",anchor="mm")
        yy=y1+125
        for line in lines:
            d.text(((x1+x2)//2,yy),line,font=f_body,fill="#243746",anchor="mm")
            yy+=55
    def arrow(a,b,label, color="#4c6474"):
        x1,y1=a; x2,y2=b
        d.line((x1,y1,x2,y2),fill=color,width=7)
        ang=math.atan2(y2-y1,x2-x1)
        p1=(x2-22*math.cos(ang-.55),y2-22*math.sin(ang-.55))
        p2=(x2-22*math.cos(ang+.55),y2-22*math.sin(ang+.55))
        d.polygon(( (x2,y2),p1,p2),fill=color)
        d.text(((x1+x2)//2,(y1+y2)//2-22),label,font=f_body,fill=color,anchor="mm")
    arrow((525,330),(665,330),"sensor I/O")
    arrow((1125,330),(1265,330),"live packets")
    arrow((595,600),(795,490),"generated gains")
    arrow((1000,600),(1040,490),"simulation only")
    d.text((W//2,865),"Solid upper path: physical acquisition and telemetry   |   Lower path: model design and synthetic evaluation",
           font=ImageFont.truetype(regular,22),fill="#475a68",anchor="mm")
    im.save(path, dpi=(300,300))
    return path


def make_range_flow():
    path=FIG/"ieee_range_alarm_flow.png"
    W,H=1800,620
    im=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(im)
    reg=ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf",24)
    bold=ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf",27)
    d.text((W//2,45),"Freshness-aware ultrasonic alarm pipeline",font=bold,fill="#152b3b",anchor="mm")
    boxes=[
        (35,"ACQUIRE",["TRIG / ECHO pulse","12 ms timeout"]),
        (390,"VALIDATE",["2–200 cm window","diagnostic + age"]),
        (745,"FILTER",["EMA: 0.65 new","+ 0.35 previous"]),
        (1100,"CONFIRM",["fresh ≤300 ms","2 distinct samples"]),
        (1455,"INDICATE",["<14 cm: red","14–28 cm: yellow","clear + fresh: green"]),
    ]
    for x,head,lines in boxes:
        d.rounded_rectangle((x,155,x+310,440),radius=18,fill="#f1f6f8",outline="#236f91",width=4)
        d.rounded_rectangle((x,155,x+310,220),radius=16,fill="#155d83")
        d.text((x+155,188),head,font=bold,fill="white",anchor="mm")
        y=270
        for line in lines:
            d.text((x+155,y),line,font=reg,fill="#243746",anchor="mm"); y+=48
    for x in [350,705,1060,1415]:
        d.line((x,297,x+33,297),fill="#4c6474",width=6)
        d.polygon(((x+33,297),(x+16,285),(x+16,309)),fill="#4c6474")
    d.text((W//2,525),"If either channel is stale, state is RANGE UNKNOWN; stale data are not treated as a clear path.",font=reg,fill="#475a68",anchor="mm")
    im.save(path,dpi=(300,300))
    return path


def setup_styles(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin = Inches(.62); sec.bottom_margin = Inches(.62)
    sec.left_margin = Inches(.68); sec.right_margin = Inches(.68)
    sec.header_distance = Inches(.28); sec.footer_distance = Inches(.28)
    set_columns(sec, 1)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"; normal.font.size = Pt(10)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.0
    for name in ("Header", "Footer"):
        st=styles[name]; st.font.name="Times New Roman"; st.font.size=Pt(8)
    footer=sec.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(footer)
    doc.core_properties.title = "AeroLab: An ESP32-Based Embedded Control and Sensor Telemetry Demonstrator"
    doc.core_properties.author = "Manav Sharma"
    doc.core_properties.subject = "IEEE-style technical paper on an educational embedded control demonstrator"
    doc.core_properties.keywords = "ESP32, embedded control, LQR, telemetry, ultrasonic sensing, residual monitoring"


def para(doc, text, first=True, align=None, after=3, keep=False, italic=False, size=10):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(after)
    p.paragraph_format.line_spacing=1.0
    p.paragraph_format.widow_control=True
    if first: p.paragraph_format.first_line_indent=Inches(.16)
    if align is not None: p.alignment=align
    if keep: p.paragraph_format.keep_with_next=True
    r=p.add_run(text); set_font(r,size=size,italic=italic)
    return p


def heading(doc, text, level=1):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER if level==1 else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before=Pt(6 if level==1 else 4)
    p.paragraph_format.space_after=Pt(3)
    p.paragraph_format.keep_with_next=True
    r=p.add_run(text.upper()); set_font(r,size=10,bold=True)
    return p


def equation(doc, text):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.keep_together=True
    r=p.add_run(text); set_font(r,size=9.5,italic=True)
    return p


def figure(doc, path, caption, width=3.15):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(0)
    p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(path),width=Inches(width))
    c=doc.add_paragraph()
    c.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    c.paragraph_format.space_after=Pt(4); c.paragraph_format.keep_together=True
    r=c.add_run(caption); set_font(r,size=8)
    return c


def table(doc, caption, headers, rows, widths=None):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(4); p.paragraph_format.space_after=Pt(2); p.paragraph_format.keep_with_next=True
    r=p.add_run(caption); set_font(r,size=8,bold=True)
    t=doc.add_table(rows=1, cols=len(headers))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    border_table(t)
    for i,txt in enumerate(headers):
        cell=t.rows[0].cells[i]; cell.text=txt; shade(cell,"DCEAF2"); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if widths: cell.width=Inches(widths[i])
        for pp in cell.paragraphs:
            pp.paragraph_format.space_after=Pt(1)
            for rr in pp.runs: set_font(rr,size=7.8,bold=True)
    for row in rows:
        cells=t.add_row().cells
        for i,txt in enumerate(row):
            cells[i].text=txt; cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths: cells[i].width=Inches(widths[i])
            for pp in cells[i].paragraphs:
                pp.paragraph_format.space_after=Pt(1); pp.paragraph_format.line_spacing=1.0
                for rr in pp.runs: set_font(rr,size=7.8)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    return t


def build():
    make_architecture()
    make_range_flow()
    make_python_control_figure()
    make_python_monitor_figure()
    make_python_range_evidence_figure()
    make_dashboard_publication_plate()
    needed=[FIG/"ieee_discrete_step_response.png", ROOT/"results"/"figures"/"matlab_digital_twin_residual_araujo2025.png", FIG/"dashboard_publication_plate.png"]
    for x in needed:
        if not x.is_file(): raise FileNotFoundError(x)
    doc=Document()
    setup_styles(doc)

    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(9); p.paragraph_format.space_after=Pt(5); p.paragraph_format.keep_with_next=True
    r=p.add_run("AeroLab: An ESP32-Based Embedded Control and Sensor Telemetry Demonstrator"); set_font(r,size=21,bold=True)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(2); p.paragraph_format.keep_with_next=True
    r=p.add_run("Manav Sharma"); set_font(r,size=12,bold=True)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(2); p.paragraph_format.keep_with_next=True
    r=p.add_run("School of Electronics Engineering, Vellore Institute of Technology, Vellore, India"); set_font(r,size=9)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(7); p.paragraph_format.keep_with_next=True
    r=p.add_run("Corresponding author: Manav Sharma"); set_font(r,size=8,italic=True)
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(3); p.paragraph_format.line_spacing=1.0
    r=p.add_run("Abstract— "); set_font(r,size=9,bold=True)
    r=p.add_run("This paper presents AeroLab, an educational embedded-control demonstrator integrating an ESP32, dual ultrasonic ranging, inertial and environmental sensing, a servo actuator, a browser dashboard, and MATLAB/Python engineering scopes. A nominal second-order model is discretized at 50 ms; MATLAB computes discrete LQR and observer coefficients that are exported to firmware. A two-sided cumulative-sum monitor is evaluated in simulation using injected drift, while sensor freshness and proximity-state transitions are assessed through bounded USB telemetry observations. Following a physical connection repair, both ultrasonic channels returned fresh echoes on 40 of 40 sampled bridge polls during a 10-s clear-scene interval. In a separate target interaction, the servo-mounted channel produced caution and critical states and recovered to nominal after target removal; the fixed channel produced a close-range critical transition and recovery. Later monitoring found intermittent freshness on the servo-mounted channel, so continuous reliability is not claimed. The servo scan estimates a commanded angular sector from one range sensor; it does not estimate continuous two-dimensional hand pose. Results distinguish model simulation, synthetic demonstration, and live telemetry, and identify calibration and independent actuator feedback as necessary next steps."); set_font(r,size=9)
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(5); p.paragraph_format.line_spacing=1.0
    r=p.add_run("Index Terms— "); set_font(r,size=9,bold=True)
    r=p.add_run("Embedded control, ESP32, discrete LQR, ultrasonic sensing, telemetry, CUSUM, model-based monitoring."); set_font(r,size=9,italic=True)

    body=doc.add_section(WD_SECTION.CONTINUOUS)
    body.page_width,body.page_height=Inches(8.5),Inches(11)
    body.top_margin=Inches(.62); body.bottom_margin=Inches(.62); body.left_margin=Inches(.68); body.right_margin=Inches(.68)
    body.header_distance=Inches(.28); body.footer_distance=Inches(.28)
    set_columns(body,2,"360")

    heading(doc,"I. Introduction")
    para(doc,"Low-cost embedded platforms make it possible to demonstrate sensing, feedback, alarms, and data visualization in one bench-scale system. The scientific value of such a platform depends not only on whether a dashboard updates, but also on whether each plotted signal has a clearly stated origin. Digital-twin literature describes a spectrum of physical-to-model coupling and lifecycle data integration [1], [2]. AeroLab is positioned more narrowly: it is an educational embedded control and telemetry demonstrator with a model-based software monitor, not a validated aircraft twin or flight controller.")
    para(doc,"The prototype combines an ESP32 firmware application, a MATLAB design script, two browser dashboards, a USB telemetry bridge, and desktop Python/MATLAB scopes. The firmware reads two ultrasonic channels and supporting inertial/environmental sensors, applies freshness-aware alarms, runs a normalized sampled-data controller, and emits JSON. MATLAB supplies the assumed plant model and generated gains. Simulated traces and live sensor packets share visualization software but are treated as different evidence classes.")
    para(doc,"This paper makes four practical contributions: (1) documents the end-to-end hardware/software architecture and signal interfaces; (2) specifies the discrete LQR, observer, saturation, and residual/CUSUM implementation; (3) reports bounded post-repair live-ranging observations alongside MATLAB simulation results; and (4) defines a reproducible validation path for calibration, timing, tracking, and detector performance. Unlike a paper claiming experimentally validated fault diagnosis, the present work does not have independent physical actuator-position feedback or a calibrated sensor data set [3], [4].")

    heading(doc,"II. Related Work")
    para(doc,"The digital-twin concept originated in aerospace lifecycle engineering and has been developed into industrial architectures linking a physical asset, model, data, and services [1], [2]. These frameworks motivate explicit synchronization and data provenance. AeroLab shares the integration goal but currently lacks a measured physical actuator state against which its model can be continuously corrected. The “twin” terminology is therefore used for the embedded model component, not as a claim of high-fidelity synchronization.")
    para(doc,"State estimation and residual-based monitoring have a long control and signal-processing history [5], [6]. CUSUM accumulates signed deviations to detect persistent shifts while tolerating small nominal fluctuations [6], [7]. The cited 2025 IEEE Access study applies a digital-twin diagnostic framework to its own monitored system [3]; it motivates the selected comparison, but its experimental performance cannot be transferred to AeroLab. Similarly, LQR theory provides an optimal state-feedback design under a specified model and quadratic cost [8]. The present paper compares design and evidence scope, not numerical performance against those published systems.")
    table(doc,"TABLE I. RELATED METHODS AND AEROLAB'S EVIDENCE SCOPE",["Literature area","Established focus","AeroLab relation"],[
        ("Digital twins [1], [2]","Physical/model integration and lifecycle data","Bench-scale subset; no demonstrated continuous state correction"),
        ("Twin-based diagnosis [3], [4]","Model residuals for monitored equipment","Software offset test; no independent actuator measurement"),
        ("CUSUM [6], [7]","Sequential detection of persistent shifts","Two-sided detector implemented; evaluated here in simulation"),
        ("Discrete LQR [8]","Optimal feedback for a specified model and cost","ZOH design and gain export; plant parameters remain assumed"),
    ],[.86,1.05,1.19])

    heading(doc,"III. Platform Architecture")
    para(doc,"Fig. 1 separates the physical acquisition path from the model/simulation path. In the physical path, the ESP32 reads sensors, updates its internal state and alarm logic, commands the servo and indicators, and emits telemetry. In the analysis path, MATLAB computes the assumed plant matrices and gains and generates model-based figures. A local Python bridge can read the ESP32 serial stream and provide the latest packet to the browser and native scope applications. All scope panels inherit the provenance and limitations of their source packet; visualization does not validate a measurement.")
    figure(doc,FIG/"ieee_architecture.png","Fig. 1. AeroLab architecture. The upper path carries physical sensor input and live firmware telemetry; the lower path contains model design and synthetic software evaluation.",3.18)

    table(doc,"TABLE II. PRINCIPAL HARDWARE AND SIGNALS",["Subsystem","Interface / pin","Reported quantity"],[
        ("Fixed ultrasonic US1","TRIG 5 / ECHO 18","Filtered range and echo health"),
        ("Servo ultrasonic US2","TRIG 19 / ECHO 23","Sector-associated range"),
        ("SG90 servo","PWM GPIO 13","Command only; no encoder"),
        ("MPU-6050 / OLED","I²C 21 / 22","Attitude / local display"),
        ("DHT11 / MQ-135 / MQ-2","GPIO 4 / ADC 32, 35","Environment; raw gas ADC"),
        ("LDR / LEDs","ADC 34 / GPIO 26, 27, 14","Raw light ADC; 3 alarm colors"),
    ],[.84,.87,1.39])
    para(doc,"The ultrasonic channels use GPIOs configured for 3.3-V ESP32 logic. Common 5-V echo outputs require a correctly rated level shifter or divider; a shared reference ground is essential. Servo and gas-sensor heater supply requirements should be met independently of signal wiring [10]. The installed module markings and exact analog front-end remain hardware-specific and should be checked against their component documentation.")
    para(doc,"For a pulse-echo module, the nominal distance calculation follows d=c_sound·t_echo/2, where division by two accounts for the outgoing and return paths [11]. Firmware pulse diagnostics preserve the distinction between a timeout and an accepted echo; the former is not converted to a plausible 120-cm measurement. The configured 12-ms timeout corresponds to roughly 206 cm at 343 m/s, while the application accepts up to 200 cm to leave margin. The current acquisition cycle samples each channel nominally at 50 ms, with a 15-ms gap between channel triggers. Given two possible 12-ms echo windows, that leaves limited scheduling headroom for the rest of the loop. Actual loop duration and missed deadlines have not been instrumented and should be measured before claiming deterministic 20-Hz operation.")

    heading(doc,"IV. Discrete Control and Model Monitor")
    para(doc,"The design script assumes a second-order normalized plant with natural frequency ωₙ=89 rad/s and damping ratio ζ=0.45. No identification data or fitting procedure is present in the project; these are design parameters, not empirically identified properties of the physical SG90 assembly. With x₁ as normalized displacement and x₂ as its rate, the continuous model is")
    equation(doc,"ẋ = [0  1; −ωₙ²  −2ζωₙ] x + [0; ωₙ²]u,     y = [1  0]x.")
    para(doc,"MATLAB applies exact zero-order-hold discretization at Tₛ=0.05 s (20-Hz nominal control schedule), producing A_d and B_d. The design uses Q=diag(100,1), R=0.01, a discrete LQR gain K, a DC prefilter N̄, and a full-order Luenberger observer with poles derived from −120±j120 rad/s. Generated values are exported to gnc_gains.h so the firmware and analysis script share coefficients. The normalized control input is saturated to [0,1]:")
    equation(doc,"x[k+1] = A_d x[k] + B_d u[k].")
    equation(doc,"u[k] = sat_[0,1](N̄r[k] − K x̂[k]).")
    para(doc,"The checked-in values are K=[−0.422821, 0.000667], N̄=0.577179, and L=[−0.186497, 8.481368]ᵀ. The nominal discrete closed-loop poles are 0.3074 and approximately 0.0000, both inside the unit circle; this is a property of the assumed, unsaturated discrete model. The script also computes full-rank controllability and observability matrices for the continuous realization. The feedback sign convention follows the implementation u=N̄r−Kx̂; changing it without changing the sign of K would alter the controller. A faster 1-ms propagation model is used internally between 50-ms controller updates. The servo output is computed from normalized internal state and is a PWM command, not an independently measured shaft angle.")
    table(doc,"TABLE III. DESIGN AND SIMULATION CONFIGURATION",["Item","Value","Interpretation"],[
        ("Plant parameters","ωₙ=89 rad/s; ζ=0.45","Assumed, not identified from hardware"),
        ("Controller period","Tₛ=50 ms","20-Hz nominal schedule"),
        ("LQR weights","Q=diag(100,1); R=0.01","Normalized-state design choices"),
        ("Discrete poles","0.3074, ≈0","Nominal linear model stability"),
        ("Observer poles","e^(−120±j120)Tₛ; |z|≈0.0025","Pole placement, model-based observer"),
        ("Command bounds","0≤u≤1","Software saturation; not voltage"),
    ],[.92,.99,1.19])
    para(doc,"Fig. 2 is the MATLAB simulation generated from the firmware’s exported discrete coefficients and includes the [0,1] command limit. It is a model simulation, not an oscilloscope trace from the servo. The source script also contains continuous-time, discrete linear, saturated-discrete, PID, and unity-feedback comparisons; these represent different designs and should not be collapsed into one empirical “best controller” claim. In particular, physical settling time, overshoot, and control accuracy require an external angle reference and repeatable input trials.")
    figure(doc,FIG/"ieee_discrete_step_response.png","Fig. 2. MATLAB-generated discrete LQR simulation using the exported firmware coefficients. The upper trace is normalized model state; the lower trace is the normalized saturated command. No physical servo position is measured.",3.18)
    para(doc,"To provide an independent plotting path, a short Python reimplementation uses the exact rounded A_d, B_d, K, and N̄ values in the checked-in firmware header. The recursion applies the same state-feedback sign convention and clips u to [0,1]. Its trace converges rapidly under the assumed model; the plot is a software cross-check of the coefficient export and is not a second hardware experiment.")
    figure(doc,FIG/"python_discrete_lqr_response.png","Fig. 3. Python-generated discrete response using the firmware-exported matrices and gain. The plotted state and saturated command are normalized simulation quantities; the command is not measured servo motion.",3.18)
    para(doc,"The fault-monitoring experiment defines signed discrepancy e[k]=y_p[k]−y_t[k], absolute residual ρ[k]=|e[k]|, and two one-sided CUSUM statistics:")
    equation(doc,"S⁺[k]=max(0,S⁺[k−1]+e[k]−κ),   S⁻[k]=max(0,S⁻[k−1]−e[k]−κ).")
    para(doc,"The shared settings are κ=0.020, h=0.060 for CUSUM, and ρ_th=0.100 for the direct residual threshold. These thresholds are implementation parameters in normalized model units. The MATLAB simulation injects a +0.145 offset at 2.5 s and adds Gaussian measurement noise with σ=0.003. In that scripted scenario, an abrupt offset exceeds the direct residual limit at the first faulty evaluation; this is a conditional response to a deliberately large synthetic step, not an estimate of real diagnostic latency.")
    figure(doc,ROOT/"results"/"figures"/"matlab_digital_twin_residual_araujo2025.png","Fig. 4. MATLAB fault-injection simulation: 0.145 synthetic offset at 2.5 s; residual and CUSUM traces normalized by their thresholds. The traces are generated by software and are not physical board measurements.",3.18)
    para(doc,"A second, independently rendered Python trace illustrates one configured detector scenario using a seeded noise stream. It shows the programmed residual step crossing both normalized limits at the first post-injection sample. The reproduction supports algorithm interpretation and plot-pipeline verification; it does not estimate field detection latency or false-alarm probability.")
    figure(doc,FIG/"python_fault_monitor_simulation.png","Fig. 5. Python-generated residual/CUSUM scenario with σ=0.003, κ=0.020, a 0.145 offset at 2.50 s, and configured thresholds 0.100 and 0.060. Scripted simulation only.",3.18)
    para(doc,"A key implementation boundary is that firmware x₁, x̂₁, and y_twin are propagated from internal model states using the same command. There is no encoder or independent actuator-output sensor. Thus the firmware residual is not a measured physical tracking error. The MATLAB software experiment adds the fault term to its synthetic plant measurement; it evaluates algorithm behavior under that modeled discrepancy. A physical fault-detection claim requires an independently measured output channel and a defined fault-injection protocol [6]–[8].")

    heading(doc,"V. Firmware and Visualization")
    para(doc,"The firmware provides six modes: all-sensor HUD; servo-sector scan/lock/reacquire; 180-degree radar sweep; LQR and model monitor; alternating step benchmark; and IMU attitude gimbal. The 50-ms schedule is nominal: it does not establish measured execution jitter or end-to-end telemetry latency. JSON packets carry source, mode, alarm reason, sensor-health flags, range ages and diagnostics, raw/filtered values, model states, control effort, and servo command. The USB bridge reads the serial JSON stream and serves the latest packet locally. The browser dashboards and desktop scopes display live firmware data or explicit synthetic demonstration data.")
    para(doc,"The dashboard brings together flight-mode controls, alarm status, sensor fields, a 3-D cockpit view, and linked plots. Fig. 6 presents a project dashboard render beside a separately recorded ESP32 packet summary so the interface and hardware evidence can be inspected together without implying they were captured at the same instant. The archived UI render itself shows NO LINK / AWAITING TELEMETRY; it documents the implemented layout, not a live-data result. The adjoining snapshot is the latest dated packet record and reports US1 fresh while US2 has no fresh echo.")
    sec=doc.add_section(WD_SECTION.CONTINUOUS)
    sec.page_width,sec.page_height=Inches(8.5),Inches(11)
    sec.top_margin=Inches(.62); sec.bottom_margin=Inches(.62); sec.left_margin=Inches(.68); sec.right_margin=Inches(.68)
    sec.header_distance=Inches(.28); sec.footer_distance=Inches(.28)
    set_columns(sec,1)
    figure(doc,FIG/"dashboard_publication_plate.png","Fig. 6. AeroLab interface and live-data evidence, shown as distinct objects. Left: project UI render with no active packet. Right: separately logged COM14 snapshot (mode 0, servo command 90°, US1 fresh at 148.83 cm, US2 timeout, RANGE UNKNOWN). Firmware-reported range is not reference-calibrated.",7.1)
    sec=doc.add_section(WD_SECTION.CONTINUOUS)
    sec.page_width,sec.page_height=Inches(8.5),Inches(11)
    sec.top_margin=Inches(.62); sec.bottom_margin=Inches(.62); sec.left_margin=Inches(.68); sec.right_margin=Inches(.68)
    sec.header_distance=Inches(.28); sec.footer_distance=Inches(.28)
    set_columns(sec,2,"360")
    para(doc,"Python and MATLAB live scopes consume the bridge stream and plot telemetry against host receive elapsed time. Their axes do not independently prove the ESP32 sampling period. Demo mode instead generates deterministic trajectories from a seeded pseudorandom process and fixed equations; demo residuals, CUSUM, servo curves, and synthetic range values are illustrative. The dashboards now preserve unavailable model fields as gaps instead of filling them with synthetic defaults, avoiding a misleading overlay when required telemetry is missing.")
    para(doc,"The explicit DEMO signal contract uses a nominal 50-ms synthetic grid, deterministic seed, common damped reference response, programmed positive and negative offsets, noise, residual, and CUSUM state. JavaScript, Python, and MATLAB test intended frame values against golden vectors. This is a cross-implementation reproducibility check, not evidence that GUI callback clocks or hardware sample clocks are synchronized. The MATLAB offline study uses a separate sampled-data simulation with 1-ms plant/twin propagation and 50-ms control/observer updates; figure labels and paper tables distinguish those experiments.")
    para(doc,"Alarm arbitration also includes temperature, gas, vibration, and model-monitor conditions. The firmware uses an adaptive temperature threshold initialized near 38 °C, suppresses MQ-135 gas alarms for the first 60 s after boot, distinguishes an elevated-gas caution from its higher critical threshold, and reports an IMU vibration caution above 0.40 g. Model drift is considered only in the LQR/model-monitor mode or when drift injection is enabled. The LDR is reported as raw ADC; there is no calibrated light-to-lux conversion or light alarm in the current firmware. Thus a dark room may lower the ADC value, but it should not be narrated as a measured illuminance without calibration.")
    para(doc,"For ultrasonic alarms, severity is computed only from fresh valid samples. Each sensor needs two consecutive newly acquired samples in its threshold band; a missing/invalid sample clears that sensor’s confirmation counter. A critical proximity state has priority over caution. Both channels are combined with logical OR for alarm activation, while the message identifies which channel triggered. If either channel is stale, the interface reports RANGE UNKNOWN, and recovery to green requires both channels to be fresh and no remaining alarm condition. This fail-safe status is intentionally different from either yellow caution or red hazard.")
    para(doc,"Ultrasonic validity is treated separately from proximity. A sample is accepted in a configured 2–200-cm window; valid readings update an exponential moving average, d_f[k]=0.65d_raw[k]+0.35d_f[k−1]. The most recent valid sample remains fresh for 300 ms. Two distinct fresh samples are required to confirm a proximity band. Under the current code, <14 cm is critical and 14–<28 cm is caution; missing either sensor’s fresh reading yields RANGE UNKNOWN rather than silently declaring the environment clear. These are firmware decision thresholds, not calibrated collision probabilities. Fig. 7 summarizes the decision path. The 200-cm upper application limit is separate from the hand-candidate limit of 55 cm. The 999-cm no-range sentinel is deliberately outside the accepted range and must never be interpreted as a real echo.")
    figure(doc,make_range_flow(),"Fig. 7. Firmware range-processing path. Invalid or stale readings do not update the filter; range availability and proximity severity are separate outputs.",3.18)
    para(doc,"Mode 1 should be described as sector-level range scanning, not general hand tracking. US2 scans approximately 35°–145° in 6° commanded steps. Candidate returns must be fresh and within 2–55 cm; scan bins require coverage and the algorithm rejects broad reflections. A single ultrasonic beam and hobby servo do not measure continuous two-dimensional hand pose, classify a person, or provide a camera-like track. Mode 5 is different: it commands an IMU-based gimbal response around 90° from roll. It is not the hand-scan mode.")
    table(doc,"TABLE IV. FIRMWARE MODES AND WHAT THEY MEASURE",["Mode","Behavior","Evidence / output"],[
        ("0","All-sensor HUD","Display and alarm monitoring"),
        ("1","35°–145° sector scan / lock / reacquire","Fresh US2 range associated with commanded sector"),
        ("2","Servo radar sweep","Wide angular sweep; range samples"),
        ("3","LQR demand + model monitor","Normalized command and model-state residual"),
        ("4","Alternating 0.15/0.85 step benchmark","Firmware model-state response metrics"),
        ("5","IMU gimbal","Roll-derived servo command near 90°"),
    ],[.45,1.25,1.40])

    heading(doc,"VI. Evaluation Protocol and Results")
    para(doc,"Evaluation is split into (A) software design/simulation, (B) deterministic visualization checks, and (C) bounded live USB observations. A successful compile or graph self-test verifies software behavior only. Live checks use packets tagged ESP32_FIRMWARE, inspect age and echo-health fields, and count read-only bridge polls; poll counts are not necessarily the number of sensor acquisitions. The board was not flashed during the most recent post-repair paper-evidence checks.")
    table(doc,"TABLE V. SIMULATION RESULTS UNDER THE SCRIPTED SCENARIOS",["Experiment","Observed result","Scope of interpretation"],[
        ("Residual / CUSUM; 300 runs","0% false-alarm runs; 100% detected; mean delay 0 ms for each detector","Drift=0.145; σ=0.003; injection at 2.5 s"),
        ("Parameter perturbation; 200 models","100% met the script's 5% final-error criterion","ωₙ ±15%; ζ ±20%; nominal controller; 60 samples"),
    ],[.98,1.03,1.09])
    para(doc,"The exact printed MATLAB results are included to make the model study reproducible: all 300 Monte Carlo runs detected the programmed 0.145 offset with both the residual threshold and CUSUM, and no run alarmed before injection. The first post-injection sample crossed each threshold, so the sample-grid delay is zero. In 200 perturbed models, all trajectories met the script’s finite-output, peak-output (<1.5), and final-error (<0.05) checks over 60 samples. This indicates that the selected nominal implementation tolerates those particular parameter perturbations under the scripted test; it does not quantify hardware reliability or cover unmodeled servo effects.")
    table(doc,"TABLE VI. BOUNDED LIVE ULTRASONIC OBSERVATIONS (24 OCTOBER 2026)",["Test interval","Observed result","What it supports"],[
        ("Clear scene, 10 s","Both channels fresh on 40/40 sampled polls; green on all 40","Fresh dual-channel returns observed in this interval"),
        ("US2 target interaction","Yellow at reported 20.5–25.1 cm; red at 12.0–13.3 cm; green after removal","Live caution/critical/clear transitions observed"),
        ("US1 target interaction","Red at reported 6.2–9.0 cm; green after removal; yellow not sustained","Close-range transition observed; caution-band check open"),
        ("Later monitor, 10 s","US1 fresh 145/145; US2 fresh 131/145; both fresh 131/145","Intermittent US2 freshness; green 91/145, caution 54/145"),
        ("Later 20 s monitor","US2 fresh on 72/285 polls (25.3%); RANGE UNKNOWN on 280/285","Intermittent echo freshness in that later scene"),
    ],[.74,1.20,1.16])
    para(doc,"The Python-generated evidence plot in Fig. 8 places the three documented bridge-poll intervals on one common scale. It makes the change in US2 freshness visible while retaining the sample denominators. Polling repeatedly reads the latest bridge packet; therefore these ratios describe observed packet freshness at poll time, not an independent count of ultrasonic trigger cycles.")
    figure(doc,FIG/"python_live_range_evidence.png","Fig. 8. Python summary of logged live bridge observations. Clear-scene and later monitor intervals are separate sessions. The latest packet snapshot is also shown, but is not part of the plotted interval denominators.",3.18)
    para(doc,"After the owner repaired a physical connection, a 10-s clear-scene interval produced fresh accepted observations from both range channels on all 40 sampled bridge polls. In a separate hands-on test, US2 produced yellow caution at reported ranges of approximately 20.5–25.1 cm, red critical at approximately 12.0–13.3 cm, then recovered to green after target removal. US1 produced red at approximately 6.2–9.0 cm and recovered to green after removal; a sustained US1 yellow response was not established. The values are firmware-reported distances and were not compared against a calibrated reference ruler/fixture.")
    para(doc,"Later observations were less stable: a 10-s monitor found US2 fresh on 131/145 bridge polls, while a separate 20-s interval found US2 fresh on 72/285 polls. During the latter interval the alarm was predominantly RANGE UNKNOWN, reflecting a missing fresh echo rather than a confirmed close object. This later result prevents a claim of uninterrupted or repeatable US2 operation. It does not identify whether the cause was target geometry, field of view, wiring, power, interference, or the sensor module itself. A controlled clear-space and known-distance repeat is needed.")
    para(doc,"The project verification record reports successful ESP32 PlatformIO release builds, dashboard JavaScript checks, Python syntax/self-test, and MATLAB simulation/demo-contract checks. The standalone host C++ control test was not run because a compatible C++ compiler was unavailable in that environment. The project also has six saved MATLAB simulation figures. The correct interpretation is that the software path was exercised; it is not a complete validation of every hardware channel or a demonstration of aircraft control performance.")

    heading(doc,"VII. Discussion")
    para(doc,"Three distinctions shape the paper’s interpretation. First, assumed-model simulation is useful for checking controller equations and detector code, but it cannot establish the physical SG90 dynamics. Second, raw sensor telemetry shows that a module returned a value, but accuracy and reliability require calibration and repeated trials. Third, an open scope window verifies the visualization process, but a live evidence claim also needs a fresh firmware source, valid timestamps, and explicit sensor-health indicators. These distinctions make the system easier to explain and prevent a visually persuasive interface from being mistaken for experimental validation.")
    para(doc,"The live results show why freshness metadata is valuable: the system can distinguish a clear-space echo from a missing echo and avoid interpreting stale range as a current obstacle. The observed US2 caution/critical transitions are a useful functional demonstration, while the later intermittent stream identifies an unfinished reliability question. For the same reason, a single range sensor’s commanded angle should be reported as a sector estimate, not a continuous target coordinate.")
    para(doc,"The LDR channel is raw ADC and is not calibrated in lux. MQ-135/MQ-2 outputs are raw ADC counts, not gas concentration; MQ-family sensors require module-specific warm-up and calibration. The IMU depends on bias, axis convention, mounting alignment, and filtering. The servo angle is commanded. These four conditions should be stated in captions or methods whenever corresponding traces are shown. If physical tracking performance is a core claim, an independent angle/position sensor or a suitable multi-sensor/camera measurement is required.")
    para(doc,"The script’s 300-run CUSUM/residual Monte Carlo study and 200-model parameter sweep are conditional simulations. Their statistics are functions of the selected random seed, noise, drift, state model, and pass/fail thresholds. They should be reported as scenario results, not empirical false-alarm probabilities or generalized robustness. The implementation should also be checked against the exact ultrasonic module’s recommended acquisition period; if it is an HC-SR04 variant, its guide recommends spacing measurement cycles beyond 60 ms, whereas the firmware’s nominal per-channel interval is 50 ms [11]. The physical module marking should be confirmed before changing the schedule.")

    heading(doc,"VIII. Reproducibility and Future Validation")
    para(doc,"A stronger hardware study should begin with a calibration fixture and synchronized logging. For each range sensor, record raw pulse width, filtered distance, validity age, commanded servo angle, reference target distance, and alarm state at 5, 10, 20, and 50 cm. Repeat clear-scene measurements at several scan angles to expose wall reflections and mounting bias. Report absolute error, spread, missed-echo fraction, and threshold-transition repeatability. Log timestamps from one monotonic clock and measure packet rate, interarrival jitter, and stale-data duration rather than inferring them from a configured timer.")
    para(doc,"For controller validation, instrument servo output with an independent angle reference, apply repeatable steps in a safe fixture, and identify the physical response from recorded input/output data. Separate model fitting trials from held-out validation trials [12]. For fault monitoring, tune thresholds on nominal training data, inject controlled sensor/model faults, and report misses, false alarms per unit time, and detection delay with confidence intervals. For hand interaction, define target trajectory and speed and score sector localization and reacquisition; continuous pose estimation requires appropriate sensing geometry. These steps are proposed future work, not completed experiments.")
    para(doc,"For reproducibility, archive the firmware binary/hash, source revision, MATLAB release, Python dependencies, bridge configuration, raw CSV logs, sensor module markings, wiring photographs, and calibration references. Plot titles/captions should encode source type—SIMULATION, DEMO, or LIVE TELEMETRY—and carry units and validity information. A measured-performance figure should include the reference sensor and uncertainty, not only a dashboard screenshot.")

    heading(doc,"IX. Conclusion")
    para(doc,"AeroLab integrates an ESP32 firmware controller, dual ultrasonic proximity channels, inertial and environmental sensing, a model-based monitoring path, and browser/Python/MATLAB visualization. The MATLAB-generated discrete LQR and injected-drift figures demonstrate model and software behavior under explicit assumptions. Post-repair live checks observed dual-channel fresh echoes in one clear-scene interval and yellow/red/green response from the servo-mounted channel; the fixed channel showed close-range red and clear recovery. Later US2 monitoring was intermittent, so continuous reliability and calibrated ranging remain unproven. The current Mode 1 is a sector-level ultrasonic scan rather than continuous hand-pose tracking, and the model residual lacks independent physical actuator feedback. The paper’s principal result is an integrated, inspectable demonstrator with clearly bounded simulation and live evidence, together with a concrete path toward calibrated evaluation.")

    heading(doc,"Acknowledgment",2)
    para(doc,"The author thanks the School of Electronics Engineering, Vellore Institute of Technology, for the academic setting in which the demonstrator was developed.",first=False)
    heading(doc,"References",2)
    refs=[
        "E. H. Glaessgen and D. S. Stargel, “The digital twin paradigm for future NASA and U.S. Air Force vehicles,” in Proc. AIAA/ASME/ASCE/AHS/ASC Structures, Structural Dynamics, and Materials Conf., Honolulu, HI, USA, 2012, Art. no. AIAA 2012-1818, doi: 10.2514/6.2012-1818.",
        "F. Tao, H. Zhang, A. Liu, and A. Y. C. Nee, “Digital twin in industry: State-of-the-art,” IEEE Trans. Ind. Informat., vol. 15, no. 4, pp. 2405–2415, Apr. 2019, doi: 10.1109/TII.2018.2873186.",
        "A. C. S. Araujo, L. M. Rabelo, P. C. M. Lamim Filho, and W. M. Caminhas, “A digital twin approach to smart monitoring and fault diagnosis,” IEEE Access, vol. 13, pp. 148384–148395, 2025, doi: 10.1109/ACCESS.2025.3601349.",
        "R. Isermann, Fault-Diagnosis Systems: An Introduction from Fault Detection to Fault Tolerance. Berlin, Germany: Springer, 2006.",
        "R. E. Kalman, “A new approach to linear filtering and prediction problems,” J. Basic Eng., vol. 82, no. 1, pp. 35–45, Mar. 1960, doi: 10.1115/1.3662552.",
        "E. S. Page, “Continuous inspection schemes,” Biometrika, vol. 41, nos. 1–2, pp. 100–115, Jun. 1954, doi: 10.1093/biomet/41.1-2.100.",
        "NIST/SEMATECH, “CUSUM control charts,” e-Handbook of Statistical Methods, §6.3.2.3. [Online]. Available: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm.",
        "B. D. O. Anderson and J. B. Moore, Optimal Control: Linear Quadratic Methods. Englewood Cliffs, NJ, USA: Prentice-Hall, 1989.",
        "K. J. Åström and R. M. Murray, Feedback Systems: An Introduction for Scientists and Engineers. Princeton, NJ, USA: Princeton Univ. Press, 2008.",
        "Espressif Systems, ESP32 Series Datasheet, Version 5.3, 2025. [Online]. Available: https://documentation.espressif.com/esp32_datasheet_en.html.",
        "ElecFreaks, “Ultrasonic ranging module HC-SR04: User guide.” [Online]. Available: https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf. Accessed: Oct. 24, 2026.",
        "L. Ljung, System Identification: Theory for the User, 2nd ed. Upper Saddle River, NJ, USA: Prentice Hall, 1999.",
    ]
    for i,ref in enumerate(refs,1):
        p=doc.add_paragraph()
        p.paragraph_format.left_indent=Inches(.17); p.paragraph_format.first_line_indent=Inches(-.17)
        p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.0
        r=p.add_run(f"[{i}] {ref}"); set_font(r,size=8.3)

    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
