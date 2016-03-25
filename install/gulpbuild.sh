#!/bin/bash
cd static/
gulp build
cd ../
gulp build
gulp minify
