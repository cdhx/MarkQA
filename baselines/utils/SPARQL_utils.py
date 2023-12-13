# 查询知识库的一些功能函数

# 查询知识库需要的一些函数from sys import path
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

wd_prefix = """
            prefix wdt: <http://www.wikidata.org/prop/direct/>
            prefix wdtn: <http://www.wikidata.org/prop/direct-normalized/>
            prefix p: <http://www.wikidata.org/prop/>
            prefix ps: <http://www.wikidata.org/prop/statement/>
            prefix psv: <http://www.wikidata.org/prop/statement/value/>
            prefix psn: <http://www.wikidata.org/prop/statement/value-normalized/>
            prefix pq: <http://www.wikidata.org/prop/qualifier/>
            prefix pqv: <http://www.wikidata.org/prop/qualifier/value/>
            prefix pqn: <http://www.wikidata.org/prop/qualifier/value-normalized/>
            prefix pr: <http://www.wikidata.org/prop/reference/>
            prefix prv: <http://www.wikidata.org/prop/reference/value/>
            prefix prn: <http://www.wikidata.org/prop/reference/value-normalized/>
            prefix wikibase: <http://wikiba.se/ontology#>
            prefix skos: <http://www.w3.org/2004/02/skos/core#>
            prefix wd: <http://www.wikidata.org/entity/>
"""

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

    def query_relation_instance(self, relation):
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
                        if var in cand:
                            dic_temp[var] = cand[var]['value']
                        else:
                            dic_temp[var]=""
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
        sparql.setTimeout(10)
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
    def __init__(self, endpoint='org'):
        KBExecutor.__init__(self)
        if endpoint == 'local':
            self.local = True
            self.endpoint = 'http://114.212.81.217:8895/sparql'
        else:
            self.local = False
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

    def change_endpoint(self, endpoint):
        if endpoint == 'local':
            self.endpoint = 'http://114.212.81.217:8890/sparql'
        else:
            self.endpoint = 'https://query.wikidata.org/sparql'



    def query_db(self, sparql_query):
        if self.local:
            sparql_query = wd_prefix + sparql_query
        KBExecutor.query_db(self, sparql_query)
        # 查询函数，输入完整query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setTimeout(10)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)  # ;df=pd.DataFrame.from_dict(answer)
        return answer

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
        if self.local:
            sparql.setQuery(
                """
                prefix wd: <http://www.wikidata.org/entity/>
                SELECT DISTINCT ?x  WHERE { FILTER (!isLiteral(?x) OR lang(?x) = '' OR langMatches(lang(?x), 'en')). wd:""" + str(
                    link) + """     rdfs:label ?x .}""")
        else:
            sparql.setQuery(
                """SELECT ?xLabel WHERE { 
                       BIND(wd:""" + link + """ AS ?x).
                              SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
                             }""")
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()  # json,type为dict
        answer = self.answer_convert(results)
        # df = pd.DataFrame.from_dict(answer)
        return answer

    # def query_relation_instance(self, relation, limit=None):
    #     # 获取一个关系的一些例子（输入p，输出s,o）
    #     KBExecutor.query_relation_instance(self, relation)
    #     # sparql中optional的作用是，如果是数值属性，本地端口是不能通过rdfs:label得到数字的标签的
    #     # 如果不是数值属性，o可以获得label，如果是数值属性，那么oLabel就用o代替（写在BIND（IF）中）
    #     if self.endpoint == 'http://114.212.81.217:8890/sparql':
    #         sparql_query = """select ?s ?sLabel ?o ?oLabel  where {
    #                         ?s wdt:""" + relation + """ ?o.
    #                         ?s rdfs:label ?sLabel.
    #                         OPTIONAL {
    #                             ?o rdfs:label ?oLabelx.
    #                             FILTER (!isLiteral(?oLabelx ) OR lang(?oLabelx ) = '' OR langMatches(lang(?oLabelx ), 'en')).
    #                             }.
    #                         FILTER (!isLiteral(?sLabel ) OR lang(?sLabel ) = '' OR langMatches(lang(?sLabel ), 'en')).
    #                         BIND(IF(BOUND(?oLabelx),?oLabelx,?o) AS ?oLabel).
    #                         }
    #                         """
    #     else:
    #         sparql_query = """select ?s ?sLabel ?o ?oLabel  where {
    #                         ?s wdt:""" + relation + """ ?o.
    #                         SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    #                         }
    #                         """
    #     if limit != None:
    #         sparql_query = sparql_query + 'LIMIT ' + str(limit)
    #     answer = self.query_db(sparql_query)
    #     return answer

    def query_relation_degree(self, relation):
        KBExecutor.query_relation_degree(self, relation)
        # 查询关系在知识库上的频次
        sparql_query = "select (count(*) AS ?x) where{?s wdt:" + relation + " ?o}"
        answer = int(self.query_db(sparql_query)[0])
        return answer

    def query_all_relation_instance(self, relation, use_type=True, unit=True, time=True, limit=None):
        """
        获取一个关系的所有实例的基本信息，可以去掉一些属性
        :param relation:
        :param use_type:
        :param unit:
        :param time:
        :param limit:
        :return:
        """
        sparql_query = "SELECT ?s ?sLabel ?st_num " + (" ?typeLabel " if use_type else "") + " ?quatity " + (
            " ?unitLabel " if unit else " ") + (" ?time " if time else " ") + " ?st  "\
                       """  WHERE { 
            ?s <http://wikiba.se/ontology#statements> ?st_num.                                
            ?s p:""" + relation + """ ?st.            
            ?st psv:""" + relation + """ ?st_value. 
            ?st_value wikibase:quantityAmount ?quatity.""" + \
                       ("?st pq:P585 ?time." if time else "") + \
                       ("?st_value wikibase:quantityUnit ?unit." if unit else "") + \
                       ("?s wdt:P31 ?type." if use_type else "") + \
                       """ 
           SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }   
        """
        if limit != None:
            sparql_query = sparql_query + 'LIMIT ' + str(limit)
        dic_list = self.query_db(sparql_query)
        df = pd.DataFrame(dic_list)
        return df

    def query_all_relation_instance_type_distribution(self, relation):
        """
        获取一个关系的实例类型分布
        :param relation:
        :return:
        """
        sparql_query = """
        SELECT ?typeLabel (COUNT(?typeLabel) AS ?num)
        WHERE
        { 
          ?s p:"""+relation+"/psv:"+relation+""" ?st .           
          ?s wdt:P31 ?type.
          ?s <http://wikiba.se/ontology#statements> ?st_num.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } 
        }GROUP BY ?typeLabel
        ORDER BY DESC(COUNT(?typeLabel))
        """
        dic_list = self.query_db(sparql_query)
        df = pd.DataFrame(dic_list)
        return df
    def query_instance_with_type(self,type):
        """
        给定类型，返回类型下所有实例，按照statement数量排序
        :param type:
        :return:
        """
        sparql_query = """
        SELECT ?s ?sLabel ?st_num 
        WHERE { 
         ?s wdt:P31 wd:"""+type+""".
          ?s <http://wikiba.se/ontology#statements> ?st_num.      
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
         }
        ORDER BY DESC(?st_num)
        """
        dic_list = self.query_db(sparql_query)
        df = pd.DataFrame(dic_list)
        return df

if __name__ == "__main__":
    test = WDExecutor()
    sparql = """
    select ?s ?sLabel
    where{
        ?s wdt:P31 wdt:Q118365.
        ?s rdfs:label ?sLabel.
    }
    """
    print(test.query_db(sparql))
