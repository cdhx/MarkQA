# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     sparql_generator
   Description : 不用自动生成tag的方法了，人工指定，因为自动获取tag还是要找地方接收，还是要起名字，没有少写
                  而且有的子查询需要不同的名字，比如中国第一高的山和第二高的山，这两个子查询最后得到的变量名是相同的，没办法在外层一起用
                  或者射程大于600米的火箭炮的平均速度比射程小于600米的火箭炮的平均速度快多少，也不能自己指定
   Author :       HX
   date：          2023/3/2
-------------------------------------------------

"""
__author__ = 'HX'
# 2023.3.29 avg,sum,count 添加group by和additional return, 解决的是除了聚合变量外还要返回其他变量的问题
# 2023.4.5 修改了get_rank，之前的还要另外写filter
#          加入了to decimal, 一些判断xsd:DateTime 的地方改成了xsd:
#          add time那三个函数里还有get_label使用,全部改成?time_+entity,因为entity可能是QID也可能是变量,所以可能返回?time_QID和?time_var
# 2023.4.6 聚合中只有group by变量里面的可以额外返回，删除additional_return，并额外返回所有group by中的变量
# 2023.4.7 time=True这一行会出错 elif  'xsd:dateTime' in time: 加一个type(time) == str and
# 2023.4.8 add time改成用自定义tag
# 2023.4.9 digit_or_var加入了传入QID的处理 如果是QID，加前缀
# 2023.4.10 筛掉check_tag，没有用了，全部用check_ent_format，如果不要问号就取[1:]
#           四个get聚合改成add,需要指定tag, get_count的count_var必须手动指定，不再默认是*
# 2023.4.17 add_rank应该是对var_list做count而不是rank_var
# 聚合中只有group by变量里面的可以额外返回
# from utils.clocq import CLOCQInterfaceClient
# TODO
# 考虑一下filter的说法，不是#1中大于6的，也不是#1中大于6的#2，应该是限制#1大于6，没有  的
import re
import copy
# from utils.SPARQL_utils import *
class SPARQL_GEN():
    def __init__(self):
        # self.equation=''
        self.head = ''
        self.head_auto_flag = True  # 如果是自动的head，可以被修改
        self.answer = ''
        self.var = []
        self.value_var=[]
        self.si_value_var = []
        self.bind_mapping={}

        self.triple_pattern = []
        self.filter = []
        self.sub_query = []
        self.aggregation = []
        # self.body=self.triple_pattern+'\nOPTINAL{\t'+self.optional.replace('\n','\n\t')+'}'

        # self.var = self.find_var(self.equation + ' '.join(self.filter) + self.order)
    def __clean_info(self):
        # 清空self所有的信息
        self.head = ''
        self.head_auto_flag = True  # 如果是自动的head，可以被修改
        self.answer = ''
        self.var = []
        self.value_var=[]
        self.si_value_var = []
        self.bind_mapping={}

        self.triple_pattern = []
        self.filter = []
        self.sub_query = []
        self.aggregation = []
    def __construct_sub_query(self):
        sub_query = ''
        for sub_q in self.sub_query:
            sub_query = sub_query + '\n{'
            if type(sub_q) == SPARQL_GEN:
                sub_query = sub_query + self.__brace_indent('\n'+sub_q.sparql) + '\n}'
            else:
                sub_query = sub_query + self.__brace_indent('\n'+sub_q) + '\n}'
        return sub_query

    def __construct_triple_pattern(self):
        return '\n'+'\n'.join(self.triple_pattern)

    def __construct_aggregation(self):
        return '\n'.join(self.aggregation)

    def __brace_indent(self, script, indent=True):
        result = ''
        if indent:
            result = script.replace('\n', '\n\t')
        return result

    def __get_label(self,*args):
        # TODO
        label_list=[x for x in args]
        # label_list=[self.clocq_client.get_label(x).replace(' ', '_').replace('.', '').replace('-', '_').replace("'", '_').replace('+', '_').replace('/', '_').replace(',', '').replace(')', '').replace('(', '')  for x in args]
        return '_'.join(label_list)

    @property
    def bind_var(self):
        return list(self.bind_mapping.values())

    @property
    def sparql(self):
        self.triple_pattern_text = self.__construct_triple_pattern()
        self.sub_query_text = self.__construct_sub_query()
        self.aggregation_text = self.__construct_aggregation()
        if self.head == '' or self.head_auto_flag == True:  # 未设置，或者是自动设置的，默认是返回查询的value，还是返回*呢,返回*不用写子查询
            # 如果指定answer了，就是answer，如果没有指定就是*，如果这个对象变成子查询了，就只返回bind的变量
            # if self.answer!='':
            #     self.head='SELECT '+self.answer
            # else:
            self.head='SELECT *'
            # 默认返回所有bind的新变量，值变量，si值变量
            # return_value = self.bind_var+self.value_var

        sparql_temp = self.head + ' {\n' + self.__brace_indent(
            self.sub_query_text + self.triple_pattern_text )  + '\n}\n'+ self.aggregation_text
        sparql_temp = sparql_temp.replace('\n\n', '\n').replace('\n\t\n\t', '\n\t').replace('\n\t\n}', '\n}')
        return sparql_temp
        # print(self.sparql)

    def add_sub_query(self,*sub_query):
        for sub_q in sub_query:
            # 如果要变成子查询,并且没有明确设定头,就返回星
            # if self.head_auto_flag == True and type(sub_q) == SPARQL_GEN:
                # 默认是*, 如果变成子查询了，并且没有主动设置head，就是可以修改的，如果有bind，就返回所有bind,如果没有bind，返回*
                # 子查询只有聚合的时候有必要使用，目前只有avg,max,count(rank)
                # if len(sub_q.bind_var)!=0:
                #     sub_q.head = 'SELECT ' + ' '.join(sub_q.bind_var)
            sub_q = sub_q.sparql
            self.sub_query.append(sub_q)
    def add_triple_pattern(self, line):
        self.triple_pattern.append(line)

    def add_quantity_by_qualifier(self,entity,main_prop,main_obj,qualifier_prop,tag,unit=False):
        '''
        数值属性在qualifier里面
        例如iPhone 12的made from material有不锈钢，玻璃，mass作为他们的qualifier
        :param entity: 实体，例如iPhone12
        :param main_prop: statement的属性,主属性，例如材料，made from material
        :param main_obj: 主属性的取值,main value，例如不锈钢
        :param qualifier_prop: 做qualifier的属性,这里是数值属性，例如质量
        :param tag:
        :param unit:
        :return: tag
        没有year了,除非和数值属性一样,做qualifier,这种统统过滤不要太复杂了
        e.g.
            wds:Q56599233-255fd1d3-4a10-b25e-9b7d-33d247d579cb
            wd:Q56599233 p:P186 ?statement.
            ?statement ps:P186  wd:Q172587.
            ?statement pqv:P2067 ?value_st.
            ?value_st wikibase:quantityAmount ?value.
            ?value_st wikibase:quantityUnit ?unit.

            a=SPARQL_GEN()
            a.add_quantity_by_qualifier(['Q56599233','P186','Q172587','P2067','stain_mass',True],
                                        ['Q56599233','P186','Q267298','P2067','stain_mass',True],
                                        ['Q56599233','P186','Q11469','P2067','stain_mass',True],)
            print(a.sparql)
        '''

        entity = self.__check_ent_format(entity)
        main_prop = self.__check_prop_format(main_prop)
        main_obj = self.__check_ent_format(main_obj)
        qualifier_prop = self.__check_prop_format(qualifier_prop)
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        main_obj_with_prefix= 'wd:' + main_obj if main_obj[0]=='Q' else main_obj
        tag= self.__check_ent_format(tag)[1:]

        if unit:
            statement_var = "?statement_" + tag
            value_var = '?non_si_' + tag
            value_st_var = "?non_si_value_st_" + tag
            si_conversion_var = '?si_conversion_' + tag
            si_value_var = '?' + tag
        else:
            statement_var="?statement_" + tag
            value_var='?'+tag
            value_st_var="?value_st_" + tag

        self.add_triple_pattern(entity_with_prefix + " p:" + main_prop + " " + statement_var + ".")
        self.add_triple_pattern(statement_var + " ps:" + main_prop + ' '+main_obj_with_prefix+".") # 限制main value
        self.add_triple_pattern(statement_var + " pqv:" + qualifier_prop + " " + value_st_var + ".")
        self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")
        if unit:
            # 不应该有哪个查询限制单位，又不是既有m记录的又有cm记录的，单位和时间还不一样
            # 单位应该全部默认是true加单位转换
            self.add_triple_pattern(value_st_var+ " wikibase:quantityUnit/p:P2370/psv:P2370/wikibase:quantityAmount " + si_conversion_var + ".")
            self.add_bind(value_var + ' * '+si_conversion_var, si_value_var)

        self.add_triple_pattern('\n')

        return tag
    def add_quantity_with_qualifier(self,entity,main_prop,qualifier_prop,qualifier_obj,tag,unit=False):
        '''
        获取数值属性值,但是有qualifier约束其他属性
        例如3090的性能，有三个数值记录，分别被（应用场景：单精度），（应用场景：半精度），（应用场景：双精度），修饰
        :param entity: 实体  例如3090
        :param main_prop: statement的属性,主属性,这里是数值属性，例如性能
        :param qualifier_prop: qualifier属性，例如应用场景 applies to part
        :param qualifier_obj: qualifier属性的取值，例如单精度，半精度，双精度
        :param tag:
        :param unit:
        :return:
        '''

        entity = self.__check_ent_format(entity)
        main_prop = self.__check_prop_format(main_prop)
        qualifier_prop = self.__check_prop_format(qualifier_prop)
        qualifier_obj = self.__check_ent_format(qualifier_obj)
        # 如果是变量不加前缀
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        qualifier_obj_with_prefix= 'wd:' + qualifier_obj if qualifier_obj[0]=='Q' else qualifier_obj
        tag= self.__check_ent_format(tag)[1:]

        if unit:
            statement_var = "?statement_" + tag
            value_var = '?non_si_' + tag
            value_st_var = "?non_si_value_st_" + tag
            si_conversion_var = '?si_conversion_' + tag
            si_value_var = '?' + tag
        else:
            statement_var="?statement_" + tag
            value_var='?'+tag
            value_st_var="?value_st_" + tag


        self.add_triple_pattern(entity_with_prefix + " p:" + main_prop + " " + statement_var + "." )
        self.add_triple_pattern(statement_var + " psv:" + main_prop + " " + value_st_var + ".")
        self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")
        self.add_triple_pattern(statement_var + " pq:" + qualifier_prop + ' ' + qualifier_obj_with_prefix + ".")  # 限制qualifier取值

        if unit:
            # 不应该有哪个查询限制单位，又不是既有m记录的又有cm记录的，单位和时间还不一样
            # 单位应该全部默认是true加单位转换
            self.add_triple_pattern(value_st_var+ " wikibase:quantityUnit/p:P2370/psv:P2370/wikibase:quantityAmount " + si_conversion_var + ".")
            self.add_bind(value_var + ' * '+si_conversion_var, si_value_var)


        self.add_triple_pattern('\n')

        return tag
    def add_quantity(self,entity, prop, tag,time=False, unit=False):
        '''
        获取数值属性的值
        :param entity: 实体
        :param prop: 数值属性
        :param time: 时间限制，填年份就是约束这一年,可以填年份或者用to_date填完整年月日，填True就是要获取时间，不填就是不管时间
        :param unit: 单位转换，填True就是要转换，不填就是不转换，转换后的变量是si_value_tag和si_unit_tag
        :return: tag　可以通过to_value_var()获取?value_tag，to_unit_var()获取?unit_tag，to_time_var()获取?time_tag
        '''
        # 处理包含多个字典的参数列表
        entity=self.__check_ent_format(entity)
        prop=self.__check_prop_format(prop)
        tag= self.__check_ent_format(tag)[1:]

        # 如果是变量不加前缀
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity

        if unit:
            statement_var = "?statement_" + tag
            value_var = '?non_si_' + tag
            value_st_var = "?non_si_value_st_" + tag
            si_conversion_var = '?si_conversion_' + tag
            si_value_var = '?' + tag
            time_var = '?time_' + tag
        else:
            statement_var="?statement_" + tag
            value_var='?'+tag
            value_st_var="?value_st_" + tag
            time_var='?time_'+tag

        if time:
            # 不只是时间，如果要用到其他qualifier也需要，但是暂时用不到
            # 如果要获取或者限制时间，就要获取statement
            self.add_triple_pattern(entity_with_prefix + " p:" + prop + " "+statement_var + ".")
            if unit:
                self.add_triple_pattern(statement_var + " psv:" + prop + " "+value_st_var + ".")
                self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")
            else:
                self.add_triple_pattern(statement_var + " psv:" + prop + "/wikibase:quantityAmount "+value_var + ".")

        else:
            # 不用时间就可以合并一句SPARQL
            if unit:
                self.add_triple_pattern(entity_with_prefix + " p:" + prop + "/psv:" + prop + " "+value_st_var + ".")
                self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")
            else:
                self.add_triple_pattern(entity_with_prefix + " p:" + prop + "/psv:" + prop + "/wikibase:quantityAmount "+value_var + ".")

        if unit:
            # 不应该有哪个查询限制单位，又不是既有m记录的又有cm记录的，单位和时间还不一样
            # 单位应该全部默认是true加单位转换
            self.add_triple_pattern(value_st_var+ " wikibase:quantityUnit/p:P2370/psv:P2370/wikibase:quantityAmount " + si_conversion_var + ".")
            self.add_bind(value_var + ' * '+si_conversion_var, si_value_var)
            # add_bind默认是加一个\n在最后的，这里这一段还没结束，给他去掉
            if self.triple_pattern[-1]=='\n':
                self.triple_pattern=self.triple_pattern[:-1]

        if time:
            # 如果是一串数字,就是年份
            if (type(time) == str and re.match('^[0-9]*$', time.strip())) or type(time) == int:
                self.add_triple_pattern(statement_var + " pq:P585 "+time_var + ".")
                self.add_filter("YEAR("+time_var + ")","=" , str(time))
            # 如果是变量
                # 要不要简化到YEAR，还是具体日期，东京奥运会开幕的那一天的新冠感染（查出来是什么就是什么），东京奥运会举办的那一年的GDP（需要加YEAR修饰），东京奥运会举办期间的新冠感染（求开始结束时间），不一样
            elif type(time) == str and time[0] == '?':
                self.add_triple_pattern(statement_var + " pq:P585 " + time + ".")
            # 如果是完整的年月日，可以当成变量直接约束，不用filter
            elif type(time) == str and 'xsd:dateTime' in time:
                self.add_triple_pattern(statement_var + " pq:P585 " + time + ".")
            # 其他情况，视为要获取时间
            else:
                self.add_triple_pattern(statement_var + " pq:P585 "+time_var+ ".")


        self.add_triple_pattern('\n')

        return tag

    def add_quantity_by_qualifier_answer(self, entity, main_prop, main_obj, qualifier_prop, tag, unit=False):
        # answer版本的add_quantity_by_qualifier,当属性值要作为答案的时候使用(最外层查询最后一步)
        self.add_quantity_by_qualifier(entity, main_prop, main_obj, qualifier_prop, tag, unit)
        self.__set_answer(tag)

    def add_quantity_with_qualifier_answer(self, entity, main_prop, qualifier_prop, qualifier_obj, tag, unit=False):
        # answer版本的add_quantity_with_qualifier,当属性值要作为答案的时候使用(最外层查询最后一步)
        self.add_quantity_with_qualifier(entity, main_prop, qualifier_prop, qualifier_obj, tag, unit)
        self.__set_answer(tag)

    def add_quantity_answer(self,entity, prop, tag,time=False, unit=False):
        # answer版本的add_quantity,当属性值要作为答案的时候使用(最外层查询最后一步)
        self.add_quantity(entity, prop, tag,time, unit)
        self.__set_answer(tag)

    def add_wdt_fact_answer(self, s, p, o, answer):
        # answer版本的add_wdt_fact,当spo中有要作为答案的时候使用(最外层查询最后一步),需要指定answer是谁
        self.add_wdt_fact(s, p, o)
        self.__set_answer(answer)
    def add_wdt_fact(self,s,p,o):
        '''
        添加wdt前缀的事实
        :param s: 主
        :param p: 谓
        :param o: 宾
        :return: 没有返回值，因为肯定要在参数列表里写变量，直接copy出来用就行了，没有返回的必要
        '''
        self.__add_fact(s,p,o,'wdt')
    def add_p_fact(self,s,p,o):
        '''
        添加p前缀的事实,目前似乎没有要用到这种情况的，用到了说一下
        :param s: 主
        :param p: 谓
        :param o: 宾
        :return: 没有返回值，因为肯定要在参数列表里写变量，直接copy出来用就行了，没有返回的必要
        '''
        self.__add_fact(s,p,o,'p')
    def add_pq_fact(self,s,p,o):
        '''
        添加pq前缀的事实,目前似乎没有要用到这种情况的，用到了说一下
        :param s: 主
        :param p: 谓
        :param o: 宾
        :return: 没有返回值，因为肯定要在参数列表里写变量，直接copy出来用就行了，没有返回的必要
        '''
        self.__add_fact(s,p,o,'pq')
    def add_pqv_fact(self,s,p,o):
        '''
        添加pqv前缀的事实,目前似乎没有要用到这种情况的，用到了说一下
        :param s: 主
        :param p: 谓
        :param o: 宾
        :return: 没有返回值，因为肯定要在参数列表里写变量，直接copy出来用就行了，没有返回的必要
        '''
        self.__add_fact(s,p,o,'pqv')

    def __add_fact(self, s, p, o, p_prefix):
        '''
        添加三元组fact，被封装在add_wdt_fact，add_p_fact，add_pq_fact，add_pqv_fact里面了
        :param s:
        :param p:
        :param o:
        :param p_prefix:
        :return: 没有返回值，新变量要自己起名字
        '''
        s = self.__check_ent_format(s)
        p = self.__check_prop_format(p)
        o = self.__check_ent_format(o)

        if s[0]=='Q':#如果是实体,加前缀,否则就是变量不用管
            s='wd:'+s if s[0]=='Q' else s
        if o[0] == 'Q':
            o = 'wd:' + o if o[0]=='Q' else o
        p=p_prefix+':'+p
        self.add_triple_pattern(s+' '+p+' '+o+'.')
        self.add_triple_pattern('\n')

    def add_bind(self, equation, var_name):
        '''
        添加bind关系，equation和要绑定的新名字, 要bind的不是答案用这个,如果要bind的是答案用add_bind_answer
        :param equation: 算式，不要加括号，会自己加
        :param var_name: 可以不写？,一定是变量，而且一定要自己手写字符串起名字的新变量
        :return:返回新变量的名字
        '''
        var_name = self.__check_ent_format(var_name)
        # 如果是单位转换用到的bind，不加到bind里
        if re.match('^\?si_value_.*?', var_name) and ' * ?si_conversion' in equation and re.match('^\?value_.*?', equation):
            pass
        else:
            self.bind_mapping[equation]=var_name
        self.add_triple_pattern('BIND( (' + equation + ') AS ' + var_name + ' )')
        self.add_triple_pattern('\n')
        return var_name
    def add_bind_answer(self,equation,var_name):
        '''
        只能用在最外层最后一步，用完整个SPARQL生成结束，绑定出来的新变量是最终的answer，在这里顺带把self.answer修改了，select 后面直接跟那个要返回的
        :param equation: 算式，不要加括号，会自己加
        :param var_name: 可以不写？,一定是变量，而且一定要自己手写字符串起名字的新变量
        :return: 没有返回值，最外层查询，整个查询的生成结束
        '''
        var_name=self.add_bind(equation,var_name) # 返回一下是为了接收to_var规范化的var_name?
        self.__set_answer(var_name)

    def add_type_constrain(self, type_id, new_var):
        '''
        加类型约束，
        :param type_id: 类型ID
        :param new_var: 是这个类型的变量
        :return: 一个变量
        '''
        type_id=self.__check_ent_format(type_id)
        ent=self.__check_ent_format(new_var)
        self.add_triple_pattern(ent + " wdt:P31/wdt:P279* wd:" + type_id + ".")
        self.add_triple_pattern('\n')
        return ent

    def add_filter(self, compare_obj1, operator, compare_obj2):
        '''
        添加filter，给定两个比较对象和做什么比较
        :param compare_obj1: 比较对象1
        :param operator: >,<,>=,<=,=
        :param compare_obj2: 比较对象2
        :return: 过滤性的功能没有返回值
        '''
        operator=self.__check_op(operator)
        compare_obj1 = digit_or_var(compare_obj1)
        compare_obj2=digit_or_var(compare_obj2)
        self.add_triple_pattern("FILTER(" + str(compare_obj1) +' '+ operator +' '+ str(compare_obj2) + ').')
        self.add_triple_pattern('\n')

    # avg,sum,count,rank,都是自动命名，不需要传tag
    def add_avg(self,avg_var, new_var, group_obj=None):
        '''
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        添加avg，传入一个变量，不能传算式
        :param avg_var: 对什么做平均,变量，不可以是算式，如果是算式再bind一次
        :param group_obj: 如果要对哪个变量做group by
        :return: 平均后新变量的名字，因为可能是子查询，所以变量名还是要返回的
        '''
        avg_var=self.__check_ent_format(avg_var)
        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # new_var=avg_var+('_avg_by_'+to_unvar(group_obj) if group_obj!=None else '_avg')
        # 如果之前调用过max min，要先用子查询包一下才能求和，求平均，求count,rank
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy一个作为要添加的子查询
            # 清空self所有的信息
            self.__clean_info()
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (AVG(' + avg_var + ') AS ' + new_var + ' ) '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (AVG(' + avg_var + ') AS ' + new_var + ' ) ')
        # 不需要添加bind，因为只能写成聚合，放在head里
        # self.bind_mapping[equation]=var_name
        # self.add_triple_pattern('BIND( AVG(' + equation + ') AS ' + var_name + ' )')
        return new_var

    def add_sum(self,sum_var, new_var, group_obj=None):
        '''
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        添加SUM,传入一个变量，不能传算式
        :param tag:
        :param sum_var: 对什么做求和,变量，不可以是算式，如果是算式再bind一次
        :param group_obj: 如果要对哪个变量做group by
        :return: 平均后新变量的名字，因为可能是子查询，所以变量名还是要返回的
        '''
        sum_var=self.__check_ent_format(sum_var)
        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # new_var=sum_var+('_sum_by_'+to_unvar(group_obj) if group_obj!=None else '_sum')
        # 如果之前调用过max min，要先用子查询包一下才能求和，求平均，求count,rank
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy一个作为要添加的子查询
            # 清空self所有的信息
            self.__clean_info()
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (SUM(' + sum_var + ') AS ' + new_var + ' ) '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (SUM(' + sum_var + ') AS ' + new_var + ' ) ')
        # 不需要添加bind，因为只能写成聚合，放在head里
        # self.bind_mapping[equation]=var_name
        # self.add_triple_pattern('BIND( SUM(' + equation + ') AS ' + var_name + ' )')
        return new_var

    def add_rank(self, rank_var, var_list,new_var):
        '''
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        问排名的时候式对FILTER筛选过后的实体做计数
        :param rank_var: 对谁计数
        :param var_lsit: 包含var的完整list
        :return: 新变量的名字，rank_var加_rank
        '''
        rank_var=self.__check_ent_format(rank_var)
        var_list = self.__check_ent_format(var_list)

        new_var=self.__check_ent_format(new_var)

        # new_var=rank_var+'_rank'

        self.add_filter(rank_var,'<',var_list)
        # 如果之前调用过max min，要先用子查询包一下才能求和，求平均，求count,rank
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy一个作为要添加的子查询
            # 清空self所有的信息
            self.__clean_info()
            self.add_sub_query(temp)
        self.set_head('SELECT (COUNT(DISTINCT ' + var_list + ')+1 AS '+new_var+ ")" )
        return new_var

    def add_count(self,count_obj,new_var, group_obj=None):
        '''
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        添加count部分
        :param count_obj: 要对什么计数,代表多值属性的变量 ，比如这里的?diplomatic，(COUNT(?diplomatic) AS ?diplomatic_count)，默认是*
        :param group_obj: 按照什么聚合,代表主语，比如这里的 ?country
        新命名的计数变量的命名规则是count_obj加'_count'，如果没填或者是*,就写死是count,如果还有group_obj，就再加'_by'+group_obj
        只要group_obj是变量,不是QID,都可以加一段GROUP没问题,不管变量是一个还是多个
        如果是对一个确定实体做,就不需要group_obj
        :return: 新变量的名字
        一个COUNT的例子
        世界上面积最大的[四个国家]的平均GDP/建交国家数量是多少
        面积前十的国家的建交国家数量
          SELECT  (COUNT(?diplomatic) AS ?ans) {
           ?country wdt:P530 ?diplomatic.
            {
          SELECT DISTINCT ?country {
            ?country wdt:P31 wd:Q6256.
            ?country p:P2046/psv:P2046 ?value_st_country_area.
            ?value_st_country_area wikibase:quantityAmount ?value_country_area.
          }
            ORDER BY DESC(?value_country_area)
            LIMIT 10
              }
            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
            } GROUP BY ?country
        '''

        count_obj=self.__check_ent_format(count_obj)

        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # 如果是count *,新变量是?count
        # if count_obj=='*':
        #     new_var='?count'
        #如果不是count *，就是count的内容加_count，如果还有group by就是count_by_xx
        # else:
        # new_var=count_obj+('_count_by_'+to_unvar(group_obj) if group_obj!=None else '_count')
        # 如果之前调用过max min，要先用子查询包一下才能求和，求平均，求count,rank
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy一个作为要添加的子查询
            # 清空self所有的信息
            self.__clean_info()
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (COUNT(DISTINCT '+count_obj+') AS '+new_var+') '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (COUNT(DISTINCT '+count_obj+') AS '+new_var+') ')

        return new_var


    def add_max(self, max_obj, return_obj='*',offset=0,limit=1):
        '''
        TODO 如果同时考虑第一名，第三名之间的关系，怎么区分命名呢,两个子查询
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        加上最高级修饰,修改head，加order by和limit
        第一名，offset 0 limit 1(默认)
        第三名，offset 2 limit 1
        第三，四，五名，offset 2 limit 3
        不是前三名，offset 3 limit None
        :param max_obj: 比较的对象 order by里面的内容
        :param return_obj: 要返回的变量，也可以写*，这样不用区分返回ent和返回value
        :param offset: 排名第几，例如第二大的，offset=2
        :param limit: 返回多少过，例如前三大的，limit=3,offset=0
        :return: 没有返回值，如果是内层查询，都返回*，可以不写，外层可以调用实体，可以调用value；
                 如果是是最外层查询，必须写return_obj，这样只有一个值返回，当?answer
                 max min本质上式一种筛选，和avg，count还不一样，【不需要有新变量出现】，筛完只剩一个，就是最值对应的
        '''
        max_obj='?'+max_obj if max_obj[0]!='?' else max_obj#要比较对象一定是变量
        return_obj = return_obj if return_obj[0] == '?' or return_obj=='*' else '?' + return_obj   # 返回的对象一定是变量
        self.set_head('SELECT DISTINCT ' + return_obj)
        self.aggregation.append("ORDER BY DESC(" + max_obj + ")")
        if limit!=None:
            self.aggregation.append("LIMIT "+str(limit))
        if offset!=0:
            self.aggregation.append("OFFSET "+str(offset))

    def add_min(self, min_obj, return_obj='*',offset=0,limit=1):
        '''
        只能在完整查询或者子查询最后一步使用，使用后要么整个查询结束，要么作为一个子查询
        加上最低级修饰,修改head，加order by和limit
        :param max_obj: 比较的对象
        :param return_obj: 要返回的变量，也可以写*
        :param offset: 排名第几，例如第二小的，offset=2
        :param limit: 返回多少过，例如前三小的，limit=3,offset=0
        :return: 没有返回值，如果是内层查询，可以不写，都返回*，这样外层可以调用实体，可以调用value；
                 如果是是最外层查询，必须写return_obj，这样只有一个值返回，当?answer
                 max min本质上式一种筛选，和avg，count还不一样，【不需要有新变量出现】，筛完只剩一个，就是最值对应的
        '''
        min_obj='?'+min_obj if min_obj[0]!='?' else min_obj#要比较对象一定是变量
        return_obj = return_obj if return_obj[0] == '?' or return_obj=='*' else '?' + return_obj   # 返回的对象一定是变量
        self.set_head('SELECT DISTINCT ' + return_obj)
        self.aggregation.append("ORDER BY (" + min_obj + ")")
        if limit != None:
            self.aggregation.append("LIMIT " + str(limit))
        if offset!=0:
            self.aggregation.append("OFFSET "+str(offset))


    def add_compare(self, obj1, op, obj2):
        '''
        只能用在最外层查询的最后一步，用完整个SPARQL生成结束，布尔问题一定是最后一步
        布尔问题，A是否大于B，A是否能排进前三（A的排名, <=, 3）
        :param obj1: 比较对象1
        :param op: 运算符
        :param obj2: 比较对象2
        :return: 不需要返回值，布尔问题一定是最外层查询
        例如这种问题：胡安卡洛斯一世的航程是否能够沿着马里兰州，密歇根州海岸线各行驶一次
        '''
        op=self.__check_op(op)
        obj1 = digit_or_var(obj1)
        obj2 = digit_or_var(obj2)
        self.add_bind("IF(" + obj1 + " " + op + " " + obj2 + ", TRUE, FALSE)", "?answer")
        self.set_head("SELECT ?answer")

    # def get_bigger_var(self, obj1, obj2,new_var):
    #     '''
    #     !!!!先不要用
    #     对两个个只有一个值的变量取最大
    #     只能用在最外层函数的最后一步,因为设置了head而且没有重命名的能力
    #     这两个函数结合起来可以问一些不确定大小的问题,例如A和B中更大的比更小的大多少
    #     :param para_list:
    #     :return:
    #     '''
    #     obj1 = digit_or_var(obj1)
    #     obj2 = digit_or_var(obj2)
    #     new_var= digit_or_var(new_var)
    #     self.add_bind("IF(" + obj1 + " > " + obj2 + ", "+obj1+", "+obj2+")", new_var)
    #     self.set_head("SELECT "+new_var)
    # def get_smaller_var(self, obj1, obj2,new_var):
    #     '''
    #     !!!!先不要用
    #     对两个个只有一个值的变量取最小
    #     只能用在最后一步
    #     :param para_list:
    #     :return:
    #     '''
    #     obj1=digit_or_var(obj1)
    #     obj2 = digit_or_var(obj2)
    #     new_var= digit_or_var(new_var)
    #     self.add_bind("IF(" + obj1 + " > " + obj2 + ", "+obj1+", "+obj2+")", new_var)
    #     self.set_head("SELECT "+ new_var)

    def add_assignment(self,var_list,new_var):
        '''
        Values, 把多个变量合成一个变量
        :param var_list: 列表，要合成一个变量的，变量或实体列表['Q123','?X','Q186']
        :param new_var: 合成的新变量的名字
        :return: 合成的新变量名字
        例如，Q319和Q2347978中谁的速度更快，结合add_max可以求出
        a=SPARQL_GEN()
        a.add_assignment(['Q319','Q2347978'],'car')
        a.add_quantity(car,'P2052','car_speed)
        a.add_max('car_speed','car')
        print(a.sparql)
        '''
        var_list=[self.__check_ent_format(x) for x in var_list]
        # 如果是QID，要加wdt:，如果是变量不用加
        var_list=['wd:'+x if x[0]=='Q' else x for x in var_list]
        self.add_triple_pattern('Values '+self.__check_ent_format(new_var)+' {'+' '.join(var_list)+'}')
        return new_var

    def set_head(self, head):
        '''
        修改head的地方,直接输入最终表示, 修改后不再使用默认的返回变量(bind变量或者*)
        优先级最高
        :param head: 完整形式的head
        :return: 不需要return
        '''
        self.head = head
        self.head_auto_flag = False

    def __set_answer(self,answer):
        '''
        暂时似乎没有用到的地方
        设置self.answer，最终的返回值
        :param answer: 要把谁当作answer
        :return: 没有返回值
        '''
        answer=self.__check_ent_format(answer)
        self.set_head('SELECT '+answer)

    def __check_op(self,op):
        '''
        检查operator是否合法
        :param op: > < >= <= =, gt, ge, lt, le, e
        :return: op
        '''
        op=op.strip()
        if op == 'gt' or op=='>':
            operator = '>'
        elif op == 'ge' or op=='>=':
            operator = '>='
        elif op == 'lt' or op=='<':
            operator = '<'
        elif op == 'le' or op=='<=':
            operator = '<='
        elif op == 'e' or op=='=':
            operator = '='
        elif op=='!=' or op=='ne':
            operator='!='
        else:
            raise Exception(
                'compare operator format error, op should be gt, ge, lt, le, e, ne or >, <, >=, <=, =,!= while you operator is ' + op)
        return operator

    def __check_ent_format(self, entity):
        '''
        # 检查实体格式,和digit or var的区别是这个会去掉前缀并且不考虑算式
        得到QID，或者变量,或者纯数字,不可能是算式不可以让实体是字符串型的字面量,否则所有的变量传入的时候都需要写?了
        :param entity: * QID，wd:QID， 纯数字，    时间或者数字(^^xsd:)  其他情况
        :return:       * QID,   QID  , 纯数字  ,  时间或者数字(^^xsd:)  ?var
        '''
        # 这两个check不好设计,有的输入里有前缀的,如果删掉又不知道前缀什么了,不删的话有的函数里又给了前缀

        entity=str(entity).strip()
        if entity=='*':
            entity=entity
        if entity[0] == '?': # 如果是变量,不变
            entity = entity
        elif re.match('^wd:Q\d+$', entity) or re.match('^wd:q\d+$', entity):  # 如果是wd:QID,去掉前缀
            entity = 'Q' + entity[4:]
        elif re.match('^Q\d+$', entity) or re.match('^q\d+$', entity):# 如果是QID
            entity = 'Q' + entity[1:]
        elif re.match('^(\-|\+)?\d+(\.\d+)?$', entity):# 纯数字,当作纯数字
            entity = entity
        elif '^^xsd:' in entity:#时间,不变
            entity=entity
        else:# 其他情况当作变量没加?
            entity='?'+' '.join(entity.split()).replace(' ','_')
        return entity

    def __check_prop_format(self, prop):
        '''
        得到PID，或者变量
        :param entity: PID，wdt:PID，p:PID，...  纯数字，其他情况
        :return:       PID,   PID  , PID  ,     PID   ， ?var
        '''
        # 检查property格式,得到PID,!!没有前缀!!,只在不需要前缀的时候用
        prop=prop.strip()
        if re.match('^P\d+$', prop) or re.match('^p\d+$', prop):# 如果是PID
            prop = 'P' + prop[1:]
        elif re.match('^\d+$', prop): # 如果是纯数字
            prop = 'P' + prop
        return prop

    def __check_tag(self,tag):
        '''
        得到tag，是一个字符串，没有问号，没有下划线
        :param tag: 字符串
        :return: _xxxxx
        '''
        tag=tag.strip()
        tag = ' '.join(tag.split()).replace(' ', '_')
        if tag[0]=='?':
            tag=tag[1:]
        return tag

    def add_start_time(self, entity,new_var):
        entity = self.__check_ent_format(entity)  # 得到QID或者?xx
        new_var= self.__check_ent_format(new_var)

        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P580 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var
    def add_end_time(self, entity, new_var):
        entity = self.__check_ent_format(entity)  # 得到QID或者?xx
        new_var = self.__check_ent_format(new_var)

        entity_with_prefix = 'wd:' + entity if entity[0] == 'Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P582 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var
    def add_time(self, entity, new_var):
        entity = self.__check_ent_format(entity)  # 得到QID或者?xx
        new_var = self.__check_ent_format(new_var)

        entity_with_prefix = 'wd:' + entity if entity[0] == 'Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P585 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var

    # def gt(self, para1, para2):
    #     return para1 + ' > ' + para2
    #
    # def ge(self, para1, para2):
    #     return para1 + ' >= ' + para2
    #
    # def lt(self, para1, para2):
    #     return para1 + ' < ' + para2
    #
    # def le(self, para1, para2):
    #     return para1 + ' <= ' + para2


# def to_unit_var(tag):
#     '''
#     只用于tag，也就是add_quantity三个函数的返回值，得到这个tag对应的unit变量
#     从tag变为对应的unit_var,?unit_加tag
#     :param tag: 只用于tag，也就是add_quantity三个函数的返回值
#     :return: 得到这个tag对应的unit变量
#     '''
#     if tag[:6]=='?unit_':
#         return tag
#     elif tag[0] in ['?','_']:
#         tag=tag[1:]
#         return '?unit_' + tag
#     else:
#         return '?unit_' + tag
# def to_time_var(tag):
#     '''
#     只用于tag，也就是add_quantity三个函数的返回值，得到这个tag对应的time变量
#     从tag变为对应的time_var,?time_加tag
#     :param tag: 只用于tag，也就是add_quantity三个函数的返回值
#     :return: 得到这个tag对应的time变量
#     '''
#     if tag[:6]=='?time_':
#         return tag
#     elif tag[0] in ['?','_']:
#         tag=tag[1:]
#         return '?time_' + tag
#     else:
#         return '?time_' + tag
# def to_si_value_var(tag):
#     '''
#     只用于tag，也就是add_quantity三个函数的返回值，得到这个tag对应的si_value变量
#     从tag变为对应的si_value_var,?si_value_加tag
#     :param tag: 只用于tag，也就是add_quantity三个函数的返回值
#     :return: 得到这个tag对应的si_value变量
#     '''
#     # 从tag变为对应的si_value_var,?si_value_加tag
#     if tag[:10]=='?si_value_':
#         return tag
#     elif tag[0] in ['?','_']:
#         tag=tag[1:]
#         return '?si_value_' + tag
#     else:
#         return '?si_value_' + tag
# def to_si_unit_var(tag):
#     '''
#     只用于tag，也就是add_quantity三个函数的返回值，得到这个tag对应的si_unit变量
#     从tag变为对应的si_unit_var,?si_unit_加tag
#     :param tag: 只用于tag，也就是add_quantity三个函数的返回值
#     :return: 得到这个tag对应的si_unit变量
#     '''
#     if tag[:9]=='?si_unit_':
#         return tag
#     elif tag[0] in ['?','_']:
#         tag=tag[1:]
#         return '?si_unit_' + tag
#     else:
#         return '?si_unit_' + tag
# def to_unvar(var):
#     '''
#     删掉变量前的?
#     :param var:
#     :return:
#     '''
#     # 删掉变量前的?
#     # ?statement ?value_st ?value_st ?value ?unit ?si_Node ?si_conversion ?si_value ?time
#     var=var.strip()
#     if var[0]=='?':
#         var=var[1:]
#     return var

def digit_or_var(para):
    '''
    只用来限制四则运算等运算的参数
    用于数字还是变量的判断，给数字或者字符串数字，不管，如果匹配不上数字，规范化成变量
    int float也可以转成str，后面要' '.join()运算列表需要str形式的，str也可以给负数加括号
    :param para: 　 纯数字 　  负数    算式有()或者ceil,floor,YEAR,ABS开头　　　　变量
    :return: 　　　  纯数字   (负数)  　算式　　　　　　　　　　　　　　　　　　　　　变量
    '''
    para=str(para).strip()
    # 如果是字符串数字，不管
    if re.match('^(\-|\+)?\d+(\.\d+)?$', para):
        if para[0]=='-':
            para='('+para+')'
        if para[0]=='+' :
            para=para[1:]
    # 如果是算式，不做修改
    elif para.startswith('(') or para.startswith('(') or \
            para.startswith('ceil') or para.startswith('floor') or \
            para.startswith('YEAR') or para.startswith('MONTH') or  \
            para.startswith('ABS') or\
            ' * ' in para or ' + ' in para or ' - ' in para or ' / ' in para:
        return para
    # 如果是 时间, 或者数字，不变
    elif '^^xsd:'  in para:
        return para
    # 如果是变量，不变
    elif para[0]=='?':
        return para
    # 如果是wd:Qxx，不变
    elif para.startswith('wd:Q'):
        return para
    # 如果是QID，加前缀
    elif re.match('^Q\d+$', para):
        return 'wd:'+para
    # 如果不是数字也不是算式，规范成变量
    else:
        para='?'+' '.join(para.split()).replace(' ','_')
    return para

def add(*para_list):
    para_list=[str(digit_or_var(para)) for para in para_list]
    return '(' + ' + '.join(para_list) + ')'

def mul(*para_list):
    para_list = [digit_or_var(para) for para in para_list]
    return ' * '.join(para_list)

def div(para1, para2):
    para1=digit_or_var(para1)
    para2 = digit_or_var(para2)
    return para1 + ' / ' + para2

def sub(para1, para2):
    para1=digit_or_var(para1)
    para2 = digit_or_var(para2)
    return '(' + para1 + ' - ' + para2 + ')'
def abs(para):
    para=digit_or_var(para)
    return 'ABS('+str(para)+')'
def avg(*para_list):
    '''
    对多个只有一个值的变量平均,SPARQL_GEN.get_avg()是对一个有多个值的变量做平均
    a.add_bind(avg('Larzac_thrust','J85_thrust','J33_thrust'),'avg_thrust')
    BIND( (?Larzac_thrust + ?J85_thrust + ?J33_thrust) / 3) AS ?avg_thrust )
    :param para_list:
    :return:
    '''
    return div(add(*para_list),str(len(para_list)))

def ceil_mul(*para_list):
    para_list = [digit_or_var(para) for para in para_list]
    return 'ceil('+' * '.join(para_list)+')'

def ceil_div(para1, para2):
    para1=digit_or_var(para1)
    para2 = digit_or_var(para2)
    return 'ceil('+para1 + ' / ' + para2+')'

def floor_mul(*para_list):
    para_list = [digit_or_var(para) for para in para_list]
    return 'floor('+' * '.join(para_list)+')'

def floor_div(para1, para2):
    para1=digit_or_var(para1)
    para2 = digit_or_var(para2)
    return 'floor('+para1 + ' / ' + para2+')'

def year(time):
    if '^^xsd:' in time:
        time=time
    elif time.strip()[0]!='?':
        time='?'+time
    return 'YEAR('+time+')'
def month(time):
    if '^^xsd:' in time:
        time=time
    elif time.strip()[0]!='?':
        time='?'+time
    return 'MONTH('+time+')'


def to_date(year,month=1,day=1):
    # 转换成标准时间格式
    year=str(year).strip()
    month=str(month).strip()
    day=str(day).strip()

    if re.match('^\d+$',year) and re.match('^\d+$',month) and re.match('^\d+$',day):
        if int(month)<10:
            month='0'+month
        if int(day)<10:
            day='0'+day
        return '"'+str(year)+'-'+str(month)+'-'+str(day)+'"^^xsd:dateTime'
    else:
        raise ValueError("参数必须是数字或字符串数字")
def to_decimal(number):
    # 返回decimal格式的数字
    number=str(number).strip()
    if re.match('^(\-|\+)?\d+(\.\d+)?$', number):
        return '"'+number+'"^^xsd:decimal'
# ['1091205214', '1114733292', '1115029293', '1115213232', '1152133200', '1170250161', '1171836162',
# '1172639234', '1183249141', '1184439142', '12091340510', '12093224514', '12094154515', '121001341',
# '12100404519', '12103405526', '12105352529', '12121722540', '12122933565', '12123519542', '1214523106',
# '1214942107', '15165352572', '15180437620', '17150048600', '17150247602', '17150554626', '17150748627',
# '17160402583', '17161923609', '17163644634', '2105308120', '2142251480', '2224533322', '3001517396', '3010323378', '3011817393', '3125628303', '3151935483', '3160332152', '3162424310', '3163113312', '3163841314', '3164604368', '3165138424', '3165555369', '3165815370', '3170648426', '3203742386', '3205103410', '3212029140', '3220309355', '3220456356', '410512189', '4105507120', '5142749672', '5210907505', '5215605506']
# a=SPARQL_GEN()
# # Secret Hitler的最小游戏人数
# a.add_quantity('Q25339944','P1872','secret_min')
# # Cards Against Humanity的最小游戏人数
# a.add_quantity('Q5038791','P1872','card_min')
# # #1减1是多少
# a.add_bind(sub('secret_min',1),'secret_need')
# # #2减1是多少
# a.add_bind(sub('card_min',1),'card_need')
# # #3减#4是多少
# a.add_bind_answer(sub('secret_need','card_need'),'ans')
# print(a.sparql)
#
# from utils.SPARQL_utils import WDExecutor
# exe=WDExecutor()
# print(exe.query_db(a.sparql))
#


# print(exe.query_db(a.sparql))
# exe.query_db(b.sparql)
# exe.query_db(c.sparql)
# exe.query_db(e.sparql)
# exe.query_db(g.sparql)