%.png: %.graphviz
	dot $< -Tpng > $@

net5.png: net5.graphviz
	dot net5.graphviz -Tpng -Kfdp > net5.png

net4.png: net4.graphviz
net3.png: net3.graphviz
net2.png: net2.graphviz
net1.png: net1.graphviz
baseproblem.png: baseproblem.graphviz

FIGURES=baseproblem.png \
net1.png \
net2.png \
net3.png \
net4.png \
net5.png

conclett.pdf: conclett.tex conclett.bib conclett.blg plainnat.bst $(FIGURES)
	pdflatex conclett.tex
	bibtex conclett
	pdflatex conclett.tex
	pdflatex conclett.tex

clean:
	rm *.log *.aux *.blg *~
