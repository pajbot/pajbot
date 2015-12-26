var gulp = require('gulp');
var watch = require('gulp-watch');
var minifyCss = require('gulp-minify-css');
var rename = require("gulp-rename");

gulp.task('minify', function () {
  gulp.src('./static/css/base.css')
  .pipe(minifyCss({compatibility: 'ie8'}))
  .pipe(rename('base.min.css'))
  .pipe(gulp.dest('./static/css/'))
});

gulp.task('watch',function() {
  gulp.watch('./static/css/base.css',['minify']);
});