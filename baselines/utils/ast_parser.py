# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     func2subq
   Description :  从中间函数生成子问题
   Author :       HX
   date：          2023/4/17
-------------------------------------------------
 
"""
__author__ = 'HX'
import ast
#
# function = """
# mul(1,'xdf')
# mul(div(2,'wdq'),100)
# a.add_bind(mul(1,2),'ans')
# """
# tree = ast.parse(function)
# for index,node in enumerate(tree.body):
#     res=chose_parse(node)
#     print(res)

# 解析代码

# line='c.add_sub_query(a,b)'
# res=parse_line(line)
# print([res['ins']]+res['args'])


def parse_assign(node):
    # 有赋值语句
    return_value=node.targets[0].id
    value=parse_call(node.value)
    return {'return':return_value,'value':value}

def parse_expr(node):
    # 实例
    value=parse_call(node.value)
    return value
def parse_call(node):

    args=[parse_args(x) for x in node.args]
    keyword = [parse_keyword(x) for x in node.keywords]
    # temp=[parse_keyword(x) for x in node.keywords]
    # keyword={list(x.keys())[0]:list(x.values())[0] for x in temp}


    # 函数的成员方法
    if 'attr' in dir(node.func):
        ins=node.func.value.id
        # 函数名
        func=node.func.attr
        return {'ins':ins, 'func':func, 'args':args,'keywords':keyword}
    # 普通方法
    else:
        # ins=''
        func=node.func.id
        return {'func':func, 'args':args,'keywords':keyword}

def parse_attr(node):
    ins = node.value.id
    func=node.attr
    return {'ins':ins,'func':func}

# target是name类,node.value.func记录函数的也是name
def parse_name(node):
    return node.id
# 参数都是这几个
def parse_str(node):
    return node.s
def parse_constant(node):
    return node.value
def parse_num(node):
    return node.n
def parse_unaryop(node):
    # 处理负数
    if isinstance(node.op,ast.USub):
        if type(node.operand.n)==int:
            return int('-'+str(node.operand.n))
        elif type(node.operand.n)==float:
            return float('-'+str(node.operand.n))
        else:
            print('parse_unaryop errpor, value not in float or int',type(node.operand.n))
    else:
        print('parse_unaryop errpor, type is not usub ', node,type(node.op))
        return node.operand.n
def parse_list(node):
    return [chose_parse(x) for x in node.elts]
def parse_name_constant(node):
    return node.value

def parse_keyword(node):
    key=node.arg
    value=chose_parse(node.value)
    return {key: value}

def parse_args(node):
    value=chose_parse(node)
    return value

def parse_line(line):
    # 只能parse一行
    tree = ast.parse(line)
    res = chose_parse(tree.body[0])
    return res
def chose_parse(node):
    pass
    if isinstance(node, ast.Assign):
        value=parse_assign(node)
    elif isinstance(node, ast.Expr):
        value=parse_expr(node)
    elif isinstance(node,ast.Call):
        value=parse_call(node)

    elif isinstance(node,ast.Name):
        value=parse_name(node)
    elif isinstance(node,ast.Constant):
        value=parse_constant(node)
    elif isinstance(node, ast.Num):
        value=parse_num(node)
    elif isinstance(node, ast.UnaryOp):
        value=parse_unaryop(node)
    elif isinstance(node, ast.Str):
        value=parse_str(node)
    elif isinstance(node,ast.List):
        value=parse_list(node)
    elif isinstance(node, ast.NameConstant):
        value = parse_name_constant(node)
    elif isinstance(node, ast.Attribute):
        value = parse_attr(node)
    else:
        print(node)
        print(type(node))
    return value





