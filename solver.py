#!/usr/bin/env python
#
# WWF/scrabble solver based on
#  http://www.cs.cmu.edu/afs/cs/academic/class/15451-s06/www/lectures/scrabble.pdf
#  http://ericsink.com/downloads/faster-scrabble-gordon.pdf
#
# python2; see board, words for file formats
#

import sys
import string
import copy
import argparse

class Node(object):
    counter = 0

    def __str__(self):
	return "N" + str(self.number)

    def __init__(self):
	Node.counter += 1
	self.number = Node.counter
	self.edges = {}

    def dump(self, out, seen):
	if self.number in seen:
	    return
	seen.add(self.number)
	for k, v in self.edges.iteritems():
	    v.dump(out, self, seen)

    def add_arc(self, ch):
	if ch not in self.edges:
	    self.edges[ch] = Edge(ch)
	return self.edges[ch].target

    def add_final_arc(self, c1, c2):
	 n = self.add_arc(c1)
	 self.edges[c1].add_letter(c2)
	 return n

    def force_arc(self, ch, fst):
	if ch in self.edges:
	    if self.edges[ch].target != fst:
		print "force_arc error!", fst, self.edges[ch].target, ch
		sys.exit(1)
	else:
	    self.edges[ch] = Edge(ch, fst)
	return self.edges[ch]

class Edge(object):
    def __init__(self, ch, target=None):
	self.ch = ch
	self.letters = set()

	if target == None:
	    target = Node()
	self.target = target
	pass

    def str_letter_set(self):
	rv = ""
	if self.letters and (len(self.letters) > 0):
	    rv = " ["
	    for k in self.letters:
		rv += k
	    rv += "]"
	return rv

    def dump(self, out, source, seen):
	mn = self.ch + self.str_letter_set()
	print >> out, source, "->", self.target, "[label=\"" + mn + '"];'
	self.target.dump(out, seen)

    def add_letter(self, ch):
	self.letters.add(ch)

    def has_letter(self, ch):
	return ch in self.letters

    def next_arc(self, ch):
	if ch in self.target.edges:
	    return self.target.edges[ch]
	return None

class GADDAG(object):
    def __init__(self, wordfile):
	self.count = 0
	self.initialState = Node()
	self.initialArc = Edge('$', self.initialState)
	self.load(wordfile)
	self.all_letters = set()
	for i in string.lowercase:
		self.all_letters.add(i)

    def load(self, wordfile):
	with open(wordfile, 'r') as inp:
	    for line in inp.readlines():
		if line[0].isupper(): # likely proper name, not accepted
		    continue
		self.add_word(line.rstrip().lower())
	print "loaded", self.count, "words"

    def add_word(self, word):
	if len(word) < 2:
	    return

	self.count += 1
	if (self.count % 5000) == 0:
	    print "...", self.count, word

	st = self.initialState
	for i in reversed(range(2, len(word))):
	    st = st.add_arc(word[i])
	st.add_final_arc(word[1], word[0])

	st = self.initialState
	for i in reversed(range(0, len(word) - 1)):
	    st = st.add_arc(word[i])
	st = st.add_final_arc('$', word[-1])

	final_state = st
	for m in reversed(range(1, len(word) - 2 + 1)):
	    force = st
	    st = self.initialState
	    for i in reversed(range(1, m + 1)):
		st = st.add_arc(word[i-1])
	    st = st.add_arc('$')

	    narc = st.force_arc(word[m+1-1], force)
	    if force == final_state:
		narc.add_letter(word[-1])

    def dump(self, fname):
	with open(fname, 'w') as out:
	    seen = set()
	    print >> out,  "digraph {"
	    self.initialState.dump(out, seen)
	    print >> out, "}"

    def lookup_path(self, arc, path):
	for p in path:
	    arc = arc.next_arc(p)
	    if arc == None:
		return None
	return arc

    def is_word(self, word):
	path = word[0] + "$" + word[1:-1]
	arc = self.lookup_path(self.initialArc, path)
	if arc:
	    return arc.has_letter(word[-1])
	return False

    def cross_set_prefix(self, word):
	prefix = set()
	for i in string.lowercase:
	    path = i + "$" + word[:-1]
	    arc = self.lookup_path(self.initialArc, path)
	    if arc and arc.has_letter(word[-1]):
		prefix.add(i)
	return prefix

    def cross_set_suffix(self, word):
	path = word[0] + "$" + word[1:]
	arc = self.lookup_path(self.initialArc, path)
	if arc and arc.letters:
	    return arc.letters
	return set()

    def cross_set_middle(self, prefix, suffix):
	middle = set()
	path = prefix[::-1] + "$"
	arc = self.lookup_path(self.initialArc, path)
	if arc == None:
	    return set()
	for i in string.lowercase:
	    rest = i + suffix[:-1]
	    rarc = self.lookup_path(arc, rest)
	    if rarc and rarc.has_letter(suffix[-1]):
		middle.add(i)
	return middle

    def cross_set(self, left, right):
	if len(left) and len(right):
	    return self.cross_set_middle(left, right)
	elif len(right):
	    return self.cross_set_prefix(right)
	elif len(left):
	    return self.cross_set_suffix(left)
	else:
	    return self.all_letters

class Board(object):
    def __init__(self, fname):
	self.rack = set()
	self.board = []
	self.load(fname)

    def parse_rack(self, line):
	self.rack = list(line.lower())

    def parse_push_row(self, line):
	row = list(line.lower())
	self.board.append(row)

    def load(self, fname):
	with open(fname, 'r') as inp:
	    self.parse_rack(inp.readline().strip())
	    for line in inp.readlines():
		self.parse_push_row(line.strip())

    def rows(self):
	return len(self.board)

    def cols(self):
	return len(self.board[0])

    def get_letter(self, row, col):
	L = self.board[row][col];
	if L == '-':
	    return None
	return L

    def patch(self, a, word):
	for L in word:
	    if self.board[a.row][a.col] == '-':
	        self.board[a.row][a.col] = L
	    a = a.add(1)

    def pretty_print(self):
	for r in self.board:
	    s=""
	    for c in r:
		s += c
		s += " "
	    print s

    def pretty_print_word(self, a, word):
	x = copy.deepcopy(self)
	x.patch(a, word)
	x.pretty_print()

class Anchor(object):
    def __init__(self, row, col, a=0):
	self.row = row
	self.col = col
	self.a = a

    def add(self, pos):
	n = Anchor(self.row, self.col)
	n.a = self.a
	if self.a:
	    n.row += pos
	else:
	    n.col += pos
	return n

    def __str__(self):
	return "<Anchor r:" + str(self.row) + " c:" + str(self.col) + " a:" + str(self.a) + ">"


class Solver(object):
    def __init__(self, board, gaddag):
	self.board = board
	self.gaddag = gaddag
	self.anchor = None
	self.rows = board.rows()
	self.cols = board.cols()
	self.plays = []

    def is_valid_address(self, row, col):
	if (row < 0) or (col < 0) or (row >= self.rows) or (col >= self.cols):
	    return False
	return True

    def test_anchor(self, row, col):
	if self.is_valid_address(row, col):
	    if None != board.get_letter(row, col):
		return True
	return False

    def get_anchors(self):
	anchors = []
	for row in range(0, board.rows()):
	    for col in range(0, board.cols()):
		if None == board.get_letter(row, col):
		    ok = False
		    ok |= self.test_anchor(row, col + 1)
		    ok |= self.test_anchor(row, col - 1)
		    ok |= self.test_anchor(row + 1, col)
		    ok |= self.test_anchor(row - 1, col)
		    if ok:
			anchors.append(Anchor(row, col, 0))
			anchors.append(Anchor(row, col, 1))
	return anchors

    def print_play(self, play):
	print "PLAY:", play[0], play[1], play[2], play[3]

	if play[1] > 0:
	    n = play[0].add(play[1] - len(play[2]) + 1)
	else:
	    n = play[0].add(play[1])

	board.pretty_print_word(n, play[2].upper())

    def solve(self):
	anchors = self.get_anchors()
	self.plays = []
	for self.anchor in anchors:
	    self.gen(0, "", board.rack, gaddag.initialArc)
	for p in sorted(self.plays, key=lambda o: len(o[2])):
	    self.print_play(p)

    def get_letter(self, a):
	return board.get_letter(a.row, a.col)

    def abs_position(self, anchor, pos):
	n = anchor.add(pos)
	if self.is_valid_address(n.row, n.col):
	    return n
	return None

    def get_square_letter(self, pos):
	return self.get_letter(self.abs_position(self.anchor, pos))

    def slurp_direction(self, start, pos, direction, s=""):
	pos += direction

	n = self.abs_position(start, pos)
	if n == None:
	    return s
	L = self.get_letter(n)
	if L == None:
	    return s
	if direction > 0:
	    s += L
	else:
	    s = L + s
	return self.slurp_direction(start, pos, direction, s)

    # anchor + pos, return cross-set
    def get_square_cross_set(self, pos):
	start = self.abs_position(self.anchor, pos)
	start.a ^= 1

	left = self.slurp_direction(start, 0, -1)
	right = self.slurp_direction(start, 0, 1)

	ss = gaddag.cross_set(left, right)

	# if len(left) or len(right):
	#    print start, "left '" + left + "' right '" + right + "' :", ss

	return ss

    # record word at anchor
    def record_play(self, pos, word, remaining_rack):
	played = board.rack[:]
	s = ""
	for i in remaining_rack: played.remove(i)
	for i in played: s += i
	p = [self.anchor, pos, word, s]
	self.plays.append(p)

    # is there an empty square here [anchor + pos] ?
    def is_empty_at(self, pos):
	n = self.abs_position(self.anchor, pos)
	return (n and (None == self.get_letter(n)))

    # [anchor + pos] is empty/edge of board?
    def does_terminate(self, pos):
	n = self.abs_position(self.anchor, pos)
	return (not n or (None == self.get_letter(n)))

    # [anchor + pos] valid board position?
    def can_i_go(self, pos):
	return self.abs_position(self.anchor, pos)

    def gen(self, pos, word, rack, arc):
	# print "GE", self.anchor, pos, word, rack
	L = self.get_square_letter(pos)
	if L != None:
	    self.goon(pos, L, word, rack, arc.next_arc(L), arc)
	elif len(rack):
	    cross_set = self.get_square_cross_set(pos)
	    tried_set = set()

	    for index in range(0, len(rack)):
		new_rack = rack[:]
		L = new_rack[index]
		del new_rack[index]

		if L == '*':
		    for L in (cross_set.difference(tried_set)):
			self.goon(pos, L, word, new_rack, arc.next_arc(L), arc)
			tried_set.add(L)
		elif L in cross_set and L not in tried_set:
		    self.goon(pos, L, word, new_rack, arc.next_arc(L), arc)
		    tried_set.add(L)


    def goon(self, pos, L, word, rack, new_arc, old_arc):
	# print "GO", pos, L, word, rack, new_arc, old_arc
	if pos <= 0:
	    word = L + word
	    if old_arc.has_letter(L) and self.does_terminate(pos - 1) and self.is_empty_at(1):
		self.record_play(pos, word, rack)
	    if new_arc:
		if self.can_i_go(pos - 1):
		    self.gen(pos - 1, word, rack, new_arc)
		new_arc = new_arc.next_arc('$')
		if new_arc and self.does_terminate(pos - 1) and self.can_i_go(1):
		    self.gen(1, word, rack, new_arc)
	else:
	    word = word + L
	    if old_arc.has_letter(L) and self.does_terminate(pos + 1):
		self.record_play(pos, word, rack)
	    if new_arc and self.can_i_go(pos + 1):
		self.gen(pos + 1, word, rack, new_arc)

board = None
gaddag = None

parser = argparse.ArgumentParser()
parser.add_argument("-d", default="words", help="word list", required=False)
parser.add_argument("-b", default="board", help="board", required=False)
parser.add_argument("-W", help="dump GADDAG as dot graph", required=False)
args = parser.parse_args()

gaddag = GADDAG(args.d)
if args.W:
    gaddag.dump(args.W)
    sys.exit(0)

board = Board(args.b)

n = Solver(board, gaddag)
n.solve()
