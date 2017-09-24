%.png: %.graphviz
	dot $< -Tpng > $@

FIGURES=net5.png \
        net6.png \
        net7.png \
        net8.png \
        markov1.png \
        markov2.png \
        stanford_parse.pdf

conclett.pdf: conclett.tex conclett.bib plainnat.bst $(FIGURES)
	pdflatex conclett.tex
	bibtex conclett
	pdflatex conclett.tex
	pdflatex conclett.tex

net5.png: net5.graphviz
#	dot net5.graphviz -Tpng -Ksfdp > net5.png

net6.png: net6.graphviz
net7.png: net7.graphviz
net8.png: net8.graphviz
markov1.png: markov1.graphviz
markov2.png: markov2.graphviz

clean:
	rm *.log *.aux *.blg *~
