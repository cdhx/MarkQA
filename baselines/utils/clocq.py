import json
import pickle
import random
import re
import time
import requests


class CLOCQInterfaceClient:
    def __init__(self, host="http://localhost", port="7777"):
        self.host = host
        self.port = port
        self.req = requests.Session()
        self.ENTITY_PATTERN = re.compile("^Q[0-9]+$")
        self.PRED_PATTERN = re.compile("^P[0-9]+$")

    def get_label(self, kb_item):
        """
        Retrieves a single label for the given KB item.
        E.g. "France national association football team" for "Q47774".

        Note: The n-triples Wikidata dump stores multiple labels (not aliases) for the same item.
        Here, we return the first KB label which is not exactly the KB item id (i.e. "Q47774").
        Shown as "Label" in Wikidata.
        """
        params = {"item": kb_item}
        res = self._req("/item_to_label", params)
        json_string = res.content.decode("utf-8")
        try:
            label = json.loads(json_string).encode('utf-8').decode('unicode_escape')
        except:
            label = json.loads(json_string)
        return label

    def get_aliases(self, kb_item):
        """
        Retrieves the aliases for the given KB item.
        E.g. "France" for "Q47774".
        Shown as "Also known as" in Wikidata.
        """
        params = {"item": kb_item}
        res = self._req("/item_to_aliases", params)
        json_string = res.content.decode("utf-8")
        aliases = json.loads(json_string)
        return aliases

    def get_description(self, kb_item):
        """
        Retrieves the description for the given KB item.
        The descriptions can be seen on top of Wikidata pages.
        E.g. "men's national association football team representing France" for "Q47774".
        Shown as "Description" in Wikidata.
        """
        params = {"item": kb_item}
        res = self._req("/item_to_description", params)
        json_string = res.content.decode("utf-8")
        aliases = json.loads(json_string)
        return aliases

    def get_types(self, kb_item):
        """
        Retrieves the types for the given KB item.
        Returns list of items with keys: {"id", "label"}.
        E.g. {"id": "Q6979593", "label": "national association football team"} for "Q47774".
        """
        params = {"item": kb_item}
        res = self._req("/item_to_types", params)
        json_string = res.content.decode("utf-8")
        types = json.loads(json_string)
        return types
    
    def get_most_frequent_type(self, kb_item):
        """
        Retrieves the types for the given KB item.
        Returns list of items with keys: {"id", "label"}.
        E.g. {"id": "Q6979593", "label": "national association football team"} for "Q47774".
        """
        params = {"item": kb_item}
        res = self._req("/item_to_type", params)
        json_string = res.content.decode("utf-8")
        types = json.loads(json_string)
        return types


    def get_frequency(self, kb_item):
        """
        A list of two frequency numbers for the given KB item:
        - number of facts with the item occuring as subject
        - number of facts with the item occuring as object/qualifier-object.
        """
        params = {"item": kb_item}
        res = self._req("/frequency", params)
        json_string = res.content.decode("utf-8")
        frequencies = json.loads(json_string)
        return frequencies


    def get_neighborhood(self, kb_item, p=1000, include_labels=True):
        """
        Returns a list of facts including the item (the 1-hop neighborhood)
        each fact is a n-tuple, with subject, predicate, object and qualifier information.
        """
        params = {"item": kb_item, "p": p, "include_labels": include_labels}
        res = self._req("/neighborhood", params)
        json_string = res.content.decode("utf-8")
        neighbors = json.loads(json_string)
        return neighbors

    def get_neighborhood_two_hop(self, kb_item, p=1000, include_labels=True):
        """
        Returns a list of facts in the 2-hop neighborhood of the item
        each fact is a n-tuple, with subject, predicate, object and qualifier information.
        """
        params = {"item": kb_item, "p": p, "include_labels": include_labels}
        res = self._req("/two_hop_neighborhood", params)
        json_string = res.content.decode("utf-8")
        neighbors = json.loads(json_string)
        return neighbors

    def connect(self, kb_item1, kb_item2):
        """
        Returns a list of paths between item1 and item2. Each path is given by either 1 fact
        (1-hop connection) or 2 facts (2-hop connections).
        """
        params = {"item1": kb_item1, "item2": kb_item2}
        res = self._req("/connect", params)
        json_string = res.content.decode("utf-8")
        paths = json.loads(json_string)
        return paths

    def connectivity_check(self, kb_item1, kb_item2):
        """
        Returns the distance of the two items in the graph, given a fact-based definition.
        Returns 1 if the items are within 1 hop of each other,
        Returns 0.5 if the items are within 2 hops of each other,
        and returns 0 otherwise.
        """
        params = {"item1": kb_item1, "item2": kb_item2}
        res = self._req("/connectivity_check", params)
        connectivity = float(res.content)
        return connectivity

    def get_search_space(self, question, parameters=dict(), include_labels=True):
        """
        Extract a question-specific context for the given question using the CLOCQ algorithm.
        Returns k (context tuple, context graph)-pairs for the given questions,
        i.e. a mapping of question words to KB items and a question-relevant KG subset.
        In case the dict is empty, the default CLOCQ parameters are used
        """
        params = {"question": question, "parameters": parameters, "include_labels": include_labels}
        res = self._req("/search_space", params)
        json_string = res.content.decode("utf-8")
        result = json.loads(json_string)
        return result

    def is_wikidata_entity(self, string):
        """
        Check whether the given string can be a wikidata entity.
        """
        return self.ENTITY_PATTERN.match(string) is not None

    def is_wikidata_predicate(self, string):
        """
        Check whether the given string can be a wikidata predicate.
        """
        return self.PRED_PATTERN.match(string) is not None

    def _req(self, action, json):
        if self.port == "443":
            return self.req.post(self.host + action, json=json)
        else:
            return self.req.post(self.host + ":" + self.port + action, json=json)


"""
MAIN
"""
if __name__ == "__main__":
    """ 
    Note that this API should not be used to evaluate efficiency of CLOCQ,
    since the current setup is not optimized e.g. for multiple simultaneous requests.
    """
    clocq = CLOCQInterfaceClient(host="https://clocq.mpi-inf.mpg.de/api", port="443")

    ### Find some example usages below.
    kb_item1 = "Q38111" # Leonardo DiCaprio
    kb_item2 = "Q25191" # Chritopher Nolan
    question = "Character played by DiCaprio in Inception?"

    # retrieve label
    res = clocq.get_label(kb_item1)
    print("Label", res)
    print("\n")

    # retrieve aliases
    res = clocq.get_aliases(kb_item1)
    print("Aliases", res)
    print("\n")

    # retrieve neighborhood
    res = clocq.get_neighborhood(kb_item1)
    for fact in res:
        print("First fact", fact, "...skipping remaining facts in code")
        break
    print("\n")

    # perform connectivity check
    res = clocq.connectivity_check(kb_item1, kb_item2)
    print("Connectivity", res)
    print("\n")

    # connect KB-items in graph
    res = clocq.connect(kb_item1, kb_item2)
    print("Connections", res)
    print("\n")

    # clocq main functionality
    res = clocq.get_search_space(question)
    kb_items = res["kb_item_tuple"]
    search_space = res["search_space"]
    print("Disambiguations", kb_items)
    print("\n")
    for fact in search_space:
        print("First fact", fact, "...skipping remaining facts in code")
        break
    print("\n")