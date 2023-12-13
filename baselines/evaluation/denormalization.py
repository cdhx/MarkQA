import re
import sys

from utils import load_json, save_json

from PyQL_parser import generate_sparql_by_functions

PYQL_VERSION = "OFFICIAL"

big_id_rel_table = load_json("../data/wikidata_properties_all.json")
big_id_ent_table = {}

def get_legal_label(label):
    res_label = ""
    """获取合法的可用于sparql中的label"""
    for i in range(0, len(label)):
        if label[i].isdigit() or label[i].isalpha():
            res_label += label[i].lower()
    return res_label


def denormalize_sparql(origin_sparql, gold_label_entity_map, gold_label_relation_map):
    modi_sparql = origin_sparql
    special_token_map = {
        "[ entity ]":  " wd:",
        "[ simple relation ]": " wdt:",
        "[ property ]": " p:",
        "[ qualifier ]": " pq:",
        "[ value ]": " ps:",
        "[ statement ]": " psv:",
        "[ qualifier statement ]": " pqv:",
        "[amount]": " wikibase:quantityAmount ",
        "[type]": " wdt:P31/wdt:P279* ",
    }

    brackets = re.findall('\[.*?\]', modi_sparql)
    idx = 0
    for b in brackets:
        if b in special_token_map:
            continue
        normalized_b = b
        normalized_b.strip("[").strip("]").strip()
        #删掉所有的非空格与下划线字符
        normalized_b = get_legal_label(normalized_b.replace(" ", ""))
        if normalized_b in gold_label_entity_map and normalized_b in gold_label_relation_map:
            if "[ entity ]" in brackets[idx-1]:
                modi_sparql = modi_sparql.replace(b, gold_label_entity_map[normalized_b])
            else:
                modi_sparql = modi_sparql.replace(b, gold_label_relation_map[normalized_b])
        elif normalized_b in gold_label_entity_map:
            modi_sparql = modi_sparql.replace(b, gold_label_entity_map[normalized_b])
            continue
        elif normalized_b in gold_label_relation_map:
            modi_sparql = modi_sparql.replace(b, gold_label_relation_map[normalized_b])
            continue
        idx += 1
    modi_sparql = modi_sparql.replace("?x", " ?x").replace("][", "] [").replace("{", " { ").replace("}", " } ")
    #
    for token in special_token_map:
        modi_sparql = modi_sparql.replace(token, " "+special_token_map[token])
    if "[rel]" in brackets:
        relations = re.findall('\[rel\] P[0-9]*', modi_sparql)
        for rel in relations:
            property = rel.split()[-1]
            modi_sparql = modi_sparql.replace(rel, "p:" + property + "/psv:" + property)

    if "[rel]" in modi_sparql:
        relation = re.findall('\[rel\] P[0-9]*', modi_sparql)
        if len(relation) == 0:
            modi_sparql = modi_sparql.replace("[rel]", "")
    modi_sparql = modi_sparql.replace("< =", "<=").replace("> =", ">=").replace("! =", "!=").replace("TRUE", "\"TRUE\"").replace("FALSE", "\"FALSE\"")
    modi_sparql = modi_sparql.replace(": ", ":").replace("  ", " ").strip()
    return modi_sparql


def denormalize_sub_functions(origin_sub_function, gold_label_entity_map, gold_label_relation_map):
    modi_sub_function = origin_sub_function
    modi_sub_function = modi_sub_function.replace(")", " ) ")
    modi_sub_function = modi_sub_function.replace("?x", " ?x").replace("][", "] [")
    brackets = re.findall('\[.*?\]', modi_sub_function)

    for b in brackets:
        if b == "[SUBQL]" or b == "[INQL]" or b == "[SUBQR]" or b == "[INQR]":
            continue
        normalized_b = b
        normalized_b.strip("[").strip("]").strip()
        #删掉所有的非空格与下划线字符
        normalized_b = get_legal_label(normalized_b.replace(" ", ""))
        if normalized_b in gold_label_entity_map and normalized_b in gold_label_relation_map:
            index1 = modi_sub_function.find(b) + len(b)
            index2 = modi_sub_function.find(b)
            while modi_sub_function[index1] != ")" and modi_sub_function[index1] != ",":     #暴力判断是否是谓语
                index1 += 1
            while modi_sub_function[index2] != "(" and modi_sub_function[index2] != ",":     #暴力判断是否是谓语
                index2 -= 1
            if modi_sub_function[index1] == "," and modi_sub_function[index2] == ",":
                modi_sub_function = modi_sub_function.replace(b, " "+gold_label_relation_map[normalized_b]+ " ")
            else:
                modi_sub_function = modi_sub_function.replace(b, " "+gold_label_entity_map[normalized_b]+ " ")
        if normalized_b in gold_label_entity_map:
            modi_sub_function = modi_sub_function.replace(b, " "+gold_label_entity_map[normalized_b]+ " ")
            continue
        if normalized_b in gold_label_relation_map:
            modi_sub_function = modi_sub_function.replace(b, " "+gold_label_relation_map[normalized_b]+ " ")
            continue
    modi_sub_function = modi_sub_function.replace(" $", "<$").replace("<$", "[").replace("$>", "]")    #也可以接受老版本的
    modi_sub_function = modi_sub_function.replace("{", "[").replace("}", "]")    #换回方括号
    modi_sub_function = modi_sub_function.replace(": ", ":").replace(" (", "(").replace(" = ", "=").replace(",", " ,").replace("  ", " ").replace("! =", " != ").replace(",=", ", = ")
    modi_sub_function = modi_sub_function.replace("< =", "<=").replace("> =", ">=")
    if PYQL_VERSION == "OFFICIAL":
        modi_sub_function = modi_sub_function.replace(" =PyQL", "=PyQL")
    else:
        modi_sub_function = modi_sub_function.replace(" =SPARQL_GEN", "=SPARQL_GEN")
    vars = re.findall(' [PQx<=>].*? ', modi_sub_function) + re.findall(' != ', modi_sub_function)
    vars = set(vars)
    for v in vars:
        modi_sub_function = modi_sub_function.replace(v, "\'" + v.strip() + "\'")

    modi_sub_function = modi_sub_function.replace("( )", "()").replace("( \'", "('").replace(" , ", ",").replace(" ,", ",").replace(
        ", ", ",").replace(" )", ")").replace("( ", "(").replace('\' )', "\')").strip()
    modi_sub_function = modi_sub_function.replace("wdt", "'wdt'")
    return modi_sub_function


def denormalize_qdt(origin_qdt, gold_label_entity_map, gold_label_relation_map):
    # print("Denormalization------------------------")
    # print(origin_qdt)
    # print(gold_label_entity_map)
    # print(gold_label_relation_map)
    modi_qdt = origin_qdt.replace(")", " ) ")
    modi_qdt = modi_qdt.replace("?x", " ?x").replace("][", "] [")
    brackets = re.findall('\[.*?\]', modi_qdt)

    for b in brackets:
        if b == "[SUBQL]" or b == "[INQL]" or b == "[SUBQR]" or b == "[INQR]":
            continue
        normalized_b = b
        normalized_b.strip("[").strip("]").strip()
        #删掉所有的非空格与下划线字符
        normalized_b = get_legal_label(normalized_b.replace(" ", ""))
        if normalized_b in gold_label_entity_map and normalized_b in gold_label_relation_map:       #如果有同名的
            index1 = modi_qdt.find(b) + len(b)-1
            index2 = modi_qdt.find(b) + 1 
            while modi_qdt[index1] != ")" and modi_qdt[index1] != ",":     #暴力判断是否是谓语
                index1 += 1
            while modi_qdt[index2] != "(" and modi_qdt[index2] != ",":     #暴力判断是否是谓语
                index2 -= 1
            if modi_qdt[index1] == "," and modi_qdt[index2] == ",":
                modi_qdt = modi_qdt.replace(b, gold_label_relation_map[normalized_b])
            else:
                modi_qdt = modi_qdt.replace(b, gold_label_entity_map[normalized_b])
        elif normalized_b in gold_label_entity_map:
            modi_qdt = modi_qdt.replace(b, gold_label_entity_map[normalized_b])
            continue
        elif normalized_b in gold_label_relation_map:
            modi_qdt = modi_qdt.replace(b, gold_label_relation_map[normalized_b])
            continue
    modi_qdt = modi_qdt.replace(")add_", ") add_")
    modi_qdt = modi_qdt.replace("{", "[").replace("}", "]")    #换回方括号
    modi_qdt = modi_qdt.replace(" $", "<$").replace("<$", "[").replace("$>", "]")    #也可以接受老版本的
    modi_qdt = modi_qdt.replace(": ", ":").replace(" (", "(").replace(" )", ")").replace(" = ", "=").replace(",", " ,").replace("  ", " ").replace("! =", " != ").replace(",=", ", = ")
    modi_qdt = modi_qdt.replace("< =", "<=").replace("> =", ">=")
    vars = re.findall(' [PQx<=>].*? ', modi_qdt) + re.findall(' != ', modi_qdt) + re.findall(' = ', modi_qdt)
    vars = set(vars)
    for v in vars:
        modi_qdt = modi_qdt.replace(v, "\'" + v.strip() + "\'")
    modi_qdt = modi_qdt.replace("( )", "()").replace("( \'", "('").replace(" , ", ",").replace(" ,", ",").replace(
        ", ", ",").replace(" )", ")").replace("( ", "(").replace('\' )', "\')").replace("[SUBQL]", " [SUBQL] ").replace("[SUBQR]", " [SUBQR] ").strip()
    # print("success")
    # print(modi_qdt)
    # print("------")
    return modi_qdt


def replace_ent_rel(expr_type, origin_sparql, gold_entity_map, gold_relation_map):
    spql_copy_copy = origin_sparql
    if gold_entity_map is None:
        gold_entity_map = {}
    if gold_relation_map is None:
        gold_relation_map = {}

    # [rel] as "p: /psv: "
    relation_prefix = re.findall(r'p:.*/psv:', spql_copy_copy)

    for rel_prefix in relation_prefix:
        if rel_prefix in spql_copy_copy:
            spql_copy_copy = spql_copy_copy.replace(rel_prefix, "[rel] ")

    # [type] as "wdt:P31/wdt:P279*"
    if "wdt:P31/wdt:P279*" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("wdt:P31/wdt:P279*", "[type]")

    # [amount] as "wikibase:quantityAmount"
    if "wikibase:quantityAmount" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("wikibase:quantityAmount", "[amount]")

    # [ent] as "wd: "
    if "wd:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("wd:", "[ entity ] ")

    # [srel] as "wdt:"
    if "wdt:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("wdt:", "[ simple relation ] ")

    # [property] as "p:"
    #需要区分 p: 与 p://
    r = re.findall("p:P\d+", spql_copy_copy)
    for item in r:
        spql_copy_copy = spql_copy_copy.replace(item, "[ property ] "+item[2:])

    # [qualifier] as "pq:"
    if "pq:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("pq:", "[ qualifier ] ")

    # [value] as "ps:"
    if "ps:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("ps:", "[ value ] ")

    # [statement] as "psv:"
    if "psv:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("psv:", "[ statement ] ")

    # [qstatement] as "pqv:"
    if "pqv:" in spql_copy_copy:
        spql_copy_copy = spql_copy_copy.replace("pqv:", "[ qualifier statement ] ")
    for ents in gold_entity_map.keys():
        if ents in spql_copy_copy:
            if expr_type == "sparql":
                spql_copy_copy = spql_copy_copy.replace(ents.strip(), "[ " + gold_entity_map[ents] + " ]")
            else:
                spql_copy_copy = spql_copy_copy.replace("\'"+ents.strip()+'\'', "[ " + gold_entity_map[ents] + " ]")
                spql_copy_copy = spql_copy_copy.replace("\""+ents.strip()+'\"', "[ " + gold_entity_map[ents] + " ]")
    for rels in gold_relation_map.keys():
        if rels in spql_copy_copy:
            spql_copy_copy = spql_copy_copy.replace("\'"+rels.strip()+'\'', "[ " + gold_relation_map[rels] + " ]")
            spql_copy_copy = spql_copy_copy.replace("\""+rels.strip()+'\"', "[ " + gold_relation_map[rels] + " ]")
    remained_rels = re.findall("P\d+", spql_copy_copy) + re.findall("P\d+", spql_copy_copy)
    for r in remained_rels:
        pid = r.split(":")[-1].strip()
        if pid in big_id_rel_table:
                spql_copy_copy = spql_copy_copy.replace(r,  "[ "+big_id_rel_table[pid]['label'].replace(" ","_") +" ]")
    return spql_copy_copy


def replace_vars_sparql(origin_sparql):
    # ?value_a, ?value_b....
    if "BIND" in origin_sparql:
        pass
    var_list_in_sparql = re.findall(r'\?.*[ \.\)]', origin_sparql)
    var_set_sparql = set()
    for lines in var_list_in_sparql:
        vars = lines.split(" ")
        for v in vars:
            # 如果后面是AS，那就不用删去)
            if v.endswith(")+1"):
                origin_sparql = origin_sparql.replace(v, v[0:-3] + " " + ")+1")
            v = v.strip('.').strip('(').strip(')').strip().strip(",")
            if v.startswith('?'):
                var_set_sparql.add(v)
    var_set_sparql = list(var_set_sparql)
    var_set_sparql.sort(key=lambda i: len(i), reverse=True)
    spql_copy = origin_sparql
    var_cnt = 0
    for v in var_set_sparql:
        if v in spql_copy:
            if v.endswith(",") or v.endswith(")") or v.endswith("}"):
                last_sym = v[-1]
                spql_copy = spql_copy.replace(v, " ?" + "x" + str(var_cnt)+" "+last_sym)
            else:
                spql_copy = spql_copy.replace(v, " ?" + "x" + str(var_cnt)+" ")
            var_cnt += 1

    spql_copy = spql_copy.replace("\n\t", " ").replace("\n", " ").replace("\t", " ").replace("  ", " ")

    return spql_copy

def preprocess_subquestion(subquestion):    #为了防止有的subquestion开头没有SPARQL GEN;以及有的subquestion顺序错位
    # if "SPARQL_GEN()" not in subquestion.split("\n")[0]:    #手动添加sparql gen
    #     subquestion = "a=SPARQL_GEN()\n" + subquestion
    subquery_functions = {}
    #print(subquestion.split("\n"))
    for func in subquestion.split("\n"):
        if func.isspace() or func == "":
            continue
        subquery = func[0]
        if subquery not in subquery_functions:  #记录其在子查询内的相对位置
            subquery_functions[subquery] = [func]
        else:
            subquery_functions[subquery].append(func)
    reformated_subquestion = ""
    for subquery, func in subquery_functions.items():           #由于dict遍历是按照key字典序来的，所以我们的abc写法没有问题
        reformated_subquestion += "\n".join(func) + "\n"
    reformated_subquestion = reformated_subquestion.strip("\n").strip()
    return reformated_subquestion

def replace_vars_sub_function(origin_sparql):
    origin_sparql = origin_sparql.replace("\"", "\'")
    # ?value_a, ?value_b....
    var_list_in_sparql = [var for var in re.findall("\'[a-zA-Z0-9_]*\'", origin_sparql) if not var[1:-1].isnumeric() and var != "'wdt'"]
    var_set_sparql = set()
    for lines in var_list_in_sparql:
        word = lines.strip("\'")
        if (word[0] == 'Q' and word[1:].isnumeric())or (word[0] == 'P' and word[1:].isnumeric()):        #10.16 bug：考虑Phillepines
            continue
        var_set_sparql.add(lines)

    var_set_sparql = list(var_set_sparql)
    var_set_sparql.sort(key=lambda i: len(i), reverse=True)
    label_var_map = dict()
    spql_copy = origin_sparql
    var_cnt = 0
    for v in var_set_sparql:
        if v in spql_copy:
            spql_copy = spql_copy.replace(v, "x" + str(var_cnt))
            label_var_map[v] = "x" + str(var_cnt)
            var_cnt += 1

    spql_copy = spql_copy.replace("\n\t", " ").replace("\n", " ").replace("\t", " ").replace("  ", " ")

    return spql_copy, label_var_map


def replace_vars_qdt(origin_sparql, label_var_map):
    origin_sparql = origin_sparql.replace("\"", "\'")
    spql_copy = origin_sparql
    for v in label_var_map.keys():
        if v in spql_copy:
            spql_copy = spql_copy.replace(v, label_var_map[v])

    spql_copy = spql_copy.replace("\n\t", " ").replace("\n", " ").replace("\t", " ").replace("  ", " ")

    return spql_copy


def replace_vars_and_ent(structure, entity_map, relation_map, structure_type, label_var_map = None):      
    '''#将子函数、sparql和qdt的替换结合到一起。返回值包含替换后的structure，如果是sub function，返回值会包含label_var_map.
        如果类型是qdt,会要求额外输入label_var_map作为参数。
    ''' 
    assert(structure_type == "sparql" or structure_type == "sub_function" or structure_type == "qdt")
    if structure_type == "sparql":
        new_sparql = replace_vars_sparql(structure)
        new_sparql = replace_ent_rel(structure_type, new_sparql, entity_map, relation_map)
        formated_structure = new_sparql
    elif structure_type == "sub_function":
        new_sub_functions, label_var_map = replace_vars_sub_function(structure)
        new_sub_functions = replace_ent_rel(structure_type, new_sub_functions, entity_map, relation_map)
        formated_structure = new_sub_functions
    else:
        new_qdt = replace_vars_qdt(structure, label_var_map)
        new_qdt = replace_ent_rel(structure_type, new_qdt, entity_map, relation_map)
        formated_structure = new_qdt
    temp = {}
    cnt = 0 #将entity与relation的内容Mask，之后再转换回来
    entity_map_list = list(entity_map.values())
    entity_map_list.sort(key = lambda s: len(s), reverse= True)
    relation_map_list = list(relation_map.values())
    relation_map_list.sort(key = lambda s: len(s), reverse= True)
    for item in entity_map_list:
        formated_structure = formated_structure.replace(item, "TEMP"+str(cnt))
        temp[item] = "TEMP"+str(cnt)
        cnt+=1
    # for item in relation_map_list:
    #     formated_structure = formated_structure.replace(item, "TEMP"+str(cnt))
    #     temp[item] = "TEMP"+str(cnt)
    #     cnt+=1
    formated_structure = formated_structure.replace("\n", " ").replace("\'", "").replace("\"", "").replace(",",
                                            " , ").replace("(", " ( ").replace(")", " ) ").replace("=", " = ").replace("  ", " ")
    for k, v in temp.items():
        formated_structure = formated_structure.replace(v, k)   #还原回来
    if structure_type == "sub_function":
        return formated_structure, label_var_map    #qdt需要子问题的label_var_map
    else: 
        return formated_structure


def do_normalization_sub_fun_sparql(data_file_name, output_file_name):
    print('preprocessing data from:', data_file_name)
    data_dict = load_json(data_file_name)
    total_normed_sparql_len = 0
    total_normed_sub_function_len = 0
    total_sparql_len = 0
    total_sub_function_len = 0
    for index, lines in enumerate(data_dict):
        lines["sub_functions"] = preprocess_subquestion(lines["PyQL"])
        #正则化sparql
        if lines['ID'] == "17112620867_all_4":
            pass
        sparql = lines["sparql"]
        data_dict[index]['normalized_sparql'] = replace_vars_and_ent(sparql, lines['gold_entity_label_map'],
                                                                    lines['gold_relation_label_map'], "sparql")
        data_dict[index]['normalized_sparql'] = " ".join(data_dict[index]['normalized_sparql'].split())
        # data_dict[index]['gold_entity_map'] = lines['gold_entity_label_map']
        # data_dict[index]['gold_relation_map'] = lines['gold_relation_label_map']
        #正则化子函数
        blanks_after_id = re.findall("\d\s+[\"\']", data_dict[index]['sub_functions'])
        for blk in blanks_after_id:
            data_dict[index]['sub_functions'] = data_dict[index]['sub_functions'].replace(blk, blk.replace(" ",""))
        subf = data_dict[index]['sub_functions'].replace("[", "{").replace("]", "}") #防止方括号出问题
        data_dict[index]['normalized_sub_functions'], label_var_map = replace_vars_and_ent(subf, lines['gold_entity_label_map'],
                                                                            lines['gold_relation_label_map'], "sub_function")
        data_dict[index]['normalized_sub_functions'] = " ".join(data_dict[index]['normalized_sub_functions'].split())
        data_dict[index]['normed_label_var_map'] = label_var_map
        #qdt与正则化qdt
        # data_dict[index]['sub_functions_qdt'] = sub_to_qdt(data_dict[index]['sub_functions'].replace("[", "{").replace("]", "}"))
        # qdt = data_dict[index]['sub_functions_qdt']
        # data_dict[index]['normalized_sub_functions_qdt'] = replace_vars_and_ent(qdt, lines['gold_entity_label_map'],
        #                                      lines['gold_relation_label_map'], "qdt", label_var_map)
        # data_dict[index]['normalized_sub_functions_qdt'] = " ".join(data_dict[index]['normalized_sub_functions_qdt'].split())
        total_sparql_len += len(lines['sparql'])
        total_sub_function_len += len(lines['sub_functions'])
        total_normed_sparql_len += len(lines['normalized_sparql'])
        total_normed_sub_function_len += len(data_dict[index]['normalized_sub_functions'])

    print('avg sparql len: ', total_sparql_len / len(data_dict))

    print('avg norm sparql len: ', total_normed_sparql_len / len(data_dict))
    print('avg sub question len: ', total_sub_function_len / len(data_dict))
    print('avg norm sub question len: ', total_normed_sub_function_len / len(data_dict))

    print('save to file: ', output_file_name)
    save_json(data_dict, output_file_name)


def do_convertion(data_file_name):
    """对某个文件中的子函数和qdt做互相转换。会自动检测是否包含这些字段，如果包含，则做转换。"""
    print("load data from： ", data_file_name)
    data_dict = load_json(data_file_name)
    for index, lines in enumerate(data_dict):
        if "sub_functions" in lines:
            sub_fun = lines["sub_functions"]
            try:
                data_dict[index]['sub_functions_qdt_from_sub_functions'] = sub_to_qdt(sub_fun)
            except:
                data_dict[index]['sub_functions_qdt_from_sub_functions'] = ""
        if "sub_functions_qdt" in lines:
            qdt = lines["sub_functions_qdt"]
            try:
                data_dict[index]['sub_functions_from_sub_functions_qdt'] = qdt_to_sub_fun(qdt)
            except:
                data_dict[index]['sub_functions_from_sub_functions_qdt'] = ""
    print("save convert result to:", data_file_name.split('.')[0] + "_converted.json")

    save_json(data_dict, data_file_name.split('.')[0] + "_converted.json")


# def run_denormed_sparql(data_file_name, golden_file_name):
#     data_dict = load_json(data_file_name)
#     wde = WDExecutor()

#     dev_dict = load_json(golden_file_name)
#     sum_of_hit = 0
#     for index, lines in enumerate(data_dict):
#         data_dict[index]['executed_res'] = []
#         data_dict[index]['is_true'] = False
#         for sparql in data_dict[index]['denormed_sparql']:
#             try:
#                 origin_res = wde.query_db(sparql)
#                 if len(origin_res) >= 0:
#                     data_dict[index]['executed_res'] = origin_res
#                     for res in origin_res:
#                         if res in dev_dict[index]['answer']:
#                             sum_of_hit += 1
#                             data_dict[index]['is_true'] = True
#                     break
#             except:
#                 continue
#     print(sum_of_hit)
#     save_json(data_dict, data_file_name.split('.')[0] + "_denormed.json")


def do_denormalization_sub_fun_sparql(data_file_name):
    print("load data from： ", data_file_name)
    data_dict = load_json(data_file_name)
    dev_file = '/home3/stcheng/demo/GMT-KBQA/data/CWQ/generation/merged/num_5350_dev.json'
    dev_dict = load_json(dev_file)
    for index, lines in enumerate(data_dict):
        print(lines.keys())
        data_dict[index]['denormed_qdt'] = denormalize_qdt(lines['normalized_sub_functions_qdt'], {get_legal_label(k):v for k, v in lines["gold_label_entity_map"].items()},
                                        {get_legal_label(k):v for k, v in lines["gold_label_relation_map"].items()})
        data_dict[index]['gen_subf'] = qdt_to_sub_fun(data_dict[index]['denormed_qdt'])
        print(data_dict[index]['ID'])
        print(data_dict[index]['gen_subf'])
        data_dict[index]['gen_sparql'] = generate_sparql_by_functions(data_dict[index]['gen_subf'])
    print("save denormed to :", data_file_name.split('.')[0] + "_denormed.json")
    save_json(data_dict, data_file_name.split('.')[0] + "_denormed.json")


def do_denormalization_qdt(data_file_name):
    print("load data from： ", data_file_name)
    data_dict = load_json(data_file_name)
    dev_file = '/home3/stcheng/demo/GMT-KBQA/data/CWQ/generation/merged/num_5350_dev.json'
    dev_dict = load_json(dev_file)
    for index, lines in enumerate(data_dict):
        data_dict[index]['denormed_sparql'] = []
        for pred in lines['predictions']:
            data_dict[index]['denormed_sparql'].append(
                denormalize_qdt(pred, dev_dict[index]["gold_label_entity_map"],
                                          dev_dict[index]["gold_label_relation_map"]))
    print("save denormed to :", data_file_name.split('.')[0] + "_denormed.json")
    save_json(data_dict, data_file_name.split('.')[0] + "_denormed.json")


def sub_to_qdt(sub_functions):
    if "count_lights_2" in sub_functions:
        pass
    sub_functions = sub_functions.replace(" = ", "=").replace(" =", "=").replace("= ", "=").strip()
    all_sub_functions = sub_functions.split("\n")
    all_sparql_gen = re.findall('[a-z]\=SPARQL_GEN\(\)', sub_functions)

    topo_relations = re.findall(r"[a-z]\.add_sub_query\([a-z, ]*\)", sub_functions)
    # 有哪些子问题 a, b, c...
    sub_querys = []

    for tag in all_sparql_gen:
        sub_querys.append(tag[0])
    # 构造树结构
    children = dict()
    for tag in sub_querys:
        tag = tag.strip()
        children[tag] = []

    for lines in topo_relations:
        splits = lines.split(".add_sub_query")
        innode = splits[0]
        outnodes = splits[1].strip("(").strip(")").split(",")
        for outn in outnodes:
            outn = outn.strip()
            children[innode].append(outn)

    # 构造每个树节点的内容
    sub_queries_for_tags = dict()
    for tag in sub_querys:
        tag = tag.strip()
        sub_queries_for_tags[tag] = []
        for lines in all_sub_functions:
            if len(lines) == 0:
                continue
            if "SPARQL_GEN" in lines:
                continue
            if "add_sub_query" in lines:
                continue
            if lines[0] == tag:
                sub_queries_for_tags[tag].append(lines.strip(tag).strip("."))

    if len(all_sparql_gen) == 1:
        return " ".join(sub_queries_for_tags[sub_querys[0]])

    def postorder(root):
        if root not in children.keys():
            return ""
        if len(children[root]) == 0:
            return " ".join(sub_queries_for_tags[root])

        result = ""
        for child in children[root]:
            result += " [SUBQL] " + postorder(child) + " [SUBQR] "

        result += " ".join(sub_queries_for_tags[root])
        return result
    
    postorder_linearlized = postorder(sub_querys[len(sub_querys) - 1])
    qdt = postorder_linearlized.replace("  ", " ").strip()
    if "[SUBQL] [SUBQR]" in qdt:
        print(children)
        print(sub_queries_for_tags)
        print(qdt)
    return qdt



cur_block_idx = ""

def qdt_to_sub_fun(qdt):
    """将qdt格式转化为子函数。主要方法是通过栈分析，将后序遍历序列还原为树"""
    #逐层取[SUBQ]内的内容,并递归地生成某个序列对应的查询
    def manage_a_level(splited):
        global cur_block_idx
        inner_questions = []
        #找到所有最外层的INQ。
        idx = 0
        while(idx < len(splited)):
            if splited[idx] == "[SUBQL]" or splited[idx] == "[INQL]": #某个
                #寻找这个子问题的终止点在哪里。利用栈
                right_idx = idx
                stack = 0
                while(right_idx < len(splited)):
                    if splited[right_idx] == "[SUBQL]" or splited[right_idx] == "[INQL]":
                        stack += 1
                    elif splited[right_idx] == "[SUBQR]" or splited[right_idx] == "[INQR]":
                        stack -= 1
                        if stack == 0:
                            #发现了一个新的最外层子问题
                            inner_questions.append(splited[idx+1:right_idx])    #取这个子问题的[SUBQL][SUBQR]内部分
                            idx = right_idx
                            break
                    right_idx += 1
                assert(right_idx < len(splited))
            idx += 1
        #递归地处理每一个子查询
        subquerys = []
        for part in inner_questions:
            subquerys.append(manage_a_level(part))
        subquery_ids = [subquery[0][0] for subquery in subquerys]
        #找到属于这层的子函数
        v_idx = len(splited)-1
        while v_idx >= 0 and splited[v_idx] != "[SUBQR]":
            v_idx -= 1
        this_part = splited[v_idx+1:]
        #求本层查询的id号。
        query_id = cur_block_idx
        cur_block_idx = chr(ord(cur_block_idx)+1)
        #先写之前的子查询
        query = []
        for subquery in subquerys:
            query += subquery
        #创建这个part的子查询
        query.append(query_id+ "=SPARQL_GEN()")
        for func in this_part:
            query.append(query_id+"."+func)
        if len(subquerys) > 0:
        #添加查询依赖关系
            dependency = query_id +".add_sub_query("
            for subq_id in subquery_ids:
                dependency+=subq_id+","
            dependency = dependency.strip(",")+")"
            query.append(dependency)
        return query
    splited = qdt.split()
    global cur_block_idx
    cur_block_idx = "a" #全局变量用于给各块赋予编号
    functions_list = manage_a_level(splited)
    #添加print
    last_block_idx = functions_list[-1][0]
    functions_list.append("print("+last_block_idx+".sparql)")
    return "\n".join(functions_list)


def do_sub_fun_to_qdt(data_file_name):
    print("load data from： ", data_file_name)
    data_dict = load_json(data_file_name)
    for index, lines in enumerate(data_dict):
        sub_fun = lines["sub_functions"]
        try:
            data_dict[index]['sub_functions_qdt'] = sub_to_qdt(sub_fun)
        except:
            data_dict[index]['sub_functions_qdt'] = ""
            print(sub_fun)

    print("save denormed to :", data_file_name.split('.')[0] + "_sub_fun_qdt.json")

    save_json(data_dict, data_file_name.split('.')[0] + "_sub_fun_qdt.json")


def do_qdt_to_sub_fun(data_file_name):  
    print("load data from： ", data_file_name)
    data_dict = load_json(data_file_name)
    for index, lines in enumerate(data_dict):
        qdt = lines["qdt"]
        try:
            data_dict[index]['sub_functions_qdt'] = qdt_to_sub_fun(qdt)
        except:
            data_dict[index]['sub_functions_qdt'] = ""
            print(qdt)


if __name__ == '__main__':
    do_normalization_sub_fun_sparql('data_file_path', 'output_file_path')