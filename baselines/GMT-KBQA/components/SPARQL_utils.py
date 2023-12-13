# 查询知识库的一些功能函数

# 查询知识库需要的一些函数from sys import path
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd


class KBExecutor():
    def __init__(self):
        pass

    def normalize_ent_link(self, link):
        # 将link统一化
        pass

    def query_db(self, sparql_query):
        pass

    def query_relation_degree(self, relation):
        pass

    def query_onehop_relation(self, link):
        pass

    def get_link_label(self, link, entity2label=None):  # entity2label是之前做的一个从id到label的大词典
        pass

    def answer_convert(self, item_answer):
        # sparql 的答案转格式
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


class FBExecutor(KBExecutor):
    def __init__(self):
        KBExecutor.__init__(self)
        self.endpoint = 'http://210.28.134.34:8890/sparql'

    def normalize_ent_link(self, link):
        KBExecutor.normalize_ent_link(self, link)
        if 'http://rdf.freebase.com/' in link or 'www.freebase.com/' in link:
            link = link[link.rfind('/') + 1:]
        elif link[:4] == 'ns:m' or link[:4] == 'ns:g':
            link = link[3:]
        else:
            link = link
        return link

    def query_db(self, sparql_query):
        KBExecutor.query_db(self, sparql_query)
        # 查询函数，输入完整query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)  # ;df=pd.DataFrame.from_dict(answer)
        return answer

    def query_relation_degree(self, relation):
        KBExecutor.query_relation_degree(self, relation)
        # 查询关系在知识库上的频次
        sparql_query = "PREFIX ns: <http://rdf.freebase.com/ns/> select count(?s) where{?s " + relation + " ?o}"
        answer = int(self.query_db(sparql_query)[0])
        return answer

    def query_onehop_relation(self, link):
        KBExecutor.query_onehop_relation(self, link)
        link = self.normalize_ent_link(link)
        # 输入entity的mid,获取一个entity直接相连的所有triple，返回df，并返回每个谓词的词频pvc
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery("""PREFIX ns: <http://rdf.freebase.com/ns/>
                            SELECT DISTINCT ?p ?o
                            WHERE {FILTER (!isLiteral(?o) OR lang(?o) = '' OR langMatches(lang(?o), 'en'))
                            ns:""" + link + """ ?p ?o .
                            }""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        df = pd.DataFrame.from_dict(answer)
        pvc = df.p.value_counts()
        return pvc

    def query_link_label(self, link, entity2label=None):
        # 之前的api叫get_link_label
        KBExecutor.get_link_label(self, link)
        # 获取mid的label，可以接受m. g.或者ns:m. ns:g.或者http://rdf.freebase.com/m. g.
        link = self.normalize_ent_link(link)

        if entity2label != None:
            answer = entity2label.get(link)
            if answer != None:
                return answer
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(
            """PREFIX ns: <http://rdf.freebase.com/ns/>  SELECT DISTINCT ?x  WHERE {FILTER (!isLiteral(?x) OR lang(?x) = '' OR langMatches(lang(?x), 'en')). ns:""" + str(
                link) + """     rdfs:label ?x .}""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        # df = pd.DataFrame.from_dict(answer)
        return answer

    def is_cvt(self, mid):
        return bool(len(self.get_link_label(mid)) == 0)


class DBExecutor(KBExecutor):
    # 并不完整，现在也不用
    def __init__(self):
        KBExecutor.__init__(self)
        self.endpoint = 'http://210.28.134.34:8892/sparql'

        import os
        os.environ['http_proxy'] = "http://114.212.86.137:8080/"
        os.environ['https_proxy'] = "https://114.212.86.137:8080/"
        self.endpoint = 'https://dbpedia.org/sparql/'

    def query_db(self, sparql_query):
        KBExecutor.query_db(self, sparql_query)
        # 查询函数，输入完整query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)  # ;df=pd.DataFrame.from_dict(answer)
        return answer

    def query_relation_degree(self, relation):
        KBExecutor.query_relation_degree(self, relation)
        # 查询关系在知识库上的频次
        sparql_query = "PREFIX dbp: <http://dbpedia.org/property/> PREFIX dbo: <http://dbpedia.org/ontology/> select count(?s) where{?s " + relation + " ?o}"
        answer = int(self.query_db(sparql_query)[0])
        return answer

    def query_onehop_relation(self, link):
        KBExecutor.query_onehop_relation(self, link)
        # 输入entity的mid,获取一个entity直接相连的所有triple，返回df，并返回每个谓词的词频pvc
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery("""PREFIX dbp: <http://dbpedia.org/property/> PREFIX dbo: <http://dbpedia.org/ontology/>
                            SELECT DISTINCT  ?p ?o
                            WHERE {FILTER (!isLiteral(?o) OR lang(?o) = '' OR langMatches(lang(?o), 'en'))
                            ns:""" + link + """ ?p ?o .
                            }""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        df = pd.DataFrame.from_dict(answer)
        pvc = df.p.value_counts()
        return pvc


class WDExecutor(KBExecutor):
    def __init__(self):
        KBExecutor.__init__(self)
        # self.endpoint = 'http://114.212.81.217:8890/sparql'
        # import os
        # os.environ['http_proxy'] = "http://114.212.86.137:8080/"
        # os.environ['https_proxy'] = "https://114.212.86.137:8080/"
        # # import http.client
        # # http.client.HTTPConnection._http_vsn = 10
        # # http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'
        self.endpoint = 'https://query.wikidata.org/sparql'

    def normalize_ent_link(self, link):
        KBExecutor.normalize_ent_link(self, link)
        if 'http://www.wikidata.org/entity/' in link:
            link = link[31:]
        elif link[:4] == 'wdt:':
            link = link[4:]
        elif link[:3] == 'wd:':
            link = link[3:]
        else:
            link = link
        return link

    def query_db(self, sparql_query):
        KBExecutor.query_db(self, sparql_query)
        # 查询函数，输入完整query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)  # ;df=pd.DataFrame.from_dict(answer)
        return answer

    def query_relation_degree(self, relation):
        KBExecutor.query_relation_degree(self, relation)
        # 查询关系在知识库上的频次
        sparql_query = "select count(?s) where{?s wdt:" + relation + " ?o}"
        answer = int(self.query_db(sparql_query)[0])
        return answer

    def query_onehop_relation(self, link):
        # 获取一跳关系
        KBExecutor.query_onehop_relation(self, link)
        link = self.normalize_ent_link(link)
        # 输入entity的mid,获取一个entity直接相连的所有triple，返回df，并返回每个谓词的词频pvc
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery("""SELECT DISTINCT  ?p ?o 
                            ns:""" + link + """ ?p ?o .
                            }""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        df = pd.DataFrame.from_dict(answer)
        pvc = df.p.value_counts()
        return pvc

    def query_link_label(self, link, entity2label=None):
        # 之前的api叫get_link_label
        KBExecutor.get_link_label(self, link)
        # 获取label，可以接受wdt:，wd:，或者不带这些的格式
        link = self.normalize_ent_link(link)
        # 是否有缓存
        if entity2label != None:
            answer = entity2label.get(link)
            if answer != None:
                return answer
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(
            """SELECT DISTINCT ?x  WHERE { FILTER (!isLiteral(?x) OR lang(?x) = '' OR langMatches(lang(?x), 'en')). wd:""" + str(
                link) + """     rdfs:label ?x .}""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        # df = pd.DataFrame.from_dict(answer)
        return answer
