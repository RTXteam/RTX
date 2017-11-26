# Type-driven Incremental Semantic Parser

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains an implementation of the semantic parser in paper [Type-driven Incremental Semantic Parsing with Polymorphism](http://www.aclweb.org/anthology/N/N15/N15-1162.pdf).

#### Required Dependencies

1. `PyPy`: due to the heavy computation required by this parser, it is strongly recommended to use PyPy instead of CPython. This program is tested with PyPy 5.4.0.
2. Python packages including:
  1. `python-gflags`: used for command-line arguments parsing.
  2. `pyparsing`: used for parsing lambda expressions in the dataset. 

#### Training

To train on the provided sample data set and saving the model, you can run:
```
trainer.py --outputprefix exps/demotrain
```
where `exps` is a directory storing all training models, and `demotrain` is the prefix of the saved model file. The trainer will dump its weights to a standalone weight file (a pickle file) at each training iteration.

#### Evaluating

To evaluate the trained model on development set and testing set, you can run:
```
trainer.py --eval exps/demotrain.9.pickle
```
where `exps/demotrain.9.pickle` is a weight file saved in the previous training.
