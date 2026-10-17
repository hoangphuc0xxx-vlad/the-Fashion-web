import os
from PIL import Image

os.makedirs('d:/ITA201/assets/images', exist_ok=True)

# 1. Load the parts
im0 = Image.open('d:/ITA201/pdf_images/img_0_Im0.png') # Header + Hero
im1 = Image.open('d:/ITA201/pdf_images/img_1_Im1.jpg') # Value props + Categories
im2 = Image.open('d:/ITA201/pdf_images/img_2_Im2.jpg') # Featured Products
im3 = Image.open('d:/ITA201/pdf_images/img_3_Im3.png') # Journal
im4 = Image.open('d:/ITA201/pdf_images/img_4_Im4.png') # Newsletter + Footer

print('Part 0 size:', im0.size)
print('Part 1 size:', im1.size)
print('Part 2 size:', im2.size)
print('Part 3 size:', im3.size)
print('Part 4 size:', im4.size)

# Crop Hero Model from im0 (Right side of hero section)
# im0 width is 1843, height is 827
# Hero image is in the right half, from about x=910 to x=1840, y=140 to 827
hero_model = im0.crop((914, 140, 1843, 827))
hero_model.save('d:/ITA201/assets/images/hero_model.jpg', quality=95)
print('Saved hero_model.jpg')

# Crop Category cards from im1
# im1 has value propositions on top (~y=0 to 180), then title 'Bắt đầu từ điều cơ bản', then 4 cards
# Let's crop the 4 category cards:
# Cards y is roughly 300 to 820. Let's inspect or crop:
w1, h1 = im1.size
card_w = (w1 - 100) // 4
# In im1, margins are around 80px on left and right, cards spaced evenly
# Let's crop the entire categories row first:
cat_strip = im1.crop((78, 305, 1766, 818))
cat_strip.save('d:/ITA201/assets/images/categories_strip.jpg', quality=95)

# Each of the 4 cards:
total_cat_w = 1766 - 78 # 1688
single_card_w = 400
gap = (total_cat_w - 4 * single_card_w) // 3 # approx 29px
for i, name in enumerate(['cat_so_mi', 'cat_polo', 'cat_quan_dai', 'cat_ao_khoac']):
    x0 = 78 + i * (single_card_w + gap)
    x1 = x0 + single_card_w
    card = im1.crop((x0, 305, x1, 818))
    card.save(f'd:/ITA201/assets/images/{name}.jpg', quality=95)
    print(f'Saved {name}.jpg')

# Crop Featured Products from im2
# im2 has title + tabs (~y=0 to 220), then 4 product cards (~y=220 to 760)
for i, name in enumerate(['prod_so_mi_linen', 'prod_polo_cotton', 'prod_so_mi_oxford', 'prod_quan_chino']):
    x0 = 78 + i * (single_card_w + gap)
    x1 = x0 + single_card_w
    # Product image portion (excluding title and price below): y ~ 220 to 660
    prod_card = im2.crop((x0, 225, x1, 660))
    prod_card.save(f'd:/ITA201/assets/images/{name}.jpg', quality=95)
    print(f'Saved {name}.jpg')

# Crop Journal Model from im3
# im3 has journal photo on the left half: x=78 to 960, y=140 to 750
journal_img = im3.crop((78, 140, 960, 750))
journal_img.save('d:/ITA201/assets/images/journal_model.jpg', quality=95)
print('Saved journal_model.jpg')

print('All assets cropped successfully!')
