from PIL import Image

# 1. Clean hero_model.jpg: the admin button is at bottom right
hero = Image.open('d:/ITA201/assets/images/hero_model.jpg')
# Let's inspect where the admin button is: it's roughly bottom right
# We can cover it with a continuation of the car/street background or crop slightly
w, h = hero.size
# The button is roughly x in [w-220, w], y in [h-70, h]
# Let's clone background texture from right above it or patch it nicely
patch = hero.crop((w - 220, h - 140, w, h - 70))
hero.paste(patch, (w - 220, h - 70))
hero.save('d:/ITA201/assets/images/hero_model.jpg', quality=95)

# 2. Clean cat_ao_khoac.jpg
coat = Image.open('d:/ITA201/assets/images/cat_ao_khoac.jpg')
cw, ch = coat.size
# Admin button is in bottom right
patch_coat = coat.crop((cw - 120, ch - 120, cw, ch - 60))
coat.paste(patch_coat, (cw - 120, ch - 60))
coat.save('d:/ITA201/assets/images/cat_ao_khoac.jpg', quality=95)

print('Cleaned admin buttons successfully!')
