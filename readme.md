# MarkQA: Co<ins>M</ins>plex Numeric<ins>A</ins>l <ins>R</ins>easoning over <ins>K</ins>nowledge Base Question Answering Dataset
 [![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg?style=flat-square)](https://github.com/dki-lab/GrailQA/issues)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![language-python3](https://img.shields.io/badge/Language-Python3-blue.svg?style=flat-square)](https://www.python.org/)
[![made-with-Pytorch](https://img.shields.io/badge/Made%20with-Pytorch-orange.svg?style=flat-square)](https://pytorch.org/)
[![paper](https://img.shields.io/badge/Paper-EMNLP2023-lightgrey?style=flat-square)](https://arxiv.org/abs/2310.15517)
<img width="1175" alt="image" src="https://github.com/cdhx/img_store/blob/main/markqa.png?raw=true">

>MarkQA is a lare-scale dataset for question answering on knowledge bases (KBQA) on Wikidata, with 31,902 questions. Each quesstion is annotated with answers, SPARQL, QDMR and PyQL. It is the first dataset focus on complex numerical reasoning in KBQA.

>This is the accompanying code for the paper "[MarkQA: A large scale KBQA dataset with numerical reasoning](http://arxiv.org/abs/2310.15517)" published at EMNLP 2023. For dataset and leaderboard, please refer to the [homepage of MarkQA](http://114.212.81.217/). In this repository, we provide the code for the baseline models for reproducibility and demonstrate how to work with this dataset.
  
 

# Knowledge Base

The instructions for setting up a SPARQL endpoint to Wikidata for MarkQA via Virtuoso.
## Requirements
* OpenLink Virtuoso 7.2.6 (download from this [link](https://sourceforge.net/projects/virtuoso/files/virtuoso/7.2.6/))
* Python 3 (required if using the provided Python script)
## Set up
### Download processed Virtuoso DB file
Our processed Virtuoso DB file can be downloaded from this [link](https://www.google.com). 
The KB we used is a tailored version of Wikidata-2023-01-23. The original KB is not available for download therefor we suggest you use our processed KB.   
  
### Manage the Virtuoso service
We provide a wrapper script (virtuoso.py, provided by [GrailQA](https://github.com/dki-lab/Freebase-Setup)) for managing the Virtuoso service. 
To use it, first change the virtuosoPath in the script to your local Virtuoso directory. 
Assuming the Virtuoso db file is located in a directory named virtuoso_db under the same directory as the script virtuoso.py and 3001 is the intended HTTP port for the service, to start the Virtuoso service:
```python
python3 virtuoso.py start 3001 -d virtuoso_db
```
and to stop a currently running service at the same port:
```python
python3 virtuoso.py stop 3001
```
You may adjust the maximum amount of RAM the service may use and other configurations via the provided script.
  
# File structure 

This repository is structured as follows:

```
MarkQA/
├─ data/: Data files for training, validation, and test
├─ PyQL_parser.py: The implementation of PyQL.
├─ tailor_kb.py: The script we use to tailor Wikidata, you can directly use our [processed dump](https://developers.google.com/freebase).   
├─ T5/: Baseline method of T5, coming soon!
├─ GMT-KBQA/: Baseline method of GMT-KBQA, coming soon!
└── QDTQA/: Baseline method of QDTQA, coming soon!
```  



# Cite
```bibtex
@inproceedings{
huang2023markqa,
title={Mark{QA}: A large scale {KBQA} dataset with numerical reasoning},
author={Xiang Huang, Sitao Cheng, Yuheng Bao, Shanshan Huang, Yuzhong Qu },
booktitle={The 2023 Conference on Empirical Methods in Natural Language Processing},
year={2023},
url={https://openreview.net/forum?id=NYstQhld8J}
}
```