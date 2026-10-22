from PIL import Image, ImageDraw
import glob, os, sys
from concurrent.futures import ProcessPoolExecutor
src='/home/claude/arena/render'; dst='/home/claude/arena/repo/images'
def conv(f):
  im=Image.open(f).convert('RGBA'); b=os.path.basename(f)
  if b=='card-back.png':
    im=im.crop((37,37,787,1087))
    m=Image.new('L',im.size,0);ImageDraw.Draw(m).rounded_rectangle((0,0,749,1049),45,fill=255);im.putalpha(m)
    im.save(dst+'/card-back.webp',quality=85,method=4)
  else:
    im.save(dst+'/cards/'+b[:-4]+'.webp',quality=85,method=4)
  return b
with ProcessPoolExecutor() as ex: list(ex.map(conv, glob.glob(src+'/*.png')))
fs=sorted(glob.glob(src+'/*.png'));cols=12;w,h=150,210
sheet=Image.new('RGB',(cols*w,((len(fs)+cols-1)//cols)*h),'#888')
for i,f in enumerate(fs):
  im=Image.open(f).convert('RGBA').resize((w,h));sheet.paste(im,((i%cols)*w,(i//cols)*h),im)
sheet.save('/home/claude/arena/test/sheet.png')
