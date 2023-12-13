import pyodbc


class ODBC_Executor:
    def __init__(self, query_host, local, timeout:int):
        conn_arg = ''
        conn_arg += 'DRIVER=/usr/local/lib/virtodbc.so;'
        conn_arg += 'Host='+ query_host+";"
        conn_arg += 'UID=dba;PWD=dba'
        self.local = local
        self.odbc_conn = None
        self.initial_connect(conn_arg, timeout)


    def initial_connect(self, conn_arg, timeout):
        self.odbc_conn = pyodbc.connect(
           conn_arg
        )
        self.odbc_conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf8')
        self.odbc_conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf8')
        self.odbc_conn.setencoding(encoding='utf8')
        self.odbc_conn.timeout = timeout # TODO: 这里修改了 timeout, 注意最终的数据集中，涉及 SPARQL 的地方，timeout 应该是一致的
        # print(f"timeout is set to {timeout}")
        print('Wikidata Virtuoso ODBC connected')

    def query(self, sparql):
        pass


class ODBC_WDexecutor(ODBC_Executor):
    def __init__(self, query_host = "114.212.81.217:1115", local=True, timeout = 10):
        super().__init__(query_host, local, timeout)
        #测试查询
        test_sparql = """
        select distinct ?Label
        where{
            wd:Q753165 rdfs:label ?Label.
            filter(lang(?Label) = 'en').
        }
        """
        print("[TEST]the name of wd:Q753165 is", self.query(test_sparql)['result'])

    def query(self, sparql: str):
        if self.local:
            prefix=("""  
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
            """)
            sparql = "SPARQL \n"+ prefix + sparql
        else:
            sparql = "SPARQL \n" + sparql
        result_list = list()
        try:
            with self.odbc_conn.cursor() as cursor:
                cursor.execute(sparql)
                rows = cursor.fetchall()
        except Exception as e:
            print(e)
            print(sparql)
            return {"result":None, "error":e}
        for row in rows:
            result_list.append(row[0])
        return {"result":result_list, "error":None}
    
if __name__ == "__main__":
    executor = ODBC_WDexecutor()
    