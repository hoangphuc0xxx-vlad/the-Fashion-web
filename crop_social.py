from PIL import Image

im0 = Image.open('d:/ITA201/pdf_images/img_0_Im0.png')
# Crop review / social proof avatars
# Left side of hero: x roughly 80 to 550, y roughly 650 to 750
review_part = im0.crop((78, 640, 520, 750))
review_part.save('d:/ITA201/assets/images/social_proof.png')
print('Saved social_proof.png')
