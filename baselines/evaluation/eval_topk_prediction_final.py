#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import argparse
from tqdm import tqdm
import re
from denormalization import *
from SPARQL_utils import WDExecutor

from PyQL_parser import generate_sparql_by_functions


#wikidata_sparql_executor = ODBC_WDexecutor()
wikidata_sparql_executor = WDExecutor(endpoint = "local")

def is_number(t):
    t = t.replace(" , ",".")
    t = t.replace(", ",".")
    t = t.replace(" ,",".")
    try:
        float(t)
        return True
    except ValueError:
        pass
    try:
        import unicodedata  # handle ascii
        unicodedata.numeric(t)  # string of number --> float
        return True
    except (TypeError, ValueError):
        pass
    return False


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', required=True, help='split to operate on, can be `test`, `dev` and `train`')
    parser.add_argument('--pred_file', default=None, help='topk prediction file')
    parser.add_argument('--server_ip', default=None, help='server ip for debugging')
    parser.add_argument('--server_port', default=None, help='server port for debugging')
    parser.add_argument('--qid', default=None,type=str, help='single qid for debug, None by default' )
    parser.add_argument('--pred_type',default=None,type=str,)
    parser.add_argument('--test_batch_size', default=2)
    parser.add_argument('--dataset', required=True, default=None, type=str, help='dataset used')
    parser.add_argument("--datasets_folder", default="data/CWQ/generation/merged", type = str, help='folder where datasets locate')
    parser.add_argument('--beam_size', default=50, type=int)

    args = parser.parse_args()

    print(f'split:{args.split}, topk_file:{args.pred_file}')
    return args




# 5.11 bao
def mrak_evaluate_valid_result(pred_data, golden_data):

    def is_numeric(s):
        try:
            int(s)  # 尝试将字符串转换为整数
            return True
        except ValueError:
            try:
                float(s)  # 尝试将字符串转换为浮点数
                return True
            except ValueError:
                return False
    """Since each question has a single answer, we only calculate ACC"""
    # origin dataset
    # dataset_data = load_json(f'data/CWQ/generation/merged/mrak_0606_{args.split}_normed.json')
    dataset_dict = {x["ID"]:x for x in golden_data}
    acc_num = 0
    pred_dict = {}
    acc_qid_list = [] # Pred Answer ACC
    for pred in pred_data:
        qid = pred['qid']
        pred_answer = set(pred['answer'])
        pred_dict[qid]=pred_answer
    for qid,example in tqdm(dataset_dict.items()):
        if 'answer' in example:
            gt_answer = set(example['answer'])
        pred_answer = set(pred_dict.get(qid,{}))
        epsilon = 1e-5
        gt_answer = list(gt_answer)
        gt_answer.sort()
        pred_answer = list(pred_answer)
        pred_answer.sort()
        correct = True
        if len(pred_answer) != len(gt_answer):
            correct = False
        else:
            for idx, element in enumerate(gt_answer):
                if is_numeric(element) and is_numeric(pred_answer[idx]):
                    dif = float(element) - float(pred_answer[idx]) 
                    if dif > epsilon or dif < -epsilon:
                        correct = False 
                        break
                else:
                    if element != pred_answer[idx]:
                        correct = False
                        break
        if correct:
            acc_num+=1
            acc_qid_list.append(qid)
        else:
            print("golden",gt_answer)
            print("pred",pred_answer)
            print("error", qid)

    res = {'acc':acc_num/len(golden_data), "acc_num": acc_num}
    res_pred = []
    for pred in pred_data:
        qid = pred['qid']
        if qid in acc_qid_list:
            pred['answer_acc'] = True
        else:
            pred['answer_acc'] = False
        res_pred.append({'qid':qid, "answer":pred_answer, "answer_acc":pred['answer_acc'], "executable":pred["executable"], "grammar_right":pred["grammar_correct"]})
    #save_json(golden_answers, "golden_answers")
    return res, res_pred



def get_denormed_sparql_for_grammar_check(denormed_sparql):
    res = denormed_sparql    
    wrong_ents = re.findall("wd\:\[.*?\]", res)
    wrong_rels = re.findall("p\:\[.*?\]", res) + re.findall("wdt\:\[.*?\]", res) + re.findall("ps\:\[.*?\]", res) + \
                 re.findall("pq\:\[.*?\]", res) + re.findall("psv\:\[.*?\]", res) + re.findall("pqv\:\[.*?\]", res)
    for item in wrong_ents:
        res = res.replace(item, "wd:Q148")
    for item in wrong_rels:
        res = res.replace(item, item.split(":")[0]+":"+"P17")
    return res

def get_denormed_subf_for_grammar_check(denormed_subf):
    res = denormed_subf
    wrong_brackets = re.findall("\[[^\'\"]*?\]", res)
    for bracket in wrong_brackets:
        idx1 = denormed_subf.index(bracket)+1
        idx2 = idx1 + len(wrong_brackets) -1
        while(denormed_subf[idx1] != "," and denormed_subf[idx1] != "("):
            idx1 -= 1
        while(denormed_subf[idx2] != "," and denormed_subf[idx2] != ")"):
            idx2 += 1
        if denormed_subf[idx1] == "," and denormed_subf[idx1] == ",":
            #property
            res = res.replace(bracket, "\'P17\'")
        else:
            res = res.replace(bracket, "\'Q148\'")
            #entity
    return res


def execute_normed_expressions(normed_expr, expr_type, label_entity_map, label_relation_map, executor):
    """execute normalized expressions."""
    #lf_executable:转化为sparql执行是否不报错
    #lf_grammarly_right:能否转为结构正确的sparql，即考虑预测错label情况
    lf_executable = True
    lf_grammarly_right = True
    assert(expr_type == "PyQLQDT" or expr_type == "PyQL" or expr_type == "SPARQL")
    #先检查：是否能够查出结果
    denormalized_expr = None
    denotation = []
    try:
        if expr_type == "PyQLQDT":
            denormalized_qdt = denormalize_qdt(normed_expr, label_entity_map, label_relation_map)
            denormalized_subf = None
            denormalized_subf = qdt_to_sub_fun(denormalized_qdt)
            last_query = chr(max(ord(f[0]) for f in denormalized_subf.split()))  #获取最大的子查询号
            #denormalized_subf = denormalized_subf.replace(" =SPARQL_GEN()", "=SPARQL_GEN()")
            #denormalized_subf = denormalized_subf.replace(" =PyQL()", "=PyQL()")
            denormalized_subf = "\n".join(denormalized_subf.split())    #用\n链接
            sparql_query = generate_sparql_by_functions(denormalized_subf)
            denormalized_expr = denormalized_qdt

        elif expr_type == "PyQL": 
            denormalized_subf = denormalize_sub_functions(normed_expr, label_entity_map, label_relation_map)
            last_query = chr(max(ord(f[0]) for f in denormalized_subf.split()))  #获取最大的子查询号
            if ("print") not in denormalized_subf.split()[-1]:
                denormalized_subf += " print("+last_query+".sparql)"    #手动添加print(x.sparql)
            denormalized_subf = denormalized_subf.replace(" =PyQL()", "=PyQL()")
            denormalized_subf = "\n".join(denormalized_subf.split())    #用\n链接
            sparql_query = generate_sparql_by_functions(denormalized_subf)
            denormalized_expr = denormalized_subf

        elif expr_type == "SPARQL":
            denormalized_sparql = denormalize_sparql(normed_expr, label_entity_map, label_relation_map)
            sparql_query = denormalized_sparql
            denormalized_expr = denormalized_sparql
    except Exception as e:
        sparql_query = "null"
        
    if sparql_query != 'null':
        try:
            #denotation, error = wikidata_sparql_executor.query(sparql=sparql_query)['result'], wikidata_sparql_executor.query(sparql=sparql_query)['error']
            denotation = wikidata_sparql_executor.query_db(sparql_query)
            if denotation is None:
                denotation = ["NOANSWER"]
            else:
                denotation = [str(item) for item in denotation]   #似乎有的返回值是int或float类型
        except Exception as e:
            e = str(e)
            if "memory" in e.lower() or "time" in e.lower():    #认为是可执行的
                denotation = ["ERROR: OUTOFMEMORY!!!"]
                lf_executable = True
            elif "time" in e.lower():
                denotation = ["ERROR: TIMEOUT!!!"]
                lf_executable = True
            else:
                #print(e)
                denotation = ["ERROR: OTHERERROR!!!"]
                lf_executable = False
    else:
        denotation = ["ERROR:NO EXECUTABLE SPARQL"]
        lf_executable = False
    if lf_executable:   #如果能够执行，那么一定是语法正确的
        lf_grammarly_right = True
    else:       #尝试放松一些，看其是否只是因为预测错label而无法执行
        if expr_type == "PyQLQDT":
            if denormalized_subf is None:
                lf_grammarly_right = False  #不能转成PyQL必然是语法错误
            else:
                try:
                    loose_subf = get_denormed_subf_for_grammar_check(denormalized_subf)
                    sparql = generate_sparql_by_functions(loose_subf)
                except Exception as e:
                    lf_grammarly_right = False
        elif expr_type == "PyQL":
            try:
                loose_subf = get_denormed_subf_for_grammar_check(denormalized_subf)
                _ = generate_sparql_by_functions(loose_subf)
            except Exception as e:
                lf_grammarly_right = False
        else:
            try:
                loose_sparql = get_denormed_sparql_for_grammar_check(denormalized_sparql)
                _ = executor.query_db(loose_sparql)

            except Exception as e:
                e = str(e).lower()
                if "badly formed" in e:
                    lf_grammarly_right = False
                else:
                    lf_grammarly_right = True
    return denormalized_expr, denotation, sparql_query, lf_executable, lf_grammarly_right



def aggressive_top_k_eval_mrak(golden_data, predictions, predict_type, label_entity_map, label_relation_map):
    
    wikidata_sparql_executor = WDExecutor(endpoint="local")
    assert(predict_type == "PyQLQDT" or predict_type == "SPARQL" or predict_type == "PyQL")

    # use_goldEnt = True # whether to use gold Entity for denormalization
    # use_goldRel = True
    # print('use_goldEnt: {}'.format(use_goldEnt))
    # print('use_goldRel: {}'.format(use_goldRel))
    # if not use_goldEnt:
    #     id_ent_map_all = load_json(ent_linking_file_path)
    #     label_entity_map = {v:k for k, v in id_ent_map_all.items()}
    # else:
    #     label_entity_map = {}
    #     for gt in golden_data:
    #         for k, v in gt['gold_label_entity_map'].items():
    #             label_entity_map[get_legal_label(k)] = v
    # if not use_goldRel:
    #     id_rel_map_all = load_json(rel_linking_file_path)
    #     label_relation_map = {v:k for k, v in id_rel_map_all.items()}
    # else:
    #     label_relation_map = {}
    #     for gt in golden_data:
    #         for k, v in gt['gold_label_relation_map'].items():
    #             label_relation_map[get_legal_label(k)] = v
    ex_cnt = 0
    top_hit = 0
    top_grammar_correct = 0
    lines = []
    official_lines = []
    failed_preds = []

    gen_executable_cnt = 0
    final_executable_cnt = 0
    gen_grammar_correct_cnt = 0
    processed = 0
    question_idx = 0    
    predict_answers = []
    for (pred,gen_feat) in tqdm(zip(predictions, golden_data), total=len(golden_data), desc='Evaluating'):
        if question_idx % 50 == 0:
            print("Progress", question_idx, "/", len(predictions))
        #print("question", question_idx)
        #print(gen_feat['ID'])
        denormed_pred = []
        qid = gen_feat['ID']
        # if use_goldEnt:
        #     label_entity_map = {get_legal_label(k):v for k,v in gen_feat['gold_label_entity_map'].items()}
        # else: 
        #     label_entity_map = ent_id_map_all
        # if use_goldRel:
        #     label_relation_map = {get_legal_label(k):v for k,v in gen_feat['gold_label_relation_map'].items()}
        # else:
        #     label_relation_map = rel_id_map_all

        executable_index = None # index of LF being finally executed
        grammarly_right_index = None # index of LF having correct grammar
        if predict_type == "PyQLQDT":
            golden_expr = gen_feat['normalized_sub_functions_qdt']
        elif predict_type == "PyQL":
            golden_expr = gen_feat['normalized_sub_functions']
        else:
            golden_expr = gen_feat['normalized_sparql']
        # find the first executable lf
        for rank, p in enumerate(pred['predictions']):
            lf, answers, sparql, lf_executable, lf_grammarly_right = execute_normed_expressions(p, predict_type, label_entity_map, label_relation_map, wikidata_sparql_executor)
            answers = [ans for ans in list(answers)]
            denormed_pred.append(lf)
            # if lf.lower() == golden_expr and not answers:
            #     print("[WARN]", question_idx,"个问题和golden gen label一致，但没有结果")
            if lf_grammarly_right and grammarly_right_index is None:
                grammarly_right_index = rank #第一个语法正确的LF
                if rank == 0:
                    top_grammar_correct += 1
            if lf_executable:
                if answers:
                    executable_index = rank
                    lines.append({
                        'qid': qid, 
                        'execute_index': executable_index,
                        'logical_form': lf, 
                        'answer':answers,
                        'gt_normed_sexpr': golden_expr,
                        'pred': pred, 
                        'denormed_pred':denormed_pred,
                        'grammar_correct': True
                    })
                    official_lines.append({
                        "QuestionId": qid,
                        "Answers": answers
                    }) 
                    if rank==0:
                        top_hit +=1

                    predict_answers.append({'qid': qid, "answer": answers, "executable": True, "grammar_correct": True})
                    break
        if executable_index is not None:
            # found executable query from generated model
            gen_executable_cnt +=1
        else:
            failed_preds.append({'qid':qid, 
                            'gt_normed_sexpr': golden_expr,
                            'pred': pred, 
                            'denormed_pred':denormed_pred,
                            'grammar_correct': (True if grammarly_right_index is not None else False)})
            predict_answers.append({'qid': qid, "answer": ["UNEXECUTABLE"], "executable": False, 
                                    "grammar_correct": (True if grammarly_right_index is not None else False)})
        if executable_index is not None:
            final_executable_cnt+=1
        if grammarly_right_index is not None:
            gen_grammar_correct_cnt += 1
        processed+=1
        question_idx += 1
    lf_status ={
    'top_hit': top_hit,
    'top_grammar_correct': top_grammar_correct,
    'gen_executable_cnt': gen_executable_cnt,
    'gen_grammar_correct_cnt': gen_grammar_correct_cnt,
    'final_executable_cnt': final_executable_cnt,
    'total_cnt': len(predictions),
    'TOP 1 Executable': top_hit/ len(predictions),
    'Gen Executable': gen_executable_cnt/ len(predictions),
    'Gen Grammar Correct rate': gen_grammar_correct_cnt / len(predictions),
    'Final Executable': final_executable_cnt/ len(predictions)
    }

    # evaluate
    exec_res, pred = mrak_evaluate_valid_result(predict_answers, golden_data)
    lf_status.update(exec_res)
    return {"execute_status": lf_status, "lines":lines, "official_lines": official_lines, "fails":failed_preds}, pred
