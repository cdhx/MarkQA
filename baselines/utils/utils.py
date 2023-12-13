import os
import re
import json
import pandas as pd
import numpy as np
from collections import Counter
from multiprocessing import Pool
from tqdm import tqdm
import math
from torch.utils import data
import warnings
import logging
import torch
warnings.filterwarnings('ignore')
from sys import path

class Dict2Obj(dict):
    def __getattr__(self, key):
        value = self.get(key)
        return Dict(value) if isinstance(value, dict) else value

    def __setattr__(self, key, value):
        self[key] = value

class IntEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, int):
            return int(obj)
        return super().default(obj)
def readjson(path):
    '''读取json,json_list就返回list,json就返回dict'''
    with open(path, 'r', encoding='utf-8') as load_f:
        data_ = json.load(load_f)
    return data_


def savejson(file_name, json_info, indent=4):
    '''json list保存为json'''
    with open('{}.json'.format(file_name), 'w') as fp:
        json.dump(json_info, fp, indent=indent, sort_keys=False,cls=IntEncoder)

def load_json(path):
    '''读取json,json_list就返回list,json就返回dict'''
    return readjson(path)

def save_json(data, file_name):
    '''json list保存为json'''
    return savejson(file_name, data)

class DataGen(data.Dataset):
    def __init__(self, encoder_question):
        self.encoding = encoder_question

    def __len__(self):
        return len(self.encoding)

    def __getitem__(self, index):
        return self.encoding[index]

def clean_question(question,two_end=True):
    if question == '':
        return ''
    question = question.strip()
    if two_end:
        # 去首尾./
        if question[0] in ['/', ']']:
            question = question[1:]
        while question[-1] in ['/', '?', '`', '.', ':','>',';']:
            question = question[:-1]

    question=question.replace(" 's","'s")
    # typo
    for typo in list(typo_dict.keys()):
        if question.find(typo) == 0:
            question = question.replace(typo + " ", typo_dict[typo] + " ")
        elif typo == question.split()[-1]:
            question = question.replace(" " + typo, " " + typo_dict[typo])
        else:
            question = question.replace(" " + typo + " ", " " + typo_dict[typo] + " ")

    question = ' '.join(question.split())  # 去多余空格
    question = question.strip()  # 去前后空格
    return question
def clean_cwq_sparql(sparql):
    keyword_list = ['FILTER (?x != ?c)', 'DISTINCT', 'EXISTS', 'FILTER']
    sparql_list = sparql.split('\n')
    for x in keyword_list:
        sparql_list = [line for line in sparql_list if x not in line]
    sparql = '\n'.join(sparql_list)
    return sparql


def is_clean_sparql_correct():
    # 简化后的cwq sparql是否查询结果和原来相同
    json_list = readjson('../../data/CWQ/ComplexWebQuestions_dev.json')
    excutor = FBExcutor()
    for js in json_list:
        sparql = js['sparql']
        ans = excutor.query_db(sparql)
        cleaned_sparql = clean_cwq_sparql(sparql)
        cleaned_ans = excutor.query_db(cleaned_sparql)


def cal_f1(golden, pred):
    if len(pred) == 0 and len(golden) == 0:
        return 1
    elif len(pred) == 0 and len(golden) != 0:
        return 0
    elif len(pred) != 0 and len(golden) == 0:
        return 0
    else:
        p = len([x for x in pred if x in golden]) / len(pred)
        r = len([x for x in golden if x in pred]) / len(golden)
        if p == 0 or r == 0:
            return 0
        else:
            return 2 * p * r / (p + r)


def get_gpu_memory(gpu_id=1):
    # 查询gpu剩余内存
    import pynvml
    pynvml.nvmlInit()
    if gpu_id < 0 or gpu_id >= pynvml.nvmlDeviceGetCount():
        # 对应的显卡不存在!
        return 0
    handler = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
    meminfo = pynvml.nvmlDeviceGetMemoryInfo(handler).free / 1024 / 1024
    return meminfo


def find_free_gpu(gpu_id=None, threshold=22000):
    # 持续刷新gpu剩余状态，在出现空闲gpu时退出，适合无人值守时在出现空闲gpu时立刻执行
    # 如果指定了gpu，查看是否可使用，如果内存不到threshold，自动寻找可用的gpu
    nvidia2torh = {0: 0, 1: 3, 2: 1, 3: 4, 4: 2}  # 从nvidia编号转到torch编号
    torch2nvidia = {v: k for k, v in nvidia2torh.items()}
    assert gpu_id == None or gpu_id in [0, 2, 4, 1, 3], 'This gpu num not exist!'
    if gpu_id != None:
        if get_gpu_memory(torch2nvidia[gpu_id]) > threshold:
            print('Current gpu: ', gpu_id, ' is avaliable!')
            return gpu_id
        else:
            print('Current gpu: ', gpu_id, ' out of memory, searching avaliable gpu...')
    print('Searching avaliable gpu...')
    while True:
        for gpu_id in [0, 2, 4, 1, 3]:
            if get_gpu_memory(gpu_id) > threshold:
                print('Find gpu :', nvidia2torh[gpu_id], ' is avaliable! ')
                return nvidia2torh[gpu_id]
def get_confusion_matrix(prediction, truth):
    confusion_vector = prediction / truth

    true_positives = torch.sum(confusion_vector == 1).item()
    false_positives = torch.sum(confusion_vector == float('inf')).item()
    true_negatives = torch.sum(torch.isnan(confusion_vector)).item()
    false_negatives = torch.sum(confusion_vector == 0).item()

    return true_positives, false_positives, true_negatives, false_negatives

def sexp2sparql():
    # SExpression转SPARQL
    pass


def merge_2qdt_dataset():
    # 把来自两个数据集的qdt合并成一个并加source属性，LC的_id统一成ID
    import stanza
    nlp = stanza.Pipeline('en')  # This sets up a default neural pipeline in English
    for part in ['test', 'dev', 'train']:
        lc_data = readjson('../../data/qdt_merged/lc_' + part + '_qdt.json')
        cwq_data = readjson('../../data/qdt_merged/cwq_' + part + '_qdt.json')
        for index, item in tqdm(enumerate(lc_data)):
            entity_list = [x.text for x in nlp(item['question']).entities]
            mask_entity = item['question']
            for ent in entity_list:
                mask_entity = mask_entity.replace(ent, '[ENT]')
            constituency = str(nlp(item['question']).sentences[0].constituency)
            lc_data[index] = {"ID": item.pop('_id'), "question": item['question'],
                              "decompostion": item['decomposition'], \
                              "constituency": constituency, "mask_entity": mask_entity, "entity": entity_list,
                              "source": 'lc'}
        for index, item in enumerate(cwq_data):
            cwq_data[index]['source'] = 'cwq'
        new_data = cwq_data + lc_data
        savejson('../../data/qdt_merged/qdt_' + part, new_data)



def outer_inner_list2edg(outer_question, inner_question):
    # 将分解结果转化成edg,传入subq1和subq2列表
    # 似乎这个函数可以完美覆盖另外两个
    all_node = [
        {'nodeType': 'Entity', 'entityID': 0, 'nodeID': 0}
    ]
    all_edge = []
    if len(inner_question) != 0:
        all_node.append({'nodeType': 'Entity', 'entityID': 1, 'nodeID': 1})

    node_id_now = len(all_node)  # 现在的node id排到哪里了
    for outer_des in outer_question:
        all_node.append({'nodeType': 'Description', 'value': outer_des, 'entityID': 0, 'nodeID': node_id_now,
                         'hasRefer': '[ENT]' in outer_des})
        all_edge.append({'from': 0, 'to': node_id_now})
        if '[ENT]' in outer_des:  # descirption指向内层实体的边
            all_edge.append({'from': node_id_now, 'to': 1})
        node_id_now += 1
    for inner_des in inner_question:
        all_node.append({'nodeType': 'Description', 'value': inner_des, 'entityID': 1, 'nodeID': node_id_now,
                         'hasRefer': '[ENT]' in inner_des})
        all_edge.append({'from': 1, 'to': node_id_now})
        node_id_now += 1

    edg_structure = {"nodes": all_node, "edge": all_edge}

    return edg_structure


def linear_qdt_to_tree(linear_qdt,two_inq=True):
    # 把生成的qdt抓换成outer,inner des list,可以接以前的函数to qdt
    if not two_inq:#如果只有一个INQ，不分INQL和INQR
        if '[INQ]' not in linear_qdt:
            outer_des = [x.strip() for x in linear_qdt.split('[DES]')]
            inner_des = []
        else:
            inq_split = [x.strip() for x in linear_qdt.split('[INQ]')]
            if len(inq_split) == 2:  # 如果只有一个[INQ]，就当SEP处理
                linear_qdt = linear_qdt.replace('[INQ]', '[DES]')
                outer_des = [x.strip() for x in linear_qdt.split('[DES]')]
                inner_des = []
            elif len(inq_split) == 3:  # 正常的
                inner_des = [x.strip() for x in inq_split[1].split('[DES]')]  # 内层描述
                outer_des = linear_qdt.replace('[INQ] ' + inq_split[1] + ' [INQ]', '[ENT]')
                outer_des = [x.strip() for x in outer_des.split('[DES]')]
            else:  # 其他的，取最远的两个[INQ]
                inner_des = ' [DES] '.join(inq_split[1:-1])
                inner_des = [x.strip() for x in inner_des.split('[DES]')]
                outer_des = ' [ENT] '.join([inq_split[0], inq_split[-1]])
                outer_des = [x.strip() for x in outer_des.split('[DES]')]
    else:#如果INQ分INQL和INQR
        if '[INQL]' not in linear_qdt and '[INQR]' not in linear_qdt:
            outer_des = [x.strip() for x in linear_qdt.split('[DES]')]
            inner_des = []
        else:
            inq_split = [x.strip() for x in re.split("\[INQL\]|\[INQR\]",linear_qdt)]
            if len(inq_split) == 2:  # 如果只有一个[INQ]，就当SEP处理
                linear_qdt = linear_qdt.replace('[INQL]', '[DES]').replace('[INQR]', '[DES]')
                outer_des = [x.strip() for x in linear_qdt.split('[DES]')]
                inner_des = []
            elif len(inq_split) == 3:  # 正常的
                inner_des = [x.strip() for x in inq_split[1].split('[DES]')]  # 内层描述
                outer_des = linear_qdt.replace('[INQL] ' + inq_split[1] + ' [INQR]', '[ENT]')
                outer_des = [x.strip() for x in outer_des.split('[DES]')]
            else:  # 其他的，取最远的两个[INQ]
                inner_des = ' [DES] '.join(inq_split[1:-1])
                inner_des = [x.strip() for x in inner_des.split('[DES]')]
                outer_des = ' [ENT] '.join([inq_split[0], inq_split[-1]])
                outer_des = [x.strip() for x in outer_des.split('[DES]')]
    outer_des = [x for x in outer_des if x!='']
    inner_des = [x for x in inner_des if x != '']
    # composition2edg可以完美覆盖conjunction2edg和simple2edg，逻辑上是一致的
    qdt = outer_inner_list2edg(outer_des, inner_des)
    return outer_des, inner_des, qdt

def tree2linear_qdt(qdt,two_inq=True):
    #qdt->linear qdt
    this_example = []  # 外层列表
    for out_des in qdt['root_question']:
        if 'inner_questions' in out_des:
            inner_part = ' [DES] '.join([x['description'] for x in out_des['inner_questions']['IQ1']])
            if two_inq:
                this_out = out_des['description'].replace('[IQ1]', '[INQL] ' + inner_part + ' [INQR]')
            else:
                this_out = out_des['description'].replace('[IQ1]', '[INQ] ' + inner_part + ' [INQ]')
        else:
            this_out = out_des['description']
        this_example.append(this_out)
    this_example = ' [DES] '.join(this_example).strip()
    return this_example

def tree_train_subq_test():
    # 树的结果按照子问题评测，不能直接用
    # eval_json 需要有Q,decomposition，decomposition_2_part,comp_type
    count = 0
    num_of_batches = math.ceil(len(eval_json) / self.inference_batch_size)
    new_json = eval_json
    for i in tqdm(range(num_of_batches)):
        new_json = eval_json[
                   i * self.inference_batch_size:i * self.inference_batch_size + self.inference_batch_size]
        if self.use_prefix:
            question_list = [row['question'] for row in new_json]
            prefix_list = [row['comp_type'] for row in new_json]
        else:
            question_list = [row['question'] for row in new_json]
            prefix_list = ["Decomp" for row in new_json]
        inputbatch = [prefix_list[index] + ": " + question_list[index] for index in range(len(question_list))]
        labelbatch = [row['decomposition'] for row in new_json]
        labelbatch_2part = [row['decomposition_2_part'] for row in new_json]
        modi_eval_pred, eval_pred = self.batch_predict(question_list, prefix_list, modi_acc)
        for index in range(len(modi_eval_pred)):
            if '[INQL]' in modi_eval_pred[index] and '[INQR]' in modi_eval_pred[index]:
                modi = ' '.join(modi_eval_pred[index].replace('[DES]', '').split()).strip()
            else:
                modi = modi_eval_pred[index]
                des_num = modi.count('[DES]')
                modi = modi.replace('[INQL]', '').replace('[INQR]', '')
                flag = 0
                if des_num == 1:
                    flag = 0
                elif des_num == 2 or  des_num == 3:
                    flag = 1
                elif des_num == 4 or des_num == 5:
                    flag = 2
                else:
                    flag = int(des_num / 2)
                new_modi = []
                current = -1
                for token in modi.split():
                    if token != '[DES]':
                        new_modi.append(token)
                    else:
                        current += 1
                        if current == flag:
                            new_modi.append(token)
                modi = ' '.join(new_modi).strip()
            if modi == labelbatch_2part[index][0]:
                count += 1