# s-exp相关的功能函数

# SExp类是一个二叉树graph，有线性化函数
# 叶子节点
TYPE_ENTITY_NODE = 'ENTITY'  #
TYPE_RELATION_NODE = 'RELATION'  #
TYPE_DIGIT_NODE = 'DIGIT'  #
# 中间节点
TYPE_ARGMAX = 'ARGMAX'  #
TYPE_ARGMIN = 'ARGMIN'  #
TYPE_JOIN = 'JOIN'  #
TYPE_AND = 'AND'  #
TYPE_GT = 'GT'  #
TYPE_GE = 'GE'  #
TYPE_LT = 'LT'  #
TYPE_LE = 'LE'  #
TYPE_TC = 'LE'  #
TYPE_COUNT = 'COUNT' #


class ContentNode():
    # sexp tree的叶子节点，例如实体，关系时间约束
    def __init__(self):
        self.node_type = ''  # entity mid，relation，数值
        self.reverse_rel = False  # T or F，仅用来表示关系的正向或反向
        self.content = ''  #


class FunctionNode():
    # sexp tree的中间节点，主要是功能函数
    def __init__(self):
        self.node_type = ''  # argmax,argmin,join,and,gt,ge,le,lt,tc
        self.monocular_operators=[TYPE_COUNT]
        self.binocular_operators=[TYPE_AND,TYPE_JOIN,TYPE_ARGMAX,TYPE_ARGMIN]
        self.triocular_operators=[TYPE_GT,TYPE_GE,TYPE_LT,TYPE_LE,TYPE_TC]

        if self.node_type in self.monocular_operators: # 单目运算接收实体list即可
            self.entity_node=''
            self.param_num=1
        elif self.node_type in self.binocular_operators:# 双目运算符接收两个实体list(AND)或者一个实体list一个关系(JOIN)或者一个实体list一个属性(ARG)

            self.entity_node = ''
            self.relation_node=''
            self.param_num = 2
        elif self.node_type in self.triocular_operators:#三目运算符接收实体list，比较属性和比较值
            self.entity_node = ''
            self.relation_node = ''
            self.property_value_node='' # 如果有的话，用于gt,ge,le,lt,tc的属性数值部分，如果没有就是None
            self.param_num = 3




class SExpTree():
    # 设计一种树结构，用于表示树状的sexp，也用于扩展时表示要merge的子树
    def __init__(self):
        self.is_leaf=True # T or F是否是叶子节点（mid,relation,digit）
        if not self.is_leaf:
            # function node就是根节点
            self.function_node_type = ''  # argmax,argmin,join,and,gt,ge,le,lt,tc
            self.monocular_operators=[TYPE_COUNT]
            self.binocular_operators=[TYPE_AND,TYPE_JOIN,TYPE_ARGMAX,TYPE_ARGMIN]
            self.triocular_operators=[TYPE_GT,TYPE_GE,TYPE_LT,TYPE_LE,TYPE_TC]
            if self.function_node_type in self.monocular_operators: # 单目运算接收实体list即可
                self.entity_node=None
                self.param_num=1
            elif self.function_node_type in self.binocular_operators:# 双目运算符接收两个实体list(AND)或者一个实体list一个关系(JOIN)或者一个实体list一个属性(ARG)
                self.entity_node = None
                self.relation_node= None
                self.param_num = 2
            elif self.function_node_type in self.triocular_operators:#三目运算符接收实体list，比较属性和比较值
                self.entity_node = None
                self.relation_node = None
                self.property_value_node=None # 如果有的话，用于gt,ge,le,lt,tc的属性数值部分，如果没有就是None
                self.param_num = 3
    def linear_representation(self,tree):
        # 线性化树的表示
        pass

    def add_join(self,entity_node,relation):
        self.entity_node=entity_node
        self.relation_node=relation
        self.child_list=[self.entity_node,self.relation_node]
    def add_add(self,entity_node1,entity_node2):
        self.entity_node1=entity_node1
        self.entity_node2=entity_node2
        self.child_list = [self.entity_node1, self.relation_node2]
    def add_ge(self,entity_node,property,property_value):
        self.entity_node=entity_node
        self.property=property
        self.property_value_node=property_value
        self.child_list = [self.entity_node, self.property,self.property_value_node]
    def add_gt(self,entity_node,property,property_value):
        pass

    def add_le(self,entity_node,property,property_value):
        pass

    def add_lt(self,entity_node,property,property_value):
        pass

    def add_tc(self,entity_node,property,property_value):
        # 实体列表 约束属性和约束值
        pass

    def add_argmax(self,entity_node,property):
        # 实体列表和比较属性
        pass

    def add_argmin(self,entity_node,property):
        pass

    def add_count(self,entity_node):
        # 一元运算符
        pass

    def tree2linear(self, tree):
        # 树结构的sexp转化成linear的sexp
        linear_sexp = ''
        return linear_sexp


def sexp2sparql(self, sexp):
    # sexp转化成sparql
    sparql = ''
    return sparql


def sparql2sexp(self, sparql):
    sexp = ''
    return sexp

