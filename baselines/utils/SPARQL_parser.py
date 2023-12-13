# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 21:42:48 2020

@author: njucsxh
"""
# 不标准的情况：
# WHERE,SELECT,ASK没有大写
# 代求变量多于实际数量，不写代求变量
# 完整链接的生成，应该严格按照前缀，简写形式的生成，才需要字典，确认一下
'''
PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?uri WHERE { 
?uri <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://dbpedia.org/ontology/Song> . 
?uri <http://dbpedia.org/ontology/artist> <http://dbpedia.org/resource/Bruce_Springsteen> . 
?uri <http://dbpedia.org/ontology/releaseDate> ?date . 
FILTER (?date >= '1980-01-01'^^<http://www.w3.org/2001/XMLSchema#date> && ?date <= '1990-12-31'^^<http://www.w3.org/2001/XMLSchema#date>) }

PREFIX xsd:<http://www.w3.org/2001/XMLSchema#> SELECT DISTINCT ?uri WHERE { ?uri <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://dbpedia.org/ontology/Song> . ?uri <http://dbpedia.org/ontology/artist> <http://dbpedia.org/resource/Bruce_Springsteen> . ?uri <http://dbpedia.org/ontology/releaseDate> ?date . FILTER (?date >= '1980-01-01'^^xsd:date && ?date <= '1990-12-31'^^xsd:date) }

还需要一个处理;共用主语形式的normalize
'''
# 遇到的小细节
# <http://.*?>多写点，不要只写<>以为filter里面有<>=
# link或者abbr都应该是针对whered ，former不应该处理
# where,filter都可以小写的

import re

import json
import socket
import requests
from SPARQLWrapper import SPARQLWrapper, JSON


def valid_find(string, start_index=0, *substr):
    '''string是字符串，start_index是开始匹配位置，substr是任意个子串
    找到substr中，有效的（查找结果不为-1）的最早匹配（最小的索引）
    '''
    valid_index = []
    for x in substr:
        temp_valid_index = string.find(x, start_index);
        temp_valid_index = temp_valid_index if temp_valid_index != -1 else 99999  # 找:后面的空格
        valid_index.append(temp_valid_index)
    return min(valid_index)


class RegexDict(dict):
    import re
    def __init__(self, *args, **kwds):
        self.update(*args, **kwds)

    def __getitem__(self, required):
        for key in dict.__iter__(self):
            if self.re.match(key, required):
                return dict.__getitem__(self, key)


# {}前后空格，末尾没有.，变量统一，去前缀
class SPARQL(object):
    def __init__(self, raw_sparql, filename='12345', question=''):
        self.raw_sparql = raw_sparql
        self.filename = filename
        self.question = question
        # =============================================================================
        #         try:
        #             self.filename = filename[0]
        #         except:
        #             self.filename = '123'
        # =============================================================================
        self.pre_map = {
            'prop': '<http://dbpedia.org/property/>',
            'owl': '<http://www.w3.org/2002/07/owl#>',
            'dbp': '<http://dbpedia.org/property/>',
            'dct': '<http://purl.org/dc/terms/>',
            'res': '<http://dbpedia.org/resource/>',
            'dbo': '<http://dbpedia.org/ontology/>',
            'skos': '<http://www.w3.org/2004/02/skos/core#>',
            'db': '<http://dbpedia.org/>',
            'yago': '<http://dbpedia.org/class/yago/>',
            'onto': '<http://dbpedia.org/ontology/>',
            # 'xsd': '<http://www.w3.org/2001/XMLSchema#>',#注释掉它，former中只有两个链接可能出现，泛化没有意义
            'rdfs': '<http://www.w3.org/2000/01/rdf-schema#>',
            'foaf': '<http://xmlns.com/foaf/0.1/>',
            'dbr': '<http://dbpedia.org/resource/>',
            'dbc': '<http://dbpedia.org/resource/Category:>',
            'dbpedia2': '<http://dbpedia.org/property/>'
        }

        self.map_pre = RegexDict({
            '<http://dbpedia.org/>': 'db',
            '<http://dbpedia.org/class/yago/.*?>': 'yago',
            '<http://dbpedia.org/ontology/.*?>': 'dbo',
            '<http://dbpedia.org/property/.*?>': 'dbp',
            '<http://dbpedia.org/resource/.*?>': 'dbr',
            '<http://dbpedia.org/resource/Category:>': 'dbc',
            '<http://purl.org/dc/terms/.*?>': 'dct',
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#>': 'rdf',
            '<http://www.w3.org/2000/01/rdf-schema#>': 'rdfs',
            '<http://www.w3.org/2001/XMLSchema#>': 'xsd',
            '<http://www.w3.org/2002/07/owl#>': 'owl',
            '<http://xmlns.com/foaf/0.1/>': 'foaf',
            '<http://www.w3.org/2004/02/skos/core#>': 'skos'
        })
        self.normalize()
        self.set_sparql()  # link_sparql
        self.set_former()  # link后的former
        self.set_where()  # link后的where
        self.set_intent()  # 意图，ask/select/count
        if self.intent != 'ASK':
            self.set_vars()  # 设置firstVar,allVar,处理冗余变量，如果有冗余变量，会重新设置former（where不变不用再写一次）
        else:
            self.firstVar = 'UNK'
            self.all_vars = []
        self.set_variable_normalize()
        self.set_abbr_sparql()  # abbr_sparql，abbr_where也处理了
        self.set_link_sparql()  # link_sparql
        self.set_abbr_where()  # abbr_where
        self.set_link_where()  # link_where

        self.set_constrain()  # constrain
        self.set_triple_info()  # 所有三元组，三元组数量，{}中按点分割，对于FILTER还没有未处理
        self.set_link()  # 所有的链接
        self.set_entity()  # 所有的实体，仅考虑dbr
        self.set_predicate()  # 所有的谓词,三元组中的第二个
        self.set_abbr_triple_list()  # abbr_triple_list

        self.set_template()  # 替换链接为<E/R>
        self.set_former_template()  # former的模板
        self.set_where_template()  # where的模板
        self.set_host_ip()  # ip

        self.set_union()
        self.set_filter()
        self.set_having()
        self.set_order()
        self.set_bind()
        self.set_contain()
        self.set_group()
        self.set_optional()

        # self.draw()#画图，文件名暂无好办法

    # 找一个sparql string的former和where,很多地方要用，抽出来
    def string_former(self, string):
        return string[:valid_find(string, 0, 'where', 'WHERE')].strip()

    def string_where(self, string):
        return string[valid_find(string, 0, 'where', 'WHERE'):].strip()

    def normalize(self):

        # 去连续空格，前后空格，{}旁边的空格
        self.sparql = ' '.join(self.raw_sparql.split())  # 去连续空格
        self.sparql = self.sparql.replace('. }', '}')  # 去掉最后一句的句号
        self.sparql = self.sparql.replace(' }', '}')  # 去掉}前的空格
        self.sparql = self.sparql.replace('{ ', '{')  # 去掉{后的空格
        self.sparql = ' '.join(self.sparql.split())  # 去连续空格
        self.sparql = self.sparql.strip()  # 去前后空格

    def set_sparql(self):  # 转换成<http://>完整形式
        '''只处理where部分，处理former没有意义'''
        string = self.sparql
        where_start = valid_find(string, 0, 'WHERE', 'where')

        # query_start是有PREFIX的时候select（former）开始的地方
        # 有前缀
        if string.find('PREFIX') != -1:  # 有PREFIX，先找到他给的词典，和正文开始的地方SELECT，再用他给的词典还原
            # 但是对于通用的rdf:type，xsd:data是可以不给前缀的
            pattern_pre = re.compile(r'PREFIX .+?>')
            pre_list = pattern_pre.findall(string)  # 所有前缀
            # 获取所有映射关系
            temp_dic = {}
            for item in pre_list:
                # 先找到:,可能有: <http://
                index_split = valid_find(item, 0, ':<http://', ': <http://')

                former_part = item[:index_split]  # PREFIX dbr:<>可以    PREFIX dbr : <>是非法的
                abbr_part = former_part.replace('PREFIX', '').replace('prefix', '').strip()  # 大小写都合法
                link_part = item[index_split + 1:].strip()  # +完整链接
                temp_dic[abbr_part] = link_part
            # query正文开始（前缀后面）
            # 最后一个前缀,为了获取正文
            last_pre = pre_list[[string.find(p) for p in pre_list].index(max([string.find(p) for p in pre_list]))]
            # 正文
            query_start = string.find(last_pre) + len(last_pre) + 1

            for pre in temp_dic.keys():
                while string.find(pre + ':', where_start) != -1:  # 找得到dbo:这种
                    content_start_index = string.find(pre + ':', where_start) + len(pre) + 1  # content开始的地方,加一是：的位置
                    # dbo:content content 就是content
                    # 下面两行应对 dbr:content}}和dbr:content.和dbr:content;和dbr:content,的情况，如果没有空格，那么查询结果为-1,还原的时候会少一个},所以如果没找到空格，就找}
                    # <http://dbpedia.org/resource/Mean_Hamster_Software}>}，模板也会少一个}

                    content_end_index = valid_find(string, content_start_index, ' ', '}', '.', ';', ',')

                    content = string[content_start_index:content_end_index]
                    # 整个缩写的的部分 dbr:xxx
                    abbr_format = string[content_start_index - len(pre) - 1:content_end_index]  # -1是：的位置
                    # 完整格式
                    new_format = temp_dic[pre][:-1] + content + '>'  # -1去掉原来的>
                    # 替换
                    string = string.replace(abbr_format, new_format)
        else:  # 没有PREFIX，用通用词典
            query_start = 0  # 全部是正文
            for pre in self.pre_map.keys():
                while string.find(pre + ':', where_start) != -1:
                    content_start_index = string.find(pre + ':', where_start) + len(pre) + 1
                    # dbo:content content 就是content
                    space_valid = string.find(' ', content_start_index)  # 找:后面的空格
                    brack_valid = string.find('}', content_start_index)  # 找:后面的}
                    if space_valid == -1:
                        content_end_index = brack_valid
                    else:
                        content_end_index = space_valid
                    content = string[content_start_index:content_end_index]
                    # 前缀形式的部分
                    pre_format = string[content_start_index - len(pre) - 1:content_end_index]
                    # 完整格式
                    new_format = self.pre_map[pre][:-1] + content + '>'
                    # 替换
                    string = string.replace(pre_format, new_format)

        self.sparql = string[query_start:]

    def deal_comma_semicolon(self):
        pass  # self.sparql

    def set_former(self):
        self.former = self.string_former(self.sparql)

    def set_where(self):
        self.where = self.string_where(self.sparql)

    def set_vars(self):
        '''sparql中所有的变量
        把变量冗余也放在这里处理，分成former和where两个部分找var，如果former里的变量没有出现在where中 且 这个变量前面没有AS这种重命名符号
        那么在self.sparql中替换这个变量为空，由于init函数中set_var前面还有set_former，这个需要重做
        where,former只能当一个工具，原版的数据，还要加两个属性abbr的和link的
        '''
        all_var = []

        def find_variable(substr):
            end_index = 999
            if substr.find(' ') != -1:
                end_index = min(end_index, substr.find(' '))
            if substr.find(')') != -1:
                end_index = min(end_index, substr.find(')'))
            if substr.find('}') != -1:
                end_index = min(end_index, substr.find('}'))
            if substr.find(';') != -1:
                end_index = min(end_index, substr.find(';'))
            if substr.find(',') != -1:
                end_index = min(end_index, substr.find(','))
            if substr.find('.') != -1:
                end_index = min(end_index, substr.find('.'))
            # valid_find(substr,0,' ',')','}',';',',','.')
            return end_index

        # 先求former中的var
        former_var = []
        end_index = 0
        start_inde = 0
        sparql_query = self.former
        while sparql_query.find('?', end_index) != -1:
            start_index = sparql_query.find('?', end_index)
            end_index = find_variable(sparql_query[start_index:])
            former_var.append(sparql_query[start_index:end_index + start_index])
            end_index += start_index
        # 再求where中的var
        where_var = []
        end_index = 0
        start_inde = 0
        sparql_query = self.where
        while sparql_query.find('?', end_index) != -1:
            start_index = sparql_query.find('?', end_index)
            end_index = find_variable(sparql_query[start_index:])
            where_var.append(sparql_query[start_index:end_index + start_index])
            end_index += start_index
        # 判断有没有异常（former里有但是where里根本没有）（找变量只要找where就可以了，former里面可能有重命名，判断一下有没有AS就行了）
        for fv in former_var:
            if fv not in where_var:
                if 'AS' not in self.former[:self.former.find(fv)] or 'as' not in self.former[:self.former.find(fv)]:
                    self.sparql = self.sparql.replace(fv, '')
                    self.set_former()
        # 一般主变量都是former里的第一个，这样写对付select *这种情况
        if len(former_var) != 0:
            self.firstVar = former_var[0]
        else:
            self.firstVar = where_var[0]
        self.all_vars = list(set(where_var))

    def set_abbr_sparql(self):
        string = self.sparql
        if string.find('PREFIX') != -1:  # 有前缀的格式,只留正文
            pattern_pre = re.compile(r'PREFIX .+?>')
            pre_list = pattern_pre.findall(string)  # 所有前缀
            # 最后一个prefix
            last_pre = pre_list[[string.find(p) for p in pre_list].index(max([string.find(p) for p in pre_list]))]
            query_start = string.find(last_pre) + len(last_pre) + 1  # 正文开始的     索引
            string = string[query_start:]  # 取query正文

        # 有些有前缀和没有前缀混合的，还有只有有前缀形式的，把有前缀的转换掉
        pattern = re.compile('<http://.+?>')
        full_format = pattern.findall(string)  # 所有完整的uri
        for x in full_format:
            content = x[max(x.rfind('/'), x.rfind('#')) + 1:-1]  # 获取local name,-1去掉>
            full_uri = x
            pre_uri = self.map_pre[x[:max(x.rfind('/'), x.rfind('#')) + 1] + '>'] + ':' + content#缩写前缀+content(local name)
            string = string.replace(full_uri, pre_uri)

            # 检查不标准的缩写 onto,res,感觉用不到
            '''
        for pre in self.pre_map.keys():
            if pre not in self.map_pre.values():#不标准，如果标准的也处理会陷入死循环
                while string.find(pre+':')!=-1:#有这种缩写
                    abr_start=string.find(pre+':')
                    abr_stop=abr_start+len(pre)
                    ill_form=string[abr_start:abr_stop]#现在的格式#
                    standard_form=self.map_pre[self.pre_map[ill_form]]
                    #替换
                    string=string.replace(ill_form,standard_form)         
                    '''
        self.abbr_sparql = string

    def set_link_sparql(self):
        self.link_sparql = self.sparql

    def set_abbr_where(self):
        self.abbr_where = self.string_where(self.abbr_sparql)

    def set_link_where(self):
        self.link_where = self.string_where(self.link_sparql)
    def link2abbr(self,string):
        #任意的str，把其中的<>换成缩写
        for x in self.link:
            content = x[max(x.rfind('/'), x.rfind('#')) + 1:-1]  # 获取local name,-1去掉>
            #完整的link  <>
            full_uri = x
            #缩写的link xxx:xxxx
            abbr_link=self.map_pre[x[:max(x.rfind('/'), x.rfind('#')) + 1] + '>'] + ':' + content  # 缩写前缀+content(local name)
            string=string.replace(full_uri,abbr_link)
        return string
    def set_abbr_triple_list(self):
        '''TODO 替换{}where为空得到triple content，对于content里面有{}就会出错'''
        # 缩写后，按照.分割不同的triple，如果link结尾也是.就会出问题，所以从完整sparql中提取triple lisk在转缩写
        # abbr_triple_content = self.abbr_where.replace('}', '').replace('{', '').replace('WHERE', '').replace('where',
        #                                                                                                      '').strip()
        # self.abbr_triple_list = list(map(lambda x: x.strip(), abbr_triple_content.split('. ')))

        self.abbr_triple_list=[self.link2abbr(x) for x in self.triple_list]

    def set_triple_info(self):
        '''TODO 替换{}where为空得到triple content，对于content里面有{}就会出错'''
        self.triple_num = len(self.where.split('. '))
        triple_content = self.where.replace('}', '').replace('{', '').replace('WHERE', '').replace('where', '').strip()
        self.triple_list = list(map(lambda x: x.strip(), triple_content.split('. ')))

    # TODO不完善，约束可能在WHERE里面
    def set_constrain(self):
        self.constrain = self.sparql[self.sparql.find('}') + 1:]

    def set_link(self):
        ''''所有链接，考虑了xsd:data和rdf:type'''
        pattern = re.compile('<http://.+?>')
        result = re.findall(pattern, self.sparql)
        if 'xsd:data' in self.sparql:
            result.append('xsd:data')
        if ' a ' in self.sparql or 'rdf:type' in self.sparql:
            result.append('rdf:type')
        self.link = list(set(result))
        self.abbr_link = self.full2abbr(self.link)

    def set_entity(self):
        # 所有的entity缩写，认为前缀为dbr的是
        self.entity = list(filter(lambda x: x[:4] == 'dbr:', self.abbr_link))

    def set_predicate(self):
        # 所有的谓词
        self.predicate = self.full2abbr(list(map(lambda x: x.split(' ')[1], self.triple_list)))

    def set_template(self):
        self.template = re.sub('<http://.+?>', '<E/R>', self.sparql)


    def set_former_template(self):

        self.former_template = self.string_former(self.template)

    def set_where_template(self):
        self.where_template = self.string_where(self.template)

    '''TODO 所有的大小写'''

    def set_union(self):
        self.union = 'UNION' in self.sparql

    def set_filter(self):
        self.filter = 'FILTER' in self.sparql

    def set_having(self):
        self.having = 'HAVING' in self.sparql

    def set_order(self):
        self.order = 'ORDER' in self.sparql

    def set_bind(self):
        self.bind = 'BIND' in self.sparql

    def set_contain(self):
        self.contain = 'contain' in self.sparql

    def set_group(self):
        self.group = 'GROUP' in self.sparql

    def set_optional(self):
        self.optional = 'OPTIONAL' in self.sparql

    def set_variable_normalize(self):
        # 把sparql的变量统一，有序，有VAR3一定有VAR2,VAR1
        try:
            firstVar, allVariable = self.firstVar, self.allVar
            # 构造映射关系
            inter_var = ['?VAR1', '?VAR2', '?VAR3',
                         '?VAR4']  # 一定要选取肯定没有在原始SPARQL中使用的变量名，假如你把?x换成了?y,?y在原SPARQL中出现了，那么?y也要映射到其他变量，相当于?x和?y成了一个变量
            sparql = self.sparql.replace(firstVar, '?MAINVAR')
            inter_index = 0  # inter_var用到第几号了
            for i in range(len(allVariable)):
                if allVariable[i] != firstVar:
                    sparql = sparql.replace(allVariable[i], inter_var[inter_index])
                    inter_index += 1
            sparql = sparql.replace('?MAINVAR', '?uri')
            self.sparql = sparql
        except:
            pass

    def set_host_ip(self):
        """查询本机ip地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        self.ip_address = ip

    def query(self, mode='1604'):
        # sparql = SPARQLWrapper('http://' + self.ip_address + ':8890/sparql')
        # HXX完整DBpedia
        if mode == '1604':  # hxx的
            sparql = SPARQLWrapper('http://114.212.86.218:8890/sparql')
        elif mode == '1610':  # hxx的
            sparql = SPARQLWrapper('http://114.212.190.19:8890/sparql')
        elif mode == 'hx':  # 自己的
            sparql = SPARQLWrapper('http://172.27.151.247:8890/sparql')
        elif mode == 'off':  # 官方
            sparql = SPARQLWrapper('https://dbpedia.org/sparql')
        elif mode == 'fb':
            sparql = SPARQLWrapper('http://210.28.134.34:8890/sparql')
        sparql.setQuery(self.raw_sparql)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        self.answer = self.answer_convert(results)
        return self.answer

    def answer_convert(self, item_answer):

        if 'boolean' in item_answer.keys():
            var = 'boolean'
            return item_answer['boolean']
        else:
            answer = []
            var_list = item_answer['head']['vars']  # 这个是变量列表，常用的就是一个变量，取第一个
            if len(var_list) == 1:  # 单个变量，QALD数据集中很多答案类型，用于解析数据集
                var = var_list[0]
                if var == 'boolean':
                    answer.append(item_answer['boolean'])
                else:
                    for cand in item_answer['results']['bindings']:
                        if var == 'date':
                            answer.append(cand['date']['value'])
                        elif var == 'number':
                            answer.append(cand['c']['value'])
                        elif var == 'resource' or var == 'uri':
                            answer.append(cand['uri']['value'])
                        elif var == 'string':
                            answer.append(cand['string']['value'])
                        elif var == 'callret-0':
                            answer.append(cand['callret-0']['value'])
                        else:  # 貌似都是这个套路，不知道还有什么类型,自己写的查询，一般是用的这个case
                            answer.append(cand[var]['value'])
            else:  # 多个变量，自用，只有最后一个case
                for cand in item_answer['results']['bindings']:
                    dic_temp = {}
                    for var in var_list:
                        dic_temp[var] = cand[var]['value']
                    answer.append(dic_temp)
        return answer

    def set_intent(self):
        '''如果ask,count小写出现在link里怎么办，这里former限制了这一点，但是former就要找对了
        former是找where/WHERE，如果where出现在link里就会出问题
        '''
        if 'ASK' in self.former or 'ask' in self.former:
            self.intent = 'ASK'
        elif 'COUNT' in self.former or 'count' in self.former:
            self.intent = 'COUNT'
        else:
            self.intent = 'SELECT'

    def draw(self):
        from graphviz import Digraph
        dot = Digraph(format='jpg')

        dot.attr(label=self.abbr_sparql + '\n' + self.question)

        for triple in self.abbr_triple_list:
            if len(triple.split(' ')) != 3:
                continue
            if 'FILTER' in triple or 'filter' in triple:
                '''TODO很复杂'''
                pass
            head = triple.split(' ')[0]
            relation = triple.split(' ')[1]
            tail = triple.split(' ')[2]
            if head == self.firstVar:
                dot.node(head.split(':')[-1], head, shape='diamond')
            else:
                dot.node(head.split(':')[-1], head)
            if tail == self.firstVar:
                dot.node(tail.split(':')[-1], tail, shape='diamond')
            else:
                dot.node(tail.split(':')[-1], tail)
            dot.edge(head.split(':')[-1], tail.split(':')[-1], relation)

        dot.render(self.filename, 'parser/', format='jpg', cleanup=True)

    def full2abbr(self, full_uri_list):
        # 把一个完整形式的链接列表转换成缩写形式，如果是一个链接先转成列表形式
        if type(full_uri_list) != list:
            full_uri_list = [full_uri_list]
        abbr_uri_list = []
        for x in full_uri_list:
            content = x[max(x.rfind('/'), x.rfind('#')) + 1:-1];  # 获取内容
            abbr_uri = self.map_pre[x[:max(x.rfind('/'), x.rfind('#')) + 1] + '>'] + ':' + content
            abbr_uri_list.append(abbr_uri)

        return abbr_uri_list





