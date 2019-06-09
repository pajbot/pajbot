from __future__ import print_function

import logging
import re

from pajbot.managers.handler import HandlerManager
from pajbot.modules import BaseModule

END_OF_STRING = 99999999
log = logging.getLogger(__name__)


class SuffixTreeNode:
    """
    Suffix tree node class. Actually, it also respresents a tree edge that points to this node.
    """

    new_identifier = 0

    def __init__(self, start=0, end=END_OF_STRING):
        self.identifier = SuffixTreeNode.new_identifier
        SuffixTreeNode.new_identifier += 1

        # suffix link is required by Ukkonen's algorithm
        self.suffix_link = None

        # child edges/nodes, each dict key represents the first letter of an edge
        self.edges = {}

        # stores reference to parent
        self.parent = None

        # bit vector shows to which strings this node belongs
        self.bit_vector = 0

        # edge info: start index and end index
        self.start = start
        self.end = end

    def add_child(self, key, start, end):
        """
        Create a new child node
        Agrs:
            key: a char that will be used during active edge searching
            start, end: node's edge start and end indices
        Returns:
            created child node
        """
        child = SuffixTreeNode(start=start, end=end)
        child.parent = self
        self.edges[key] = child
        return child

    def add_exisiting_node_as_child(self, key, node):
        """
        Add an existing node as a child
        Args:
            key: a char that will be used during active edge searching
            node: a node that will be added as a child
        """
        node.parent = self
        self.edges[key] = node

    def get_edge_length(self, current_index):
        """
        Get length of an edge that points to this node
        Args:
            current_index: index of current processing symbol (usefull for leaf nodes that have "infinity" end index)
        """
        return min(self.end, current_index + 1) - self.start

    def __str__(self):
        return "id=" + str(self.identifier)


class SuffixTree:
    """
    Generalized suffix tree
    """

    def __init__(self):
        # the root node
        self.root = SuffixTreeNode()

        # all strings are concatenaited together. Tree's nodes stores only indices
        self.input_string = ""

        # number of strings stored by this tree
        self.strings_count = 0

        # list of tree leaves
        self.leaves = []

    def append_string(self, input_string):
        """
        Add new string to the suffix tree
        """
        start_index = len(self.input_string)
        current_string_index = self.strings_count

        # each sting should have a unique ending
        input_string += "$" + str(current_string_index)

        # gathering 'em all together
        self.input_string += input_string
        self.strings_count += 1

        # these 3 variables represents current "active point"
        active_node = self.root
        active_edge = 0
        active_length = 0

        # shows how many
        remainder = 0

        # new leaves appended to tree
        new_leaves = []

        # main circle
        for index in range(start_index, len(self.input_string)):
            previous_node = None
            remainder += 1
            while remainder > 0:
                if active_length == 0:
                    active_edge = index

                if self.input_string[active_edge] not in active_node.edges:
                    # no edge starting with current char, so creating a new leaf node
                    leaf_node = active_node.add_child(self.input_string[active_edge], index, END_OF_STRING)

                    # a leaf node will always be leaf node belonging to only one string
                    # (because each string has different termination)
                    leaf_node.bit_vector = 1 << current_string_index
                    new_leaves.append(leaf_node)

                    # doing suffix link magic
                    if previous_node is not None:
                        previous_node.suffix_link = active_node
                    previous_node = active_node
                else:
                    # ok, we've got an active edge
                    next_node = active_node.edges[self.input_string[active_edge]]

                    # walking down through edges (if active_length is bigger than edge length)
                    next_edge_length = next_node.get_edge_length(index)
                    if active_length >= next_node.get_edge_length(index):
                        active_edge += next_edge_length
                        active_length -= next_edge_length
                        active_node = next_node
                        continue

                    # current edge already contains the suffix we need to insert.
                    # Increase the active_length and go forward
                    if self.input_string[next_node.start + active_length] == self.input_string[index]:
                        active_length += 1
                        if previous_node is not None:
                            previous_node.suffix_link = active_node
                        previous_node = active_node
                        break

                    # splitting edge
                    split_node = active_node.add_child(
                        self.input_string[active_edge], next_node.start, next_node.start + active_length
                    )
                    next_node.start += active_length
                    split_node.add_exisiting_node_as_child(self.input_string[next_node.start], next_node)
                    leaf_node = split_node.add_child(self.input_string[index], index, END_OF_STRING)
                    leaf_node.bit_vector = 1 << current_string_index
                    new_leaves.append(leaf_node)

                    # suffix link magic again
                    if previous_node is not None:
                        previous_node.suffix_link = split_node
                    previous_node = split_node

                remainder -= 1

                # follow suffix link (if exists) or go to root
                if active_node == self.root and active_length > 0:
                    active_length -= 1
                    active_edge = index - remainder + 1
                else:
                    active_node = active_node.suffix_link if active_node.suffix_link is not None else self.root

        # update leaves ends from "infinity" to actual string end
        for leaf in new_leaves:
            leaf.end = len(self.input_string)
        self.leaves.extend(new_leaves)

    def find_longest_common_substrings(self):
        """
        Search longest common substrings in the tree by locating lowest common ancestors what belong to all strings
        """

        # all bits are set
        success_bit_vector = 2 ** self.strings_count - 1

        lowest_common_ancestors = []

        # going up to the root
        for leaf in self.leaves:
            node = leaf
            while node.parent is not None:
                if node.bit_vector != success_bit_vector:
                    # updating parent's bit vector
                    node.parent.bit_vector |= node.bit_vector
                    node = node.parent
                else:
                    # hey, we've found a lowest common ancestor!
                    lowest_common_ancestors.append(node)
                    break

        longest_common_substrings = [""]
        longest_length = 0

        # need to filter the result array and get the longest common strings
        for common_ancestor in lowest_common_ancestors:
            common_substring = ""
            node = common_ancestor
            while node.parent is not None:
                label = self.input_string[node.start : node.end]
                common_substring = label + common_substring
                node = node.parent
            # remove unique endings ($<number>), we don't need them anymore
            common_substring = re.sub(r"(.*?)\$?\d*$", r"\1", common_substring)
            if len(common_substring) > longest_length:
                longest_length = len(common_substring)
                longest_common_substrings = [common_substring]
            elif len(common_substring) == longest_length and common_substring not in longest_common_substrings:
                longest_common_substrings.append(common_substring)

        return longest_common_substrings


def longest_repeated_substring(string):
    length = len(string)
    substr = ""
    repeated_index = -1
    longest_repeated_substr = ""
    # get every possible repeated substring by looping through each beginning
    # character index and incrementing its ending index with each iteration
    for begin in range(length):
        for end in range(begin + 1, length):
            substr_len = end - begin
            remaining_search_len = length - end
            # if the length of the substring is greater than the remaining
            # search length, then it is impossible for that substring and
            # further substrings starting with the beginning character to be
            # repeated
            if substr_len > remaining_search_len:
                break
            else:
                substr = string[begin:end]
                repeated_index = string.find(substr, end, length)
                if repeated_index != -1 and not substr.isspace():
                    if len(substr) > len(longest_repeated_substr):
                        longest_repeated_substr = substr
    if longest_repeated_substr == "":
        return None

    return longest_repeated_substr, string.count(longest_repeated_substr)


class RepspamModule(BaseModule):

    ID = __name__.split(".")[-1]
    NAME = "Repetitive Spam"
    DESCRIPTION = "Looks at each message for repetitive spam"
    ENABLED_DEFAULT = False
    CATEGORY = "Filter"
    SETTINGS = []

    def enable(self, bot):
        HandlerManager.add_handler("on_message", self.on_message, priority=150)

    def disable(self, bot):
        HandlerManager.remove_handler("on_message", self.on_message)

    def on_message(self, source, message, whisper, **rest):
        if whisper:
            return
        if source.level >= 420 or source.moderator:
            return

        suffix_tree = SuffixTree()

        suffix_tree.append_string(message)

        word_freq = []
        word_list = message.split(" ")
        if len(word_list) <= 1:
            # Not enough words to see if it's repetitive this way
            return

        if len(message) < 50:
            # Message too short
            return

        for w in word_list:
            word_freq.append(word_list.count(w))

        word_dict = dict(zip(word_list, word_freq))

        word_freq = [(word_dict[key], key) for key in word_dict]
        word_freq.sort()
        word_freq.reverse()

        if len(word_freq) < 3:
            # There needs to be at least 3 unique words
            return

        if word_freq[0][0] == word_freq[1][0]:
            if word_freq[0][0] > 4:
                log.info("Time out {}".format(message))
                self.bot._timeout(source.username, 10, reason="No repetitive messages OMGScoods")

        log.debug("Word pairs: {}".format(str(word_freq)))
