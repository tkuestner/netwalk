#!/bin/sh

rm assets.png assets.atlas
python3 -m kivy.atlas assets 200 *.png 
mv assets-0.png assets.png
sed -i -e 's/assets-0/assets/g' assets.atlas

