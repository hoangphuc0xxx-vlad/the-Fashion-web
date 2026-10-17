from PIL import Image
import numpy as np

im0 = Image.open('d:/ITA201/pdf_images/img_0_Im0.png')
# Review part: y roughly 690 to 770
review_exact = im0.crop((78, 700, 520, 770))
review_exact.save('d:/ITA201/assets/images/review_exact.png')

# Button color sample
arr0 = np.array(im0)
btn_color = arr0[620, 200]
print('CTA Button color:', btn_color, '#%02x%02x%02x' % tuple(btn_color))

# Hero bg color
hero_bg = arr0[400, 400]
print('Hero bg color:', hero_bg, '#%02x%02x%02x' % tuple(hero_bg))
