#!/bin/bash

# cd into the directory containing this script
cd "${0%/*}"

for f in badge_sub_*.png
do
    STREAMER=${f:10:-4}
    convert badge_sub_$STREAMER.png -define icon:auto-resize=64,48,32,16 favicon_$STREAMER.ico
done
