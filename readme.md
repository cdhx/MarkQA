# MarkQA: Co<ins>M</ins>plex Numeric<ins>A</ins>l <ins>R</ins>easoning over <ins>K</ins>nowledge Base <ins>Q</ins>uestion <ins>A</ins>nswering Dataset
 [![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg?style=flat-square)](https://github.com/dki-lab/GrailQA/issues)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![language-python3](https://img.shields.io/badge/Language-Python3-blue.svg?style=flat-square)](https://www.python.org/)
[![made-with-Pytorch](https://img.shields.io/badge/Made%20with-Pytorch-orange.svg?style=flat-square)](https://pytorch.org/)
[![paper](https://img.shields.io/badge/Paper-EMNLP2023-lightgrey?style=flat-square)](https://arxiv.org/abs/2310.15517)
<img width="1175" alt="image" src="https://raw.githubusercontent.com/cdhx/img_store/main/markqa.png">

>MarkQA is a lare-scale dataset for question answering on knowledge bases (KBQA) on Wikidata, with 31,902 questions. Each quesstion is annotated with answers, SPARQL, QDMR and PyQL. It is the first dataset focus on complex numerical reasoning in KBQA.

>This is the accompanying code for the paper "[MarkQA: A large scale KBQA dataset with numerical reasoning](http://arxiv.org/abs/2310.15517)" published at EMNLP 2023. For dataset and leaderboard, please refer to the [homepage of MarkQA](http://ws.nju.edu.cn/MarkQA). In this repository, we provide the code for the baseline models for reproducibility and demonstrate how to work with this dataset.
  
 

# Knowledge Base

The instructions for setting up a SPARQL endpoint to Wikidata for MarkQA via Virtuoso.
## Requirements
* OpenLink Virtuoso 7.2.6 (download from this [link](https://sourceforge.net/projects/virtuoso/files/virtuoso/7.2.6/))
* Python 3 (required if using the provided Python script)
## Set up

Our processed Virtuoso DB file are split into two files. 
They can be downloaded via wget and then be put together via cat:

(WARNING: 200G+ disk space is needed for the ziped file and 440G+ disk space is needed for the unziped file)
```linux
wget https://box.nju.edu.cn/f/edd62b714b6b4fefb84e/?dl=1 -O virtuoso_db_part1
wget https://box.nju.edu.cn/f/3b0986513ff2409db5df/?dl=1 -O virtuoso_db_part2
cat virtuoso_db_part1 virtuoso_db_part2 >virtuoso_db.zip
```

The KB we used is a tailored version of Wikidata-2023-01-23. The original KB is not available for download therefor we suggest you use our processed KB.   
  
### Manage the Virtuoso service
We provide a Virtuoso configration file virtuoso.ini. It should be located under the same directory as the virtuoso.db file.

The virtuoso.ini can be obtained by:
```Linux
wget https://box.nju.edu.cn/f/6829889a369c4b0aab6f/?dl=1 -O virtuoso.ini
```
To use it, first replace all virtuoso_installed_path in the file to your local Virtuoso directory.
For example, if the local Virtuoso directory is /data/virtuoso-fixed, change the file via sed:
```Linux
sed -i 's#virtuoso_installed_path#/data/virtuoso-fixed#g' virtuoso.ini
```

Then, under the same directory as the virtuoso.ini file, to start the Virtuoso service:
```Linux
virtuoso-t -fd
```
When you see this sentence in your virtuoso.log file, your virtuoso service has been started up successfully:
```Linux
INFO: Server online at 1111 (pid xxxx)
```
Now you can access the service via the default port 8890. Enter [ip]:8890 in a browser, you will see the virtuoso service page.
You may adjust the maximum amount of RAM the service may use and other configurations in the provided virtuoso.ini file.
# File structure 

This repository is structured as follows:

```
MarkQA/
├─ dataset/: Data files for training, validation, and test.
├─ PyQL_parser.py: The implementation of PyQL.
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