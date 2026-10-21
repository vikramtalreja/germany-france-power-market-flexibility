"""Build the stable printable guide from its Markdown source (pip install reportlab)."""
from pathlib import Path
import re
import unicodedata
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/printable/Power_Market_BESS_Project_Guide.pdf'

def clean(s):
    for a, b in {'–':'-', '—':'-', '’':"'", '‘':"'", '“':'"', '”':'"', '€':'EUR', '→':'->', '≤':'<=', '≥':'>=', '×':'x', '−':'-', '₂':'2', '•':'-'}.items():
        s = s.replace(a,b)
    return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyGuide',fontName='Helvetica',fontSize=10,leading=13,spaceAfter=7))
styles.add(ParagraphStyle(name='CellGuide',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=0))
for n in ('Title','Heading1','Heading2','Heading3'):
    styles[n].textColor=colors.HexColor('#17384A')
styles['Title'].fontSize=25
styles['Title'].leading=29
styles['Heading1'].fontSize=19
styles['Heading1'].leading=23
styles['Heading3'].fontSize=11
styles['Heading3'].leading=14

def para(s, style='BodyGuide'):
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1 (\2)',s)
    s=escape(clean(s))
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    return Paragraph(s, styles[style])

def footer(c, doc):
    c.setFont('Helvetica',8)
    c.setFillColor(colors.HexColor('#52606D'))
    c.drawString(42,27,'Vikram Talreja | Master project guide | 21 October 2026, revision 2')
    c.drawRightString(A4[0]-42,27,str(doc.page))

story=[]
for page,chunk in enumerate((ROOT/'docs/project-learning-guide.md').read_text().split('<!-- PAGE -->')):
    if page: story.append(PageBreak())
    lines=chunk.strip().splitlines(); i=0
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('|'):
            rows=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip());i+=1
            data=[]
            for row in rows:
                if re.fullmatch(r'[|\s:\-]+',row):continue
                data.append([para(cell.strip(),'CellGuide') for cell in row.strip('|').split('|')])
            n=len(data[0]); widths=[(A4[0]-84)/n]*n
            t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5EEF2')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#CCD6DD')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([t,Spacer(1,9)])
        else:
            m=re.match(r'^(#{1,3}) (.*)',line)
            if m:
                lvl=len(m[1]);style=('Title' if page==0 else 'Heading1') if lvl==1 else ('Heading2' if lvl==2 else 'Heading3')
                story.append(para(m[2],style))
            else:story.append(para(line))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=43,pageCompression=0,title='From power prices to battery decisions',author='Vikram Talreja').build(story,onFirstPage=footer,onLaterPages=footer)
# Keep this font-only uncompressed PDF ASCII-compatible for text-based Git APIs.
# Changing only the four-byte binary marker preserves every PDF byte offset.
b=OUT.read_bytes(); b=b.replace(b'%\x93\x8c\x8b\x9e',b'%PDF-',1);b.decode('ascii');OUT.write_bytes(b)
print(OUT)
