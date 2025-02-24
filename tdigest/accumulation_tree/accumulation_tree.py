from __future__ import absolute_import
from .abctree import ABCTree
import operator

class Node:
    # cdef readonly object key
    # cdef readonly object value
    # cdef readonly Node left
    # cdef readonly Node right
    # cdef object accumulation
    # cdef int red
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.red = True
        self.left = None
        self.right = None

    def free(self):
        self.left = None
        self.right = None
        self.key = None
        self.value = None

    def get(self, key: int):
        return self.left if key == 0 else self.right

    def set(self, key: int, value: 'Node') -> None:
        if key == 0:
            self.left = value
        else:
            self.right = value

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)


def is_red(node: Node) -> bool:
    if (node is not None) and node.red:
        return True
    else:
        return False

class NullKey:
    pass

null_key = NullKey()

class _RBTree(object):
    # cdef public Node _root
    # cdef public int _count
    def __int__(self):
        self._count: int = 0
        self._root: Node = None

    def _new_node(self, key, value) -> Node:
        self._count += 1
        return Node(key, value)

    @staticmethod
    def set(node: Node, direction: int, child_node: Node):
        node.set(direction, child_node)

    def insert(self, key, value):
        if self._root is None:  # Empty tree case
            self._root = self._new_node(key, value)
            self._root.red = False  # make root black
            return

        head: Node = Node(key=null_key)  # False tree root
        grand_parent: Node = None
        grand_grand_parent: Node = head
        parent: Node = None  # parent
        direction: int = 0
        last: int = 0

        # Set up helpers
        grand_grand_parent.right = self._root
        node: Node = grand_grand_parent.right
        # Search down the tree
        while True:
            if node is None:  # Insert new node at the bottom
                node = self._new_node(key, value)
                self.set(parent, direction, node)
            elif is_red(node.left) and is_red(node.right):  # Color flip
                node.red = True
                node.left.red = False
                node.right.red = False

            # Fix red violation
            if is_red(node) and is_red(parent):
                direction2 = 1 if grand_grand_parent.right is grand_parent else 0
                if node is parent.get(last):
                    self.set(grand_grand_parent, direction2, self.jsw_single(grand_parent, 1 - last))
                else:
                    self.set(grand_grand_parent, direction2, self.jsw_double(grand_parent, 1 - last))

            # Stop if found
            if key == node.key:
                node.value = value  # set new value for key
                break

            last = direction
            direction = 0 if key < node.key else 1
            # Update helpers
            if grand_parent is not None:
                grand_grand_parent = grand_parent
            grand_parent = parent
            parent = node
            node = node.get(direction)

        self._root = head.right  # Update root
        self._root.red = False   # make root black

    def remove(self, key):
        if self._root is None:
            raise KeyError(str(key))
        head: Node = Node(key=null_key)  # False tree root
        node: Node = head
        node.right = self._root
        parent: Node = None
        grand_parent: Node = None
        found: Node = None  # Found item
        direction: int = 1

        # Search and push a red down
        while node.get(direction) is not None:
            last = direction

            # Update helpers
            grand_parent = parent
            parent = node
            node = node.get(direction)

            direction = 1 if key > node.key else 0

            # Save found node
            if key == node.key:
                found = node

            # Push the red node down
            if not is_red(node) and not is_red(node.get(direction)):
                if is_red(node.get(1 - direction)):
                    self.set(parent, last, self.jsw_single(node, direction))
                    parent = parent.get(last)
                elif not is_red(node.get(1 - direction)):
                    sibling = parent.get(1 - last)
                    if sibling is not None:
                        if (not is_red(sibling.get(1 - last))) and (not is_red(sibling.get(last))):
                            # Color flip
                            parent.red = False
                            sibling.red = True
                            node.red = True
                        else:
                            direction2 = 1 if grand_parent.right is parent else 0
                            if is_red(sibling.get(last)):
                                self.set(grand_parent, direction2, self.jsw_double(parent, last))
                            elif is_red(sibling.get(1-last)):
                                self.set(grand_parent, direction2, self.jsw_single(parent, last))
                            # Ensure correct coloring
                            grand_parent.get(direction2).red = True
                            node.red = True
                            grand_parent.get(direction2).left.red = False
                            grand_parent.get(direction2).right.red = False

        # Replace and remove if found
        if found is not None:
            found.key = node.key
            found.value = node.value
            self.set(parent, int(parent.right is node), node.get(int(node.left is None)))
            node.free()
            self._count -= 1

        # Update root and make it black
        self._root = head.right
        if self._root is not None:
            self._root.red = False
        if not found:
            raise KeyError(str(key))

    def jsw_single(self, root: Node, direction: int) -> Node:
        other_side: int = 1 - direction
        save: Node = root.get(other_side)
        self.set(root, other_side, save.get(direction))
        self.set(save, direction, root)
        root.red = True
        save.red = False
        return save


    def sw_double(self, root: Node, direction: int):
        other_side = 1 - direction
        self.set(root, other_side, self.jsw_single(root.get(other_side), other_side))
        return self.jsw_single(root, direction)

    def __getstate__(self):
        return { 'payload': {k: v for k, v in self.items()} }

    def __setstate__(self, state):
        self._count = 0
        self._root = None
        for k, v in state['payload'].items():
            self.insert(k, v)

class RBTree(_RBTree, ABCTree):
    pass

class _AccumulationTree(_RBTree):
    # cdef object _zero
    # cdef object _mapper
    # cdef object _reducer
    # cdef set _dirty_nodes

    def __init__(self, mapper, reducer=operator.add, zero=0):
        _RBTree.__init__(self)
        self._zero = zero
        self._mapper = mapper
        self._reducer = reducer
        self._dirty_nodes = set()

    def _new_node(self, key, value) -> Node:
        """Create a new tree node."""
        node: Node = _RBTree._new_node(self, key, value)
        node.accumulation = self._mapper(value)
        return node

    def set(self, node: Node, direction: int, child_node: Node) -> None:
        if node.key is not null_key:
            self._dirty_nodes.add(node.key)
        node.set(direction, child_node)

    def insert(self, key, value):
        try:
            self._dirty_nodes.add(key)
            RBTree.insert(self, key, value)
        finally:
            self._update_dirty_nodes()

    def remove(self, key):
        try:
            RBTree.remove(self, key)
        finally:
            self._update_dirty_nodes()

    def _get_full_accumulation(self, node: Node):
        if node is None:
            return self._zero
        else:
            return node.accumulation

    def _get_right_accumulation(self, node: Node, lower):
        if node is None:
            return self._zero
        if lower <= node.key:
            return self._reducer(
                self._reducer(
                    self._get_right_accumulation(node.left, lower),
                    self._get_full_accumulation(node.right),
                ),
                self._mapper(node.value),
            )
        else:
            return self._get_right_accumulation(node.right, lower)

    def _get_left_accumulation(self, node: Node, upper):
        if node is None:
            return self._zero
        if upper > node.key:
            return self._reducer(
                self._reducer(
                    self._get_full_accumulation(node.left),
                    self._get_left_accumulation(node.right, upper),
                ),
                self._mapper(node.value),
            )
        else:
            return self._get_left_accumulation(node.left, upper)

    def _get_accumulation(self, node: Node, lower, upper):
        if node is None or lower >= upper:
            return self._zero
        if node.key < lower:
            return self._get_accumulation(node.right, lower, upper)
        if node.key >= upper:
            return self._get_accumulation(node.left, lower, upper)
        return self._reducer(
            self._reducer(
                self._get_right_accumulation(node.left, lower),
                self._get_left_accumulation(node.right, upper),
            ),
            self._mapper(node.value),
        )

    def get_accumulation(self, lower, upper):
        return self._get_accumulation(self._root, lower, upper)

    def get_left_accumulation(self, upper):
        return self._get_left_accumulation(self._root, upper)

    def get_right_accumulation(self, lower):
        return self._get_right_accumulation(self._root, lower)

    def get_full_accumulation(self):
        return self._get_full_accumulation(self._root)

    def _update_dirty_nodes(self) -> None:
        for key in self._dirty_nodes:
            path = self._path_to_key(key)
            self._update_accumulation(path)
        self._dirty_nodes.clear()

    def _path_to_key(self, key) -> list:
        path = []
        node: Node = self._root
        while True:
            if node is None:
                break
            path.append(node)
            if node.key == key:
                break
            elif node.key < key:
                node = node.right
            else:
                node = node.left
        return path

    def _update_accumulation(self, nodes) -> None:
        # cdef Node x
        for node in reversed(nodes):
            x = node.copy() # TODO: check if copy is needed here
            if x.left is not None and x.right is not None:
                x.accumulation = self._reducer(
                    self._reducer(
                        x.left.accumulation,
                        x.right.accumulation,
                    ),
                    self._mapper(x.value),
                )
            elif x.left is not None:
                x.accumulation = self._reducer(
                    x.left.accumulation,
                    self._mapper(x.value),
                )
            elif x.right is not None:
                x.accumulation = self._reducer(
                    x.right.accumulation,
                    self._mapper(x.value),
                )
            else:
                x.accumulation = self._mapper(x.value)

    def __getstate__(self):
        state = _RBTree.__getstate__(self)
        state['mapper'] = self._mapper
        state['reducer'] = self._reducer
        state['zero'] = self._zero
        return state

    def __setstate__(self, state):
        self._dirty_nodes = set()
        self._mapper = state.pop('mapper')
        self._reducer = state.pop('reducer')
        self._zero = state.pop('zero')
        _RBTree.__setstate__(self, state)

class AccumulationTree(_AccumulationTree, ABCTree):
    pass

