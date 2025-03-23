"""
Create a class that implements a data structure that acts as a Least Recently Used (LRU) cache. The cache should allow for O(1) fetching and adding operations.

Requirements:

The class should have methods get(key) and put(key, value).

If the number of elements exceeds a specified limit, the longest unused element should be removed.

Ensure that the operations are optimized for time complexity.
"""

size = 3


class NodeL:
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  


        self.head = NodeL()  
        self.tail = NodeL()
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def add(self,node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node
    def remove(self,node):
        prev = node.prev
        next = node.next
        prev.next = next
        next.prev = prev
        del self.cache[node.key]
        
    def Show(self):
        print("Show cache:")
        for k, v in self.cache.items():
            print(k, v.value)
        print()
        
    def get(self, key: int) -> int:
        print(self.cache[key].value)
        
    def put(self, key: int, value: int) -> None:
        node = NodeL(key, value)
        self.cache[key] = node
        self.add(node)
        if len(self.cache) > self.capacity:
            self.remove(self.tail.prev)
            
            
cache = LRUCache(size)

cache.Show()
cache.put(1, 1)
cache.Show()
cache.put(2, 2)
cache.Show()
cache.get(1)
cache.put(3,15)
cache.Show()
cache.get(3)
cache.put(2, 4)
cache.Show()