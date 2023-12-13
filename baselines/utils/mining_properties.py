
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import random
from urllib.error import URLError

wikidata_endpoint = "https://query.wikidata.org/sparql"

def remove_prefix(uri):
    return uri.split("/")[-1]


def mining_on_specific_class(target_entities_qid:list=None, class_qid = None, class_name = "New"):
    mining_result = []
    sparql_wrapper = SPARQLWrapper(wikidata_endpoint)
    sparql_wrapper.setReturnFormat(JSON)
    if target_entities_qid is None and class_qid is None:
        print("Error, at least one of 2 qids must have value")
        return 
    if class_qid is not None:
        class_qid = remove_prefix(class_qid)
    elif target_entities_qid is not None:
        possible_classes = []
        existing_classes = {}
        for entity_qid in target_entities_qid:
            entity_qid = remove_prefix(entity_qid)
            sparql_wrapper.setQuery("""
            select ?class  ?classLabel
            where{
                """+ "wd:"+entity_qid + " wdt:P31" +  """ ?class. 
                SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
            }
            """)
            for res in sparql_wrapper.query().convert()['results']['bindings']:
                if remove_prefix(res['class']['value']) not in existing_classes:        #counting occurance of these classes
                    existing_classes[remove_prefix(res['class']['value'])] = 1
                else:
                    existing_classes[remove_prefix(res['class']['value'])] += 1
        for key in existing_classes:
            if existing_classes[key] == len(target_entities_qid):   #all entitys are instance of this type
                possible_classes.append(key)
        final_class = prune_superclasses(possible_classes)      #find the lowest common class
        class_qid = final_class
        if class_qid is None:
            return
    items_in_category = []
    #get all entities that are instance of this class
    print(class_qid)
    sparql_wrapper.setQuery("""
    select ?s  ?sLabel
    where{
        ?s wdt:P31 """ + "wd:" + class_qid +  """ 
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    """)
    print("mining on class:", class_qid)
    possible_properties = {}
    property_labels = {}
    #get some common properties.
    #first, find some 'big' nodes via wikibase:statements.
    big_nodes =[]
    sparql_wrapper.setQuery(
    """
    select ?s ?sLabel ?num
    where{
    ?s wdt:P31 """ + "wd:"+class_qid+ """. 
    ?s wikibase:statements ?num.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    order by desc(?num)
    """)
    res_order_by_number_of_statements = sparql_wrapper.query().convert()['results']['bindings']
    for res in res_order_by_number_of_statements[0:30]:
        if remove_prefix(res['s']['value']) not in big_nodes and res['s']['type']=='uri':
            big_nodes.append(remove_prefix(res['s']['value']))
    print("finding these big entities:",big_nodes)
    for qid in big_nodes:
        sparql_wrapper.setQuery("""
        select distinct ?pt  ?pLabel
        where{
            wd:"""+qid+ """ ?pt ?o.
            ?p wikibase:directClaim ?pt.
            SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        """)
        for res in sparql_wrapper.query().convert()['results']['bindings']:
            property = remove_prefix(res['pt']['value'])    #get all properties linked to countries
            if property.startswith("P") and property not in property_labels:
                property_labels[property] = res['pLabel']['value']
        print("now we have", len(property_labels), "properties")
    #second, find all entities of this class and rank by popularity desc.
    for res in res_order_by_number_of_statements:
        items_in_category.append([res['sLabel']['value'], remove_prefix(res['s']['value']) ])
    number_of_item = len(items_in_category)
    print("mining properties -- totally", number_of_item," entities are of this type, and", len(property_labels), "properties")
    #sampling.
    select_num = min(100, int((len(items_in_category))))
    #selected_items = random.choices(items_in_category, k=select_num) #random select some entities in these classes
    selected_items = items_in_category[0:select_num]
    print("random sampling", select_num, "entities")
    cnt = 0
    #check each property.
    for property in property_labels:
        cnt +=1 
        print("progress:", cnt, "/", len(property_labels))
        exist_count = 0
        total_linked_num = 0
        try:
            sparql_wrapper.setQuery("""
            select ?s ?o
            where{"""
            +   " ?s " + " wdt:P31 " + " wd:" + class_qid +"."
            +   " ?s " + " wdt:"+property + " ?o.} "
            )
            result = sparql_wrapper.query().convert()['results']['bindings']
            result_num = len(result)
            if result_num > 0:
                #check result type
                # url -> must be a Qxxxxx           
                if result[0]['o']['type'] == 'uri':
                    if not result[0]['o']['value'].split("/")[-1].startswith("Q"):      #if result contains non-item 
                        print("this property's return value is not an wikidata item or number.")
                        print("----------------------------------")
                        continue       #   skip this property
                # literal -> must be a decimal number
                elif not 'datatype' in result[0]['o'] or result[0]['o']['datatype'] != "http://www.w3.org/2001/XMLSchema#decimal":
                    print("this property's return value is not an wikidata item or number.")
                    print("----------------------------------")
                    continue
            counting_dict = {}
            for item in selected_items:
                counting_dict[item[1]] = 0    #[occurance, sum of number of objects]
            for res in result:
                if remove_prefix(res['s']['value']) in counting_dict: #an (s, v, o)
                    counting_dict[remove_prefix(res['s']['value'])] += 1
        except URLError:
            print("urlerror")
        #calculating statistics
        total_linked_num = 0
        for key in counting_dict:
            if counting_dict[key] > 0:
                exist_count += 1
                total_linked_num += counting_dict[key]
        existence_ratio = exist_count/len(selected_items)
        if exist_count > 0:
            avg_set_size = total_linked_num/exist_count
        else:
            avg_set_size = 0
        print("current property", property, "label:", property_labels[property])
        print("exist percentage", existence_ratio)
        print("average set size", avg_set_size)
        print("-----------------------------------------------------------------------")
        property_item = {}
        property_item['property'] = [property, property_labels[property]]
        property_item['existence_ratio'] = existence_ratio
        property_item['avg_object_set_size'] = avg_set_size
        mining_result.append(property_item)
    mining_result.sort(key = lambda i:i['existence_ratio'], reverse=True)       #可以选择以出现频率（existenct ratio）或以平均宾语数量排序
    with open("result_"+class_name+".json","w") as f:
        json.dump(mining_result, f, indent=1)



def prune_superclasses(classes:list, thresold = 50):
    sparql = SPARQLWrapper(wikidata_endpoint)
    print("----------pruning classes----------------")
    print("possible_classes are,",classes)
    sparql.setReturnFormat(JSON)
    final_results = []
    abundant_classes = [] 
    cnt = 1
    #first, delete classes with instances less than thresold 50.
    freq_of_classes = {}
    for c in classes:
        sparql.setQuery("""
        select (COUNT(?s) AS ?num)
        where{
            ?s wdt:P31""" + " wd:" + c+ """.
        }
        """
        )
        freq =  int(sparql.query().convert()['results']['bindings'][0]['num']['value'])
        freq_of_classes[c] = freq
        if freq >= thresold:
            abundant_classes.append(c)
    print("possible classes with more than (thresold) instances",abundant_classes)
    if len(abundant_classes) == 0:  #if none of the classes has instances more than thresold, we consider all original classes.
        abundant_classes = classes
        print("[WARN] no class having more instances than the thresold found. Consider all class instead.")
    for class_qid in abundant_classes:
        print("checking", class_qid, "progress", cnt, "/", len(abundant_classes))
        cnt += 1
        throw = False
        #if it is superclass of another result, throw it
        try:
            sparql.setQuery("""
            select ?s ?sLabel
            where{
            """ + "?s wdt:P279 wd:" +class_qid+ """. 
            SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
            }
            """
            )
            for res in sparql.query().convert()['results']['bindings']:
                if  remove_prefix(res['s']['value']) in abundant_classes:
                    print(res['sLabel']['value'], "is a subclass of", class_qid,"throw",class_qid)
                    throw = True
                    break
            if not throw:                    
                final_results.append([class_qid, freq_of_classes[class_qid]])
        except URLError:
            print("urlerror")
    if len(final_results) > 1:
        final_results.sort(key=lambda i: i[1])
        print("[WARN]There exists more than one leave classes, they are:", print(final_results))
        print("select class with the least instances among them")
    print("------------------------ ---------------")
    if len(final_results) == 0:
        print('[ERROR] No possible class find.')
        return None
    else:
        return final_results[0][0]


entities = ['Q1463050','Q1634161']
mining_on_specific_class(target_entities_qid= entities,class_name='tesla')
#可以选择使用某个类型的qid查询，也可以选择使用某些实体查询（会计算它们的适当公共类型）。class_name仅用于标记输出文件名
#prune_superclasses中的thresold为可调参数，同时可以调整采样方法（包括采样Property和采样selected_item）