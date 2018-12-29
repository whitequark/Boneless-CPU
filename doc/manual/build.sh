#!/bin/sh -ex

cd $(dirname $0)
pdflatex -halt-on-error -interaction batchmode manual.tex
pdflatex -halt-on-error -interaction batchmode manual.tex
