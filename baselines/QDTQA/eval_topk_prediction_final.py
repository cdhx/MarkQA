#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   eval_topk_prediction_final.py
@Time    :   2022/01/08 21:26:57
@Author  :   Xixin Hu 
@Version :   1.0
@Contact :   xixinhu97@foxmail.com
@Desc    :   None
'''

# here put the import lib
import argparse
from ast import dump
from cmath import exp
from math import fabs
from pickle import load
from typing import OrderedDict
from detect_and_link_entity import get_top1_entity_linking_from_earl, save_EARL_cache
from cwq_evaluate import cwq_evaluate_valid_results
from webqsp_evaluate import webqsp_evaluate_valid_results
from components.utils import dump_json, load_json
from tqdm import tqdm
from executor.sparql_executor import execute_query_with_odbc, execute_query_with_odbc_filter_answer, get_label, execute_query
from executor.logic_form_util import lisp_to_sparql
import re
import json
import os
from entity_linker import surface_index_memory
import difflib

def is_value_tok(t):
    if t[0].isalpha():
        return False
    return (process_literal(t) != 'null')

# copied from grail value extractor
def process_literal(value: str):  # process datetime mention; append data type
    pattern_date = r"(?:(?:jan.|feb.|mar.|apr.|may|jun.|jul.|aug.|sep.|oct.|nov.|dec.) the \d+(?:st|nd|rd|th), \d{4}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})"
    pattern_datetime = r"\d{4}-\d{2}-\d{2}t[\d:z-]+"
    pattern_float = r"(?:[-]*\d+[.]*\d*e[+-]\d+|(?<= )[-]*\d+[.]\d*|^[-]*\d+[.]\d*)"
    pattern_yearmonth = r"\d{4}-\d{2}"
    pattern_year = r"(?:(?<= )\d{4}|^\d{4})"
    pattern_int = r"(?:(?<= )[-]*\d+|^[-]*\d+)"
    if len(re.findall(pattern_datetime, value)) == 1:
        value = value.replace('t', "T").replace('z', 'Z')
        return f'{value}^^http://www.w3.org/2001/XMLSchema#dateTime'
    elif len(re.findall(pattern_date, value)) == 1:
        if value.__contains__('-'):
            return f'{value}^^http://www.w3.org/2001/XMLSchema#date'
        elif value.__contains__('/'):
            fields = value.split('/')
            value = f"{fields[2]}-{fields[0]}-{fields[1]}"
            return f'{value}^^http://www.w3.org/2001/XMLSchema#date'
    elif len(re.findall(pattern_yearmonth, value)) == 1:
        return f'{value}^^http://www.w3.org/2001/XMLSchema#gYearMonth'
    elif len(re.findall(pattern_float, value)) == 1:
        return f'{value}^^http://www.w3.org/2001/XMLSchema#float'
    elif len(re.findall(pattern_year, value)) == 1 and int(value) <= 2015:
        return f'{value}^^http://www.w3.org/2001/XMLSchema#gYear'
    elif len(re.findall(pattern_int, value)) == 1:
        return f'{value}^^http://www.w3.org/2001/XMLSchema#integer'
    else:
        return 'null'


def is_number(t):
    t = t.replace(" , ",".")
    t = t.replace(", ",".")
    t = t.replace(" ,",".")
    try:  # 如果能运行float(t)语句，返回True（字符串t是浮点数）
        float(t)
        return True
    except ValueError:  # ValueError为Python的一种标准异常，表示"传入无效的参数"
        pass  # 如果引发了ValueError这种异常，不做任何事情（pass：不做任何事情，一般用做占位语句）
    try:
        import unicodedata  # 处理ASCii码的包
        unicodedata.numeric(t)  # 把一个表示数字的字符串转换为浮点数返回的函数
        return True
    except (TypeError, ValueError):
        pass
    return False


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', required=True, help='split to operate on, can be `test`, `dev` and `train`')
    parser.add_argument('--pred_file', default=None, help='topk prediction file')
    parser.add_argument('--revise_only', action='store_true', dest='revise_only', default=False, help='only do revising')
    parser.add_argument('--server_ip', default=None, help='server ip for debugging')
    parser.add_argument('--server_port', default=None, help='server port for debugging')
    parser.add_argument('--qid',default=None,type=str, help='single qid for debug, None by default' )
    parser.add_argument('--dataset', default='CWQ', type=str, help='dataset type, can be `CWQ、`WebQSP`')

    args = parser.parse_args()

    print(f'split:{args.split}, topk_file:{args.pred_file}')
    return args


# dev_el_results = load_json(f'data/CWQ_dev_entities.json')
# train_el_results = load_json(f'data/CWQ_train_entities.json')
# test_el_results = load_json(f'data/CWQ_test_entities.json')
# dev_el_results = load_json(f'data/linking_results/merged_CWQ_dev_linking_results.json')
# train_el_results = load_json(f'data/linking_results/merged_CWQ_train_linking_results.json')
# test_el_results = load_json(f'data/linking_results/merged_CWQ_test_linking_results.json')

def test_type_checker():
    test_cases = [
        '1875-07-26', 
        '2009',
        '1933-03-04',
        '1775-05-10',
        '5732212',
        '1894000',
        '91534889',
        '3565',
        '1966-07',
        '64339',
        '523000'
    ]
    for case in test_cases:
        print('{}: {}'.format(case, type_checker(case)))

def type_checker(token:str)->str:
    """Check the type of a token, e.g. Integer, Float or date.
       Return original token if no type is detected."""
    
    pattern_year = r"^\d{4}$"
    pattern_year_month = r"^\d{4}-\d{2}$"
    pattern_year_month_date = r"^\d{4}-\d{2}-\d{2}$"
    if re.match(pattern_year, token):
        token = token+"^^http://www.w3.org/2001/XMLSchema#dateTime"
    elif re.match(pattern_year_month, token):
        token = token+"^^http://www.w3.org/2001/XMLSchema#dateTime"
    elif re.match(pattern_year_month_date, token):
        token = token+"^^http://www.w3.org/2001/XMLSchema#dateTime"
    else:
        return token

    return token

def denormalize_s_expr_new(normed_expr, 
                            entity_label_map,
                            entity_mention_map,
                            type_label_map,
                            rel_label_map,
                            train_entity_map,
                            surface_index):
    
    
    expr = normed_expr


    convert_map ={
        '( greater equal': '( ge',
        '( greater than':'( gt',
        '( less equal':'( le',
        '( less than':'( lt'
    }

    for k in convert_map:
        expr = expr.replace(k,convert_map[k])
        expr = expr.replace(k.upper(),convert_map[k])

    expr = expr.replace(', ',' , ')
    tokens = expr.split(' ')

    segments = []
    prev_left_bracket = False
    prev_left_par = False
    cur_seg = ''

    for t in tokens:
        
        if t=='[':
            prev_left_bracket=True
            if cur_seg:
                segments.append(cur_seg)
        elif t==']':
            prev_left_bracket=False
            cur_seg = cur_seg.strip()
            
            # find in linear origin map
            processed = False

            if not processed:
                # find in label entity map

                if cur_seg.lower() in entity_label_map: # entity
                    cur_seg = entity_label_map[cur_seg.lower()]
                    processed = True
                # elif cur_seg.lower() in entity_mention_map:
                #     cur_seg = entity_mention_map[cur_seg.lower()]
                #     processed = True
                elif cur_seg.lower() in type_label_map: # type
                    cur_seg = type_label_map[cur_seg.lower()]
                    processed = True
                else: # relation or unlinked entity
                    if ' , ' in cur_seg: 
                        if cur_seg.lower() in rel_label_map: # relation
                            cur_seg = rel_label_map[cur_seg.lower()]
                        elif cur_seg.lower() in train_entity_map: # entity in trainset
                            cur_seg = train_entity_map[cur_seg.lower()]
                        else: 
                            # try to link entity by FACC1
                            facc1_cand_entities = surface_index.get_indexrange_entity_el_pro_one_mention(cur_seg,top_k=1)
                            if facc1_cand_entities:
                                cur_seg = list(facc1_cand_entities.keys())[0] # take the first entity
                            else: 
                                if is_number(cur_seg):
                                    # check if it is a number
                                    cur_seg = cur_seg.replace(" , ",".")
                                    cur_seg = cur_seg.replace(" ,",".")
                                    cur_seg = cur_seg.replace(", ",".")
                                else:
                                    # view as relation
                                    cur_seg = cur_seg.replace(' , ',',')
                                    cur_seg = cur_seg.replace(',','.')
                                    cur_seg = cur_seg.replace(' ', '_')
                        processed = True
                    else:
                        # unlinked entity    
                        if cur_seg.lower() in train_entity_map:
                            cur_seg = train_entity_map[cur_seg.lower()]
                        else:
                            # keep it, time or integer
                            if is_number(cur_seg):
                                cur_seg = cur_seg.replace(" , ",".")
                                cur_seg = cur_seg.replace(" ,",".")
                                cur_seg = cur_seg.replace(", ",".")
                                cur_seg = cur_seg.replace(",","")
                                
                            else:
                                # find most similar entity label from candidate entity label map
                                find_sim_entity = False
                                for ent_label in entity_label_map:
                                    string_sim = difflib.SequenceMatcher(None, cur_seg.lower(), ent_label).quick_ratio()
                                    if string_sim >= 0.8: # highly similar
                                        cur_seg = entity_label_map[ent_label]
                                        find_sim_entity = True
                                        break
                                
                                # if not find_sim_entity:
                                #     for ent_mention in entity_mention_map:
                                #         string_sim = difflib.SequenceMatcher(None, cur_seg.lower(), ent_mention).quick_ratio()
                                #         if string_sim >= 0.8: # highly similar
                                #             cur_seg = entity_mention_map[ent_mention]
                                #             find_sim_entity = True
                                #             break
                                
                                if not find_sim_entity:
                                    # try facc1 linking
                                    facc1_cand_entities = surface_index.get_indexrange_entity_el_pro_one_mention(cur_seg,top_k=1)
                                    if facc1_cand_entities:
                                        cur_seg = list(facc1_cand_entities.keys())[0]
                                    else:
                                        pass
                                        # try earl linking
                                        # earl_cand_entities = get_top1_entity_linking_from_earl(cur_seg)
                                        # if earl_cand_entities:
                                        #     cur_seg = list(earl_cand_entities)[0]
                                
            segments.append(cur_seg)
            cur_seg = ''
        else:
            if prev_left_bracket:
                # in a bracket
                cur_seg = cur_seg + ' '+t
            else:
                if t=='(':
                    prev_left_par = True
                    segments.append(t)
                else:
                    if prev_left_par:
                        if t in ['ge', 'gt', 'le', 'lt']: # [ge, gt, le, lt] lowercase
                            segments.append(t)
                        else:                
                            segments.append(t.upper()) # [and, join, r, argmax, count] upper case
                        prev_left_par = False 
                    else:
                        # TODO # can be a date string, e.g., 1997
                        if t != ')':
                            if t.lower() in entity_label_map:
                                t = entity_label_map[t]
                            else:
                                t = type_checker(t) # number
                        segments.append(t)

    # print(segments)
    expr = " ".join(segments)
                
    # print(expr)
    return expr


def execute_normed_s_expr_from_label_maps(normed_expr, 
                                        entity_label_map,
                                        entity_mention_map,
                                        type_label_map,
                                        rel_label_map,
                                        train_entity_map,
                                        surface_index
                                        ):
    # print(normed_expr)
    try:
        denorm_sexpr = denormalize_s_expr_new(normed_expr, 
                                        entity_label_map, 
                                        entity_mention_map,
                                        type_label_map,
                                        rel_label_map,
                                        train_entity_map,
                                        surface_index
                                        )
    except:
        return 'null', []
    
    query_expr = denorm_sexpr.replace('( ','(').replace(' )', ')')
    if query_expr != 'null':
        try:
            if 'OR' in query_expr or 'WITH' in query_expr or 'PLUS' in query_expr:
                denotation = []
            else:
                sparql_query = lisp_to_sparql(query_expr)
                # print('sparql:', sparql_query)
                denotation = execute_query_with_odbc(sparql_query)
                denotation = [res.replace("http://rdf.freebase.com/ns/",'') for res in denotation]
        except:
            denotation = []
 
    return query_expr, denotation



def aggressive_top_k_eval_new(split, predict_file, dataset):
    """Run top k predictions, using linear origin map"""
    if dataset == "CWQ":
        train_gen_dataset = load_json('data/CWQ/final/merged/CWQ_train.json')
        test_gen_dataset = load_json('data/CWQ/final/merged/CWQ_test.json')
        dev_gen_dataset = load_json('data/CWQ/final/merged/CWQ_dev.json')
    elif dataset == "WebQSP":
        train_gen_dataset = load_json('data/WebQSP/final/merged/WebQSP_train.json')
        test_gen_dataset = load_json('data/WebQSP/final/merged/WebQSP_test.json')
        dev_gen_dataset = None
    
    predictions = load_json(predict_file)

    # print(os.path.dirname(predict_file))
    dirname = os.path.dirname(predict_file)
    filename = os.path.basename(predict_file)
    
    # augment_data_file = os.path.join(dirname, 'predict_data_all.json')
    # augment_data = load_json(augment_data_file)

    if split=='dev':
        gen_dataset = dev_gen_dataset
    elif split=='train':
        gen_dataset = train_gen_dataset
    else:
        gen_dataset = test_gen_dataset

    use_goldEnt = "goldEnt" in predict_file # whether to use gold Entity for denormalization
    use_goldRel = "goldRel" in predict_file

    if dataset == "CWQ":
        gold_label_maps = load_json(f"data/CWQ/final/label_maps/CWQ_{split}_label_maps.json")    
        train_entity_map = load_json(f"data/CWQ/final/label_maps/CWQ_train_entity_label_map.json")
        train_entity_map = {l.lower():e for e,l in train_entity_map.items()}
    elif dataset == "WebQSP":
        gold_label_maps = load_json(f"data/WebQSP/final/label_maps/WebQSP_{split}_label_maps.json")
        train_entity_map = load_json(f"data/WebQSP/final/label_maps/WebQSP_train_entity_label_map.json")
        train_entity_map = {l.lower():e for e,l in train_entity_map.items()}

    if not use_goldEnt:
        if dataset == "CWQ":
            candidate_entity_map = load_json(os.path.join(dirname, 'CWQ_candidate_entity_map.json'))
            train_type_map = load_json(f"data/CWQ/final/label_maps/CWQ_train_type_label_map.json")
            train_type_map = {l.lower():t for t,l in train_type_map.items()}
        elif dataset == "WebQSP":
            candidate_entity_map = load_json(os.path.join(dirname, "WebQSP_candidate_entity_map.json"))
            train_type_map = load_json(f"data/WebQSP/final/label_maps/WebQSP_train_type_label_map.json")
            train_type_map = {l.lower():t for t,l in train_type_map.items()}
        
    if not use_goldRel:
        if dataset == "CWQ":
            train_relation_map = load_json(f"data/CWQ/final/label_maps/CWQ_train_relation_label_map.json")
            train_relation_map = {l.lower():r for r,l in train_relation_map.items()}
        elif dataset == "WebQSP":
            train_relation_map = load_json(f"data/WebQSP/final/label_maps/WebQSP_train_relation_label_map.json")
            train_relation_map = {l.lower():r for r,l in train_relation_map.items()}
    
    # load FACC1 Index
    # surface_index = None
        
    surface_index = surface_index_memory.EntitySurfaceIndexMemory(
        "entity_linker/data/entity_list_file_freebase_complete_all_mention", 
        "entity_linker/data/surface_map_file_freebase_complete_all_mention",
        "entity_linker/data/freebase_complete_all_mention")
    
    ex_cnt = 0
    top_hit = 0
    lines = []
    failed_preds = []
    # denormalize_failed = []

    gen_executable_cnt = 0
    final_executable_cnt = 0
    processed = 0
    for (pred,gen_feat) in tqdm(zip(predictions,gen_dataset), total=len(gen_dataset), desc=f'Evaluating {split}'):
        
        denormed_pred = []
        qid = gen_feat['ID']
        
        if not use_goldEnt:
            # entity label map, Dict[label:mid]
            if qid in candidate_entity_map:
                entity_label_map = {key:value['id'] for key,value in candidate_entity_map[qid].items()}
            else:
                entity_label_map = {}
            
            entity_mention_map = None
            type_label_map = train_type_map
        else:
            # goldEnt label map
            entity_label_map = gold_label_maps[qid]['entity_label_map']
            type_label_map = gold_label_maps[qid]['type_label_map']
            type_label_map = {l.lower():t for t,l in type_label_map.items()}
        
        if not use_goldRel:
            rel_label_map = train_relation_map # not use gold Relation, use relations from train
        else:
            # goldRel label map
            rel_label_map = gold_label_maps[qid]['rel_label_map']
            rel_label_map = {l.lower():r for r,l in rel_label_map.items()}

        # found_executable = False
        executable_index = None # 更进一步，记录最终执行了哪个 logical form

        # find the first executable lf
        for rank, p in enumerate(pred['predictions']):
            lf, answers = execute_normed_s_expr_from_label_maps(
                                                p, 
                                                entity_label_map, 
                                                entity_mention_map,
                                                type_label_map, 
                                                rel_label_map, 
                                                train_entity_map,
                                                surface_index)
            answers = list(answers)
            
            denormed_pred.append(lf)

            if rank == 0 and lf.lower() ==gen_feat['sexpr'].lower():
                ex_cnt +=1
            
            if answers:
                # found_executable = True
                executable_index = rank
                lines.append({
                    'qid': qid, 
                    'execute_index': executable_index,
                    'logical_form': lf, 
                    'answer':answers,
                    'gt_sexpr': gen_feat['sexpr'], 
                    'gt_normed_sexpr': pred['gen_label'],
                    'pred': pred, 
                    'denormed_pred':denormed_pred
                })
               
                if rank==0:
                    top_hit +=1
                break

        
        if executable_index is not None:
            # found executable query from generated model
            gen_executable_cnt +=1
        else:
            
            failed_preds.append({'qid':qid, 
                            'gt_sexpr': gen_feat['sexpr'], 
                            'gt_normed_sexpr': pred['gen_label'],
                            'pred': pred, 
                            'denormed_pred':denormed_pred})
        
            
        if executable_index is not None:
            final_executable_cnt+=1
        
        processed+=1
        if processed%100==0:
            print(f'Processed:{processed}, gen_executable_cnt:{gen_executable_cnt}')


    save_EARL_cache()
        
    print('STR Match', ex_cnt/ len(predictions))
    print('TOP 1 Executable', top_hit/ len(predictions))
    print('Gen Executable', gen_executable_cnt/ len(predictions))
    print('Final Executable', final_executable_cnt/ len(predictions))

    result_file = os.path.join(dirname,f'{filename}_gen_sexpr_results.json')
    dump_json(lines, result_file, indent=4)

    # write failed predictions
    dump_json(failed_preds,os.path.join(dirname,f'{filename}_gen_failed_results.json'),indent=4)
    dump_json({
        'STR Match': ex_cnt/ len(predictions),
        'TOP 1 Executable': top_hit/ len(predictions),
        'Gen Executable': gen_executable_cnt/ len(predictions),
        'Final Executable': final_executable_cnt/ len(predictions)
    }, os.path.join(dirname,f'{filename}_statistics.json'),indent=4)

    # evaluate
    args.pred_file = result_file
    if dataset == "CWQ":
        cwq_evaluate_valid_results(args)
    elif dataset == "WebQSP":
        webqsp_evaluate_valid_results(args)


if __name__=='__main__':
    """go down the top-k list to get the first executable locial form"""
    args = _parse_args()

    if args.server_ip and args.server_port:
        import ptvsd
        print("Waiting for debugger attach...",flush=True)
        ptvsd.enable_attach(address=(args.server_ip, args.server_port))
        ptvsd.wait_for_attach()
        
    
    if args.qid:
        pass
    else:
        aggressive_top_k_eval_new(args.split, args.pred_file, args.dataset)
        