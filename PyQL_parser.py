# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name : PyQL_parser.py 
   Description :  PyQL implementation
   Author :       HX
   date :    2023/10/24 15:33 
-------------------------------------------------
"""
__author__ = 'HX'

import re
import copy
class PyQL():
    def __init__(self):
        self.head = ''ｓｕ
        self.head_already_set = False  # If it's an automatic head, it can be modified
        self.answer = '*'
        self.var = []
        self.value_var=[]

        self.triple_pattern = []
        self.filter = []
        self.sub_query = []
        self.aggregation = []

    def __clean_info(self):
        # Clear all information in this PyQL
        self.head = ''
        self.head_already_set = False
        self.answer = '*'
        self.var = []
        self.value_var=[]

        self.triple_pattern = []
        self.filter = []
        self.sub_query = []
        self.aggregation = []
    def __construct_sub_query(self):
        sub_query = ''
        for sub_q in self.sub_query:
            sub_query = sub_query + '\n{'
            if type(sub_q) == PyQL:
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

    def set_head(self, head):
        '''
        Where head is modified, enter the final representation directly, and the default return variable (self.answer) is no longer used after the modification.
        Highest priority, this is used in min, max, avg where there is no way to change it again
        :param head: head of this sparql
        :return: No need
        '''
        self.head = head
        # can not be changed
        self.head_already_set = True

    def set_answer(self,answer='*'):
        '''
        set self.answer explicitly
        :param answer: which variable is the answer

        '''
        answer = self.__check_ent_format(answer)

        self.answer=answer


    @property
    def sparql_inner(self):
        # used for sparql of inner query,where we want the inner query return every variable as it can
        self.triple_pattern_text = self.__construct_triple_pattern()
        self.sub_query_text = self.__construct_sub_query()
        self.aggregation_text = self.__construct_aggregation()

        # If it's not a query that can only return some specific variable, it returns all of the variable
        if not self.head_already_set:
            if 'ORDER BY' in self.aggregation_text:
                self.head='SELECT DISTINCT '+self.answer
            else:
                self.head = 'SELECT DISTINCT *'

        sparql_temp = self.head + ' {\n' + self.__brace_indent(
            self.sub_query_text + self.triple_pattern_text) + '\n}\n' + self.aggregation_text
        sparql_temp = sparql_temp.replace('\n\n', '\n').replace('\n\t\n\t', '\n\t').replace('\n\t\n}', '\n}')
        return sparql_temp
    @property
    def sparql(self):
        self.triple_pattern_text = self.__construct_triple_pattern()
        self.sub_query_text = self.__construct_sub_query()
        self.aggregation_text = self.__construct_aggregation()

        if not self.head_already_set:
            self.head='SELECT DISTINCT '+self.answer


        sparql_temp = self.head + ' {\n' + self.__brace_indent(
            self.sub_query_text + self.triple_pattern_text )  + '\n}\n'+ self.aggregation_text
        sparql_temp = sparql_temp.replace('\n\n', '\n').replace('\n\t\n\t', '\n\t').replace('\n\t\n}', '\n}')
        return sparql_temp
    def add_sub_query(self,*sub_query):
        for sub_q in sub_query:
            # append the sparql of sub_query into outer query
            sub_q = sub_q.sparql_inner
            self.sub_query.append(sub_q)
    def add_triple_pattern(self, line):
        '''
        add a line of sparql
        :param line: any format of sparql line
        '''
        self.triple_pattern.append(line)

    def add_quantity_by_qualifier(self,entity,main_prop,main_obj,qualifier_prop,tag):
        '''
        add a fact whose qualifier is a quantity qualifier,here is an example
        <wd:Q56599233(iPhone XS Max), p:P1223(made from material), wds:Q56599233-255fd1d3-4a10-b25e-9b7d-33d247d579cb>
        <wds:Q56599233-255fd1d3-4a10-b25e-9b7d-33d247d579cb, pq:P2067(mass), 67>
        <statement, ps:P123(made from material),  wd:Q172587(stainless steel)>

        :param entity: entity, in this case is: iPhone XS Max
        :param main_prop: the property of the statement(main property), in this case is: made from material
        :param main_obj: the value of main_prop, in this case is: stainless steel
        :param qualifier_prop: the property of qualifier, in this case is: mass
        :param tag: the value of qualiier,  in this case is: 67
        '''

        entity = self.__check_ent_format(entity)
        main_prop = self.__check_prop_format(main_prop)
        main_obj = self.__check_ent_format(main_obj)
        qualifier_prop = self.__check_prop_format(qualifier_prop)
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        main_obj_with_prefix= 'wd:' + main_obj if main_obj[0]=='Q' else main_obj
        tag= self.__check_ent_format(tag)[1:]

        statement_var="?statement_" + tag
        value_var='?'+tag
        value_st_var="?value_st_" + tag

        self.add_triple_pattern(entity_with_prefix + " p:" + main_prop + " " + statement_var + ".")
        self.add_triple_pattern(statement_var + " ps:" + main_prop + ' '+main_obj_with_prefix+".") # 限制main value
        self.add_triple_pattern(statement_var + " pqv:" + qualifier_prop + " " + value_st_var + ".")
        self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")

        self.add_triple_pattern('\n')

        self.set_answer(tag)
        return tag
    def add_quantity_with_qualifier(self,entity,main_prop,qualifier_prop,qualifier_obj,tag,unit=False):
        '''
        add a quantity fact which is constrained by a qualifier,here is an example
        <wd:Q110646789(Nvidia GeForce RTX 3090), p:P7256(computer performance), 	wds:Q122655985-4f6ef776-496b-c9ec-19fb-9e14a0df0303>
        <wds:Q122655985-4f6ef776-496b-c9ec-19fb-9e14a0df0303, pq:P2283(use), wd:Q1307173(single-precision floating-point format)>
        <statement, ps:P7256(computer performance),  wd:Q172587(stainless steel)>
        :param entity: entity, in this case is: iPhone XS Max
        :param main_prop:  the property of the statement(main property), in this case is: made from material
        :param qualifier_prop: the property of qualifier, in this case is: mass
        :param qualifier_obj: the value of qualifier_obj, in this case is: stainless steel
        :param tag: the value of main_prop,  in this case is: 67
        :return:
        '''
        entity = self.__check_ent_format(entity)
        main_prop = self.__check_prop_format(main_prop)
        qualifier_prop = self.__check_prop_format(qualifier_prop)
        qualifier_obj = self.__check_ent_format(qualifier_obj)
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        qualifier_obj_with_prefix= 'wd:' + qualifier_obj if qualifier_obj[0]=='Q' else qualifier_obj
        tag= self.__check_ent_format(tag)[1:]

        if unit:
            statement_var = "?statement_" + tag
            value_var = '?non_si_' + tag
            value_st_var = "?non_si_value_st_" + tag
        else:
            statement_var="?statement_" + tag
            value_var='?'+tag
            value_st_var="?value_st_" + tag

        self.add_triple_pattern(entity_with_prefix + " p:" + main_prop + " " + statement_var + "." )
        self.add_triple_pattern(statement_var + " psv:" + main_prop + " " + value_st_var + ".")
        self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")
        self.add_triple_pattern(statement_var + " pq:" + qualifier_prop + ' ' + qualifier_obj_with_prefix + ".")  # 限制qualifier取值
        self.add_triple_pattern('\n')

        self.set_answer(tag)

        return tag
    def add_quantity(self,entity, prop, tag,time=False):
        '''
        get the value of a quantity property
        :param entity: the entity
        :param prop: quantity property
        :param time: time constrain, set to a year will get the value in this year, you can use to_date function to constrain the year, month and day.
            you can also set to True to acquire the variable that represent for the timme of this fact
            If you set to False, this function will not consider the time of this fact
        :return: tag　the variable name of the quantity value
        '''
        entity=self.__check_ent_format(entity)
        prop=self.__check_prop_format(prop)
        tag= self.__check_ent_format(tag)[1:]

        # if it is a variable, do not add prefix
        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity

        statement_var="?statement_" + tag
        value_var='?'+tag
        value_st_var="?value_st_" + tag
        time_var='?time_'+tag


        self.add_triple_pattern(entity_with_prefix + " p:" + prop + " "+statement_var + ".")
        self.add_triple_pattern(statement_var + " psv:" + prop + " " + value_st_var + ".")
        self.add_triple_pattern(value_st_var + " wikibase:quantityAmount " + value_var + ".")


        if time:
            # if it is a digit, regard it as a year
            if (type(time) == str and re.match('^[0-9]*$', time.strip())) or type(time) == int:
                self.add_triple_pattern(statement_var + " pq:P585 "+time_var + ".")
                self.add_filter("YEAR("+time_var + ")","=" , str(time))
            # if it is a variable, constrain the time of this fact with this variable
            elif type(time) == str and time[0] == '?':
                self.add_triple_pattern(statement_var + " pq:P585 " + time + ".")
            # if it is a xsd:dataTime, constrain the time of this fact with this literal
            elif type(time) == str and 'xsd:dateTime' in time:
                self.add_triple_pattern(statement_var + " pq:P585 " + time + ".")
            # other cases are considered to require the creation of a time_var for further processing
            else:
                self.add_triple_pattern(statement_var + " pq:P585 "+time_var+ ".")


        self.add_triple_pattern('\n')

        self.set_answer(tag)

        return tag

    def add_fact(self, s, p, o, p_prefix):
        '''
        add a fact by subject, property, object, and the prefix of property
        :param s: subject
        :param p: property
        :param o: object
        :param p_prefix: the prefix of property
        '''
        s = self.__check_ent_format(s)
        p = self.__check_prop_format(p)
        o = self.__check_ent_format(o)

        if s[0]=='Q':# if it is an entity, add prefix
            s='wd:'+s if s[0]=='Q' else s
        if o[0] == 'Q':
            o = 'wd:' + o if o[0]=='Q' else o
        p=p_prefix+':'+p
        self.add_triple_pattern(s+' '+p+' '+o+'.')
        self.add_triple_pattern('\n')

    def add_bind(self, expression, var_name):
        '''
        add a bind phrase, bind mathematical expression  to var_name
        :param expression: a mathematical expression  or other expression
        :param var_name: the variable that represent the expression

        '''
        var_name = self.__check_ent_format(var_name)
        self.add_triple_pattern('BIND( (' + expression + ') AS ' + var_name + ' )')
        self.add_triple_pattern('\n')

        self.set_answer(var_name)


    def add_type_constrain(self, type_id, new_var):
        '''
        add a type constrain
        :param type_id: the QID of the type
        :param new_var: the variable that need to satisfy this type
        '''
        type_id=self.__check_ent_format(type_id)
        ent=self.__check_ent_format(new_var)
        self.add_triple_pattern(ent + " wdt:P31/wdt:P279* wd:" + type_id + ".")
        self.add_triple_pattern('\n')
        return ent


    def add_avg(self,avg_var, new_var, group_obj=None):
        '''
        add a phrase to calculate the average of avg_var, and name the result as new_var
        :param avg_var: calculate average on what variable
        :param new_var: the variable represent for the result of average
        :param group_obj: do group by on what variable
        '''
        avg_var=self.__check_ent_format(avg_var)
        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # if have use add_max or add_min, and forget to start a new query, we need use a new query to wrap this one
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy this query
            # clean all information of this query
            self.__clean_info()
            # add this query as a sub query
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (AVG(' + avg_var + ') AS ' + new_var + ' ) '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (AVG(' + avg_var + ') AS ' + new_var + ' ) ')
        return new_var

    def add_sum(self,sum_var, new_var, group_obj=None):
        '''
        add a phrase to calculate the summmation of sum_var, and name the result as new_var
        :param sum_var: do summation to what variable
        :param new_var: the variable represent for the result of summation
        :param group_obj: do group by on what variable
        '''
        sum_var=self.__check_ent_format(sum_var)
        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # if have use add_max or add_min, and forget to start a new query, we need use a new query to wrap this one
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy this query
            # clean all information of this query
            self.__clean_info()
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (SUM(' + sum_var + ') AS ' + new_var + ' ) '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (SUM(' + sum_var + ') AS ' + new_var + ' ) ')
        return new_var

    def add_rank(self, rank_var, var_list,new_var):
        '''
        add a phrase to calculate the rank of rank_var in var_list, and name the result as new_var
        :param rank_var: calculate rank of which variable
        :param var_lsit: the list contain rank_var
        :param new_var: the variable represent for the result of rank
        '''
        rank_var=self.__check_ent_format(rank_var)
        var_list = self.__check_ent_format(var_list)

        new_var=self.__check_ent_format(new_var)

        self.add_filter(rank_var,'<',var_list)
        # if have use add_max or add_min, and forget to start a new query, we need use a new query to wrap this one
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy this query
            # clean all information of this query
            self.__clean_info()
            self.add_sub_query(temp)
        self.set_head('SELECT (COUNT(DISTINCT ' + var_list + ') +1 AS '+new_var+ ")" )
        return new_var

    def add_count(self,count_var,new_var, group_obj=None):
        '''
        add a phrase to calculate the size of count_var, and name the result as new_var
        :param count_var: count on what variable
        :param group_obj: do group by on what variable
        :param new_var: the variable represent for the result of count
        '''

        count_var=self.__check_ent_format(count_var)

        new_var=self.__check_ent_format(new_var)
        if group_obj!=None:
            group_obj=self.__check_ent_format(group_obj)

        # if have use add_max or add_min, and forget to start a new query, we need use a new query to wrap this one
        if 'order by ' in self.sparql.lower():
            temp=copy.deepcopy(self) # copy this query
            # clean all information of this query
            self.__clean_info()
            self.add_sub_query(temp)

        if group_obj!=None:
            self.aggregation.append('GROUP BY '+self.__check_ent_format(group_obj))
            self.set_head('SELECT (COUNT(DISTINCT '+count_var+') AS '+new_var+') '+' '+self.__check_ent_format(group_obj))
        else:
            self.set_head('SELECT (COUNT(DISTINCT '+count_var+') AS '+new_var+') ')

        return new_var


    def add_max(self, max_var, return_obj='*',offset=0,limit=1):
        '''
        add a ordinal constraint constrain, where all variables that satisfy that max_var is the offset-th bigest to offset+limit-th biggest
        :param max_var: constrain on what variable
        :param return_obj: return what variable in select
        :param offset:
        :param limit:
        '''
        max_var='?'+max_var if max_var[0]!='?' else max_var
        return_obj = return_obj if return_obj[0] == '?' or return_obj.strip()=='*' else '?' + return_obj
        self.set_answer(return_obj)

        self.aggregation.append("ORDER BY DESC(" + max_var + ")")
        if limit!=None:
            self.aggregation.append("LIMIT "+str(limit))
        if offset!=0:
            self.aggregation.append("OFFSET "+str(offset))

    def add_min(self, min_obj, return_obj='*',offset=0,limit=1):
        '''
        similar to add_max
        :param max_var: constrain on what variable
        :param return_obj: return what variable in select
        :param offset:
        :param limit:
        '''
        min_obj='?'+min_obj if min_obj[0]!='?' else min_obj
        return_obj = return_obj if return_obj[0] == '?' or return_obj.strip()=='*' else '?' + return_obj
        self.set_answer(return_obj)
        self.aggregation.append("ORDER BY (" + min_obj + ")")
        if limit != None:
            self.aggregation.append("LIMIT " + str(limit))
        if offset!=0:
            self.aggregation.append("OFFSET "+str(offset))


    def add_filter(self, compare_obj1, operator, compare_obj2):
        '''
        add filter, to constrain compare_obj1 is operator to compare_obj2
        :param compare_obj1: compare object
        :param operator: >,<,>=,<=,=
        :param compare_obj2: another compare object
        '''
        operator=self.__check_op(operator)
        compare_obj1 = digit_or_var(compare_obj1)
        compare_obj2=digit_or_var(compare_obj2)
        self.add_triple_pattern("FILTER(" + str(compare_obj1) +' '+ operator +' '+ str(compare_obj2) + ').')
        self.add_triple_pattern('\n')

    def add_compare(self, obj1, op, obj2):
        '''
        for boolean question, check if obj1 is op to obj2
        :param obj1: compare obj
        :param op: operator, >, <, =, >=, <=
        :param obj2: another compare obj
        '''
        op=self.__check_op(op)
        obj1 = digit_or_var(obj1)
        obj2 = digit_or_var(obj2)
        self.add_bind("IF(" + obj1 + " " + op + " " + obj2 + ', "TRUE", "FALSE")', "?answer")
        self.set_head("SELECT ?answer")


    def add_assignment(self,var_list,new_var):
        '''
        Values in SPARQL grammmer, bind a list of entity or variable to a variable
        :param var_list: the list to bind, e.g.['Q123','Q482','Q186']
        :param new_var: the name of the variable that represent the var_list
        '''
        var_list=[self.__check_ent_format(x) for x in var_list]
        var_list=['wd:'+x if x[0]=='Q' else x for x in var_list]
        self.add_triple_pattern('Values '+self.__check_ent_format(new_var)+' {'+' '.join(var_list)+'}')
        return new_var




    def __check_op(self,op):
        '''
        check whether the op is valid
        :param op: > < >= <= =, gt, ge, lt, le, e
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
        check whether the entity is valid
        normalize to QID，or variable or digit
        :param entity: *, QID,  wd:QID, digit,  literal(^^xsd:),  other
        '''
        entity=str(entity).strip()
        if entity=='*':
            return entity

        if entity[0] == '?': # if it is a variable, do not chane
            entity = entity
        elif re.match('^wd:Q\d+$', entity) or re.match('^wd:q\d+$', entity):  # if it is wd:QID, drop prefix
            entity = 'Q' + entity[4:]
        elif re.match('^Q\d+$', entity) or re.match('^q\d+$', entity):# QID
            entity = 'Q' + entity[1:]
        elif re.match('^(\-|\+)?\d+(\.\d+)?$', entity):# digit
            entity = entity
        elif '^^xsd:' in entity:# literal
            entity=entity
        else:# other situation regard as a variable forget ?
            entity='?'+' '.join(entity.split()).replace(' ','_')
        return entity

    def __check_prop_format(self, prop):
        '''
        check whether the property is valid
        :param entity: PID,  wdt:PID,  p:PID, digit,  other
        '''
        prop=prop.strip()
        if re.match('^P\d+$', prop) or re.match('^p\d+$', prop):# 如果是PID
            prop = 'P' + prop[1:]
        elif re.match('^\d+$', prop): # 如果是纯数字
            prop = 'P' + prop
        return prop

    def __check_tag(self,tag):
        '''
        normalize a string to a string without ? and _
        :param tag: string
        '''
        tag=tag.strip()
        tag = ' '.join(tag.split()).replace(' ', '_')
        if tag[0]=='?':
            tag=tag[1:]
        return tag

    def add_start_time(self, entity,new_var):
        '''
        add a phrase to constrain start time(P580)
        :param entity: require time of which variable
        :param new_var: the variable represent the time
        '''
        entity = self.__check_ent_format(entity)
        new_var= self.__check_ent_format(new_var)

        entity_with_prefix= 'wd:' + entity if entity[0]=='Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P580 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var
    def add_end_time(self, entity, new_var):
        '''
        add a phrase to constrain end time(P582)
        :param entity: require time of which variable
        :param new_var: the variable represent the time
        '''
        entity = self.__check_ent_format(entity)
        new_var = self.__check_ent_format(new_var)

        entity_with_prefix = 'wd:' + entity if entity[0] == 'Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P582 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var
    def add_time(self, entity, new_var):
        '''
        add a phrase to constrain point in time(P585)
        :param entity: require time of which variable
        :param new_var: the variable represent the time
        '''
        entity = self.__check_ent_format(entity)
        new_var = self.__check_ent_format(new_var)

        entity_with_prefix = 'wd:' + entity if entity[0] == 'Q' else entity
        self.add_triple_pattern(entity_with_prefix + ' wdt:P585 ' + new_var + '.')
        self.add_triple_pattern('\n')
        return new_var


def digit_or_var(para):
    '''
    normalize digit, variable and entity
    :param para: 　 digit, entity 　 mathematical expression, variable
    '''
    para=str(para).strip()
    # digit or digit in string
    if re.match('^(\-|\+)?\d+(\.\d+)?$', para):
        if para[0]=='-':
            para='('+para+')'
        if para[0]=='+' :
            para=para[1:]
    # mathematical expression
    elif para.startswith('(') or para.startswith('(') or \
            para.startswith('ceil') or para.startswith('floor') or \
            para.startswith('YEAR') or para.startswith('MONTH') or  \
            para.startswith('ABS') or\
            ' * ' in para or ' + ' in para or ' - ' in para or ' / ' in para:
        return para
    # literal(time or digit)
    elif '^^xsd:'  in para:
        return para
    # variable
    elif para[0]=='?':
        return para
    # wd:QID
    elif para.startswith('wd:Q'):
        return para
    # QID
    elif re.match('^Q\d+$', para):
        return 'wd:'+para
    # not digit or expression, regard as variable
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
    # convert to standard time format
    year=str(year).strip()
    month=str(month).strip()
    day=str(day).strip()

    if re.match('^\d+$',year) and re.match('^\d+$',month) and re.match('^\d+$',day):
        if int(month)<10:
            month='0'+month
        if int(day)<10:
            day='0'+day
        return '"'+str(year)+'-'+str(month)+'-'+str(day)+'T00:00:00Z"^^xsd:dateTime'
    else:
        raise ValueError("parameter must be digit or digit in string!")
