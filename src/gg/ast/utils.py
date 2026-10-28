class Stack(object):
    def __init__(self):
        self.stk = []
    
    def push(self, val):
        self.stk.append(val)

    def pop(self):
        return self.stk.pop()

    def clear(self):
        self.stk = []

    @property
    def top(self):
        return self.stk[-1]

    @top.setter
    def top(self, value):
        if len(self.stk):
            self.stk[-1] = value
        else:
            raise IndexError("Stack is empty")

    def empty(self):
        return len(self.stk) == 0

    def __len__(self):
        return len(self.stk)

    def __iter__(self):
        return iter(self.stk)

    def __reversed__(self):
        return reversed(self.stk)

    def __str__(self):
        return str(self.stk)
