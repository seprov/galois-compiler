from collections import deque
            
def test_printer(node, parent, depth, data = None):
    print("  "*depth, node, node.data, parent)

class TNode(object):
    def __init__(self, data, children = None):
        self.data = data
        self.children = children if children else []

    def add_child(self, node):
        self.children.append(node)
        return node

    def __str__(self):
        return "TNode(%s)" % (self.data,)

    __repr__ = __str__

class Tree(object):
    def __init__(self, root_data, root_children = None):
        self.root = TNode(root_data, root_children)
        
    def add_child(self, node):
        return self.root.add_child(node)

    def dfs(self, fn, node = None, parent = None, depth = 0, order = "pre", data = None):
        if node is None: node = self.root

        if depth == 0:
            assert parent is None or node in parent.children

        if order == "pre":
            cont = fn(node, parent, depth, data)
            if cont == False:
                return

        for c in node.children:
            self.dfs(fn, c, node, depth + 1, order, data)

        if order == "post":
            fn(node, parent, depth, data)


    def bfs(self, fn, node = None, parent = None, depth = 0, data = None):
        if node is None: node = self.root

        if depth == 0:
            assert parent is None or node in parent.children

        self.bfs_queue = deque([(node, parent, depth)])

        while len(self.bfs_queue):
            cn, cp, cd = self.bfs_queue.popleft()

            cont = fn(cn, cp, cd, data)
            if cont == False:
                break

            for c in cn.children:
                self.bfs_queue.append((c, cn, cd + 1))

    def dump(self, fn = test_printer):
        self.bfs(fn)


if __name__ == "__main__":
    a = Tree("a")
    b = a.add_child(TNode("b"))
    c = a.add_child(TNode("c"))
    bd = b.add_child(TNode("bd"))
    ce = c.add_child(TNode("ce"))

    print("DFS")
    a.dfs(test_printer)

    print("BFS")
    a.bfs(test_printer)
