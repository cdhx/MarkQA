# 用于sample 要生成的SPARQL
import numpy as np

def extract_fb_entity(sparql):
    # 从SPARQL中抽取实体
    pass
def extract_fb_relation(sparql):
    # 从SPARQL中抽取关系
    pass
def extract_fb_digit(sparql):
    # 从SPARQL中抽取数值或时间
    pass

def is_cvt(ent):
    # 判读是否为cvt节点
    pass


class sparql_sampler:
    # 设计一个SPARQL的sample类，用于从KB上sample SPARQL
    # 可以指定包含某些实体，或关系，或子结构，指定采用某种结构（需要对结构有一个单独的数据结构表示）
    def __init__(self,entit_list=[],relation_list=[]):
        self.ent_in_corpus = []  # 所有可以取的entity
        self.rel_in_corpus = []  # 所有可以取的关系

        self.entity_list = entit_list  # 预先指定必须有什么entity
        self.pred_list = relation_list  # 预先指定必须有什么关系

    # 两个基础思路，替换已有SPARQL的E,R,D和对模板填槽，其实一样
    def sample_based_on_sparql(self, sparql, k=1, ent_unchange=False, rel_unchange=False, dig_unchange=False, order_unchange=False):
        # 替换给定sparql中的E,R,D,比较方向（>,<，max,min）
        # 需要保证1.联通,2.替换不受到overlap现象干扰
        pass

    def sample_based_on_template(self, template):
        # 向给定模板中填槽
        pass

    # 下面本意是一个按照概率随机生成不同结构的方案
    def sample_sparql_randomly(self):
        # 返回一个采样的SPARQL，最外层函数
        pass
    def sampler(self, cand_list):
        # 采样任意内容，输入候选list，sample一个
        return np.random.choice(cand_list, size=1, replace=False)[0]#不重复采样，设置为False


    def sample_entity(self):
        # 采样一个实体
        return self.sampler(self.ent_in_corpus)

    def sample_one_hop(self, EntOrCvt, reverse=False):
        # 给一个entity或者cvt获取一跳关系,reverse是反向  ?one_hop_ent rel EntOrCvt
        pass

    def extend_path(self, entity, hop=1):
        pass

    def extend_cvt(self):
        # 如果是cvt则扩展路径
        pass

    def get_one_hop_triple(self, entity):
        # 获取一跳的实体或关系，不考虑是否是cvt
        pass

    def get_one_hop_ent(self, entity):
        return self.get_one_hop_triple(entity)

    def get_one_hop_rel(self, entity):
        # 获取一跳的关系
        return self.get_one_hop_triple(entity)
