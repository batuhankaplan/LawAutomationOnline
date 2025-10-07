İKON DOSYALARI

Extension'ın çalışması için aşağıdaki boyutlarda PNG ikonlar gereklidir:

- icon16.png (16x16 piksel)
- icon48.png (48x48 piksel)
- icon128.png (128x128 piksel)

## İkon Oluşturma:

### Yöntem 1: Online Araçlar
1. icon.svg dosyasını https://svgtopng.com/ adresine yükleyin
2. 16x16, 48x48 ve 128x128 boyutlarında PNG olarak indirin
3. Dosyaları bu klasöre kaydedin

### Yöntem 2: Photoshop/GIMP
1. icon.svg dosyasını açın
2. Farklı boyutlarda export edin
3. PNG formatında kaydedin

### Yöntem 3: ImageMagick (Command Line)
```bash
# SVG'yi farklı boyutlarda PNG'ye çevir
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png
```

### Yöntem 4: Inkscape (Command Line)
```bash
inkscape icon.svg --export-type=png --export-filename=icon16.png -w 16 -h 16
inkscape icon.svg --export-type=png --export-filename=icon48.png -w 48 -h 48
inkscape icon.svg --export-type=png --export-filename=icon128.png -w 128 -h 128
```

## Geçici Çözüm:

İkonlar hazır değilse, extension yine de çalışacaktır ama Chrome varsayılan bir ikon gösterecektir.

Extension'ı test ederken ikonları daha sonra ekleyebilirsiniz.
