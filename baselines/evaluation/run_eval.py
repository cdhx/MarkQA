import json 
import sys 
import os
from tqdm import tqdm
import re
from multiprocessing import Process

from eval_topk_prediction_final import aggressive_top_k_eval_mrak
from utils import readjson, savejson
from denormalization import *

def evaluate_expr_results_per_level(model, golden_file_dir, predict_file_dir, expr_type="qdt", output_file_name = ""):
    def compare_expr(expr1, expr2):
        expr1 = rename_regs(expr1.replace(" ","").lower())
        expr2 = rename_regs(expr2.replace(" ","").lower())
        return expr1 == expr2
    """分不同的composition level判断LF的match情况"""
    golden_data = readjson(golden_file_dir)
    all_gen_predictions = readjson(predict_file_dir)
    prediction_results = []
    err_log = []
    if model == "QDTQA":
        for k, v in all_gen_predictions.items():
            idx = k
            predictions = v
            prediction_results.append({'ID': idx,  "predictions": predictions})
    elif model == 'GMT' or model == 'T5':
        idx = 0
        for pred in all_gen_predictions:
            prediction_results.append({"ID": golden_data[idx]['ID'], 
                                        "predictions": pred['predictions']})
            idx += 1
    performance_per_level = {item['comp_level']:{} for item in golden_data}
    performance_compositional = {ty:{} for ty in ["composition", "no_composition"]}
    for level in performance_per_level:
        performance_per_level[level]['ex_cnt'] = 0
        performance_per_level[level]['contains_ex_cnt'] = 0
        performance_per_level[level]['cnt'] = 0
        performance_per_level[level]['real_cnt'] = 0
    for comp in performance_compositional:
        performance_compositional[comp]['ex_cnt'] = 0
        performance_compositional[comp]['contains_ex_cnt'] = 0
        performance_compositional[comp]['cnt'] = 0
        performance_compositional[comp]['real_cnt'] = 0
    for i, pred in tqdm(enumerate(prediction_results)):
        question_feat = golden_data[i]
        if expr_type == "PyQLQDT":
            gen_label = question_feat['normalized_sub_functions_qdt']
        elif expr_type == "PyQL":
            gen_label = question_feat['normalized_sub_functions']
        elif expr_type == "SPARQL":
            gen_label = question_feat['normalized_sparql']
        level = question_feat['comp_level']
        performance_per_level[level]['cnt'] += 1
        comp = ("composition" if "entities" in question_feat['ID'] else "no_composition")
        performance_compositional[comp]['cnt'] += 1
        if gen_label.lower() != 'null':
            performance_per_level[level]['real_cnt'] += 1
            performance_compositional[comp]['real_cnt'] += 1
        ex = False
        if compare_expr(pred['predictions'][0], gen_label):
            performance_compositional[comp]['ex_cnt'] += 1
            performance_per_level[level]['ex_cnt'] += 1
            ex = True
        contains_ex = False
        if any([compare_expr(x, gen_label) for x in pred['predictions']]):
            performance_per_level[level]['contains_ex_cnt'] += 1
            performance_compositional[comp]['contains_ex_cnt'] += 1
            contains_ex = True
        if not contains_ex and not ex:
            err_log.append({"preds": [rename_regs(p) for p in pred['predictions']], "golden":rename_regs(gen_label), "level":level})

    total_perf = {
        "cnt": sum([perf['cnt'] for perf in performance_per_level.values()]),
        "real_cnt": sum([perf['real_cnt'] for perf in performance_per_level.values()]),
        "ex_cnt": sum([perf['ex_cnt'] for perf in performance_per_level.values()]),
        "ex_rate": sum([perf['ex_cnt'] for perf in performance_per_level.values()])/ sum([perf['cnt'] for perf in performance_per_level.values()]),
        "real_ex_rate": sum([perf['ex_cnt'] for perf in performance_per_level.values()]) / sum([perf['real_cnt'] for perf in performance_per_level.values()]),
        "contains_ex_cnt": sum([perf['contains_ex_cnt'] for perf in performance_per_level.values()]), 
        "contains_ex_rate": sum([perf['contains_ex_cnt'] for perf in performance_per_level.values()])/ sum([perf['cnt'] for perf in performance_per_level.values()]),
        "real_contains_ex_rate": sum([perf['contains_ex_cnt'] for perf in performance_per_level.values()]) /  sum([perf['real_cnt'] for perf in performance_per_level.values()]),
    }
    performance_per_level["total"] = total_perf
    for comp, perf in performance_compositional.items():
        performance_per_level[comp] = perf
    for level, perf in performance_per_level.items():
        print(f"""Level:{level}
                    total:{perf['cnt']}, 
                    ex_cnt:{perf['ex_cnt']}, 
                    ex_rate:{perf['ex_cnt'] / perf['cnt']}, 
                    real_ex_rate:{perf['ex_cnt'] / perf['real_cnt']}, 
                    contains_ex_cnt:{perf['contains_ex_cnt']}, 
                    contains_ex_rate:{perf['contains_ex_cnt']/ perf['cnt']},
                    real_contains_ex_rate:{perf['contains_ex_cnt']/ perf['real_cnt']}
                    """)
        gen_statistics = {}
        for level, perf in performance_per_level.items():
            gen_statistics[level] = {
                'total': perf['cnt'],
                'exmatch_num': perf['ex_cnt'],
                'exmatch_rate': perf['ex_cnt'] / perf['cnt'],
                'real_exmatch_rate': perf['ex_cnt'] / perf['real_cnt'],
                'contains_ex_num': perf['contains_ex_cnt'],
                'contains_ex_rate': perf['contains_ex_cnt']/ perf['cnt'],
                'real_contains_ex_rate': perf['contains_ex_cnt']/ perf['real_cnt']
            }
        if output_file_name:
            if not os.path.isdir("../evaluation_results/logical_form/" +output_file_name):
                os.mkdir("../evaluation_results/logical_form/" +output_file_name)
            gen_statistics_file_path = os.path.join("../evaluation_results/logical_form",
                                                output_file_name,'gen_statistics_per_level')
            gen_fails_file_path = os.path.join("../evaluation_results/logical_form",
                                                output_file_name,'gen_fails')
            print(gen_statistics_file_path)
            savejson(gen_statistics_file_path, gen_statistics, indent=4)
            savejson(gen_fails_file_path, err_log, indent=4)

def rename_regs(expr):
    rename_list = {}
    regs = re.findall("x\d+", expr)
    for reg in regs:
        if reg not in rename_list:
            rename_list[reg] = "X"+str(len(rename_list))
    # print(rename_list)
    # print("before")
    # print(expr)
    for r in rename_list:
        expr = expr.replace(r, rename_list[r])
        # print(expr)
    expr = expr.replace("X", "x")
    # print("after")
    # print(expr)
    return expr


def start_query_process(model, golden_file_dir, predict_file_dir, predict_type, rel_linking_path = None, ent_linking_path = None, output_file = None):
    query_process = Process(target = evaluate_topk_predictions_exec_perf_per_level, args=(model, golden_file_dir, predict_file_dir, 
                                                                                 predict_type, rel_linking_path, ent_linking_path, output_file))
    query_process.start()

def evaluate_topk_predictions_exec_perf_per_level(model, golden_file_dir, predict_file_dir, predict_type, rel_linking_path = None, ent_linking_path = None, output_file = None):
    golden_data = readjson(golden_file_dir)
    all_gen_predictions = readjson(predict_file_dir)
    if rel_linking_path is not None:
        rel_linking_results = load_json(rel_linking_path)
    else:
        rel_linking_results = None
    if ent_linking_path is not None:
        ent_linking_results = load_json(ent_linking_path)
    else:
        ent_linking_results = None
    prediction_data = []
    if model == "QDTQA":
        for k, v in all_gen_predictions.items():
            idx = k
            predictions = v
            prediction_data.append({'ID': idx,  "predictions": predictions})
    elif model == 'GMT' or model == "T5":
        idx = 0
        for pred in all_gen_predictions:
            prediction_data.append({"ID": golden_data[idx]['ID'], 
                                        "predictions": pred['predictions']})
            idx += 1
    levels = set([item['comp_level'] for item in golden_data])
    label_entity_map_all = {}
    label_relation_map_all = {}
    for item in golden_data:        # prepare legal label->id dict golden
        for k, v in item['gold_entity_label_map'].items():
            label_entity_map_all[get_legal_label(v)] = k
        for k, v in item['gold_relation_label_map'].items():
            label_relation_map_all[get_legal_label(v)] = k
    if ent_linking_results is not None:
        for k, v in ent_linking_results.items():
            label_entity_map_all[get_legal_label(k)] = v
    if rel_linking_results is not None:
        for k, v in rel_linking_results.items():
            label_relation_map_all[get_legal_label(k)] = v
    eval_results = {"execute_status":{}, "official_lines":[], "lines":[], 'fails':{}}
    preds = []
    for level in levels:
        golden_data_this_level = [item for item in golden_data if item['comp_level'] == level]
        golden_ids_this_level = {item["ID"]:1 for item in golden_data_this_level}
        predictions_this_level = [item for item in prediction_data if item['ID'] in golden_ids_this_level]
        eval_result_this_level, pred_this_level = aggressive_top_k_eval_mrak(golden_data_this_level, predictions_this_level, 
                                                            predict_type, label_entity_map_all, label_relation_map_all)
        eval_results['execute_status'][level] = eval_result_this_level['execute_status']
        eval_results['fails'][level] = eval_result_this_level['fails']
        eval_results['lines'] += eval_result_this_level['lines']
        eval_results['official_lines'] += eval_result_this_level['official_lines']
        for p in pred_this_level:
            preds.append({'ID':p['qid'], 'split_type':level, 'composition':(True if "entities" in p['qid'] else False), "answer_acc": p['answer_acc']})
    # lf_status ={
    # 'top_hit': top_hit,
    # 'gen_executable_cnt': gen_executable_cnt,
    # 'final_executable_cnt': final_executable_cnt,
    # 'total_cnt': len(predictions)
    # 'TOP 1 Executable': top_hit/ len(predictions),
    # 'Gen Executable': gen_executable_cnt/ len(predictions),
    # 'Final Executable': final_executable_cnt/ len(predictions)
    # }
    # get perf on all levels
    top_hit = sum([static['top_hit'] for static in eval_results['execute_status'].values()])
    top_grammar_correct = sum([static['top_grammar_correct'] for static in eval_results['execute_status'].values()])
    total_cnt = sum([static['total_cnt'] for static in eval_results['execute_status'].values()])
    gen_executable_cnt = sum([static['gen_executable_cnt'] for static in eval_results['execute_status'].values()])
    final_executable_cnt = sum([static['final_executable_cnt'] for static in eval_results['execute_status'].values()])
    has_correct_grammar_cnt = sum([static['gen_grammar_correct_cnt'] for static in eval_results['execute_status'].values()])
    acc_num = sum([static['acc_num'] for static in eval_results['execute_status'].values()])
    eval_results['execute_status']['Total'] = {
    'top_hit': top_hit,
    'top_grammar_correct': top_grammar_correct, 
    'gen_executable_cnt': gen_executable_cnt,
    'final_executable_cnt': final_executable_cnt,
    'total_cnt': total_cnt,
    'TOP 1 Executable': top_hit/ total_cnt,
    'TOP 1 Grammar Correct Rate': top_grammar_correct/ total_cnt,
    'Gen Executable': gen_executable_cnt/ total_cnt,
    'Final Executable': final_executable_cnt/ total_cnt,
    'Final Grammar Correct Rate': has_correct_grammar_cnt/ total_cnt,
    'Accuracy Rate': acc_num / total_cnt,
    'composition question acc rate': len([p for p in preds if p['composition'] and p['answer_acc']]) / len([c for c in golden_data if "entities" in c['ID']]),
    'no composition question acc rate': len([p for p in preds if not p['composition'] and p['answer_acc']]) / len([c for c in golden_data if not "entities" in c['ID']])
    }
    #增加一项复合与不复合的比较
    print(eval_results['execute_status'])
    if output_file is not None:
        output_dir = "../evaluation_results/"+ output_file
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        savejson(output_dir + "/" + "acc_lines", preds)
        savejson(output_dir + "/" + "lines", eval_results['lines'])
        savejson(output_dir + "/" + "official_lines", eval_results['official_lines'])
        savejson(output_dir + "/" + "execute_status", eval_results['execute_status'])
        savejson(output_dir + "/" + "fails", eval_results['fails'])
        return 0 

if __name__ == "__main__":


    start_query_process("GMT", "yourpath/mark_dev_linked.json",
                                "yourpath/beam_25_test_4_top_k_predictions.json",
                                "PyQL",
                                output_file="GMT_test")


